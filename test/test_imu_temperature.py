#!/usr/bin/env python3
"""
BNO055 Temperature Reading Test
Tests the BNO055 temperature sensor reading functionality
"""

import time
import board
import busio
import adafruit_bno055
from lib.qwiic_mux import QwiicMux

def test_bno055_temperature():
    """BNO055 온도 센서 테스트"""
    print("BNO055 온도 센서 테스트 시작...")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C 버스 초기화 성공")
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        print("✓ Qwiic Mux 초기화 성공")
        
        # 채널 4 선택 (IMU 위치)
        mux.select_channel(4)
        print("✓ 채널 4 선택 완료")
        time.sleep(0.1)
        
        # BNO055 센서 초기화
        try:
            imu = adafruit_bno055.BNO055_I2C(i2c, address=0x28)
            print("✓ BNO055 초기화 성공 (주소: 0x28)")
        except Exception as e:
            print(f"✗ BNO055 초기화 실패: {e}")
            return False
        
        # 센서 안정화 대기
        time.sleep(1.0)
        
        # 온도 읽기 테스트 (20회)
        print("\n온도 읽기 테스트 (20회):")
        temperatures = []
        
        for i in range(20):
            try:
                # 온도 읽기
                temp = imu.temperature
                if temp is not None:
                    temperatures.append(temp)
                    print(f"  {i+1:2d}: 온도={temp:.2f}°C")
                else:
                    print(f"  {i+1:2d}: 온도=사용 불가")
                
                # 온도 소스 확인 (가능한 경우)
                try:
                    temp_source = imu.temperature_source
                    print(f"      온도소스={temp_source}")
                except:
                    pass
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        # 통계 계산
        if temperatures:
            avg_temp = sum(temperatures) / len(temperatures)
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            
            print(f"\n온도 통계:")
            print(f"  평균: {avg_temp:.2f}°C")
            print(f"  최소: {min_temp:.2f}°C")
            print(f"  최대: {max_temp:.2f}°C")
            print(f"  범위: {max_temp - min_temp:.2f}°C")
            print(f"  샘플 수: {len(temperatures)}")
        
        print("\n✓ BNO055 온도 센서 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ BNO055 온도 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_bno055_temperature() 