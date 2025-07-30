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
        voltage = chan0.voltage
        # Simple linear conversion: voltage to temperature
        # Assuming 0V = 0°C and 3.3V = 330°C (adjust as needed)
        temp = (voltage - offset) * 100.0  # Simple linear conversion
        return voltage, temp
    except Exception as e:
        print(f"Error reading NIR: {e}")
        return 0.0, 0.0

def main():
    print("NIR Sensor Test (Simplified Implementation)")
    print("=" * 50)
    
    try:
        i2c, chan0, chan1 = init_nir()
        print("NIR sensor initialized successfully")
        
        while True:
            voltage, temp = read_nir(chan0, chan1)
            print(f"Voltage: {voltage:.5f} V, Temperature: {temp:.2f} °C")
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