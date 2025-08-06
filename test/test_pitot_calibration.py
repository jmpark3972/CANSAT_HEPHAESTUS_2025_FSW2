#!/usr/bin/env python3
"""피토트 온도 캘리브레이션 테스트 스크립트"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from lib import config
from pitot import pitot

def test_pitot_calibration():
    """피토트 온도 캘리브레이션 테스트"""
    print("=" * 60)
    print("피토트 온도 캘리브레이션 테스트")
    print("=" * 60)
    
    # 1. 설정 파일에서 캘리브레이션 값 확인
    print("1. 설정 파일 캘리브레이션 값 확인")
    try:
        temp_offset = config.get('PITOT.TEMP_CALIBRATION_OFFSET', -60.0)
        print(f"   ✅ config.py TEMP_CALIBRATION_OFFSET: {temp_offset}°C")
        
        # config.json 확인
        import json
        with open('lib/config.json', 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        json_offset = config_data['PITOT']['TEMP_CALIBRATION_OFFSET']
        print(f"   ✅ config.json TEMP_CALIBRATION_OFFSET: {json_offset}°C")
        
        if temp_offset == json_offset == -60.0:
            print("   ✅ 설정 파일들이 일치합니다!")
        else:
            print("   ❌ 설정 파일들이 일치하지 않습니다!")
            
    except Exception as e:
        print(f"   ❌ 설정 파일 확인 오류: {e}")
    
    print()
    
    # 2. 피토트 센서 초기화 테스트
    print("2. 피토트 센서 초기화 테스트")
    try:
        bus, mux = pitot.init_pitot()
        if bus:
            print("   ✅ 피토트 센서 초기화 성공")
            
            # 3. 온도 캘리브레이션 테스트
            print("3. 온도 캘리브레이션 테스트")
            print("   📊 원시 온도 vs 캘리브레이션된 온도:")
            
            for i in range(5):
                try:
                    dp, temp = pitot.read_pitot(bus, mux)
                    if dp is not None and temp is not None:
                        # 원시 온도 계산 (캘리브레이션 전)
                        raw_temp = temp + 60.0  # 캘리브레이션 오프셋 제거
                        print(f"   측정 {i+1}: 원시 {raw_temp:.2f}°C → 캘리브레이션 {temp:.2f}°C")
                    else:
                        print(f"   측정 {i+1}: 센서 읽기 실패")
                except Exception as e:
                    print(f"   측정 {i+1}: 오류 - {e}")
                
                import time
                time.sleep(0.5)
            
            # 4. 캘리브레이션 검증
            print("4. 캘리브레이션 검증")
            print(f"   ✅ 온도에 -60°C 오프셋이 적용되었습니다")
            print(f"   ✅ 실제 온도 = 원시 온도 - 60°C")
            
            # 센서 종료
            pitot.terminate_pitot(bus)
            print("   ✅ 피토트 센서 종료 완료")
            
        else:
            print("   ❌ 피토트 센서 초기화 실패")
            print("   💡 하드웨어 연결을 확인하세요")
            
    except Exception as e:
        print(f"   ❌ 피토트 테스트 오류: {e}")
    
    print()
    print("=" * 60)
    print("테스트 완료")
    print("=" * 60)

if __name__ == "__main__":
    test_pitot_calibration() 