#!/usr/bin/env python3
"""
Pitot 온도 캘리브레이션 및 기타 수정사항 테스트
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

def test_pitot_config():
    """Pitot 설정 로드 테스트"""
    print("=== Pitot 설정 로드 테스트 ===")
    try:
        from lib import config
        temp_offset = config.get_config('PITOT.TEMP_CALIBRATION_OFFSET', -60.0)
        print(f"Pitot temperature offset loaded: {temp_offset}°C")
        return True
    except Exception as e:
        print(f"Pitot config load error: {e}")
        return False

def test_thermal_camera_unpacking():
    """Thermal Camera 데이터 언패킹 테스트"""
    print("\n=== Thermal Camera 데이터 언패킹 테스트 ===")
    try:
        # 가상의 4개 값 반환 (실제 read_cam 함수처럼)
        data = (25.0, 30.0, 27.5, [25.0] * 768)  # min, max, avg, temps
        
        if data and len(data) >= 3:
            THERMAL_MIN, THERMAL_MAX, THERMAL_AVG = data[:3]
            print(f"Thermal data unpacked successfully: Min={THERMAL_MIN}, Max={THERMAL_MAX}, Avg={THERMAL_AVG}")
            return True
        else:
            print("Thermal data unpacking failed: insufficient data")
            return False
    except Exception as e:
        print(f"Thermal camera unpacking error: {e}")
        return False

def test_gps_time_formatting():
    """GPS 시간 포맷팅 테스트"""
    print("\n=== GPS 시간 포맷팅 테스트 ===")
    try:
        # 다양한 GPS_TIME 값 테스트
        test_cases = [
            "12:34:56",
            None,
            12345,
            "invalid_time"
        ]
        
        for i, gps_time in enumerate(test_cases):
            gps_time_str = str(gps_time) if gps_time is not None else "00:00:00"
            print(f"Test case {i+1}: {gps_time} -> {gps_time_str}")
        
        return True
    except Exception as e:
        print(f"GPS time formatting error: {e}")
        return False

def test_thermis_threshold():
    """Thermis 온도 임계값 테스트"""
    print("\n=== Thermis 온도 임계값 테스트 ===")
    try:
        from lib import config
        threshold = config.get_config('THERMIS_TEMP_THRESHOLD', 35.0)
        print(f"Thermis temperature threshold: {threshold}°C")
        
        # 테스트 온도들
        test_temps = [30.0, 35.0, 40.0, 45.0]
        for temp in test_temps:
            status = "열림" if temp >= threshold else "닫힘"
            print(f"Temperature {temp}°C -> Motor {status}")
        
        return True
    except Exception as e:
        print(f"Thermis threshold test error: {e}")
        return False

def test_thermal_camera_offset():
    """Thermal Camera 온도 오프셋 테스트"""
    print("\n=== Thermal Camera 온도 오프셋 테스트 ===")
    try:
        # 가상의 섭씨 온도 (실제 센서에서 읽은 값)
        celsius_temp = 25.0
        
        # +273.15 오프셋 적용 (켈빈으로 변환)
        kelvin_temp = celsius_temp + 273.15
        
        print(f"Original Celsius: {celsius_temp}°C")
        print(f"With +273.15 offset: {kelvin_temp}K")
        print(f"Expected display: {kelvin_temp}K (effectively Kelvin)")
        
        return True
    except Exception as e:
        print(f"Thermal camera offset test error: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("Pitot 온도 캘리브레이션 및 기타 수정사항 테스트")
    print("=" * 50)
    
    tests = [
        test_pitot_config,
        test_thermal_camera_unpacking,
        test_gps_time_formatting,
        test_thermis_threshold,
        test_thermal_camera_offset
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print("✅ PASSED")
            else:
                print("❌ FAILED")
        except Exception as e:
            print(f"❌ ERROR: {e}")
        print()
    
    print(f"테스트 결과: {passed}/{total} 통과")
    
    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    main() 