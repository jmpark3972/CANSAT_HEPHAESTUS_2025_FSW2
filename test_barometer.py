#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""Barometer 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from barometer import barometer

def test_barometer():
    """Barometer 센서 테스트"""
    print("=" * 50)
    print("Barometer 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. Barometer 센서 초기화 중...")
        i2c, bmp = barometer.init_barometer()
        
        if bmp is None:
            print("❌ Barometer 초기화 실패")
            return False
            
        print("✅ Barometer 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                pressure, temperature, altitude = barometer.read_barometer(bmp, 0)
                
                print(f"📊 Barometer 데이터:")
                print(f"   압력: {pressure:.2f} hPa")
                print(f"   온도: {temperature:.2f} °C")
                print(f"   고도: {altitude:.2f} m")
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
        barometer.terminate_barometer(i2c)
        print("✅ Barometer 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ Barometer 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_barometer() 