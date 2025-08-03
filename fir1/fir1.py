#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
fir1.py – MLX90614 far-infrared temperature sensor helper (Channel 0)
Qwiic Mux를 통해 채널 0에 연결된 MLX90614 센서 제어
"""

import os, time
from datetime import datetime

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
fir1_log = open(os.path.join(LOG_DIR, "fir1.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    fir1_log.write(f"{t},{line}\n")
    fir1_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_fir1():
    """MLX90614 객체를 초기화해 (mux, sensor) 튜플 반환."""
    import board, busio, adafruit_mlx90614
    from lib.qwiic_mux import QwiicMux
    
    # I2C 버스 초기화
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
    
    # Qwiic Mux 초기화
    mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
    
    # 채널 0 선택
    if not mux.select_channel(0):
        raise RuntimeError("Qwiic Mux 채널 0 선택 실패")
    
    # MLX90614 센서 초기화
    sensor = adafruit_mlx90614.MLX90614(i2c)
    
    _log("FIR1 초기화 완료 (채널 0)")
    return mux, sensor

def terminate_fir1(mux):
    try:
        if mux:
            mux.close()
    except Exception as e:
        print(f"FIR1 종료 오류: {e}")
    finally:
        fir1_log.close()

# ─────────────────────────────
# 3) 데이터 읽기
# ─────────────────────────────
def read_fir1(mux, sensor):
    """
    (ambient, object) 튜플 반환.
    오류 발생 시 (None, None) + 로그 기록.
    """
    try:
        # 채널 0 선택 확인
        if mux.get_current_channel() != 0:
            mux.select_channel(0)
            time.sleep(0.01)  # 안정화 대기
        
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
    mux, s = init_fir1()
    try:
        while True:
            a, o = read_fir1(mux, s)
            if a is not None:
                print(f"FIR1 (Ch0) - Ambient: {a:.2f} °C  Object: {o:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_fir1(mux) 