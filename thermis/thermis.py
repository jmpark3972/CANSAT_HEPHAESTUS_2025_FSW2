#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
thermis.py – ADS1115 thermistor temperature sensor helper
"""

import os, time, math
from datetime import datetime

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
thermis_log = open(os.path.join(LOG_DIR, "thermis.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    thermis_log.write(f"{t},{line}\n")
    thermis_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_thermis():
    """Thermis 센서 초기화 (직접 I2C 연결)"""
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    try:
        # Thermis 센서 직접 연결
        ads = ADS.ADS1115(i2c)
        chan = AnalogIn(ads, ADS.P0)
        time.sleep(0.1)
        # Thermis 센서 초기화 완료 (직접 I2C 연결)
        return i2c, chan
    except Exception as e:
        # Thermis 초기화 실패: {e}
        raise Exception(f"Thermis 초기화 실패: {e}")

def terminate_thermis(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass  # busio 버전에 따라 deinit() 없음
    thermis_log.close()

# ─────────────────────────────
# 3) 데이터 읽기
# ─────────────────────────────
def read_thermis(chan):
    """Thermis 센서 데이터 읽기"""
    try:
        voltage = chan.voltage
        # 전압을 온도로 변환 (간단한 선형 변환)
        temperature = (voltage - 0.5) * 100  # 예시 변환 공식
        return round(temperature, 2)
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None

# ─────────────────────────────
# 4) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    i2c, chan = init_thermis()
    try:
        while True:
            temp = read_thermis(chan)
            if temp is not None:
                pass  # Temperature: {temp:.2f} °C
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_thermis(i2c) 