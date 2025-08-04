#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
fir1.py – MLX90614 far-infrared temperature sensor helper (Channel 0)
Qwiic Mux를 통해 채널 0에 연결된 MLX90614 센서 제어
"""

import time
import os
from datetime import datetime

log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file
fir1logfile = open(os.path.join(log_dir, 'fir1.txt'), 'a')

def _log(text):
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    fir1logfile.write(string_to_write)
    fir1logfile.flush()

def init_fir1():
    """FIR1 센서 초기화 (직접 I2C 연결)"""
    import board
    import busio
    import adafruit_mlx90614
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    try:
        # FIR1 센서 직접 연결 (주소 0x5a)
        sensor = adafruit_mlx90614.MLX90614(i2c, address=0x5a)
        time.sleep(0.1)
        _log("FIR1 초기화 완료 (직접 I2C 연결)")
        return i2c, sensor
    except Exception as e:
        _log(f"FIR1 초기화 실패: {e}")
        raise Exception(f"FIR1 초기화 실패: {e}")

def read_fir1(sensor):
    """FIR1 센서 데이터 읽기"""
    try:
        # 센서에서 온도 읽기
        ambient_temp = sensor.ambient_temperature
        object_temp = sensor.object_temperature
        
        # 소수점 2자리로 반올림
        ambient_temp = round(ambient_temp, 2)
        object_temp = round(object_temp, 2)
        
        _log(f"{ambient_temp:.2f}, {object_temp:.2f}")
        return ambient_temp, object_temp
        
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None, None

def terminate_fir1(i2c):
    """FIR1 센서 종료"""
    try:
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        elif hasattr(i2c, "close"):
            i2c.close()
    except Exception as e:
        _log(f"TERMINATE_ERROR,{e}") 