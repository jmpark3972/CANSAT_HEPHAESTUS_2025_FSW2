#!/usr/bin/env python3
"""
IMU 센서 직접 테스트 스크립트
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

def test_imu():
    """IMU 센서 직접 테스트"""
    print("IMU 센서 테스트 시작...")
    
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
        
        # IMU 센서 초기화 (여러 주소 시도)
        imu_addresses = [0x28, 0x29, 0x68, 0x69]  # 일반적인 IMU 주소들
        imu = None
        
        for addr in imu_addresses:
            try:
                print(f"IMU I2C 주소 0x{addr:02X} 시도 중...")
                
                # MPU6050/MPU9250 시도
                try:
                    import adafruit_mpu6050
                    imu = adafruit_mpu6050.MPU6050(i2c, address=addr)
                    print(f"✓ MPU6050/MPU9250 초기화 성공 (주소: 0x{addr:02X})")
                    break
                except:
                    pass
                
                # ICM20948 시도
                try:
                    import adafruit_icm20x
                    imu = adafruit_icm20x.ICM20948(i2c, address=addr)
                    print(f"✓ ICM20948 초기화 성공 (주소: 0x{addr:02X})")
                    break
                except:
                    pass
                    
            except Exception as e:
                print(f"주소 0x{addr:02X} 실패: {e}")
                continue
        
        if imu is None:
            print("✗ IMU 센서를 찾을 수 없습니다.")
            return False
        
        # 센서 읽기 테스트
        print("\n센서 읽기 테스트 (10회):")
        for i in range(10):
            try:
                # 가속도계
                accel = imu.acceleration
                # 자이로스코프
                gyro = imu.gyro
                
                print(f"  {i+1:2d}: 가속도=({accel[0]:.2f}, {accel[1]:.2f}, {accel[2]:.2f})m/s²")
                print(f"      자이로=({gyro[0]:.2f}, {gyro[1]:.2f}, {gyro[2]:.2f})°/s")
                
                # 자력계가 있는 경우
                try:
                    mag = imu.magnetic
                    print(f"      자력계=({mag[0]:.2f}, {mag[1]:.2f}, {mag[2]:.2f})μT")
                except:
                    print(f"      자력계=사용 불가")
                
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        print("\n✓ IMU 센서 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ IMU 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_imu() 