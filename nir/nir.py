import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# NIR 센서 보정 상수
V_IN = 1.623     # 분압 전원
R_REF = 1000.0    # 직렬 기준저항
ALPHA_NI = 0.006178  # 6178 ppm/K
SENS_IR = 0.0034   # [V/°C] - 실측해 맞춘 감도

# NIR 센서 설정
NIR_OFFSET = 25.0  # 보정값 (V) - 손/책상 온도 보정
NIR_SENSITIVITY = 1  # 감도: 전압 → 온도 변환 계수 (100.0 = 1V당 100°C)

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

def read_nir_with_calibration(chan0, chan1):
    """보정이 적용된 NIR 온도 읽기"""
    try:
        # 센서에서 전압 읽기
        v_tp = read_nir(chan0, chan1)  # 열전소자 전압
        v_rtd = chan1.voltage  # RTD 노드 전압
        
        # 새로운 보정식 사용
        t_obj = (v_tp-V_IN)*10 + NIR_OFFSET
        
        return v_tp, t_obj
    except Exception as e:
        log_nir(f"ERROR,{e}")
        print(f"NIR calibration error: {e}")
        return 0.0, 0.0

def set_nir_offset(offset):
    """NIR 보정값 설정"""
    global NIR_OFFSET
    NIR_OFFSET = offset
    log_nir(f"OFFSET_SET,{offset}")

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
            voltage, temp = read_nir_with_calibration(chan0, chan1)
            print(f"NIR Voltage: {voltage:.5f}V, Temperature: {temp:.2f}°C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
