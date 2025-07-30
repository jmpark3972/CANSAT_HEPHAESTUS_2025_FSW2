import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
nir_log = open(os.path.join(LOG_DIR, "nir.txt"), "a")

def log_nir(text):
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    nir_log.write(f"{t},{text}\n")
    nir_log.flush()

def init_nir():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    chan0 = AnalogIn(ads, ADS.P0)  # G-TPCO-035 신호가 연결된 채널
    chan1 = AnalogIn(ads, ADS.P1)  # G-TPCO-035의 저항 그라운드 채널
    return i2c, ads, chan0, chan1

def read_nir(chan0, chan1, offset=0.0):
    try:
        # G-TPCO-035 (P0) - NIR 센서만 처리
        voltage = chan0.voltage
        # Simple linear conversion: voltage to temperature
        # Assuming 0V = 0°C and 3.3V = 330°C (adjust as needed)
        temp = (voltage - offset) * 100.0  # Simple linear conversion
        log_nir(f"{voltage:.5f},{temp:.2f}")
        return voltage, temp
    except Exception as e:
        log_nir(f"ERROR,{e}")
        return 0.0, 0.0

def terminate_nir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass
    nir_log.close()

if __name__ == "__main__":
    i2c, ads, chan0, chan1 = init_nir()
    try:
        while True:
            voltage, temp_c = read_nir(chan0, chan1)
            print(f"NIR Voltage: {voltage:.5f} V, Temp: {temp_c:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
