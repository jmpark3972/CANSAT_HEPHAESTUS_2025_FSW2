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
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    # Barometer 센서 직접 연결
    bmp = None
    
    # BMP390 I2C 주소 (0x77)
    try:
        print(f"Barometer BMP390 I2C 주소 0x77 시도 중...")
        bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=0x77)
        print(f"Barometer BMP390 초기화 성공 (주소: 0x77)")
    except Exception as e:
        print(f"BMP390 주소 0x77 실패: {e}")
        # 폴백으로 다른 주소들 시도
        bmp_addresses = [0x76]
        for addr in bmp_addresses:
            try:
                print(f"Barometer I2C 주소 0x{addr:02X} 시도 중...")
                bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=addr)
                print(f"Barometer 초기화 성공 (주소: 0x{addr:02X})")
                break
            except Exception as e2:
                print(f"주소 0x{addr:02X} 실패: {e2}")
                continue

    if bmp is None:
        raise Exception("Barometer를 찾을 수 없습니다. I2C 연결을 확인하세요.")
    
    bmp.pressure_oversampling = 8
    bmp.temperature_oversampling = 2

    return i2c, bmp

# Read Barometer data and returns tuple (pressure, temperature, altitude)
def read_barometer(bmp, offset:float):
    global altitude_altZero
    
    # 마지막 유효 데이터 저장
    if not hasattr(read_barometer, "last_valid_data"):
        read_barometer.last_valid_data = (1013.25, 25.0, 0.0)  # 기본값
        read_barometer.error_count = 0
    
    try:
        # 센서 데이터 읽기
        pressure = bmp.pressure
        temperature = bmp.temperature
        altitude = bmp.altitude

        # 데이터 유효성 검사
        if pressure is None or temperature is None or altitude is None:
            raise Exception("센서에서 None 값 반환")
        
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

        # 데이터 범위 검증
        if pressure < 300 or pressure > 1200:  # hPa 범위
            raise Exception(f"압력 범위 오류: {pressure} hPa")
        
        if temperature < -40 or temperature > 85:  # 섭씨 범위
            raise Exception(f"온도 범위 오류: {temperature}°C")
        
        if altitude < -1000 or altitude > 10000:  # 고도 범위 (미터)
            raise Exception(f"고도 범위 오류: {altitude} m")

        # Apply offset
        altitude = round(altitude - offset, 2)

        # 유효한 데이터인 경우 마지막 유효 데이터 업데이트
        read_barometer.last_valid_data = (pressure, temperature, altitude)
        read_barometer.error_count = 0

        log_barometer(f"{pressure:.2f}, {temperature:.2f}, {altitude:.2f}")
        
        return (pressure, temperature, altitude)
        
    except Exception as e:
        read_barometer.error_count += 1
        
        # 오류 로깅 (너무 자주 출력하지 않도록)
        if read_barometer.error_count <= 5 or read_barometer.error_count % 10 == 0:
            print(f"Barometer 읽기 오류: {e}")
            log_barometer(f"READ_ERROR,{e}")
        
        # 연속 오류가 많으면 하드웨어 점검 안내
        if read_barometer.error_count >= 50:
            print(f"Barometer 연속 오류 {read_barometer.error_count}회 - 하드웨어/배선 점검 필요")
            read_barometer.error_count = 0
        
        # 마지막 유효 데이터 반환
        return read_barometer.last_valid_data

def terminate_barometer(i2c):
    try:
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        elif hasattr(i2c, "close"):
            i2c.close()
    except Exception as e:
        print(f"I2C cleanup failed: {e}")

if __name__ == "__main__":
    i2c, bmp = init_barometer()
    try:
        while True:
            data = read_barometer(bmp, 0)
            print(data)
            time.sleep(1)
    except KeyboardInterrupt:
        terminate_barometer(i2c)
