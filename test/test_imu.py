#!/usr/bin/env python3
"""
IMU 센서 (BNO055) 직접 테스트 스크립트
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

def test_imu():
    """IMU 센서 (BNO055) 직접 테스트"""
    print("IMU 센서 (BNO055) 테스트 시작...")
    
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
        
        # BNO055 센서 초기화 (0x28 주소)
        try:
            import adafruit_bno055
            imu = adafruit_bno055.BNO055_I2C(i2c, address=0x28)
            print("✓ BNO055 초기화 성공 (주소: 0x28)")
        except ImportError:
            print("✗ adafruit_bno055 모듈이 설치되지 않았습니다.")
            print("설치 명령: pip install adafruit-circuitpython-bno055")
            return False
        except Exception as e:
            print(f"✗ BNO055 초기화 실패: {e}")
            return False
        
        # 센서 안정화 대기
        time.sleep(1.0)
        
        # 센서 읽기 테스트
        print("\n센서 읽기 테스트 (10회):")
        for i in range(10):
            try:
                # 쿼터니언
                quaternion = imu.quaternion
                if quaternion[0] is not None:
                    w, x, y, z = quaternion
                    print(f"  {i+1:2d}: 쿼터니언=({w:.3f}, {x:.3f}, {y:.3f}, {z:.3f})")
                else:
                    print(f"  {i+1:2d}: 쿼터니언=사용 불가")
                
                # 오일러 각도
                euler = imu.euler
                if euler[0] is not None:
                    roll, pitch, yaw = euler
                    print(f"      오일러=({roll:.2f}°, {pitch:.2f}°, {yaw:.2f}°)")
                else:
                    print(f"      오일러=사용 불가")
                
                # 가속도계
                accel = imu.acceleration
                if accel[0] is not None:
                    print(f"      가속도=({accel[0]:.2f}, {accel[1]:.2f}, {accel[2]:.2f})m/s²")
                else:
                    print(f"      가속도=사용 불가")
                
                # 자이로스코프
                gyro = imu.gyro
                if gyro[0] is not None:
                    print(f"      자이로=({gyro[0]:.2f}, {gyro[1]:.2f}, {gyro[2]:.2f})°/s")
                else:
                    print(f"      자이로=사용 불가")
                
                # 자력계
                mag = imu.magnetic
                if mag[0] is not None:
                    print(f"      자력계=({mag[0]:.2f}, {mag[1]:.2f}, {mag[2]:.2f})μT")
                else:
                    print(f"      자력계=사용 불가")
                
                # 온도
                temp = imu.temperature
                if temp is not None:
                    print(f"      온도={temp:.1f}°C")
                else:
                    print(f"      온도=사용 불가")
                
                # 온도 센서 상태 확인
                try:
                    temp_status = imu.temperature_source
                    print(f"      온도소스={temp_status}")
                except:
                    print(f"      온도소스=확인 불가")
                
                print()
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        print("\n✓ IMU 센서 (BNO055) 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ IMU 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_imu() 