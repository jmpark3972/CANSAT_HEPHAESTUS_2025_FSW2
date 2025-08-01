#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G-TPCO-036(thermopile) + 10 kΩ NTC(ambient)  ─ ADS1115 드라이버
2025-08-02 rev-A  (단극 측정 + NTC 보정)
"""

import os, time, math
from datetime import datetime

import board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

# ────────────── 하드웨어 상수 (필요 시 수정) ──────────────
V_SUPPLY      = 3.300        # ADS1115·센서 공급 전압 [V]
ADS_GAIN      = 16           # ±0.256 V  (thermopile 해상도 ↑)

# ── Thermopile 보정
TP_SENS_UV_PER_K = 40.0      # 40 µV/K  (데이터시트 값; 교정 시 조정)
TP_CAL_OFFSET  = 0.0         # °C      (0점 보정용 편차)

# ── 10 k NTC 파라미터 (Datasheet 없으면 Beta=3950 기준)
NTC_R_25   = 10_000.0        # Ω @25 °C
NTC_BETA   = 3950.0          # [K]
NTC_PULLUP = 10_000.0        # Ω  (분압용 고정저항)

# ── 로깅
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
log_file = open(os.path.join(LOG_DIR, "nir.txt"), "a", buffering=1)

# ────────────── ADS1115 초기화 ──────────────
def init_ads():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c, gain=ADS_GAIN, data_rate=64)
    ch_tp  = AnalogIn(ads, ADS.P0)   # thermopile (AIN0-GND)
    ch_ntc = AnalogIn(ads, ADS.P1)   # NTC 분압  (AIN1-GND)
    return i2c, ads, ch_tp, ch_ntc

# ────────────── 보정/계산 함수 ──────────────
def read_thermopile(ch_tp, n=8):
    """thermopile 전압(V) n회 평균"""
    return sum(ch_tp.voltage for _ in range(n)) / n

def calc_ntc_temp(ch, v_supply=V_SUPPLY):
    """NTC 분압 → 주변온도(°C) : 단순 Beta 방정식"""
    v_ntc = ch.voltage
    if v_ntc <= 0 or v_ntc >= v_supply:  # 오픈/단락 보호
        return float("nan")
    r_ntc = NTC_PULLUP * v_ntc / (v_supply - v_ntc)
    ln = math.log(r_ntc / NTC_R_25)
    t_k = 1 / (1/298.15 + ln / NTC_BETA)      # Kelvin
    return t_k - 273.15                       # °C

def calc_object_temp(tp_v, t_amb):
    """thermopile ΔV + 주변온도로 대상온도(°C) 추정"""
    delta_t = (tp_v * 1e6) / TP_SENS_UV_PER_K      # µV → K
    return t_amb + delta_t + TP_CAL_OFFSET

# ────────────── 로깅 ──────────────
def log(msg):
    now = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    print(msg)
    log_file.write(f"{now},{msg}\n")

# ────────────── 메인 루프 ──────────────
def main():
    i2c, ads, ch_tp, ch_ntc = init_ads()
    retry = 0
    while True:
        try:
            v_tp  = read_thermopile(ch_tp)
            t_amb = calc_ntc_temp(ch_ntc)
            t_obj = calc_object_temp(v_tp, t_amb)

            log(f"TP={v_tp:.6f} V, NTC={t_amb:.2f} °C, OBJ={t_obj:.2f} °C")
            time.sleep(1.0)
            retry = 0

        except OSError as e:                      # I²C Errno 5 대응
            if getattr(e, "errno", None) == 5 and retry < 5:
                log(f"I2C_ERR_RETRY_{retry}: {e}")
                try: i2c.deinit()
                except Exception: pass
                time.sleep(0.1)
                i2c, ads, ch_tp, ch_ntc = init_ads()
                retry += 1
                continue
            else:
                raise
        except KeyboardInterrupt:
            break

    try: i2c.deinit()
    except Exception: pass
    log_file.close()

# ────────────── 실행 ──────────────
if __name__ == "__main__":
    main()
