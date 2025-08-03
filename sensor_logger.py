#!/usr/bin/env python3
"""
Multi-Sensor Logger with Dual Logging
DHT11, AS7263, FIR 센서를 동시에 읽고 CSV로 저장 (이중 로깅 지원)
"""

import time
import csv
import os
from datetime import datetime
import board
import busio
import adafruit_dht
import adafruit_as7263
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import shutil

class MultiSensorLogger:
    def __init__(self, primary_log_dir="sensorlogs", secondary_log_dir="/mnt/log_sd/sensorlogs"):
        self.primary_log_dir = primary_log_dir
        self.secondary_log_dir = secondary_log_dir
        
        # 로그 디렉토리 생성
        os.makedirs(self.primary_log_dir, exist_ok=True)
        try:
            os.makedirs(self.secondary_log_dir, exist_ok=True)
            self.secondary_sd_available = True
        except Exception as e:
            print(f"보조 SD카드 로그 디렉토리 생성 실패: {e}")
            self.secondary_sd_available = False
        
        # CSV 파일명 생성 (날짜_시간)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.primary_csv_filename = os.path.join(self.primary_log_dir, f"multi_sensor_{timestamp}.csv")
        self.secondary_csv_filename = os.path.join(self.secondary_log_dir, f"multi_sensor_{timestamp}.csv")
        
        # 센서 초기화
        self.init_sensors()
        
        # CSV 헤더 작성
        self.write_csv_header()
        
    def init_sensors(self):
        """모든 센서 초기화"""
        try:
            # I2C 버스 초기화
            self.i2c = busio.I2C(board.SCL, board.SDA)
            
            # DHT11 센서 (GPIO 핀 사용)
            self.dht = adafruit_dht.DHT11(board.D4)  # GPIO4 사용
            
            # AS7263 스펙트럼 센서
            self.as7263 = adafruit_as7263.AS7263(self.i2c)
            
            # ADS1115 (FIR 센서용)
            self.ads = ADS.ADS1115(self.i2c)
            self.ads.gain = 1  # ±4.096V 범위
            self.ads.data_rate = 128  # 128 SPS
            
            # FIR 센서 채널
            self.fir_chan0 = AnalogIn(self.ads, ADS.P0)  # FIR 센서
            self.fir_chan1 = AnalogIn(self.ads, ADS.P1)  # 보조 채널
            
            print("모든 센서 초기화 완료!")
            
        except Exception as e:
            print(f"센서 초기화 오류: {e}")
            raise
    
    def write_csv_header(self):
        """CSV 파일 헤더 작성 (이중 저장)"""
        headers = [
            'timestamp',
            'dht11_temp', 'dht11_humidity',
            'as7263_violet', 'as7263_blue', 'as7263_green', 'as7263_yellow', 'as7263_orange', 'as7263_red',
            'fir_voltage', 'fir_temp'
        ]
        
        # 메인 CSV 파일 생성
        with open(self.primary_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
        
        print(f"메인 CSV 파일 생성: {self.primary_csv_filename}")
        
        # 보조 CSV 파일 생성 (SD카드 사용 가능한 경우만)
        if self.secondary_sd_available:
            try:
                with open(self.secondary_csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(headers)
                print(f"보조 CSV 파일 생성: {self.secondary_csv_filename}")
            except Exception as e:
                print(f"보조 CSV 파일 생성 실패: {e}")
                self.secondary_sd_available = False
    
    def read_dht11(self):
        """DHT11 센서 읽기"""
        try:
            temperature = self.dht.temperature
            humidity = self.dht.humidity
            return temperature, humidity
        except Exception as e:
            print(f"DHT11 읽기 오류: {e}")
            return None, None
    
    def read_as7263(self):
        """AS7263 스펙트럼 센서 읽기"""
        try:
            # 모든 색상 채널 읽기
            violet = self.as7263.violet
            blue = self.as7263.blue
            green = self.as7263.green
            yellow = self.as7263.yellow
            orange = self.as7263.orange
            red = self.as7263.red
            
            return violet, blue, green, yellow, orange, red
        except Exception as e:
            print(f"AS7263 읽기 오류: {e}")
            return None, None, None, None, None, None
    
    def read_fir(self):
        """FIR 센서 읽기"""
        try:
            voltage = self.fir_chan0.voltage
            
            # 음수 전압 처리
            if voltage < 0:
                voltage = 0.0
            
            # 간단한 선형 변환 (전압 → 온도)
            temp = voltage * 100.0  # 0V = 0°C, 3.3V = 330°C
            
            return voltage, temp
        except Exception as e:
            print(f"FIR 센서 읽기 오류: {e}")
            return None, None
    
    def log_data(self):
        """모든 센서 데이터 읽기 및 CSV 저장 (이중 저장)"""
        timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")
        
        # 센서 데이터 읽기
        dht_temp, dht_humidity = self.read_dht11()
        as7263_data = self.read_as7263()
        fir_voltage, fir_temp = self.read_fir()
        
        # CSV에 데이터 저장
        row = [
            timestamp,
            dht_temp if dht_temp is not None else "ERROR",
            dht_humidity if dht_humidity is not None else "ERROR",
            as7263_data[0] if as7263_data[0] is not None else "ERROR",
            as7263_data[1] if as7263_data[1] is not None else "ERROR",
            as7263_data[2] if as7263_data[2] is not None else "ERROR",
            as7263_data[3] if as7263_data[3] is not None else "ERROR",
            as7263_data[4] if as7263_data[4] is not None else "ERROR",
            as7263_data[5] if as7263_data[5] is not None else "ERROR",
            fir_voltage if fir_voltage is not None else "ERROR",
            fir_temp if fir_temp is not None else "ERROR"
        ]
        
        # 메인 CSV 파일에 저장
        try:
            with open(self.primary_csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(row)
        except Exception as e:
            print(f"메인 CSV 파일 쓰기 오류: {e}")
        
        # 보조 CSV 파일에 저장 (SD카드 사용 가능한 경우만)
        if self.secondary_sd_available:
            try:
                with open(self.secondary_csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(row)
            except Exception as e:
                print(f"보조 CSV 파일 쓰기 오류: {e}")
                self.secondary_sd_available = False
        
        # 콘솔 출력
        print(f"[{timestamp}]")
        print(f"DHT11: {dht_temp}°C, {dht_humidity}%")
        print(f"AS7263: V{as7263_data[0]:.1f} B{as7263_data[1]:.1f} G{as7263_data[2]:.1f} Y{as7263_data[3]:.1f} O{as7263_data[4]:.1f} R{as7263_data[5]:.1f}")
        print(f"FIR: {fir_voltage:.5f}V → {fir_temp:.2f}°C")
        print("-" * 50)
    
    def run(self, interval=1.0):
        """센서 로깅 실행"""
        print("멀티 센서 로깅 시작...")
        print(f"저장 위치: {self.csv_filename}")
        print(f"간격: {interval}초")
        print("Ctrl+C로 종료")
        print("=" * 60)
        
        try:
            while True:
                self.log_data()
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n로깅 종료")
            self.cleanup()
    
    def cleanup(self):
        """리소스 정리"""
        try:
            self.i2c.deinit()
            print("I2C 연결 해제 완료")
        except:
            pass

def main():
    logger = MultiSensorLogger()
    logger.run(interval=1.0)  # 1초 간격으로 로깅

if __name__ == "__main__":
    main() 