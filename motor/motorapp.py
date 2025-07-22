

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

def set_servo_angle(angle: int | float) -> None:
    """Clamp 0‑180°, convert to pulse width and command the servo."""
    global CURRENT_ANGLE
    if pi is None or not pi.connected:
        raise RuntimeError("pigpio not initialised")

    pulse = motor._angle_to_pulse(angle)
    pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, pulse)
    CURRENT_ANGLE = int(max(0, min(180, int(angle))))

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

    # Set initial angle 0° (pulse 500 µs)
    set_servo_angle(0)
    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Motorapp initialised, servo at 0°")


def motorapp_terminate() -> None:
    global MOTORAPP_RUNSTATUS, pi
    MOTORAPP_RUNSTATUS = False

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Terminating motorapp")

    if pi and pi.connected:
        pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, 0)  # stop PWM
        pi.stop()

    for t in thread_dict.values():
        t.join()

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                    "Motorapp termination complete")

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
            angle = float(recv.data)
            set_servo_angle(angle)
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.info,
                            f"Servo moved to {angle}° (pulse={motor._angle_to_pulse(angle)}µs)")
        except Exception as e:
            events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                            f"Bad angle cmd: {recv.data} – {e}")
        return
    if recv.MsgID == appargs.MotorAppArg.MID_SetServoAngle:
        target = float(recv.data)
        set_servo_angle(target)

    if recv.MsgID == appargs.ImuAppArg.MID_SendYawData:
        # 필요하다면 Yaw 데이터 활용, 아니면 pass
        pass

    events.LogEvent(appargs.MotorAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# ────────────────────────────────────────────
# Main loop
# ────────────────────────────────────────────

thread_dict: dict[str, threading.Thread] = {}

def motorapp_main(main_q: Queue, main_pipe: connection.Connection):
    global MOTORAPP_RUNSTATUS
    MOTORAPP_RUNSTATUS = True

    motorapp_init()

    # HK thread
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(main_q,),
                                         name="HKSender_Thread")
    thread_dict["HK"].start()

    try:
        while MOTORAPP_RUNSTATUS:
            raw = main_pipe.recv()
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
            set_servo_angle(float(a))
    except KeyboardInterrupt:
        print()
    finally:
        motorapp_terminate()
