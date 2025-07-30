#!/usr/bin/env python3
"""
Test script for NIR sensor with simplified implementation
"""

import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

def init_nir():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c)
    chan0 = AnalogIn(ads, 0)  # A0 channel
    chan1 = AnalogIn(ads, 1)  # A1 channel (not used in simplified version)
    return i2c, chan0, chan1

def read_nir(chan0, chan1, offset=0.0):
    try:
        # G-TPCO-035 (P0) - NIR 센서만 처리
        voltage = chan0.voltage
        raw_value = chan0.value
        
        # 음수 전압 처리 (노이즈나 바이어스 문제일 수 있음)
        if voltage < 0:
            voltage = 0.0  # 음수 전압은 0으로 처리
        
        # Simple linear conversion: voltage to temperature
        # Assuming 0V = 0°C and 3.3V = 330°C (adjust as needed)
        temp = (voltage - offset) * 100.0  # Simple linear conversion
        
        return voltage, temp, raw_value
    except Exception as e:
        print(f"Error reading NIR: {e}")
        return 0.0, 0.0, 0

def main():
    print("NIR Sensor Test (G-TPCO-035 on P0) - Enhanced Debug")
    print("=" * 60)
    
    try:
        i2c, chan0, chan1 = init_nir()
        print("NIR sensor initialized successfully")
        print("ADS1115 Gain: ±4.096V, Data Rate: 128 SPS")
        print()
        
        while True:
            voltage, temp, raw_value = read_nir(chan0, chan1)
            print(f"Raw ADC: {raw_value:.0f}, Voltage: {voltage:.5f}V → {temp:.2f}°C")
            print("-" * 40)
            time.sleep(1.0)
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        try:
            i2c.deinit()
        except:
            pass

if __name__ == "__main__":
    main() 