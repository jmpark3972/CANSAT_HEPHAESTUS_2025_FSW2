import time
import os
import csv
from datetime import datetime
import signal
import sys

import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# NIR 센서 보정 상수
V_IN = 1.621  # 분압 전원
R_REF = 1000.0  # 직렬 기준저항
ALPHA_NI = 0.006178  # 6178 ppm/K
SENS_IR = 0.0034  # [V/°C] - 실측해 맞춘 감도
NIR_OFFSET = 835.0  # 보정값 (V) - 손/책상 온도 보정
NIR_SENSITIVITY = 1  # 감도: 전압 → 온도 변환 계수

# Thermistor 보정 상수
THERMISTOR_BETA = 3950  # Beta 값
THERMISTOR_R0 = 10000  # 25°C에서의 저항값 (Ω)
THERMISTOR_T0 = 298.15  # 25°C (Kelvin)
V_REF = 3.3  # 기준 전압

class IntegratedSensorLogger:
    def __init__(self):
        self.log_dir = "sensorlogs"
        os.makedirs(self.log_dir, exist_ok=True)
        
        # CSV 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = os.path.join(self.log_dir, f"integrated_sensor_log_{timestamp}.csv")
        
        # 센서 초기화
        self.init_sensors()
        self.write_csv_header()
        
        # 종료 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        print(f"통합 센서 로거 시작: {self.csv_filename}")
        print("Ctrl+C로 종료하면 모든 데이터가 로그에 저장됩니다.")
    
    def init_sensors(self):
        """모든 센서 초기화"""
        try:
            # I2C 버스 초기화
            self.i2c = busio.I2C(board.SCL, board.SDA)
            
            # ADS1115 ADC 초기화
            self.ads = ADS.ADS1115(self.i2c)
            self.ads.gain = 1  # ±4.096V 범위
            self.ads.data_rate = 128  # 128 SPS
            
            # ADS1115 채널 설정
            # P0: G-TPCO-035 (NIR 열전소자)
            # P1: Thermistor
            # P2: FIR 센서 (MLX90614)
            self.nir_chan = AnalogIn(self.ads, ADS.P0)
            self.thermistor_chan = AnalogIn(self.ads, ADS.P1)
            self.fir_chan = AnalogIn(self.ads, ADS.P2)
            
            print("✅ 모든 센서 초기화 완료")
            
        except Exception as e:
            print(f"❌ 센서 초기화 오류: {e}")
            sys.exit(1)
    
    def write_csv_header(self):
        """CSV 파일 헤더 작성"""
        headers = [
            "Timestamp",
            "Thermistor_Temp(°C)", "Thermistor_Voltage(V)", "Thermistor_Resistance(Ω)",
            "FIR_Temp(°C)", "FIR_Voltage(V)",
            "NIR_Temp(°C)", "NIR_Voltage(V)"
        ]
        
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
    
    def read_thermistor(self):
        """Thermistor 온도 센서 읽기"""
        try:
            voltage = self.thermistor_chan.voltage
            
            # 전압을 저항으로 변환 (분압 회로)
            resistance = R_REF * voltage / (V_REF - voltage)
            
            # Steinhart-Hart 방정식으로 온도 계산
            if resistance > 0:
                steinhart = resistance / THERMISTOR_R0
                steinhart = (steinhart ** (1/THERMISTOR_BETA))
                temperature = (1 / steinhart - THERMISTOR_T0) + 25
            else:
                temperature = "ERROR"
            
            return temperature, voltage, resistance
        except Exception as e:
            print(f"Thermistor 읽기 오류: {e}")
            return "ERROR", "ERROR", "ERROR"
    
    def read_fir(self):
        """FIR 적외선 온도 센서 읽기"""
        try:
            voltage = self.fir_chan.voltage
            
            # 간단한 선형 변환 (실제로는 센서별 보정 필요)
            # MLX90614의 경우 보통 10mV/°C 정도
            temperature = voltage * 100  # 10mV/°C 가정
            
            return temperature, voltage
        except Exception as e:
            print(f"FIR 읽기 오류: {e}")
            return "ERROR", "ERROR"
    
    def read_nir(self):
        """NIR 열전소자 센서 읽기"""
        try:
            voltage = self.nir_chan.voltage
            
            # NIR 보정식 적용
            temperature = (voltage - V_IN) * 500 + NIR_OFFSET
            
            return temperature, voltage
        except Exception as e:
            print(f"NIR 읽기 오류: {e}")
            return "ERROR", "ERROR"
    
    def log_data(self):
        """모든 센서 데이터 읽기 및 로그 저장"""
        timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")
        
        # 각 센서에서 데이터 읽기
        therm_temp, therm_voltage, therm_resistance = self.read_thermistor()
        fir_temp, fir_voltage = self.read_fir()
        nir_temp, nir_voltage = self.read_nir()
        
        # CSV에 데이터 저장
        data_row = [
            timestamp,
            therm_temp, therm_voltage, therm_resistance,
            fir_temp, fir_voltage,
            nir_temp, nir_voltage
        ]
        
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(data_row)
        
        # 콘솔 출력
        print(f"\n[{timestamp}]")
        print(f"Thermistor: {therm_temp}°C ({therm_voltage:.4f}V, {therm_resistance:.1f}Ω)")
        print(f"FIR: {fir_temp}°C ({fir_voltage:.4f}V)")
        print(f"NIR: {nir_temp}°C ({nir_voltage:.4f}V)")
        print("-" * 50)
    
    def signal_handler(self, signum, frame):
        """종료 시그널 처리"""
        print(f"\n\n🛑 종료 신호 수신 (Signal: {signum})")
        print("📊 최종 데이터 로깅 중...")
        
        # 마지막 데이터 로깅
        self.log_data()
        
        # 정리 작업
        self.cleanup()
        
        print(f"✅ 모든 데이터가 {self.csv_filename}에 저장되었습니다.")
        print("👋 프로그램을 종료합니다.")
        sys.exit(0)
    
    def cleanup(self):
        """리소스 정리"""
        try:
            self.i2c.deinit()
        except:
            pass
    
    def run(self, interval=1.0):
        """메인 실행 루프"""
        print(f"🔄 {interval}초 간격으로 센서 데이터를 읽습니다...")
        
        try:
            while True:
                self.log_data()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n\n⌨️  KeyboardInterrupt 감지")
            self.signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    logger = IntegratedSensorLogger()
    logger.run(interval=1.0) 