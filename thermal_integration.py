#!/usr/bin/env python3
"""
통합 온도 센서 모듈
- Thermistor (ADS1115)
- DHT11 (온도/습도)
- FIR1, FIR2 (MLX90614 - 주소 변경 고려)
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
thermal_log = open(os.path.join(LOG_DIR, "thermal_integration.txt"), "a")

def log_thermal(text):
    """온도 센서 로그 기록"""
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    thermal_log.write(f"{t},{text}\n")
    thermal_log.flush()

class ThermalIntegration:
    def __init__(self):
        self.i2c = None
        self.ads = None
        self.thermistor_channel = None
        self.dht11 = None
        self.fir1 = None
        self.fir2 = None
        
        # Thermistor 보정 상수 (thermis.py와 동일하게)
        self.VCC = 3.3
        self.R_fix = 10000.0  # 고정 저항
        self.R0 = 10000.0     # 기준 저항
        self.T0 = 298.15      # 기준 온도 (25°C)
        self.B = 3435.0       # B-parameter
        
        # FIR 센서 주소 (기본값, 필요시 변경)
        self.FIR1_ADDRESS = 0x5A  # 기본 주소
        self.FIR2_ADDRESS = 0x5B  # 변경된 주소
        
        self.initialized = False

    def init_sensors(self):
        """모든 온도 센서 초기화"""
        try:
            # I2C 초기화
            self.i2c = busio.I2C(board.SCL, board.SDA)
            
            # ADS1115 초기화 (Thermistor용) - thermis.py와 동일하게 P1 사용
            self.ads = ADS.ADS1115(self.i2c)
            self.ads.gain = 1  # ±4.096V
            self.thermistor_channel = AnalogIn(self.ads, ADS.P1)  # A1 채널 사용
            
            # DHT11 초기화
            self.dht11 = adafruit_dht.DHT11(board.D4)  # GPIO4 사용
            
            # FIR 센서들 초기화 (MLX90614)
            self._init_fir_sensors()
            
            self.initialized = True
            log_thermal("All thermal sensors initialized successfully")
            print("모든 온도 센서 초기화 완료")
            
            return True
            
        except Exception as e:
            log_thermal(f"ERROR,{e}")
            print(f"센서 초기화 오류: {e}")
            return False

    def _init_fir_sensors(self):
        """FIR 센서들 초기화 (TCA9548A 멀티플렉서 지원)"""
        try:
            import adafruit_mlx90614
            import adafruit_tca9548a
            
            # TCA9548A 멀티플렉서 확인
            try:
                self.tca = adafruit_tca9548a.TCA9548A(self.i2c)
                print("TCA9548A 멀티플렉서 발견 - 채널 분할 모드")
                
                # FIR1 초기화 (채널 0)
                try:
                    self.fir1 = adafruit_mlx90614.MLX90614(self.tca[0])
                    print("FIR1 (MLX90614) 초기화 성공 - TCA9548A 채널 0")
                except Exception as e:
                    print(f"FIR1 초기화 실패: {e}")
                    self.fir1 = None
                
                # FIR2 초기화 (채널 1)
                try:
                    self.fir2 = adafruit_mlx90614.MLX90614(self.tca[1])
                    print("FIR2 (MLX90614) 초기화 성공 - TCA9548A 채널 1")
                except Exception as e:
                    print(f"FIR2 초기화 실패: {e}")
                    self.fir2 = None
                    
            except Exception as e:
                print("TCA9548A 멀티플렉서 없음 - 직접 연결 모드")
                
                # 직접 연결된 MLX90614 초기화
                try:
                    self.fir1 = adafruit_mlx90614.MLX90614(self.i2c, address=self.FIR1_ADDRESS)
                    print(f"FIR1 (MLX90614) 초기화 성공 - 주소: 0x{self.FIR1_ADDRESS:02X}")
                except Exception as e:
                    print(f"FIR1 초기화 실패: {e}")
                    self.fir1 = None
                
                # FIR2는 연결되지 않음
                print("FIR2 (MLX90614) 연결되지 않음")
                self.fir2 = None
                
        except ImportError as e:
            print(f"라이브러리 import 오류: {e}")
            print("설치: pip install adafruit-circuitpython-mlx90614 adafruit-circuitpython-tca9548a")
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
                log_thermal(f"THERMISTOR_ERROR,Invalid voltage: {voltage:.4f} V")
                return 0.0
            
            # 저항 계산
            R_th = self.R_fix * (self.VCC - voltage) / voltage
            
            # 저항 비율 계산
            ratio = R_th / self.R0
            if ratio <= 0.0:
                log_thermal(f"THERMISTOR_ERROR,Invalid resistance ratio: R_th={R_th:.1f} Ω")
                return 0.0
            
            # 온도 계산 (Steinhart-Hart 방정식)
            T_kelvin = 1.0 / (1.0/self.T0 + (1.0/self.B) * log(ratio))
            T_celsius = T_kelvin - 273.15
            
            # 보정값 +50 추가
            T_celsius += 50.0
            
            return round(T_celsius, 2)
            
        except Exception as e:
            log_thermal(f"THERMISTOR_ERROR,{e}")
            print(f"Thermistor 읽기 오류: {e}")
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
            log_thermal(f"DHT11_ERROR,{e}")
            print(f"DHT11 읽기 오류: {e}")
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
            log_thermal(f"FIR1_ERROR,{e}")
            print(f"FIR1 읽기 오류: {e}")
            return 0.0, 0.0

    def read_fir2(self):
        """FIR2 (MLX90614) 온도 읽기"""
        try:
            if not self.fir2:
                return 0.0, 0.0
                
            ambient_temp = self.fir2.ambient_temperature
            object_temp = self.fir2.object_temperature
            
            return ambient_temp, object_temp
            
        except Exception as e:
            log_thermal(f"FIR2_ERROR,{e}")
            print(f"FIR2 읽기 오류: {e}")
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
            
            # FIR2
            fir2_ambient, fir2_object = self.read_fir2()
            
            # 로그 기록
            log_thermal(f"DATA,{thermistor_temp:.2f},{dht11_temp:.2f},{dht11_humidity:.1f},{fir1_ambient:.2f},{fir1_object:.2f},{fir2_ambient:.2f},{fir2_object:.2f}")
            
            return {
                'thermistor': thermistor_temp,
                'dht11_temp': dht11_temp,
                'dht11_humidity': dht11_humidity,
                'fir1_ambient': fir1_ambient,
                'fir1_object': fir1_object,
                'fir2_ambient': fir2_ambient,
                'fir2_object': fir2_object
            }
            
        except Exception as e:
            log_thermal(f"ERROR,{e}")
            print(f"전체 센서 읽기 오류: {e}")
            return {
                'thermistor': 0.0,
                'dht11_temp': 0.0,
                'dht11_humidity': 0.0,
                'fir1_ambient': 0.0,
                'fir1_object': 0.0,
                'fir2_ambient': 0.0,
                'fir2_object': 0.0
            }

    def set_fir_addresses(self, fir1_addr, fir2_addr):
        """FIR 센서 주소 설정"""
        self.FIR1_ADDRESS = fir1_addr
        self.FIR2_ADDRESS = fir2_addr
        log_thermal(f"FIR_ADDR_SET,{fir1_addr},{fir2_addr}")
        print(f"FIR 센서 주소 설정: FIR1=0x{fir1_addr:02X}, FIR2=0x{fir2_addr:02X}")

    def scan_i2c_devices(self):
        """I2C 디바이스 스캔"""
        try:
            if not self.i2c:
                return []
                
            self.i2c.try_lock()
            devices = self.i2c.scan()
            self.i2c.unlock()
            
            print("I2C 디바이스 스캔 결과:")
            for device in devices:
                print(f"  주소: 0x{device:02X} ({device})")
                if device == 0x48:
                    print("    → ADS1115")
                elif device == 0x5A:
                    print("    → MLX90614 (기본 주소)")
                elif device == 0x5B:
                    print("    → MLX90614 (변경된 주소)")
                    
            return devices
            
        except Exception as e:
            print(f"I2C 스캔 오류: {e}")
            return []

    def terminate(self):
        """센서 종료"""
        try:
            if self.i2c:
                self.i2c.deinit()
        except AttributeError:
            pass
        thermal_log.close()

def main():
    print("통합 온도 센서 테스트")
    print("=" * 60)
    print("센서 목록:")
    print("  - Thermistor (ADS1115)")
    print("  - DHT11 (온도/습도)")
    print("  - FIR1 (MLX90614)")
    print("  - FIR2 (MLX90614)")
    print("=" * 60)
    
    # 센서 초기화
    thermal = ThermalIntegration()
    
    # I2C 디바이스 스캔
    devices = thermal.scan_i2c_devices()
    
    if not thermal.init_sensors():
        print("센서 초기화 실패")
        return
    
    try:
        while True:
            data = thermal.read_all_sensors()
            
            print(f"\n=== 온도 센서 데이터 ===")
            print(f"Thermistor: {data['thermistor']:.2f}°C")
            print(f"DHT11:      {data['dht11_temp']:.2f}°C, {data['dht11_humidity']:.1f}%")
            print(f"FIR1:       Ambient={data['fir1_ambient']:.2f}°C, Object={data['fir1_object']:.2f}°C")
            print(f"FIR2:       Ambient={data['fir2_ambient']:.2f}°C, Object={data['fir2_object']:.2f}°C")
            print("-" * 60)
            
            time.sleep(2.0)
            
    except KeyboardInterrupt:
        print("\n테스트 중단")
    finally:
        thermal.terminate()

if __name__ == "__main__":
    main() 