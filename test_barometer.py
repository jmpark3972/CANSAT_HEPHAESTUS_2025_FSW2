#!/usr/bin/env python3
"""
Barometer 센서 (BMP390) 직접 테스트 스크립트
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

def test_barometer():
    """Barometer 센서 (BMP390) 직접 테스트"""
    print("Barometer 센서 (BMP390) 테스트 시작...")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        print("✓ I2C 버스 초기화 성공")
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        print("✓ Qwiic Mux 초기화 성공")
        
        # 채널 4 선택 (Barometer 위치)
        mux.select_channel(4)
        print("✓ 채널 4 선택 완료")
        time.sleep(0.1)
        
        # BMP390 센서 초기화 (0x77 주소)
        try:
            import adafruit_bmp390
            bmp = adafruit_bmp390.BMP390_I2C(i2c, address=0x77)
            print("✓ BMP390 초기화 성공 (주소: 0x77)")
        except ImportError:
            print("✗ adafruit_bmp390 모듈이 설치되지 않았습니다.")
            print("설치 명령: pip install adafruit-circuitpython-bmp390")
            return False
        except Exception as e:
            print(f"✗ BMP390 초기화 실패: {e}")
            return False
        
        # 센서 읽기 테스트
        print("\n센서 읽기 테스트 (10회):")
        for i in range(10):
            try:
                temperature = bmp.temperature
                pressure = bmp.pressure
                altitude = bmp.altitude
                print(f"  {i+1:2d}: 온도={temperature:.2f}°C, 압력={pressure:.1f}hPa, 고도={altitude:.1f}m")
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        print("\n✓ Barometer 센서 (BMP390) 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ Barometer 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_barometer() 