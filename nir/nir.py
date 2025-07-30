import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# NIR 센서 보정 상수
V_IN   = 3.30              # 3V3 실측값!
R_REF  = 1086.0            # 실측 고정저항(Ω)
ALPHA_NI = 0.006178
k_ir   = 0.00045           # IR 보정계수(실측 후 조정)
T_OFFSET_IR  = 0.0         # IR 전용 오프셋
T_OFFSET_RTD = 0.0         # RTD 전용 오프셋

# 전역 변수로 선언
ch_ir = None
ch_rtd = None
ads = None

LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
nir_log = open(os.path.join(LOG_DIR, "nir.txt"), "a")

def log_nir(text):
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    nir_log.write(f"{t},{text}\n")
    nir_log.flush()

def init_nir():
    global ch_ir, ch_rtd, ads
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    
    # ADS1115 설정 최적화
    ads.gain = 1  # ±4.096V 범위로 설정
    ads.data_rate = 128  # 128 SPS로 설정 (노이즈 감소)
    
    # 채널 객체
    ch_ir  = AnalogIn(ads, ADS.P0, ADS.P1)   # **차동** (Vout-1.65)
    ch_rtd = AnalogIn(ads, ADS.P2, ADS.GND)           # RTD 노드 (싱글)
    
    return i2c, ads, ch_ir, ch_rtd

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
    global ads, ch_ir, ch_rtd
    try:
        # 1) RTD (gain=1)
        ads.gain = 1
        _       = ch_rtd.voltage          # 더미
        v_rtd   = ch_rtd.voltage
        r_rtd   = R_REF * v_rtd / (V_IN - v_rtd)
        t_rtd   = (r_rtd / R_REF - 1) / ALPHA_NI + T_OFFSET_RTD

        # 2) Thermopile (gain=16)
        ads.gain = 16
        _     = ch_ir.voltage            # 더미
        v_tp  = ch_ir.voltage            # (Vout-1.65)

        t_obj = ((v_tp / k_ir) + (t_rtd+273.15)**4) ** 0.25 - 273.15 + T_OFFSET_IR

        return v_tp, t_obj, r_rtd, t_rtd, v_rtd
    except Exception as e:
        log_nir(f"ERROR,{e}")
        print(f"NIR calibration error: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0

def set_nir_offset(offset):
    """NIR 보정값 설정"""
    global T_OFFSET_IR
    T_OFFSET_IR = offset
    log_nir(f"OFFSET_SET,{offset}")

def terminate_nir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass
    nir_log.close()

if __name__ == "__main__":
    i2c, ads, ch_ir, ch_rtd = init_nir()
    try:
        while True:
            voltage, temp, r_rtd, t_rtd, v_rtd = read_nir_with_calibration(ch_ir, ch_rtd)
            print(f"NIR Voltage: {voltage:.5f} V, Temperature: {temp:.2f}°C, RTD_R: {r_rtd:.1f}Ω, RTD_T: {t_rtd:.1f}°C, RTD_V: {v_rtd:.5f}V")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
