#!/usr/bin/env python3
"""
통합 온도 센서 모듈
- Thermistor (ADS1115)
- DHT11 (온도/습도)
- FIR1 (MLX90614)
"""

import time
import os
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from datetime import datetime
from math import log

# 로그 디렉토리 설정
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)

# 실행 시간으로 로그 파일명 생성
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"thermal_integration_{timestamp}.log"
log_file_path = os.path.join(LOG_DIR, log_filename)

# 로그 파일 열기
log_file = open(log_file_path, "w")

def log_data(text):
    """로그 기록"""
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    log_entry = f"[{t}] {text}\n"
    log_file.write(log_entry)
    log_file.flush()
    print(text)

class ThermalIntegration:
    def __init__(self):
        self.i2c = None
        self.ads = None
        self.thermistor_channel = None
        self.dht11 = None
        self.fir1 = None
        
        # Thermistor 보정 상수 (thermis.py와 동일하게)
        self.VCC = 3.3
        self.R_fix = 10000.0  # 고정 저항
        self.R0 = 10000.0     # 기준 저항
        self.T0 = 298.15      # 기준 온도 (25°C)
        self.B = 3435.0       # B-parameter
        
        self.initialized = False

    def init_sensors(self):
        """모든 온도 센서 초기화"""
        try:
            log_data("=== 통합 온도 센서 초기화 시작 ===")
            
            # I2C 초기화
            self.i2c = busio.I2C(board.SCL, board.SDA)
            log_data("I2C 버스 초기화 완료")
            
            # ADS1115 초기화 (Thermistor용) - thermis.py와 동일하게 P1 사용
            self.ads = ADS.ADS1115(self.i2c)
            self.ads.gain = 1  # ±4.096V
            self.thermistor_channel = AnalogIn(self.ads, ADS.P1)  # A1 채널 사용
            log_data("ADS1115 초기화 완료 (채널 P1)")
            
            # DHT11 초기화
            self.dht11 = adafruit_dht.DHT11(board.D4)  # GPIO4 사용
            log_data("DHT11 초기화 완료 (GPIO4)")
            
            # FIR 센서 초기화
            self._init_fir_sensors()
            
            self.initialized = True
            log_data("=== 모든 센서 초기화 완료 ===")
            
            return True
            
        except Exception as e:
            log_data(f"센서 초기화 오류: {e}")
            return False

    def _init_fir_sensors(self):
        """FIR 센서 초기화 (FIR1만 사용)"""
        try:
            import adafruit_mlx90614
            
            # FIR1 초기화 (직접 연결)
            try:
                self.fir1 = adafruit_mlx90614.MLX90614(self.i2c, address=0x5A)
                log_data("FIR1 (MLX90614) 초기화 성공 - 주소: 0x5A")
            except Exception as e:
                log_data(f"FIR1 초기화 실패: {e}")
                self.fir1 = None
            
            # FIR2는 사용하지 않음
            self.fir2 = None
                
        except ImportError as e:
            log_data(f"라이브러리 import 오류: {e}")
            log_data("설치: pip install adafruit-circuitpython-mlx90614")
            self.fir1 = None
            self.fir2 = None

    def read_thermistor(self):
        """Thermistor 온도 읽기 (thermis.py와 동일한 방식)"""
        try:
            if not self.thermistor_channel:
                return 0.0
                
            voltage = self.thermistor_channel.voltage
            
            # 전압 범위 검증
            if voltage <= 0.0 or voltage >= self.VCC:
                log_data(f"THERMISTOR_ERROR,Invalid voltage: {voltage:.4f} V")
                return 0.0
            
            # 저항 계산
            R_th = self.R_fix * (self.VCC - voltage) / voltage
            
            # 저항 비율 계산
            ratio = R_th / self.R0
            if ratio <= 0.0:
                log_data(f"THERMISTOR_ERROR,Invalid resistance ratio: R_th={R_th:.1f} Ω")
                return 0.0
            
            # 온도 계산 (Steinhart-Hart 방정식)
            T_kelvin = 1.0 / (1.0/self.T0 + (1.0/self.B) * log(ratio))
            T_celsius = T_kelvin - 273.15
            
            # 보정값 +50 추가
            T_celsius += 50.0
            
            return round(T_celsius, 2)
            
        except Exception as e:
            log_data(f"THERMISTOR_ERROR,{e}")
            return 0.0

    def read_dht11(self):
        """DHT11 온도/습도 읽기"""
        try:
            if not self.dht11:
                return 0.0, 0.0
                
            temperature = self.dht11.temperature
            humidity = self.dht11.humidity
            
            return temperature, humidity
            
        except Exception as e:
            log_data(f"DHT11_ERROR,{e}")
            return 0.0, 0.0

    def read_fir1(self):
        """FIR1 (MLX90614) 온도 읽기"""
        try:
            if not self.fir1:
                return 0.0, 0.0
                
            ambient_temp = self.fir1.ambient_temperature
            object_temp = self.fir1.object_temperature
            
            return ambient_temp, object_temp
            
        except Exception as e:
            log_data(f"FIR1_ERROR,{e}")
            return 0.0, 0.0

    def read_all_sensors(self):
        """모든 센서에서 데이터 읽기"""
        try:
            # Thermistor
            thermistor_temp = self.read_thermistor()
            
            # DHT11
            dht11_temp, dht11_humidity = self.read_dht11()
            
            # FIR1
            fir1_ambient, fir1_object = self.read_fir1()
            
            # 로그 기록
            log_data(f"SENSOR_DATA: Thermistor={thermistor_temp:.2f}°C, DHT11={dht11_temp:.2f}°C/{dht11_humidity:.1f}%, FIR1_Ambient={fir1_ambient:.2f}°C, FIR1_Object={fir1_object:.2f}°C")
            
            return {
                'thermistor': thermistor_temp,
                'dht11_temp': dht11_temp,
                'dht11_humidity': dht11_humidity,
                'fir1_ambient': fir1_ambient,
                'fir1_object': fir1_object
            }
            
        except Exception as e:
            log_data(f"전체 센서 읽기 오류: {e}")
            return {
                'thermistor': 0.0,
                'dht11_temp': 0.0,
                'dht11_humidity': 0.0,
                'fir1_ambient': 0.0,
                'fir1_object': 0.0
            }

    def scan_i2c_devices(self):
        """I2C 디바이스 스캔"""
        try:
            if not self.i2c:
                return []
                
            self.i2c.try_lock()
            devices = self.i2c.scan()
            self.i2c.unlock()
            
            log_data("I2C 디바이스 스캔 결과:")
            for device in devices:
                device_info = f"  주소: 0x{device:02X} ({device})"
                if device == 0x48:
                    device_info += " → ADS1115"
                elif device == 0x5A:
                    device_info += " → MLX90614"
                log_data(device_info)
                    
            return devices
            
        except Exception as e:
            log_data(f"I2C 스캔 오류: {e}")
            return []

    def terminate(self):
        """센서 종료"""
        try:
            if self.i2c:
                self.i2c.deinit()
            log_data("센서 종료 완료")
        except AttributeError:
            pass
        log_file.close()

def main():
    log_data("=== 통합 온도 센서 테스트 시작 ===")
    log_data("센서 목록:")
    log_data("  - Thermistor (ADS1115)")
    log_data("  - DHT11 (온도/습도)")
    log_data("  - FIR1 (MLX90614)")
    log_data("=" * 60)
    
    # 센서 초기화
    thermal = ThermalIntegration()
    
    # I2C 디바이스 스캔
    devices = thermal.scan_i2c_devices()
    
    if not thermal.init_sensors():
        log_data("센서 초기화 실패")
        return
    
    log_data("=== 센서 데이터 읽기 시작 ===")
    
    try:
        while True:
            data = thermal.read_all_sensors()
            
            # 콘솔 출력 (한 줄로 간단하게)
            print(f"Thermistor: {data['thermistor']:.2f}°C | DHT11: {data['dht11_temp']:.2f}°C/{data['dht11_humidity']:.1f}% | FIR1: {data['fir1_ambient']:.2f}°C/{data['fir1_object']:.2f}°C")
            
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        log_data("테스트 중단됨 (Ctrl+C)")
    finally:
        thermal.terminate()
        log_data("=== 테스트 종료 ===")

if __name__ == "__main__":
    main() 