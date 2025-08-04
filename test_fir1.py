#!/usr/bin/env python3
"""FIR1 센서 직접 테스트"""

import time
import board
import busio
import adafruit_mlx90614

def test_fir1():
    print("FIR1 센서 테스트 시작...")
    
    try:
        # I2C 설정
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("I2C 초기화 완료")
        
        # FIR1 센서 초기화
        sensor = adafruit_mlx90614.MLX90614(i2c, address=0x5a)
        print("FIR1 센서 초기화 완료 (주소: 0x5a)")
        
        # 데이터 읽기 테스트
        for i in range(10):
            try:
                ambient_temp = sensor.ambient_temperature
                object_temp = sensor.object_temperature
                print(f"읽기 {i+1}: Ambient={ambient_temp:.2f}°C, Object={object_temp:.2f}°C")
            except Exception as e:
                print(f"읽기 {i+1} 실패: {e}")
            
            time.sleep(1)
            
    except Exception as e:
        print(f"FIR1 테스트 실패: {e}")

if __name__ == "__main__":
    test_fir1() 