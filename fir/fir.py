#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
fir.py – MLX90614 far-infrared temperature sensor helper
"""

import os, time
from datetime import datetime

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
fir_log = open(os.path.join(LOG_DIR, "fir.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    fir_log.write(f"{t},{line}\n")
    fir_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_fir():
    """MLX90614 객체를 초기화해 (i2c, sensor) 튜플 반환."""
    import board, busio, adafruit_mlx90614
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
    sensor = adafruit_mlx90614.MLX90614(i2c)
    return i2c, sensor

def terminate_fir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass  # busio 버전에 따라 deinit() 없음
    fir_log.close()

# ─────────────────────────────
# 3) 데이터 읽기
# ─────────────────────────────
def read_fir(sensor):
    """
    (ambient, object) 튜플 반환.
    오류 발생 시 (None, None) + 로그 기록.
    """
    try:
        amb = round(float(sensor.ambient_temperature), 2)
        obj = round(float(sensor.object_temperature),  2)
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None, None

    _log(f"{amb:.2f},{obj:.2f}")
    return amb, obj

# ─────────────────────────────
# 4) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    i2c, s = init_fir()
    try:
        while True:
            a, o = read_fir(s)
            if a is not None:
                print(f"Ambient: {a:.2f} °C  Object: {o:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_fir(i2c)
