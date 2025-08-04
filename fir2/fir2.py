#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
fir2.py – MLX90614 far-infrared temperature sensor helper (Channel 1)
Qwiic Mux를 통해 채널 1에 연결된 MLX90614 센서 제어
"""

import os, time
from datetime import datetime

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
fir2_log = open(os.path.join(LOG_DIR, "fir2.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    fir2_log.write(f"{t},{line}\n")
    fir2_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_fir2():
    """MLX90614 객체를 초기화해 (mux, sensor) 튜플 반환."""
    import board, busio, adafruit_mlx90614
    from lib.qwiic_mux import QwiicMux
    
    # I2C 버스 초기화
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
    time.sleep(0.1)  # 안정화 대기
    
    # Qwiic Mux 초기화
    mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
    
    # 채널 1 선택
    if not mux.select_channel(1):
        raise RuntimeError("Qwiic Mux 채널 1 선택 실패")
    time.sleep(0.1)  # 안정화 대기
    
    # MLX90614 센서 초기화
    sensor = adafruit_mlx90614.MLX90614(i2c)
    time.sleep(0.1)  # 안정화 대기
    
    _log("FIR2 초기화 완료 (채널 1)")
    return mux, sensor

def terminate_fir2(mux):
    try:
        if mux:
            mux.close()
    except Exception as e:
        print(f"FIR2 종료 오류: {e}")
    finally:
        fir2_log.close()

# ─────────────────────────────
# 3) 데이터 읽기
# ─────────────────────────────
def read_fir2(mux, sensor):
    """
    (ambient, object) 튜플 반환.
    오류 발생 시 (0.0, 0.0) + 로그 기록.
    """
    try:
        # 채널 1 선택 확인 및 강제 선택
        current_channel = mux.get_current_channel()
        if current_channel != 1:
            _log(f"Channel switch: {current_channel} -> 1")
            mux.select_channel(1)
            time.sleep(0.1)  # 안정화 대기 증가
        
        # 센서 재초기화 시도 (채널 변경 후)
        if current_channel != 1:
            try:
                import adafruit_mlx90614
                sensor = adafruit_mlx90614.MLX90614(mux.i2c)
                time.sleep(0.05)
            except Exception as e:
                _log(f"Sensor reinit error: {e}")
        
        amb = round(float(sensor.ambient_temperature), 2)
        obj = round(float(sensor.object_temperature),  2)
        
        # 유효한 값인지 확인
        if amb < -40 or amb > 125 or obj < -40 or obj > 125:
            _log(f"Invalid temperature values: amb={amb}, obj={obj}")
            return 0.0, 0.0
            
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return 0.0, 0.0

    _log(f"{amb:.2f},{obj:.2f}")
    return amb, obj

# ─────────────────────────────
# 4) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    mux, s = init_fir2()
    try:
        while True:
            a, o = read_fir2(mux, s)
            if a is not None:
                print(f"FIR2 (Ch1) - Ambient: {a:.2f} °C  Object: {o:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_fir2(mux) 