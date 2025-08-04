#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""GPS 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from gps import gps

def test_gps():
    """GPS 센서 테스트"""
    print("=" * 50)
    print("GPS 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. GPS 센서 초기화 중...")
        serial_port, gps_sensor = gps.init_gps()
        
        if gps_sensor is None:
            print("❌ GPS 초기화 실패")
            return False
            
        print("✅ GPS 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                latitude, longitude, altitude, time_str, satellites = gps.read_gps(gps_sensor)
                
                print(f"📊 GPS 데이터:")
                print(f"   위도: {latitude:.6f} °")
                print(f"   경도: {longitude:.6f} °")
                print(f"   고도: {altitude:.2f} m")
                print(f"   시간: {time_str}")
                print(f"   위성 수: {satellites}")
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
        gps.terminate_gps(serial_port)
        print("✅ GPS 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ GPS 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_gps() 