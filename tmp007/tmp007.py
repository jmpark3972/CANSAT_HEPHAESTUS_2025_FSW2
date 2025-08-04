#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""tmp007.py – TMP007 온도 센서 제어 모듈

* Qwiic Mux 채널 3번에 연결
* I2C 주소: 0x40 (기본)
* 정밀 온도 측정 센서
* 비접촉 온도 측정 가능

설치:
    pip install adafruit-circuitpython-tmp007
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

# TMP007 센서 클래스
class TMP007:
    def __init__(self, i2c, address=0x40):
        """TMP007 센서 초기화"""
        self.i2c = i2c
        self.address = address
        
        # TMP007 레지스터 주소
        self.REG_VOLTAGE = 0x00
        self.REG_TDIE = 0x01
        self.REG_CONFIG = 0x02
        self.REG_TOBJ = 0x03
        self.REG_STATUS = 0x04
        self.REG_TOBJ_MAX = 0x05
        self.REG_TOBJ_MIN = 0x06
        self.REG_TOBJ_FAULT = 0x07
        self.REG_DEVID = 0x1F
        
        # 설정값
        self.CONVERSION_TIME = 0.133  # 133ms (8 samples averaged)
        self.last_read_time = 0
        
        # 센서 초기화
        self._init_sensor()
    
    def _init_sensor(self):
        """센서 초기화 및 설정"""
        try:
            # 디바이스 ID 확인
            dev_id = self._read_register(self.REG_DEVID)
            if dev_id != 0x78:  # TMP007 디바이스 ID
                raise Exception(f"Invalid device ID: 0x{dev_id:02X}")
            
            # 설정 레지스터 초기화 (8샘플 평균, 4Hz 샘플링)
            config = 0x1000  # 8샘플 평균, 4Hz
            self._write_register(self.REG_CONFIG, config)
            
            # 상태 레지스터 초기화
            self._write_register(self.REG_STATUS, 0x0000)
            
            print(f"TMP007 초기화 성공 (주소: 0x{self.address:02X})")
            
        except Exception as e:
            raise Exception(f"TMP007 초기화 실패: {e}")
    
    def _read_register(self, reg):
        """레지스터 읽기 (16비트)"""
        try:
            result = bytearray(2)
            self.i2c.writeto_then_readfrom(self.address, bytes([reg]), result)
            return (result[0] << 8) | result[1]
        except Exception as e:
            raise Exception(f"레지스터 읽기 실패 (0x{reg:02X}): {e}")
    
    def _write_register(self, reg, value):
        """레지스터 쓰기 (16비트)"""
        try:
            data = bytes([reg, (value >> 8) & 0xFF, value & 0xFF])
            self.i2c.writeto(self.address, data)
        except Exception as e:
            raise Exception(f"레지스터 쓰기 실패 (0x{reg:02X}): {e}")
    
    def read_temperature(self):
        """온도 읽기 (섭씨)"""
        try:
            # 변환 시간 대기
            current_time = time.time()
            if current_time - self.last_read_time < self.CONVERSION_TIME:
                time.sleep(self.CONVERSION_TIME - (current_time - self.last_read_time))
            
            # 객체 온도 읽기
            tobj_raw = self._read_register(self.REG_TOBJ)
            
            # 온도 변환 (14비트, 0.03125°C/LSB)
            if tobj_raw & 0x8000:  # 음수 온도
                temperature = -((~tobj_raw + 1) & 0x7FFF) * 0.03125
            else:
                temperature = (tobj_raw & 0x7FFF) * 0.03125
            
            self.last_read_time = time.time()
            return round(temperature, 2)
            
        except Exception as e:
            raise Exception(f"온도 읽기 실패: {e}")
    
    def read_die_temperature(self):
        """다이 온도 읽기 (섭씨)"""
        try:
            tdie_raw = self._read_register(self.REG_TDIE)
            
            # 온도 변환 (14비트, 0.03125°C/LSB)
            if tdie_raw & 0x8000:  # 음수 온도
                temperature = -((~tdie_raw + 1) & 0x7FFF) * 0.03125
            else:
                temperature = (tdie_raw & 0x7FFF) * 0.03125
            
            return round(temperature, 2)
            
        except Exception as e:
            raise Exception(f"다이 온도 읽기 실패: {e}")
    
    def read_voltage(self):
        """전압 읽기 (마이크로볼트)"""
        try:
            voltage_raw = self._read_register(self.REG_VOLTAGE)
            
            # 전압 변환 (14비트, 156.25μV/LSB)
            if voltage_raw & 0x8000:  # 음수 전압
                voltage = -((~voltage_raw + 1) & 0x7FFF) * 156.25
            else:
                voltage = (voltage_raw & 0x7FFF) * 156.25
            
            return round(voltage, 2)
            
        except Exception as e:
            raise Exception(f"전압 읽기 실패: {e}")
    
    def get_status(self):
        """상태 정보 읽기"""
        try:
            status = self._read_register(self.REG_STATUS)
            return {
                'data_ready': bool(status & 0x4000),
                'object_high': bool(status & 0x2000),
                'object_low': bool(status & 0x1000),
                'object_fault': bool(status & 0x0800),
                'voltage_high': bool(status & 0x0400),
                'voltage_low': bool(status & 0x0200),
                'voltage_fault': bool(status & 0x0100)
            }
        except Exception as e:
            raise Exception(f"상태 읽기 실패: {e}")
    
    def read_all_data(self):
        """모든 데이터 읽기"""
        try:
            temperature = self.read_temperature()
            die_temp = self.read_die_temperature()
            voltage = self.read_voltage()
            status = self.get_status()
            
            return {
                'object_temperature': temperature,
                'die_temperature': die_temp,
                'voltage': voltage,
                'status': status,
                'timestamp': time.time()
            }
        except Exception as e:
            raise Exception(f"데이터 읽기 실패: {e}")


def init_tmp007():
    """TMP007 센서 초기화"""
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        
        # Qwiic Mux 초기화 및 채널 3 선택 (TMP007 위치)
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        mux.select_channel(3)  # TMP007는 채널 3에 연결
        time.sleep(0.1)  # 안정화 대기
        
        # TMP007 센서 초기화
        sensor = TMP007(i2c, address=0x40)
        
        # 센서 안정화를 위한 추가 지연
        time.sleep(0.5)
        
        return i2c, sensor, mux
        
    except Exception as e:
        raise Exception(f"TMP007 초기화 실패: {e}")


def read_tmp007_data(sensor):
    """TMP007 센서 데이터 읽기"""
    try:
        data = sensor.read_all_data()
        return data
    except Exception as e:
        print(f"TMP007 데이터 읽기 실패: {e}")
        return None


def tmp007_terminate(i2c):
    """TMP007 센서 종료"""
    try:
        if i2c:
            i2c.deinit()
        print("TMP007 센서 종료 완료")
    except Exception as e:
        print(f"TMP007 종료 오류: {e}")


# 테스트 코드
if __name__ == "__main__":
    try:
        print("TMP007 센서 테스트 시작...")
        
        # 센서 초기화
        i2c, sensor, mux = init_tmp007()
        
        print("온도 측정 시작 (Ctrl+C로 종료)...")
        
        while True:
            try:
                data = read_tmp007_data(sensor)
                if data:
                    print(f"객체 온도: {data['object_temperature']}°C")
                    print(f"다이 온도: {data['die_temperature']}°C")
                    print(f"전압: {data['voltage']}μV")
                    print(f"상태: {data['status']}")
                    print("-" * 40)
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"측정 오류: {e}")
                time.sleep(1)
        
    except Exception as e:
        print(f"TMP007 테스트 실패: {e}")
    finally:
        try:
            tmp007_terminate(i2c)
        except:
            pass 