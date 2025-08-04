#!/usr/bin/env python3
"""
FIR 센서들 (MLX90614) 직접 테스트 스크립트
"""

import time
import board
import busio
from lib.qwiic_mux import QwiicMux

def test_fir_sensors():
    """FIR 센서들 직접 테스트"""
    print("FIR 센서들 (MLX90614) 테스트 시작...")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C 버스 초기화 성공")
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        print("✓ Qwiic Mux 초기화 성공")
        
        # FIR1 센서 테스트 (채널 0)
        print("\n=== FIR1 센서 테스트 (채널 0) ===")
        mux.select_channel(0)
        print("✓ 채널 0 선택 완료")
        time.sleep(0.1)
        
        try:
            import adafruit_mlx90614
            fir1 = adafruit_mlx90614.MLX90614(i2c, address=0x5A)
            print("✓ FIR1 (MLX90614) 초기화 성공 (주소: 0x5A)")
            
            # FIR1 센서 읽기 테스트
            print("FIR1 센서 읽기 테스트 (5회):")
            for i in range(5):
                try:
                    ambient_temp = fir1.ambient_temperature
                    object_temp = fir1.object_temperature
                    print(f"  {i+1}: 주변온도={ambient_temp:.2f}°C, 대상온도={object_temp:.2f}°C")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  {i+1}: 오류 = {e}")
                    time.sleep(0.5)
                    
        except ImportError:
            print("✗ adafruit_mlx90614 모듈이 설치되지 않았습니다.")
            print("설치 명령: pip install adafruit-circuitpython-mlx90614")
            return False
        except Exception as e:
            print(f"✗ FIR1 초기화 실패: {e}")
        
        # FIR2 센서 테스트 (채널 1)
        print("\n=== FIR2 센서 테스트 (채널 1) ===")
        mux.select_channel(1)
        print("✓ 채널 1 선택 완료")
        time.sleep(0.1)
        
        try:
            fir2 = adafruit_mlx90614.MLX90614(i2c, address=0x5A)
            print("✓ FIR2 (MLX90614) 초기화 성공 (주소: 0x5A)")
            
            # FIR2 센서 읽기 테스트
            print("FIR2 센서 읽기 테스트 (5회):")
            for i in range(5):
                try:
                    ambient_temp = fir2.ambient_temperature
                    object_temp = fir2.object_temperature
                    print(f"  {i+1}: 주변온도={ambient_temp:.2f}°C, 대상온도={object_temp:.2f}°C")
                    time.sleep(0.5)
                except Exception as e:
                    print(f"  {i+1}: 오류 = {e}")
                    time.sleep(0.5)
                    
        except Exception as e:
            print(f"✗ FIR2 초기화 실패: {e}")
        
        print("\n✓ FIR 센서들 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ FIR 센서들 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_fir_sensors() 