#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""Pitot 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from pitot import pitot

def test_pitot():
    """Pitot 센서 테스트"""
    print("=" * 50)
    print("Pitot 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. Pitot 센서 초기화 중...")
        i2c, pitot_sensor = pitot.init_pitot()
        
        if pitot_sensor is None:
            print("❌ Pitot 초기화 실패")
            return False
            
        print("✅ Pitot 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                pressure, temperature = pitot.read_pitot(pitot_sensor)
                
                print(f"📊 Pitot 데이터:")
                print(f"   압력: {pressure:.2f} Pa")
                print(f"   온도: {temperature:.2f} °C")
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
        pitot.terminate_pitot(i2c)
        print("✅ Pitot 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ Pitot 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_pitot() 