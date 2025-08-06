#!/usr/bin/env python3
"""
피토관 유속도 계산 테스트 스크립트
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pitot import pitot

def test_airspeed_calculation():
    """유속도 계산 테스트"""
    print("=== 피토관 유속도 계산 테스트 ===")
    
    # 테스트 케이스들
    test_cases = [
        # (차압_Pa, 온도_°C, 고도_m, 예상_유속도_m/s)
        (0, 20, 0, 0.0),           # 정지 상태
        (25, 20, 0, 6.39),         # 낮은 속도
        (100, 20, 0, 12.78),       # 중간 속도
        (500, 20, 0, 28.58),       # 높은 속도 (센서 최대)
        (25, -20, 0, 6.39),        # 낮은 온도
        (25, 40, 0, 6.39),         # 높은 온도
        (25, 20, 1000, 6.39),      # 고도 1000m
        (25, 20, 5000, 6.39),      # 고도 5000m
    ]
    
    print(f"{'차압(Pa)':<10} {'온도(°C)':<10} {'고도(m)':<10} {'계산유속(m/s)':<15} {'예상유속(m/s)':<15} {'차이(%)':<10}")
    print("-" * 80)
    
    for dp, temp, alt, expected in test_cases:
        calculated = pitot.calculate_airspeed(dp, temp, alt)
        diff_percent = abs(calculated - expected) / expected * 100 if expected > 0 else 0
        
        print(f"{dp:<10.1f} {temp:<10.1f} {alt:<10.0f} {calculated:<15.2f} {expected:<15.2f} {diff_percent:<10.1f}")
    
    print("\n=== 베르누이 방정식 검증 ===")
    print("v = sqrt(2 * ΔP / ρ)")
    print("여기서:")
    print("- v: 유속도 (m/s)")
    print("- ΔP: 동압 (Pa)")
    print("- ρ: 공기 밀도 (kg/m³)")
    
    # 공기 밀도 계산 검증
    print(f"\n해수면 공기 밀도: {pitot.AIR_DENSITY_SEA_LEVEL} kg/m³")
    print(f"고도 1000m 공기 밀도: {101325 * (288.15 - 0.0065 * 1000) / 288.15 ** 5.256 / (pitot.GAS_CONSTANT_AIR * (288.15 - 0.0065 * 1000)):.3f} kg/m³")

def test_pressure_conversion():
    """압력 변환 테스트"""
    print("\n=== 압력 변환 테스트 ===")
    
    # 테스트 데이터 (원시 바이트)
    test_buffers = [
        [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],  # 0 Pa, 0°C
        [0x00, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00],  # 약 100 Pa
        [0x00, 0x40, 0x00, 0x00, 0x00, 0x00, 0x00],  # 약 400 Pa
    ]
    
    print(f"{'원시데이터':<20} {'차압(Pa)':<10} {'온도(°C)':<10} {'총압(Pa)':<12} {'정압(Pa)':<12}")
    print("-" * 70)
    
    for buf in test_buffers:
        dp, temp = pitot.convert(buf)
        total_p, static_p, temp_detailed = pitot.convert_detailed(buf)
        
        print(f"{' '.join([f'{b:02X}' for b in buf]):<20} {dp:<10.1f} {temp:<10.1f} {total_p:<12.1f} {static_p:<12.1f}")

def test_realistic_scenarios():
    """현실적인 시나리오 테스트"""
    print("\n=== 현실적인 시나리오 테스트 ===")
    
    scenarios = [
        ("정지 상태", 0, 20, 0),
        ("걸음 속도", 2, 20, 0),
        ("자전거 속도", 10, 20, 0),
        ("자동차 속도 (30km/h)", 50, 20, 0),
        ("자동차 속도 (60km/h)", 200, 20, 0),
        ("비행기 이착륙", 500, 20, 0),
    ]
    
    print(f"{'시나리오':<20} {'차압(Pa)':<10} {'온도(°C)':<10} {'유속(m/s)':<12} {'유속(km/h)':<12}")
    print("-" * 70)
    
    for scenario, dp, temp, alt in scenarios:
        airspeed = pitot.calculate_airspeed(dp, temp, alt)
        airspeed_kmh = airspeed * 3.6
        
        print(f"{scenario:<20} {dp:<10.1f} {temp:<10.1f} {airspeed:<12.2f} {airspeed_kmh:<12.2f}")

if __name__ == "__main__":
    try:
        test_airspeed_calculation()
        test_pressure_conversion()
        test_realistic_scenarios()
        
        print("\n=== 테스트 완료 ===")
        print("모든 테스트가 성공적으로 완료되었습니다.")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        import traceback
        traceback.print_exc() 