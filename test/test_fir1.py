#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""FIR1 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fir1 import fir1

def test_fir1():
    """FIR1 센서 테스트"""
    print("=" * 50)
    print("FIR1 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. FIR1 센서 초기화 중...")
        i2c, fir1_sensor = fir1.init_fir1()
        
        if fir1_sensor is None:
            print("❌ FIR1 초기화 실패")
            return False
            
        print("✅ FIR1 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                ambient_temp, object_temp = fir1.read_fir1(fir1_sensor)
                
                print(f"📊 FIR1 데이터:")
                print(f"   주변 온도: {ambient_temp:.2f} °C")
                print(f"   대상 온도: {object_temp:.2f} °C")
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
        fir1.terminate_fir1(i2c)
        print("✅ FIR1 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ FIR1 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_fir1() 