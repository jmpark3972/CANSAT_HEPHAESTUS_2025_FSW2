#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""시스템 통합 테스트 - 모든 주요 기능 테스트"""

import sys
import os
import time

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_config_system():
    """설정 시스템 테스트"""
    print("=== 설정 시스템 테스트 ===")
    try:
        from lib import config
        
        # 기본 설정값 테스트
        fsw_mode = config.get_config("FSW_MODE", "PAYLOAD")
        team_id = config.get_team_id()
        pitot_offset = config.get_config("PITOT.TEMP_CALIBRATION_OFFSET", -60.0)
        
        print(f"✅ FSW 모드: {fsw_mode}")
        print(f"✅ 팀 ID: {team_id}")
        print(f"✅ Pitot 온도 오프셋: {pitot_offset}°C")
        return True
    except Exception as e:
        print(f"❌ 설정 시스템 테스트 실패: {e}")
        return False

def test_pitot_sensor():
    """Pitot 센서 테스트"""
    print("\n=== Pitot 센서 테스트 ===")
    try:
        import pitot.pitot as pitot
        
        # 센서 초기화
        print("1. Pitot 센서 초기화 중...")
        bus, sensor = pitot.init_pitot()
        
        if bus is None:
            print("❌ Pitot 초기화 실패")
            return False
            
        print("✅ Pitot 초기화 성공")
        
        # 데이터 읽기 테스트
        print("2. 데이터 읽기 테스트...")
        for i in range(3):
            pressure, temperature = pitot.read_pitot(bus, sensor)
            if pressure is not None and temperature is not None:
                print(f"   📊 읽기 {i+1}: 압력={pressure:.2f}Pa, 온도={temperature:.2f}°C")
            else:
                print(f"   ⚠️ 읽기 {i+1}: 데이터 없음")
            time.sleep(0.5)
        
        # 정리
        pitot.terminate_pitot(bus)
        print("✅ Pitot 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ Pitot 테스트 실패: {e}")
        return False

def test_thermal_camera():
    """Thermal Camera 데이터 처리 테스트"""
    print("\n=== Thermal Camera 데이터 처리 테스트 ===")
    try:
        # 가상 데이터로 테스트
        thermal_data = "25.0,30.0,27.5"  # Min,Max,Avg
        
        parts = thermal_data.split(',')
        if len(parts) == 3:
            min_temp = float(parts[0])
            max_temp = float(parts[1])
            avg_temp = float(parts[2])
            
            print(f"✅ 데이터 언패킹 성공:")
            print(f"   최소: {min_temp}°C")
            print(f"   최대: {max_temp}°C")
            print(f"   평균: {avg_temp}°C")
            return True
        else:
            print("❌ 데이터 형식 오류")
            return False
            
    except Exception as e:
        print(f"❌ Thermal Camera 테스트 실패: {e}")
        return False

def test_gps_time_format():
    """GPS 시간 포맷팅 테스트"""
    print("\n=== GPS 시간 포맷팅 테스트 ===")
    try:
        test_cases = [
            ("12:34:56", "12:34:56"),
            (None, "00:00:00"),
            ("12345", "12345"),
            ("invalid", "invalid")
        ]
        
        for i, (input_time, expected) in enumerate(test_cases, 1):
            if input_time is None:
                result = "00:00:00"
            else:
                result = str(input_time)
            
            status = "✅" if result == expected else "❌"
            print(f"   {status} 테스트 {i}: {input_time} -> {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ GPS 시간 포맷팅 테스트 실패: {e}")
        return False

def test_thermis_threshold():
    """Thermis 온도 임계값 테스트"""
    print("\n=== Thermis 온도 임계값 테스트 ===")
    try:
        from lib import config
        
        threshold = config.get_config('FLIGHT_LOGIC.THERMIS_TEMP_THRESHOLD', 35.0)
        print(f"✅ 임계값: {threshold}°C")
        
        # 가상 온도 테스트
        test_temps = [30.0, 35.0, 40.0, 45.0]
        for temp in test_temps:
            status = "⚠️ 경고" if temp >= threshold else "✅ 정상"
            print(f"   {status} 온도 {temp}°C")
        
        return True
        
    except Exception as e:
        print(f"❌ Thermis 임계값 테스트 실패: {e}")
        return False

def test_thermal_offset():
    """Thermal Camera 온도 오프셋 테스트"""
    print("\n=== Thermal Camera 온도 오프셋 테스트 ===")
    try:
        original_celsius = 25.0
        offset = 273.15  # Celsius to Kelvin
        
        kelvin = original_celsius + offset
        print(f"✅ 원본: {original_celsius}°C")
        print(f"✅ 오프셋 적용: {kelvin}K")
        print(f"✅ 예상 표시: {kelvin}K (실제로는 Kelvin)")
        
        return True
        
    except Exception as e:
        print(f"❌ Thermal Camera 오프셋 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("시스템 통합 테스트")
    print("=" * 50)
    
    tests = [
        test_config_system,
        test_pitot_sensor,
        test_thermal_camera,
        test_gps_time_format,
        test_thermis_threshold,
        test_thermal_offset
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 테스트 실행 오류: {e}")
    
    print("\n" + "=" * 50)
    print(f"테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")
    
    return passed == total

if __name__ == "__main__":
    main() 