

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


from lib import appargs, events, msgstructure, logging  # type: ignore
from motor import motor  # local helper that provides angle_to_pulse()

# ────────────────────────────────────────────
# Global flags & state
# ────────────────────────────────────────────
MOTORAPP_RUNSTATUS = True
CURRENT_ANGLE = 0  # deg – last commanded angle

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
    global pi
    signal.signal(signal.SIGINT, signal.SIG_IGN)  # parent handles SIGINT

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Initialising motorapp (pigpio)")

    pi = pigpio.pi()
    if not pi.connected:
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                        "pigpio daemon not running – aborting")
        raise SystemExit(1)

    # Set initial angle 180° (pulse 2500 µs)
    set_servo_pulse(2500)
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Motorapp initialised, servo at 180°")


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

    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.join()

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
        time.sleep(1)

# ────────────────────────────────────────────
# Command handler
# ────────────────────────────────────────────

def command_handler(main_q: Queue, recv: msgstructure.MsgStructure) -> None:
    global MOTORAPP_RUNSTATUS

    # Termination from Main
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        MOTORAPP_RUNSTATUS = False
        events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                        "Termination command received")
        return
	
    # Angle command from Flightlogic
    if recv.MsgID == appargs.FlightlogicAppArg.MID_SetServoAngle:
        try:
            pulse = int(float(recv.data))
            set_servo_pulse(pulse)
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                            f"Servo pulse set to {pulse}µs (from flightlogic)")
        except Exception as e:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                            f"Bad pulse cmd: {recv.data} – {e}")
        return
    if recv.MsgID == appargs.MotorAppArg.MID_SetServoAngle:
        pulse = int(float(recv.data))
        set_servo_pulse(pulse)

    if recv.MsgID == appargs.ImuAppArg.MID_SendYawData:
        # 필요하다면 Yaw 데이터 활용, 아니면 pass
        pass

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

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
        time.sleep(1)

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while MOTORAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            time.sleep(1)
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
            try:
                raw = main_pipe.recv(timeout=1.0)  # 1초 타임아웃 추가
            except:
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
