#!/usr/bin/env python3
"""
AS7263 스펙트럼 센서 모듈
AS7263는 6개 채널의 가시광선 스펙트럼 센서입니다.
"""

import time
import os
import board
import busio
from datetime import datetime
import adafruit_as726x

# AS7263 센서 설정
AS7263_I2C_ADDRESS = 0x49  # 기본 I2C 주소
GAIN_SETTING = 1  # 0=1x, 1=3.7x, 2=16x, 3=64x
INTEGRATION_TIME = 50  # ms (0-255)
LED_CURRENT = 12.5  # mA (0-12.5mA)

# 로그 디렉토리 설정
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
as7263_log = open(os.path.join(LOG_DIR, "as7263.txt"), "a")

def log_as7263(text):
    """AS7263 로그 기록"""
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    as7263_log.write(f"{t},{text}\n")
    as7263_log.flush()

def init_as7263():
    """AS7263 센서 초기화"""
    try:
        # I2C 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        
        # AS7263 센서 초기화
        sensor = adafruit_as726x.AS726x(i2c)
        
        # 센서 설정
        sensor.gain = GAIN_SETTING
        sensor.integration_time = INTEGRATION_TIME
        sensor.led_current = LED_CURRENT
        
        # LED 끄기 (기본값)
        sensor.led = False
        
        log_as7263("AS7263 initialized successfully")
        print("AS7263 센서 초기화 완료")
        print(f"Gain: {sensor.gain}, Integration Time: {sensor.integration_time}ms")
        
        return i2c, sensor
        
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 초기화 오류: {e}")
        return None, None

def read_as7263_raw(sensor):
    """AS7263 원시 데이터 읽기"""
    try:
        # 6개 채널의 원시 값 읽기
        raw_values = [
            sensor.violet,
            sensor.blue, 
            sensor.green,
            sensor.yellow,
            sensor.orange,
            sensor.red
        ]
        
        return raw_values
        
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 읽기 오류: {e}")
        return [0, 0, 0, 0, 0, 0]

def read_as7263_calibrated(sensor):
    """AS7263 보정된 데이터 읽기"""
    try:
        # 6개 채널의 보정된 값 읽기
        calibrated_values = [
            sensor.violet_calibrated,
            sensor.blue_calibrated,
            sensor.green_calibrated, 
            sensor.yellow_calibrated,
            sensor.orange_calibrated,
            sensor.red_calibrated
        ]
        
        return calibrated_values
        
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 보정 데이터 읽기 오류: {e}")
        return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

def read_as7263_temperature(sensor):
    """AS7263 온도 읽기"""
    try:
        temp = sensor.temperature
        return temp
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 온도 읽기 오류: {e}")
        return 0.0

def set_as7263_led(sensor, enable=True):
    """AS7263 LED 제어"""
    try:
        sensor.led = enable
        status = "ON" if enable else "OFF"
        log_as7263(f"LED_{status}")
        print(f"AS7263 LED {status}")
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 LED 제어 오류: {e}")

def set_as7263_gain(sensor, gain):
    """AS7263 게인 설정"""
    try:
        sensor.gain = gain
        log_as7263(f"GAIN_SET,{gain}")
        print(f"AS7263 게인 설정: {gain}")
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 게인 설정 오류: {e}")

def set_as7263_integration_time(sensor, integration_time):
    """AS7263 적분 시간 설정"""
    try:
        sensor.integration_time = integration_time
        log_as7263(f"INT_TIME_SET,{integration_time}")
        print(f"AS7263 적분 시간 설정: {integration_time}ms")
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 적분 시간 설정 오류: {e}")

def read_as7263_complete(sensor):
    """AS7263 완전한 데이터 읽기 (원시값, 보정값, 온도)"""
    try:
        # 원시 데이터
        raw_data = read_as7263_raw(sensor)
        
        # 보정된 데이터
        cal_data = read_as7263_calibrated(sensor)
        
        # 온도
        temperature = read_as7263_temperature(sensor)
        
        # 로그 기록
        raw_str = ",".join([f"{x}" for x in raw_data])
        cal_str = ",".join([f"{x:.6f}" for x in cal_data])
        log_as7263(f"DATA,{raw_str},{cal_str},{temperature:.2f}")
        
        return raw_data, cal_data, temperature
        
    except Exception as e:
        log_as7263(f"ERROR,{e}")
        print(f"AS7263 완전 데이터 읽기 오류: {e}")
        return [0, 0, 0, 0, 0, 0], [0.0, 0.0, 0.0, 0.0, 0.0, 0.0], 0.0

def terminate_as7263(i2c):
    """AS7263 종료"""
    try:
        i2c.deinit()
    except AttributeError:
        pass
    as7263_log.close()

if __name__ == "__main__":
    print("AS7263 스펙트럼 센서 테스트")
    print("=" * 50)
    
    i2c, sensor = init_as7263()
    if sensor is None:
        print("AS7263 초기화 실패")
        exit(1)
    
    try:
        # LED 켜기
        set_as7263_led(sensor, True)
        
        while True:
            raw_data, cal_data, temp = read_as7263_complete(sensor)
            
            print(f"온도: {temp:.2f}°C")
            print("원시 데이터:")
            print(f"  Violet: {raw_data[0]}")
            print(f"  Blue:   {raw_data[1]}")
            print(f"  Green:  {raw_data[2]}")
            print(f"  Yellow: {raw_data[3]}")
            print(f"  Orange: {raw_data[4]}")
            print(f"  Red:    {raw_data[5]}")
            print("보정 데이터:")
            print(f"  Violet: {cal_data[0]:.6f}")
            print(f"  Blue:   {cal_data[1]:.6f}")
            print(f"  Green:  {cal_data[2]:.6f}")
            print(f"  Yellow: {cal_data[3]:.6f}")
            print(f"  Orange: {cal_data[4]:.6f}")
            print(f"  Red:    {cal_data[5]:.6f}")
            print("-" * 50)
            
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\n테스트 중단")
    finally:
        set_as7263_led(sensor, False)
        terminate_as7263(i2c) 