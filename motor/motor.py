#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""motor.py – Servo angle helper for the payload release motor

* GPIO 12 (BCM) → PWM signal to a standard hobby servo
* Uses **pigpio** (be sure `pigpiod` is running)
* Provides a simple `set_angle()` API + interactive test loop

Install:
    sudo apt install -y pigpio python3-pigpio
    sudo systemctl enable pigpiod --now  # start daemon at boot
"""

import pigpio
import sys
import time
from typing import Union

# ────────────────────────────────────────────────
# User‑tunable constants
# ────────────────────────────────────────────────
PAYLOAD_MOTOR_PIN: int = 18          # BCM numbering
PAYLOAD_MOTOR_MIN_PULSE: int = 500     # µs → 0 °
PAYLOAD_MOTOR_MAX_PULSE: int = 2500    # µs → 180 °

# ────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────

def _angle_to_pulse(angle: Union[int, float]) -> int:
    """Clamp *angle* to 0‑180 ° and convert to pulse‑width in µs."""
    if angle < 0:
        angle = 0
    elif angle > 180:
        angle = 180
    return int(PAYLOAD_MOTOR_MIN_PULSE + (angle / 180.0) * (PAYLOAD_MOTOR_MAX_PULSE - PAYLOAD_MOTOR_MIN_PULSE))


# ────────────────────────────────────────────────
# pigpio initialisation
# ────────────────────────────────────────────────
pi = pigpio.pi()
if not pi.connected:
    sys.exit("pigpiod daemon not running. Start it with: sudo pigpiod")

# Ensure servo is initialised to a known safe pulse (0 °)
pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, _angle_to_pulse(0))


# ────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────

def set_angle(angle: Union[int, float]):
    """Move the servo to *angle* degrees (0‑180)."""
    pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, _angle_to_pulse(angle))


def cleanup():
    """Release the servo and disconnect from pigpio."""
    pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, 0)  # stop pulses
    pi.stop()


# ────────────────────────────────────────────────
# CLI test harness
# ────────────────────────────────────────────────
if __name__ == "__main__":
    try:
        print("Interactive servo test. Type an angle 0‑180, or 'q' to quit.")
        while True:
            raw = input("angle> ").strip()
            if raw.lower() in {"q", "quit", "exit"}:
                break
            try:
                set_angle(float(raw))
            except ValueError:
                print("⚠︎  Enter a number between 0 and 180, or q to quit.")
    except KeyboardInterrupt:
        pass
    finally:
        cleanup()
