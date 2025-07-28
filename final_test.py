#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
multisensor_single.py – DHT11 + MLX90614 + G-TPCO-035(ADS1115) 한 파일 테스트
• 2 초마다 세 센서 값을 읽어 콘솔 출력
• ./sensorlogs/tri_sensor.csv 에 로그 저장
"""

import os, time, csv
from datetime import datetime

# ─────────────────────────────────────────────
# 0)  로그 디렉터리 & CSV 파일
# ─────────────────────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
CSV_PATH = os.path.join(LOG_DIR, "tri_sensor.csv")
new_csv  = not os.path.exists(CSV_PATH)
csv_fp   = open(CSV_PATH, "a", newline="")
csv_wr   = csv.writer(csv_fp)
if new_csv:
    csv_wr.writerow([
        "ISO8601",
        "DHT_temp_C", "DHT_RH_%", 
        "FIR_ambient_C", "FIR_object_C", 
        "NIR_voltage_V", "NIR_temp_C"
    ])
    csv_fp.flush()

# ─────────────────────────────────────────────
# 1)  DHT11(DHT12) 헬퍼
# ─────────────────────────────────────────────
def init_dht(pin=None):
    try:
        # DHT12(I²C) 우선 탐색
        import adafruit_dht12, board, busio
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_dht12.DHT12(i2c)
        return ("DHT12", sensor)
    except Exception:
        # 없으면 DHT11(GPIO)
        import adafruit_dht, board
        if pin is None:
            pin = board.D4
        sensor = adafruit_dht.DHT11(pin, use_pulseio=False)
        return ("DHT11", sensor)

def read_dht(dht_tuple):
    kind, sensor = dht_tuple
    try:
        if kind == "DHT12":
            t = sensor.temperature
            h = sensor.humidity
        else:
            t = sensor.temperature
            h = sensor.humidity
        return round(float(t), 1), round(float(h), 1)
    except Exception:
        return None, None

def terminate_dht(sensor_tuple):
    _, sensor = sensor_tuple
    try:
        sensor.exit()
    except AttributeError:
        pass

# ─────────────────────────────────────────────
# 2)  MLX90614(FIR) 헬퍼
# ─────────────────────────────────────────────
# ─────────────────────────────────────────────
# 3)  G-TPCO-035(ADS1115) 헬퍼
# ─────────────────────────────────────────────
def init_nir():
    import board, busio, adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    chan = AnalogIn(ads, ADS.P0)   # 센서 출력 핀 연결 채널
    return i2c, chan

def read_nir(chan, offset=0.0):
    try:
        volt = chan.voltage
        temp = (volt - offset) * 100.0      # 하드웨어에 맞게 보정
        return round(volt, 5), round(temp, 2)
    except Exception:
        return None, None

def terminate_nir(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass

# ─────────────────────────────────────────────
# 4)  메인 루프
# ─────────────────────────────────────────────
def main():
    dht         = init_dht()
    #i2c_fir, F  = init_fir()
    i2c_nir, N  = init_nir()

    print("=== multisensor_single 시작 (Ctrl-C 종료) ===")
    try:
        while True:
            now = datetime.now().isoformat(sep=" ", timespec="milliseconds")

            dht_t, dht_h   = read_dht(dht)
            #fir_amb, fir_o = read_fir(F)
            nir_v,  nir_t  = read_nir(N)

            print(f"[{now}] "
                  f"DHT: {dht_t or '--'}°C {dht_h or '--'}%  | "
                  #f"FIR: {fir_amb or '--'}°C {fir_o or '--'}°C  | "
                  f"NIR: {nir_v or '--'}V {nir_t or '--'}°C")

            csv_wr.writerow([
                now, dht_t, dht_h, 
                #fir_amb, fir_o, 
                nir_v, nir_t
            ])
            csv_fp.flush()
            time.sleep(2.0)   # DHT11 최소 간격

    except KeyboardInterrupt:
        print("\n종료 중…")
    finally:
        terminate_dht(dht)
        #terminate_fir(i2c_fir)
        terminate_nir(i2c_nir)
        csv_fp.close()
        print("로그 저장:", CSV_PATH)

if __name__ == "__main__":
    main()
