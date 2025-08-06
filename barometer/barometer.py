# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import os
import math
from datetime import datetime
 
OFFSET_FILE = './sensorlogs/altitude_offset.txt'
log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file (메모리 최적화)
_barometer_log_buffer = []
_barometer_log_buffer_size = 50
_last_barometer_flush_time = time.time()
_barometer_flush_interval = 10  # 10초마다 플러시

def save_offset(offset):
    with open(OFFSET_FILE, 'w') as f:
        f.write(f"{offset:.2f}")

def load_offset():
    try:
        with open(OFFSET_FILE, 'r') as f:
            return float(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None 

def log_barometer(text):
    """메모리 최적화된 로깅 함수"""
    global _barometer_log_buffer, _barometer_log_buffer_size, _last_barometer_flush_time, _barometer_flush_interval
    
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    
    # 버퍼에 추가
    _barometer_log_buffer.append(string_to_write)
    
    # 버퍼가 가득 차거나 시간이 지나면 플러시
    current_time = time.time()
    if (len(_barometer_log_buffer) >= _barometer_log_buffer_size or 
        current_time - _last_barometer_flush_time >= _barometer_flush_interval):
        _flush_barometer_log_buffer()

def _flush_barometer_log_buffer():
    """Barometer 로그 버퍼를 파일에 플러시"""
    global _barometer_log_buffer, _last_barometer_flush_time
    
    try:
        if _barometer_log_buffer:
            log_file_path = os.path.join(log_dir, 'barometer.txt')
            with open(log_file_path, 'a') as f:
                f.writelines(_barometer_log_buffer)
            
            # 버퍼 정리
            _barometer_log_buffer.clear()
            _last_barometer_flush_time = time.time()
            
    except Exception as e:
        print(f"Barometer 로그 플러시 오류: {e}")
    
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
    offset2 = load_offset()
    if offset2 is None:
        offset2 = 0.0

    # 마지막 유효 데이터 저장
    if not hasattr(read_barometer, "last_valid_data"):
        read_barometer.last_valid_data = (1013.25, 25.0, 0.0)  # 기본값
        read_barometer.error_count = 0
    
    try:
        # 센서 데이터 읽기 (재시도 로직 추가)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                pressure = bmp.pressure
                temperature = bmp.temperature
                altitude = bmp.altitude
                break  # 성공하면 루프 탈출
            except Exception as retry_error:
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # 잠시 대기 후 재시도
                    continue
                else:
                    raise retry_error  # 마지막 시도에서도 실패하면 예외 발생

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
        altitude = round(altitude - offset - offset2, 2)

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

def calculate_sea_level_pressure(pressure, altitude, temperature):
    """
    해수면 기압 계산
    
    Args:
        pressure: 현재 압력 (hPa)
        altitude: 현재 고도 (m)
        temperature: 현재 온도 (°C)
    
    Returns:
        sea_level_pressure: 해수면 기압 (hPa)
    """
    try:
        # 온도를 켈빈으로 변환
        temp_k = temperature + 273.15
        
        # 해수면 기압 계산 (국제표준대기모델)
        # P0 = P * exp(g * h / (R * T))
        # g = 9.80665 m/s², R = 287.1 J/(kg·K)
        g = 9.80665
        R = 287.1
        
        sea_level_pressure = pressure * math.exp(g * altitude / (R * temp_k))
        
        return round(sea_level_pressure, 2)
        
    except Exception as e:
        print(f"해수면 기압 계산 오류: {e}")
        return pressure

def get_sensor_resolution(bmp):
    """
    센서 해상도 정보 반환
    
    Args:
        bmp: BMP390 센서 객체
    
    Returns:
        dict: 해상도 정보
    """
    try:
        # BMP390의 기본 해상도 (데이터시트 기준)
        resolution_info = {
            'pressure_resolution': 0.01,  # hPa (0.01 hPa = 1 Pa)
            'temperature_resolution': 0.01,  # °C
            'altitude_resolution': 0.01,  # m
            'pressure_accuracy': 0.08,  # hPa (±0.08 hPa)
            'temperature_accuracy': 0.5,  # °C (±0.5°C)
            'altitude_accuracy': 0.5,  # m (±0.5m)
            'pressure_range': [300, 1250],  # hPa
            'temperature_range': [-40, 85],  # °C
            'altitude_range': [-500, 9000]  # m
        }
        
        return resolution_info
        
    except Exception as e:
        print(f"센서 해상도 정보 오류: {e}")
        return None

def read_barometer_advanced(bmp, offset:float):
    """
    Barometer 고급 데이터 읽기 - 추가 계산값들 포함
    
    Returns:
        tuple: (pressure, temperature, altitude, sea_level_pressure, resolution_info)
    """
    try:
        # 기본 데이터 읽기
        pressure, temperature, altitude = read_barometer(bmp, offset)
        
        # 해수면 기압 계산
        sea_level_pressure = calculate_sea_level_pressure(pressure, altitude, temperature)
        
        # 센서 해상도 정보
        resolution_info = get_sensor_resolution(bmp)
        
        # 고급 데이터 로그
        log_barometer(f"ADVANCED_DATA,SLP:{sea_level_pressure:.2f},RES_P:{resolution_info['pressure_resolution']:.3f},"
                     f"RES_T:{resolution_info['temperature_resolution']:.3f}")
        
        return (pressure, temperature, altitude, sea_level_pressure, resolution_info)
        
    except Exception as e:
        print(f"Barometer 고급 데이터 읽기 오류: {e}")
        log_barometer(f"ADVANCED_READ_ERROR,{e}")
        return (1013.25, 25.0, 0.0, 1013.25, None)

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
