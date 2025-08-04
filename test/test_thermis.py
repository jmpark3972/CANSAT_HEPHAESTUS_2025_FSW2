#!/usr/bin/env python3
"""
THERMIS 센서 직접 테스트 스크립트
"""

import time
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
# QwiicMux import 제거됨 - 직접 I2C 통신 사용

def test_thermis():
    """THERMIS 센서 직접 테스트"""
    print("THERMIS 센서 테스트 시작...")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA)
        print("✓ I2C 버스 초기화 성공")
        
        # 직접 I2C 통신 사용 (Qwiic Mux 없음)
        print("✓ 직접 I2C 통신으로 Thermis 테스트")
        
        # ADS1115 초기화 (0x48 주소)
        ads = ADS.ADS1115(i2c, address=0x48)
        print("✓ ADS1115 초기화 성공 (주소: 0x48)")
        
        # A1 채널 설정
        chan = AnalogIn(ads, ADS.P1)
        print("✓ A1 채널 설정 완료")
        
        # 센서 읽기 테스트
        print("\n센서 읽기 테스트 (10회):")
        for i in range(10):
            try:
                voltage = chan.voltage
                print(f"  {i+1:2d}: 전압 = {voltage:.4f}V")
                time.sleep(0.5)
            except Exception as e:
                print(f"  {i+1:2d}: 오류 = {e}")
                time.sleep(0.5)
        
        # 온도 계산 테스트
        print("\n온도 계산 테스트:")
        VCC = 3.3
        R_fix = 10000.0
        R0 = 10000.0
        T0 = 298.15
        B = 3435.0
        
        voltage = chan.voltage
        if voltage > 0 and voltage < VCC:
            R_th = R_fix * (VCC - voltage) / voltage
            ratio = R_th / R0
            if ratio > 0:
                import math
                T_kelvin = 1.0 / (1.0/T0 + (1.0/B) * math.log(ratio))
                T_celsius = T_kelvin - 273.15
                print(f"  전압: {voltage:.4f}V")
                print(f"  저항: {R_th:.1f}Ω")
                print(f"  온도: {T_celsius:.2f}°C")
                print(f"  +50 오프셋 적용: {T_celsius + 50:.2f}°C")
            else:
                print("  저항 비율 계산 오류")
        else:
            print("  전압 범위 오류")
        
        print("\n✓ THERMIS 센서 테스트 완료!")
        return True
        
    except Exception as e:
        print(f"✗ THERMIS 센서 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_thermis() 