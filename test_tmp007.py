#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""TMP007 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tmp007 import tmp007

def test_tmp007():
    """TMP007 센서 테스트"""
    print("=" * 50)
    print("TMP007 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. TMP007 센서 초기화 중...")
        i2c, tmp007_sensor = tmp007.init_tmp007()
        
        if tmp007_sensor is None:
            print("❌ TMP007 초기화 실패")
            return False
            
        print("✅ TMP007 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        while True:
            try:
                # 센서 데이터 읽기
                data = tmp007.read_tmp007_data(tmp007_sensor)
                
                if data:
                    print(f"📊 TMP007 데이터:")
                    print(f"   객체 온도: {data['object_temperature']:.2f} °C")
                    print(f"   다이 온도: {data['die_temperature']:.2f} °C")
                    print(f"   전압: {data['voltage']:.2f} μV")
                    print(f"   상태: {data['status']}")
                    print("-" * 30)
                else:
                    print("❌ 데이터 읽기 실패")
                
                time.sleep(1)
                
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 데이터 읽기 오류: {e}")
                time.sleep(1)
        
        # 정리
        print("\n3. 센서 정리 중...")
        tmp007.terminate_tmp007(i2c)
        print("✅ TMP007 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ TMP007 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_tmp007() 