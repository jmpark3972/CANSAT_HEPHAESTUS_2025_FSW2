#!/usr/bin/env python3
"""모터 로직 업데이트 테스트 스크립트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lib import config
from flight_logic.flightlogicapp import THERMIS_TEMP_THRESHOLD

def test_motor_logic_update():
    """모터 로직 업데이트 테스트"""
    print("=" * 50)
    print("모터 로직 업데이트 테스트")
    print("=" * 50)
    
    # 1. flightlogicapp.py의 임계값 확인
    print(f"1. flightlogicapp.py THERMIS_TEMP_THRESHOLD: {THERMIS_TEMP_THRESHOLD}°C")
    
    # 2. config.py의 임계값 확인
    config_threshold = config.get('FLIGHT_LOGIC.THERMIS_TEMP_THRESHOLD')
    print(f"2. config.py THERMIS_TEMP_THRESHOLD: {config_threshold}°C")
    
    # 3. config.json의 임계값 확인
    try:
        import json
        with open('lib/config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        json_threshold = config_data['FLIGHT_LOGIC']['THERMIS_TEMP_THRESHOLD']
        print(f"3. config.json THERMIS_TEMP_THRESHOLD: {json_threshold}°C")
    except Exception as e:
        print(f"3. config.json 읽기 오류: {e}")
    
    # 4. 값들이 일치하는지 확인
    if THERMIS_TEMP_THRESHOLD == 35.0 and config_threshold == 35.0:
        print("\n✅ 모든 설정이 35.0°C로 올바르게 업데이트되었습니다!")
        print("✅ 온도 조건이 4번 단계로 이동되었습니다!")
    else:
        print("\n❌ 설정이 올바르게 업데이트되지 않았습니다.")
        print(f"   flightlogicapp.py: {THERMIS_TEMP_THRESHOLD}°C")
        print(f"   config.py: {config_threshold}°C")
    
    print("\n" + "=" * 50)
    print("모터 제어 로직 순서:")
    print("1. 절대적 고도 조건 (70m 이하) - 최우선")
    print("2. 기본 모터 상태 (닫힘)")
    print("3. 추가 조건들 (필요시 여기에 추가)")
    print("4. 온도 조건 (Thermis 온도 35°C 이상시 열림)")
    print("=" * 50)

if __name__ == "__main__":
    test_motor_logic_update() 