import time
import os
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# NIR 센서 보정 상수
V_IN   = 1.65      # 분압 전원
R_REF  = 1000.0     # 직렬 기준저항 (실제로 납땜한 값!)
ALPHA_NI = 0.006178 # 6178 ppm/K
SENS_IR  = 0.034    # [V/°C]  ← 실측해 맞추기
T_OFFSET = 0.0      # 캘리브레이션 상수

LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
nir_log = open(os.path.join(LOG_DIR, "nir.txt"), "a")

def log_nir(text):
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    nir_log.write(f"{t},{text}\n")
    nir_log.flush()

def init_nir():
    global ain_ir, ain_rtd
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    
    # ADS1115 설정 최적화
    ads.gain = 1  # ±4.096V 범위로 설정   16
    ads.data_rate = 128  # 128 SPS로 설정 (노이즈 감소)
    
    # 차동 입력과 싱글 입력 설정
    ain_ir = AnalogIn(ads, ADS.P0, ADS.P1)  # 차동 (Vout‒1.65 V)
    ain_rtd = AnalogIn(ads, ADS.P2)  # 싱글 (RTD 노드)
    
    return i2c, ads, ain_ir, ain_rtd

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
        """
        # ── (1) RTD 온도 ────────────────────────────
        v_rtd  = ain_rtd.voltage               # RTD 노드 전압
        r_rtd  = R_REF * v_rtd / (V_IN - v_rtd)
        t_rtd  = (r_rtd / 1000.0 - 1.0) / ALPHA_NI  # 1차 근사
        
        # ── (2) 열전소자(NIR) 대상 온도 ─────────────
        v_tp   = ain_ir.voltage                # 이미 (Vout‒1.65)
        # 거친 1차식
        t_obj  = (v_tp / SENS_IR) + t_rtd + T_OFFSET
        # 정밀식(예시): k ≈ 0.00045 V/K⁴  → 실측 보정 필요
                # t_obj  = ( (v_tp/0.00045) + (t_rtd+273.15)**4 )**0.25 - 273.15
                """
        ads.gain = 1
        _      = ain_rtd.voltage        # 설정 적용용 더미 읽기
        v_rtd  = ain_rtd.voltage
        r_rtd  = R_REF * v_rtd / (V_IN - v_rtd)
        t_rtd  = (r_rtd / R_REF - 1) / ALPHA_NI + T_OFFSET   # ↔ 분리

        # 2) Thermopile
        ads.gain = 16
        _     = ain_ir.voltage          # 더미
        v_tp  = ain_ir.voltage          # (VOUT – 1.65 V)

        # Stefan-Boltzmann 근사
        k_ir  = 0.00045                 # 실측으로 교정!
        t_obj = ((v_tp / k_ir) + (t_rtd + 273.15)**4)**0.25 - 273.15 + T_OFFSET

        return v_tp, t_obj, r_rtd, t_rtd, v_rtd
    except Exception as e:
        log_nir(f"ERROR,{e}")
        print(f"NIR calibration error: {e}")
        return 0.0, 0.0, 0.0, 0.0, 0.0

def set_nir_offset(offset):
    """NIR 보정값 설정"""
    global T_OFFSET
    T_OFFSET = offset
    log_nir(f"OFFSET_SET,{offset}")

def terminate_nir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass
    nir_log.close()

if __name__ == "__main__":
    i2c, ads, ain_ir, ain_rtd = init_nir()
    try:
        while True:
            voltage, temp, r_rtd, t_rtd, v_rtd = read_nir_with_calibration(ain_ir, ain_rtd)
            print(f"NIR Voltage: {voltage:.5f} V, Temperature: {temp:.2f}°C, RTD_R: {r_rtd:.1f}Ω, RTD_T: {t_rtd:.1f}°C, RTD_V: {v_rtd:.5f}V")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_nir(i2c)
