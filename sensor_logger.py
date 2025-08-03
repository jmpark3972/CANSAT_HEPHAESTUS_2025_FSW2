#!/usr/bin/env python3
"""
Multi-Sensor Logger with Dual Logging
DHT11, FIR 센서를 동시에 읽고 CSV로 저장 (이중 로깅 지원)
Qwiic Mux를 통해 FIR 센서 두 개 사용
"""

import time
import csv
import os
from datetime import datetime
import board
import busio
import adafruit_dht
import adafruit_mlx90614
import shutil
from lib.qwiic_mux import QwiicMux

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
            
            # Qwiic Mux 초기화
            self.mux = QwiicMux(i2c_bus=self.i2c, mux_address=0x70)
            
            # FIR1 센서 (채널 0)
            self.mux.select_channel(0)
            time.sleep(0.1)  # 안정화 대기
            self.fir1 = adafruit_mlx90614.MLX90614(self.i2c)
            
            # FIR2 센서 (채널 1)
            self.mux.select_channel(1)
            time.sleep(0.1)  # 안정화 대기
            self.fir2 = adafruit_mlx90614.MLX90614(self.i2c)
            
            print("모든 센서 초기화 완료!")
            
        except Exception as e:
            print(f"센서 초기화 오류: {e}")
            raise
    
    def write_csv_header(self):
        """CSV 파일 헤더 작성 (이중 저장)"""
        headers = [
            'timestamp',
            'dht11_temp', 'dht11_humidity',
            'fir1_ambient', 'fir1_object',
            'fir2_ambient', 'fir2_object'
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
    
    def read_fir1(self):
        """FIR1 센서 읽기 (채널 0)"""
        try:
            # 채널 0 선택
            self.mux.select_channel(0)
            time.sleep(0.01)  # 안정화 대기
            
            ambient = round(float(self.fir1.ambient_temperature), 2)
            object_temp = round(float(self.fir1.object_temperature), 2)
            
            return ambient, object_temp
        except Exception as e:
            print(f"FIR1 센서 읽기 오류: {e}")
            return None, None
    
    def read_fir2(self):
        """FIR2 센서 읽기 (채널 1)"""
        try:
            # 채널 1 선택
            self.mux.select_channel(1)
            time.sleep(0.01)  # 안정화 대기
            
            ambient = round(float(self.fir2.ambient_temperature), 2)
            object_temp = round(float(self.fir2.object_temperature), 2)
            
            return ambient, object_temp
        except Exception as e:
            print(f"FIR2 센서 읽기 오류: {e}")
            return None, None
    
    def log_data(self):
        """모든 센서 데이터 읽기 및 CSV 저장 (이중 저장)"""
        timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")
        
        # 센서 데이터 읽기
        dht_temp, dht_humidity = self.read_dht11()
        fir1_amb, fir1_obj = self.read_fir1()
        fir2_amb, fir2_obj = self.read_fir2()
        
        # CSV에 데이터 저장
        row = [
            timestamp,
            dht_temp if dht_temp is not None else "ERROR",
            dht_humidity if dht_humidity is not None else "ERROR",
            fir1_amb if fir1_amb is not None else "ERROR",
            fir1_obj if fir1_obj is not None else "ERROR",
            fir2_amb if fir2_amb is not None else "ERROR",
            fir2_obj if fir2_obj is not None else "ERROR"
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
        print(f"FIR1: {fir1_amb}°C (amb), {fir1_obj}°C (obj)")
        print(f"FIR2: {fir2_amb}°C (amb), {fir2_obj}°C (obj)")
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
            if hasattr(self, 'mux'):
                self.mux.close()
            if hasattr(self, 'i2c') and hasattr(self.i2c, 'deinit'):
                self.i2c.deinit()
            print("센서 연결 해제 완료")
        except:
            pass

def main():
    logger = MultiSensorLogger()
    logger.run(interval=1.0)  # 1초 간격으로 로깅

if __name__ == "__main__":
    main() 