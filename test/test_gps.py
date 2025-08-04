#!/usr/bin/env python3
"""
GPS 센서 직접 테스트 스크립트
"""

import time
import serial

def test_gps():
    """GPS 센서 직접 테스트"""
    print("GPS 센서 테스트 시작...")
    
    try:
        # 시리얼 포트 설정
        gps_port = '/dev/serial0'  # GPS 포트
        baud_rate = 9600
        
        print(f"GPS 포트 {gps_port} 연결 시도 중...")
        
        # 시리얼 연결
        try:
            gps_serial = serial.Serial(gps_port, baud_rate, timeout=1)
            print(f"✓ GPS 시리얼 포트 연결 성공 (포트: {gps_port}, 속도: {baud_rate})")
        except Exception as e:
            print(f"✗ GPS 시리얼 포트 연결 실패: {e}")
            return False
        
        # GPS 데이터 읽기 테스트
        print("\nGPS 데이터 읽기 테스트 (10회):")
        for i in range(10):
            try:
                if gps_serial.in_waiting > 0:
                    line = gps_serial.readline().decode('utf-8').strip()
                    if line.startswith('$GPGGA'):  # GPS 위치 데이터
                        print(f"  {i+1}: {line}")
                    elif line.startswith('$GPRMC'):  # GPS 권장 최소 데이터
                        print(f"  {i+1}: {line}")
                    elif line.startswith('$GPGSV'):  # GPS 위성 정보
                        print(f"  {i+1}: {line}")
                    else:
                        print(f"  {i+1}: {line}")
                else:
                    print(f"  {i+1}: 데이터 없음")
                
                time.sleep(1.0)
            except Exception as e:
                print(f"  {i+1}: 오류 = {e}")
                time.sleep(1.0)
        
        # 시리얼 포트 닫기
        gps_serial.close()
        print("\n✓ GPS 센서 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ GPS 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_gps() 