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
    v_in = 3.3
    r_ref = 1000 # 저항 값
    sensitivity = 0.02 
    voltage = chan0.voltage
    v_rtd = chan1.voltage
    # 열전쌍+INA333의 출력 전압을 온도로 변환 (예시: 1mV/°C, 증폭비 등 실제 하드웨어에 맞게 조정)
    r_rtd = (v_rtd / (v_in - v_rtd)) * r_ref
    t_sensor = (r_rtd / 1000 - 1) / 0.006178 # RTD 온도 계산 (예시: 1000Ω RTD, 0.006178Ω/°C)
    t_target = (voltage/ sensitivity) + t_sensor 
    log_nir(f"{voltage:.5f},{t_target:.2f}")
    return voltage, t_target

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
