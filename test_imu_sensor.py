#!/usr/bin/env python3
"""
IMU 센서 테스트 스크립트
"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(__file__))

def test_imu_initialization():
    """IMU 센서 초기화 테스트"""
    print("=== IMU 센서 초기화 테스트 ===")
    try:
        from imu import imu
        i2c, sensor = imu.init_imu()
        if i2c and sensor:
            print("✅ IMU 센서 초기화 성공")
            return i2c, sensor
        else:
            print("❌ IMU 센서 초기화 실패")
            return None, None
    except Exception as e:
        print(f"❌ IMU 센서 초기화 오류: {e}")
        return None, None

def test_imu_data_reading(sensor):
    """IMU 데이터 읽기 테스트"""
    print("\n=== IMU 데이터 읽기 테스트 ===")
    if not sensor:
        print("❌ 센서가 초기화되지 않음")
        return False
    
    try:
        # 센서 상태 확인
        print(f"센서 모드: {sensor.mode}")
        print(f"센서 온도: {sensor.temperature}")
        
        # 각 센서 데이터 개별 테스트
        print("\n--- 개별 센서 데이터 테스트 ---")
        
        # 자이로스코프
        gyro = sensor.gyro
        print(f"자이로스코프: {gyro}")
        
        # 가속도계
        accel = sensor.acceleration
        print(f"가속도계: {accel}")
        
        # 자기계
        mag = sensor.magnetic
        print(f"자기계: {mag}")
        
        # 쿼터니언
        quat = sensor.quaternion
        print(f"쿼터니언: {quat}")
        
        # 오일러 각도
        euler = sensor.euler
        print(f"오일러 각도: {euler}")
        
        return True
        
    except Exception as e:
        print(f"❌ IMU 데이터 읽기 오류: {e}")
        return False

def test_imu_continuous_reading(sensor, duration=5):
    """IMU 연속 데이터 읽기 테스트"""
    print(f"\n=== IMU 연속 데이터 읽기 테스트 ({duration}초) ===")
    if not sensor:
        print("❌ 센서가 초기화되지 않음")
        return False
    
    try:
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < duration:
            try:
                from imu import imu
                gyro, accel, mag, euler, temp = imu.read_sensor_data(sensor)
                
                if gyro is not None and accel is not None and mag is not None and euler is not None:
                    count += 1
                    print(f"데이터 {count}: Gyro={gyro}, Accel={accel}, Mag={mag}, Euler={euler}, Temp={temp}")
                else:
                    print(f"데이터 {count}: None 값 반환")
                    
                time.sleep(0.1)  # 10Hz
                
            except Exception as e:
                print(f"연속 읽기 오류: {e}")
                time.sleep(0.1)
        
        print(f"✅ {count}개의 유효한 데이터 읽기 완료")
        return count > 0
        
    except Exception as e:
        print(f"❌ IMU 연속 읽기 오류: {e}")
        return False

def test_i2c_devices():
    """I2C 장치 검색 테스트"""
    print("\n=== I2C 장치 검색 테스트 ===")
    try:
        import board
        import busio
        
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        
        # I2C 장치 검색
        devices = []
        for address in range(0x08, 0x78):
            try:
                i2c.try_lock()
                i2c.scan()
                if address in i2c.scan():
                    devices.append(hex(address))
                i2c.unlock()
            except:
                pass
        
        print(f"발견된 I2C 장치: {devices}")
        
        # BNO055의 기본 주소 확인 (0x28 또는 0x29)
        bno055_addresses = ['0x28', '0x29']
        found_bno055 = any(addr in devices for addr in bno055_addresses)
        
        if found_bno055:
            print("✅ BNO055 센서 발견")
        else:
            print("❌ BNO055 센서를 찾을 수 없음")
            
        return found_bno055
        
    except Exception as e:
        print(f"❌ I2C 검색 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("IMU 센서 테스트")
    print("=" * 50)
    
    # 1. I2C 장치 검색
    i2c_ok = test_i2c_devices()
    
    # 2. IMU 센서 초기화
    i2c, sensor = test_imu_initialization()
    
    # 3. IMU 데이터 읽기 테스트
    if sensor:
        data_ok = test_imu_data_reading(sensor)
        
        # 4. 연속 데이터 읽기 테스트
        if data_ok:
            continuous_ok = test_imu_continuous_reading(sensor, 3)
        else:
            continuous_ok = False
    else:
        data_ok = False
        continuous_ok = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"I2C 장치 검색: {'✅ 성공' if i2c_ok else '❌ 실패'}")
    print(f"IMU 초기화: {'✅ 성공' if sensor else '❌ 실패'}")
    print(f"데이터 읽기: {'✅ 성공' if data_ok else '❌ 실패'}")
    print(f"연속 읽기: {'✅ 성공' if continuous_ok else '❌ 실패'}")
    
    if sensor:
        try:
            from imu import imu
            imu.imu_terminate(i2c)
            print("IMU 센서 종료 완료")
        except:
            pass
    
    if not all([i2c_ok, sensor, data_ok, continuous_ok]):
        print("\n⚠️ 문제 해결 방법:")
        print("1. I2C 배선 확인 (SDA, SCL, VCC, GND)")
        print("2. BNO055 센서가 올바른 주소에 연결되었는지 확인")
        print("3. 센서 전원 공급 확인")
        print("4. 센서 하드웨어 상태 확인")

if __name__ == "__main__":
    main() 