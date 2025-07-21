# NIR Sensor App
# Author : Jeongmin Park
# sensor : G-TPCO-035 + INA333 + 10Kohm + ADC1115

import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
nir_log = open(os.path.join(LOG_DIR, "nir.txt"), "a")

def log_nir(text):
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    nir_log.write(f"{t},{text}\n")
    nir_log.flush()

def init_nir():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    chan = AnalogIn(ads, ADS.P0)  # G-TPCO-035 신호가 연결된 채널
    return i2c, ads, chan

def read_nir(chan, offset=0.0):
    voltage = chan.voltage
    # 열전쌍+INA333의 출력 전압을 온도로 변환 (예시: 1mV/°C, 증폭비 등 실제 하드웨어에 맞게 조정)
    temp_c = (voltage - offset) * 100.0  # 예시 변환식
    log_nir(f"{voltage:.5f},{temp_c:.2f}")
    return voltage, temp_c

def terminate_nir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass
    nir_log.close()

if __name__ == "__main__":
    i2c, ads, chan = init_nir()
    try:
        while True:
            voltage, temp_c = read_nir(chan)
            print(f"NIR Voltage: {voltage:.5f} V, Temp: {temp_c:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
