#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""IMU 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from imu import imu

def test_imu():
    """IMU 센서 테스트"""
    print("=" * 50)
    print("IMU 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. IMU 센서 초기화 중...")
        i2c, imu_sensor = imu.init_imu()
        
        if imu_sensor is None:
            print("❌ IMU 초기화 실패")
            return False
            
        print("✅ IMU 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                gyro_x, gyro_y, gyro_z, accel_x, accel_y, accel_z, mag_x, mag_y, mag_z, temp = imu.read_imu(imu_sensor)
                
                print(f"📊 IMU 데이터:")
                print(f"   자이로스코프: X={gyro_x:.3f}, Y={gyro_y:.3f}, Z={gyro_z:.3f} °/s")
                print(f"   가속도계: X={accel_x:.3f}, Y={accel_y:.3f}, Z={accel_z:.3f} m/s²")
                print(f"   자기계: X={mag_x:.3f}, Y={mag_y:.3f}, Z={mag_z:.3f} μT")
                print(f"   온도: {temp:.2f} °C")
                print("-" * 30)
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 데이터 읽기 오류: {e}")
                time.sleep(1)
        
        # 정리
        print("\n3. 센서 정리 중...")
        imu.terminate_imu(i2c)
        print("✅ IMU 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ IMU 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_imu() 