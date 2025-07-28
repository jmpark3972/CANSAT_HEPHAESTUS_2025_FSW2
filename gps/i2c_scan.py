#!/usr/bin/env python3
"""
I2C 디바이스 스캔 스크립트
"""

import board
import busio

def scan_i2c_devices():
    """I2C 버스에 연결된 모든 디바이스 스캔"""
    print("I2C 디바이스 스캔 시작...")
    print("=" * 50)
    
    try:
        # I2C 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        
        # I2C 스캔
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        if not devices:
            print("❌ I2C 버스에 연결된 디바이스가 없습니다.")
            print("\n가능한 원인:")
            print("1. I2C 케이블 연결 확인")
            print("2. 전원 공급 확인")
            print("3. SDA, SCL 핀 연결 확인")
            return False
        
        print(f"✅ {len(devices)}개의 I2C 디바이스 발견:")
        print("-" * 50)
        
        for device in devices:
            print(f"주소: 0x{device:02X} ({device})")
            
            # 알려진 디바이스 주소 확인
            if device == 0x42:
                print("  → MAX-M10S GPS (I2C 주소 0x42)")
            elif device == 0x43:
                print("  → MAX-M10S GPS (I2C 주소 0x43)")
            elif device == 0x48:
                print("  → ADS1115 ADC")
            elif device == 0x49:
                print("  → ADS1115 ADC")
            elif device == 0x5C:
                print("  → DHT12 센서")
            elif device == 0x33:
                print("  → MLX90640 열화상 카메라")
            else:
                print("  → 알 수 없는 디바이스")
        
        print("-" * 50)
        return True
        
    except Exception as e:
        print(f"❌ I2C 스캔 오류: {e}")
        return False

if __name__ == "__main__":
    scan_i2c_devices() 