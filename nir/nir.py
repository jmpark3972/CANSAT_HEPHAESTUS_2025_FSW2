import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# NIR 센서 설정
NIR_SENSITIVITY = 100.0  # 감도: 전압 → 온도 변환 계수 (100.0 = 1V당 100°C)

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
    
    # ADS1115 설정 최적화
    ads.gain = 1  # ±4.096V 범위로 설정 (더 안정적)
    ads.data_rate = 128  # 128 SPS로 설정 (노이즈 감소)
    
    chan0 = AnalogIn(ads, ADS.P0)  # G-TPCO-035 신호가 연결된 채널
    chan1 = AnalogIn(ads, ADS.P1)  # G-TPCO-035의 저항 그라운드 채널
    return i2c, ads, chan0, chan1

def read_nir(chan0, chan1):
    try:
        # G-TPCO-035 (P0) - NIR 센서만 처리
        voltage = chan0.voltage
        
        # 음수 전압 처리 (노이즈나 바이어스 문제일 수 있음)
        if voltage < 0:
            voltage = 0.0  # 음수 전압은 0으로 처리
        
        log_nir(f"{voltage:.5f}")
        return voltage
    except Exception as e:
        log_nir(f"ERROR,{e}")
        print(f"NIR read error: {e}")  # 콘솔에도 출력
        return 0.0

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
            voltage = read_nir(chan0, chan1)
            print(f"NIR Voltage: {voltage:.5f} V")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
