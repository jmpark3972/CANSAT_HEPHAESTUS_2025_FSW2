#!/usr/bin/env python3
"""
Barometer 센서 (BMP3XX) 직접 테스트 스크립트
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

def test_barometer():
    """Barometer 센서 (BMP3XX) 직접 테스트"""
    print("Barometer 센서 (BMP3XX) 테스트 시작...")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C 버스 초기화 성공")
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        print("✓ Qwiic Mux 초기화 성공")
        
        # 채널 4 선택 (Barometer 위치)
        mux.select_channel(4)
        print("✓ 채널 4 선택 완료")
        time.sleep(0.1)
        
        # BMP3XX 센서 초기화 (0x77 주소)
        try:
            import adafruit_bmp3xx
            bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c, address=0x77)
            print("✓ BMP3XX 초기화 성공 (주소: 0x77)")
            
            # 설정
            bmp.pressure_oversampling = 8
            bmp.temperature_oversampling = 2
            print("✓ BMP3XX 설정 완료")
            
        except ImportError:
            print("✗ adafruit_bmp3xx 모듈이 설치되지 않았습니다.")
            print("설치 명령: pip install adafruit-circuitpython-bmp3xx")
            return False
        except Exception as e:
            print(f"✗ BMP3XX 초기화 실패: {e}")
            return False
        
        # 센서 읽기 테스트
        print("\n센서 읽기 테스트 (10회):")
        for i in range(10):
            try:
                pressure = bmp.pressure
                temperature = bmp.temperature
                altitude = bmp.altitude
                print(f"  {i+1:2d}: 압력={pressure:.1f}hPa, 온도={temperature:.2f}°C, 고도={altitude:.1f}m")
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        print("\n✓ Barometer 센서 (BMP3XX) 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ Barometer 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_barometer() 