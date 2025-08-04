# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import os
from datetime import datetime

log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file
barometerlogfile = open(os.path.join(log_dir, 'barometer.txt'), 'a')

def log_barometer(text):

    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    barometerlogfile.write(string_to_write)
    barometerlogfile.flush()
    
def init_barometer():
    import adafruit_bmp3xx
    import board
    import busio
    from lib.qwiic_mux import QwiicMux
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    # Qwiic Mux 초기화 및 채널 5 선택 (Barometer 위치 - 실제 연결된 채널)
    from lib.qwiic_mux import create_mux_instance
    mux = create_mux_instance(i2c_bus=i2c, mux_address=0x70)
    
    # channel_guard를 사용하여 안전하게 채널 선택 및 센서 초기화
    bmp = None
    with mux.channel_guard(5):  # 🔒 채널 5 점유
        print("Qwiic Mux 채널 5 선택 완료 (Barometer)")
        
        # 여러 I2C 주소 시도 (BMP280/BMP388 일반적인 주소들)
        bmp_addresses = [0x76, 0x77]
        
        for addr in bmp_addresses:
            try:
                print(f"Barometer I2C 주소 0x{addr:02X} 시도 중...")
                bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=addr)
                print(f"Barometer 초기화 성공 (주소: 0x{addr:02X})")
                break
            except Exception as e:
                print(f"주소 0x{addr:02X} 실패: {e}")
                continue
    
    if bmp is None:
        raise Exception("Barometer를 찾을 수 없습니다. I2C 연결을 확인하세요.")
    
    bmp.pressure_oversampling = 8
    bmp.temperature_oversampling = 2

    return i2c, bmp, mux

# Read Barometer data and returns tuple (pressure, temperature, altitude)
def read_barometer(bmp, mux, offset:float):
    global altitude_altZero
    
    # channel_guard를 사용하여 안전하게 센서 읽기
    with mux.channel_guard(5):  # 🔒 채널 5 점유
        pressure = bmp.pressure
        temperature = bmp.temperature
        altitude = bmp.altitude

    # Type Checking of barometer data
    if type(pressure) == float:
        pressure = round(pressure, 2)
    else:
        pressure = 0

    if type(temperature) == float:
        temperature = round(temperature, 2)
    else:
        temperature = 0

    if type(altitude) == float:
        altitude = round(altitude, 2)
    else:
        altitude = 0

    # Apply offset
    altitude = round(altitude - offset, 2)

    log_barometer(f"{pressure:.2f}, {temperature:.2f}, {altitude:.2f}")
    
    return ( pressure, temperature, altitude )

def terminate_barometer(i2c):
    try:
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        elif hasattr(i2c, "close"):
            i2c.close()
    except Exception as e:
        print(f"I2C cleanup failed: {e}")

if __name__ == "__main__":
    i2c, bmp, mux = init_barometer()
    try:
        while True:
            data = read_barometer(bmp, mux, 0)
            print(data)
            time.sleep(1)
    except KeyboardInterrupt:
        terminate_barometer(i2c)
