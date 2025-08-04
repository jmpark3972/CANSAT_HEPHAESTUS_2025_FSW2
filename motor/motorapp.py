

#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""motorapp.py – Payload servo controller service

· Listens on the software bus for **“set‑angle”** commands coming from Flightlogic.
· Drives a hobby‑class servo (PWM) via **pigpio** on GPIO 12.
· Publishes a 1 Hz HK packet.

Message IDs (add to `appargs`)
------------------------------
ThermoCam → Flightlogic already handles the temperature/altitude logic and will
produce a message:
    appargs.FlightlogicAppArg.MID_SetPayloadMotorAngle  # data: "<angle_deg>"
This app must also define its own HK and App IDs:
    appargs.MotorAppArg.AppID / AppName / MID_SendHK

FSW integration checklist
-------------------------
1. `sudo apt install -y pigpio python3-pigpio`
2. `sudo systemctl enable pigpiod --now`
3. Define the missing constants in *appargs.py*.
4. Add MotorApp to the main process spawn list.

"""
from __future__ import annotations

import signal, threading, time
from multiprocessing import Queue, connection

import pigpio


from lib import appargs, events, msgstructure, logging, config  # type: ignore
from motor import motor  # local helper that provides angle_to_pulse()

# ────────────────────────────────────────────
# Global flags & state
# ────────────────────────────────────────────
MOTORAPP_RUNSTATUS = True
CURRENT_ANGLE = 0  # deg – last commanded angle

# Flag that determines the activation of payload motor
PAYLOAD_MOTOR_ENABLE = True

# pigpio handle (initialised in motorapp_init)
pi: pigpio.pi | None = None

# ────────────────────────────────────────────
# Helper: set servo angle safely
# ────────────────────────────────────────────

PAYLOAD_MOTOR_PIN = 12 #motor.PAYLOAD_MOTOR_PIN  # default GPIO 12

def set_servo_pulse(pulse: int) -> None:
    """pulse값(500~2500)을 직접 받아서 모터에 전달"""
    global CURRENT_ANGLE
    if pi is None or not pi.connected:
        raise RuntimeError("pigpio not initialised")
    pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, int(pulse))
    CURRENT_ANGLE = int(pulse)  # 실제 각도와 다르지만, 상태 보고용

# ────────────────────────────────────────────
# Initialisation / termination
# ────────────────────────────────────────────

def motorapp_init() -> None:
    global pi, PAYLOAD_MOTOR_ENABLE
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # parent handles SIGINT

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Initialising motorapp (pigpio)")

    pi = pigpio.pi()
    if not pi.connected:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                        "pigpio daemon not running – aborting")
        raise SystemExit(1)

    # 설정에 따른 초기화
    if config.FSW_CONF == config.CONF_PAYLOAD:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Payload motor standby")
        # 페이로드 모터 초기 위치 설정
        set_servo_pulse(1500)  # 90도 (중립 위치)
    elif config.FSW_CONF == config.CONF_CONTAINER:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Container motor standby")
    elif config.FSW_CONF == config.CONF_ROCKET:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Rocket motor standby")
    else:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "No Valid configuration!")
        PAYLOAD_MOTOR_ENABLE = False

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Motorapp initialised")


def motorapp_terminate() -> None:
    global MOTORAPP_RUNSTATUS, pi
    MOTORAPP_RUNSTATUS = False

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Terminating motorapp - rotating to 180°")

    if pi and pi.connected:
        # 종료 시 모터를 180도로 회전
        pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, 2500)  # 180도 (2500µs)
        time.sleep(1)  # 모터가 회전할 시간을 줌
        pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, 0)  # PWM 정지
        pi.stop()

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        try:
            if not hasattr(thread_dict[thread_name], '_is_resilient') or not thread_dict[thread_name]._is_resilient:
                thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
                if thread_dict[thread_name].is_alive():
                    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.warning, f"Thread {thread_name} did not terminate gracefully")
            else:
                # resilient thread는 자동으로 종료됨
                pass
        except Exception as e:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, f"Error joining thread {thread_name}: {e}")
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

# ────────────────────────────────────────────
# HK sender thread
# ────────────────────────────────────────────

def send_hk(main_q: Queue) -> None:
    """Publish simple heartbeat with current angle every 1 s."""
    hk = msgstructure.MsgStructure()
    while MOTORAPP_RUNSTATUS:
        hk_payload = f"{MOTORAPP_RUNSTATUS},{CURRENT_ANGLE}"
        msgstructure.send_msg(main_q, hk,
                              appargs.MotorAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.MotorAppArg.MID_SendHK,
                              hk_payload)
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not MOTORAPP_RUNSTATUS:
                break
            time.sleep(0.1)

# ────────────────────────────────────────────
# Command handler
# ────────────────────────────────────────────

def command_handler(main_q: Queue, recv: msgstructure.MsgStructure) -> None:
    global MOTORAPP_RUNSTATUS, PAYLOAD_MOTOR_ENABLE

    # Termination from Main
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        MOTORAPP_RUNSTATUS = False
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                        "Termination command received")
        return
	
    # On receiving yaw data
    elif recv.MsgID == appargs.ImuAppArg.MID_SendYawData:
        # Control motor only if config is payload and is activated
        if config.FSW_CONF == config.CONF_PAYLOAD and PAYLOAD_MOTOR_ENABLE == True:
            recv_yaw = float(recv.data)
            # Yaw 데이터를 기반으로 모터 제어 (간단한 예시)
            angle = max(0, min(180, 90 + recv_yaw))  # 90도를 중심으로 ±90도
            pulse = motor.angle_to_pulse(angle)
            set_servo_pulse(pulse)
        else:
            return

    # On rocket motor activation command
    elif recv.MsgID == appargs.FlightlogicAppArg.MID_RocketMotorActivate:
        # This command should only be activated on rocket
        if config.FSW_CONF == config.CONF_ROCKET:
            activaterocketmotor()
        else:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"Not Performing Rocket Motor Activation, current conf : {config.FSW_CONF}")

    # On rocket motor standby command
    elif recv.MsgID == appargs.FlightlogicAppArg.MID_RocketMotorStandby:
        # This command should only be activated on rocket
        if config.FSW_CONF == config.CONF_ROCKET:
            standbyrocketmotor()
        else:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"Not Performing Rocket Motor Standby, current conf : {config.FSW_CONF}")

    # On Payload Release motor activation command
    elif recv.MsgID == appargs.FlightlogicAppArg.MID_PayloadReleaseMotorActivate:
        if config.FSW_CONF == config.CONF_CONTAINER:
            activatepayloadreleasemotor()
        else:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"Not Performing Payload Release Motor Activation, current conf : {config.FSW_CONF}")

    # On Payload Release motor standby command
    elif recv.MsgID == appargs.FlightlogicAppArg.MID_PayloadReleaseMotorStandby:
        if config.FSW_CONF == config.CONF_CONTAINER:
            standbypayloadreleasemotor()
        else:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"Not Performing Payload Release Motor Standby, current conf : {config.FSW_CONF}")

    # MEC command from Comm app
    elif recv.MsgID == appargs.CommAppArg.MID_RouteCmd_MEC:
        if config.FSW_CONF == config.CONF_ROCKET:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"MEC : Current conf : rocket, activating rocket motor...")
            activaterocketmotor()
        elif config.FSW_CONF == config.CONF_CONTAINER:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"MEC : Current conf : container, Current Option : {recv.data}...")
            if recv.data == "ON":
                activatepayloadreleasemotor()
            elif recv.data == "OFF":
                freepayloadreleasemotor()
            else:
                events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, 
                              f"Error Activating container motor, invalid option : {recv.data}")
        elif config.FSW_CONF == config.CONF_PAYLOAD:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, 
                          f"MEC : Current conf : payload, Current Option : {recv.data}...")
            if recv.data == "ON":
                PAYLOAD_MOTOR_ENABLE = True
            elif recv.data == "OFF":
                PAYLOAD_MOTOR_ENABLE = False
            else:
                events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, 
                              f"Error Activating payload motor, invalid option : {recv.data}")

    # Angle command from Flightlogic
    elif recv.MsgID == appargs.FlightlogicAppArg.MID_SetServoAngle:
        try:
            pulse = int(float(recv.data))
            set_servo_pulse(pulse)
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                            f"Servo pulse set to {pulse}µs (from flightlogic)")
        except Exception as e:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                            f"Bad pulse cmd: {recv.data} – {e}")
        return

    elif recv.MsgID == appargs.MotorAppArg.MID_SetServoAngle:
        pulse = int(float(recv.data))
        set_servo_pulse(pulse)

    else:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                        f"MID {recv.MsgID} not handled")

# ────────────────────────────────────────────
# Motor control functions
# ────────────────────────────────────────────

def activaterocketmotor():
    """로켓 모터 활성화"""
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Activating Rocket Motor")
    # 로켓 모터 제어 로직 구현

def standbyrocketmotor():
    """로켓 모터 대기"""
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Standby Rocket Motor")
    # 로켓 모터 대기 로직 구현

def activatepayloadreleasemotor():
    """페이로드 해제 모터 활성화"""
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Activating Payload Release Motor")
    # 페이로드 해제 모터 제어 로직 구현

def standbypayloadreleasemotor():
    """페이로드 해제 모터 대기"""
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Standby Payload Release Motor")
    # 페이로드 해제 모터 대기 로직 구현

def freepayloadreleasemotor():
    """페이로드 해제 모터 해제"""
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, "Free Payload Release Motor")
    # 페이로드 해제 모터 해제 로직 구현

def controlgimbalmotor(yaw):
    """짐벌 모터 제어 (Yaw 기반)"""
    if config.FSW_CONF == config.CONF_PAYLOAD and PAYLOAD_MOTOR_ENABLE == True:
        # Yaw 데이터를 기반으로 모터 제어
        angle = max(0, min(180, 90 + yaw))  # 90도를 중심으로 ±90도
        pulse = motor.angle_to_pulse(angle)
        set_servo_pulse(pulse)
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info, f"Gimbal motor controlled by yaw: {yaw}° -> angle: {angle}°")

# ────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────

thread_dict: dict[str, threading.Thread] = {}

def read_motor_status():
    global MOTOR_STATUS, MOTORAPP_RUNSTATUS
    while MOTORAPP_RUNSTATUS:
        try:
            # 실제 모터 상태 읽기 코드 (예시)
            status = get_motor_status()
            if status is not None:
                MOTOR_STATUS = status
        except Exception:
            # 에러 메시지 출력하지 않고, 이전 값 유지
            pass
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not MOTORAPP_RUNSTATUS:
                break
            time.sleep(0.1)

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while MOTORAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            # 더 빠른 종료를 위해 짧은 간격으로 체크
            for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
                if not MOTORAPP_RUNSTATUS:
                    break
                time.sleep(0.1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

def motorapp_main(main_q: Queue, main_pipe: connection.Connection):
    global MOTORAPP_RUNSTATUS
    MOTORAPP_RUNSTATUS = True

    motorapp_init()

    # HK thread
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(main_q,),
                                         name="HKSender_Thread")
    thread_dict["HK"].start()

    # 스레드 자동 재시작 래퍼
    thread_dict["READ"] = resilient_thread(read_motor_status, name="READ")

    try:
        while MOTORAPP_RUNSTATUS:
            # Non-blocking receive with timeout
            try:
                if main_pipe.poll(0.5):  # 0.5초 타임아웃으로 단축
                    try:
                        raw = main_pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError):
                        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, "Pipe connection lost")
                        break
                    except Exception as e:
                        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, f"Pipe receive error: {e}")
                        continue
                else:
                    # 타임아웃 시 루프 계속
                    continue
                    
                m = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(m, raw):
                    continue

                if m.receiver_app in (appargs.MotorAppArg.AppID, appargs.MainAppArg.AppID):
                    command_handler(main_q, m)
                else:
                    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                                    "Receiver AppID mismatch for motorapp")
                                    
            except Exception as e:
                events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error, f"Main loop error: {e}")
                time.sleep(0.1)  # 에러 시 짧은 대기

    except Exception as e:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                        f"motorapp runtime error: {e}")
        MOTORAPP_RUNSTATUS = False

    motorapp_terminate()

# ────────────────────────────────────────────
# Stand‑alone test (python3 motorapp.py)
# ────────────────────────────────────────────
if __name__ == "__main__":
    print("[motorapp] Stand‑alone interactive test mode – CTRL‑C to quit")
    try:
        motorapp_init()
        while True:
            a = input("Angle 0‑180 › ")
            if a.strip() == "":
                continue
            set_servo_pulse(float(a))
    except KeyboardInterrupt:
        print()
    finally:
        motorapp_terminate()
