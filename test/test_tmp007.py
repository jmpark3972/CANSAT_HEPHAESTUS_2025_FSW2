#!/usr/bin/env python3
"""TMP007 센서 테스트 스크립트"""

import sys
import os
import time

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tmp007 import tmp007

def test_tmp007_sensor():
    """TMP007 센서 기본 테스트"""
    print("=== TMP007 센서 테스트 시작 ===")
    
    try:
        # 센서 초기화
        print("1. 센서 초기화 중...")
        i2c_instance, sensor_instance, mux_instance = tmp007.init_tmp007()
        print("✓ 센서 초기화 성공")
        
        # 기본 데이터 읽기 테스트
        print("\n2. 기본 데이터 읽기 테스트...")
        for i in range(5):
            try:
                data = tmp007.read_tmp007_data(sensor_instance)
                if data:
                    print(f"   측정 {i+1}: 객체={data['object_temperature']}°C, "
                          f"다이={data['die_temperature']}°C, "
                          f"전압={data['voltage']}μV")
                else:
                    print(f"   측정 {i+1}: 데이터 읽기 실패")
                time.sleep(0.5)
            except Exception as e:
                print(f"   측정 {i+1}: 오류 - {e}")
        
        # 개별 함수 테스트
        print("\n3. 개별 함수 테스트...")
        
        # 온도 읽기
        try:
            temp = sensor_instance.read_temperature()
            print(f"   객체 온도: {temp}°C")
        except Exception as e:
            print(f"   객체 온도 읽기 실패: {e}")
        
        # 다이 온도 읽기
        try:
            die_temp = sensor_instance.read_die_temperature()
            print(f"   다이 온도: {die_temp}°C")
        except Exception as e:
            print(f"   다이 온도 읽기 실패: {e}")
        
        # 전압 읽기
        try:
            voltage = sensor_instance.read_voltage()
            print(f"   전압: {voltage}μV")
        except Exception as e:
            print(f"   전압 읽기 실패: {e}")
        
        # 상태 읽기
        try:
            status = sensor_instance.get_status()
            print(f"   상태: {status}")
        except Exception as e:
            print(f"   상태 읽기 실패: {e}")
        
        # 연속 측정 테스트
        print("\n4. 연속 측정 테스트 (10초)...")
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < 10:
            try:
                data = tmp007.read_tmp007_data(sensor_instance)
                if data:
                    count += 1
                    if count % 4 == 0:  # 4초마다 출력
                        print(f"   측정 {count}: 객체={data['object_temperature']:.2f}°C, "
                              f"다이={data['die_temperature']:.2f}°C")
                time.sleep(0.25)  # 4Hz
            except Exception as e:
                print(f"   측정 오류: {e}")
                time.sleep(0.25)
        
        print(f"   총 {count}회 측정 완료")
        
        # 센서 종료
        print("\n5. 센서 종료...")
        tmp007.tmp007_terminate(i2c_instance)
        print("✓ 센서 종료 완료")
        
        print("\n=== TMP007 센서 테스트 완료 ===")
        return True
        
    except Exception as e:
        print(f"\n❌ TMP007 센서 테스트 실패: {e}")
        return False

def test_tmp007_limits():
    """TMP007 센서 한계값 테스트"""
    print("\n=== TMP007 센서 한계값 테스트 ===")
    
    try:
        # 센서 초기화
        i2c_instance, sensor_instance, mux_instance = tmp007.init_tmp007()
        
        # 여러 번 측정하여 안정성 확인
        print("안정성 테스트 (20회 측정)...")
        temps = []
        die_temps = []
        voltages = []
        
        for i in range(20):
            try:
                data = tmp007.read_tmp007_data(sensor_instance)
                if data:
                    temps.append(data['object_temperature'])
                    die_temps.append(data['die_temperature'])
                    voltages.append(data['voltage'])
                time.sleep(0.25)
            except Exception as e:
                print(f"측정 {i+1} 실패: {e}")
        
        if temps:
            print(f"객체 온도: 최소={min(temps):.2f}°C, 최대={max(temps):.2f}°C, "
                  f"평균={sum(temps)/len(temps):.2f}°C")
        if die_temps:
            print(f"다이 온도: 최소={min(die_temps):.2f}°C, 최대={max(die_temps):.2f}°C, "
                  f"평균={sum(die_temps)/len(die_temps):.2f}°C")
        if voltages:
            print(f"전압: 최소={min(voltages):.2f}μV, 최대={max(voltages):.2f}μV, "
                  f"평균={sum(voltages)/len(voltages):.2f}μV")
        
        # 센서 종료
        tmp007.tmp007_terminate(i2c_instance)
        print("✓ 한계값 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 한계값 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("TMP007 센서 테스트 스크립트")
    print("=" * 50)
    
    # 기본 테스트
    success1 = test_tmp007_sensor()
    
    # 한계값 테스트
    success2 = test_tmp007_limits()
    
    print("\n" + "=" * 50)
    if success1 and success2:
        print("🎉 모든 테스트 통과!")
    else:
        print("❌ 일부 테스트 실패")
        sys.exit(1) 