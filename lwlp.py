#!/usr/bin/env python3
# LWLP5000 차압·온도 센서  —  콘솔 출력 전용 (CSV 저장 X)

import time, struct
from datetime import datetime
from smbus2 import SMBus, i2c_msg     # sudo apt install python3-smbus2

I2C_ADDR = 0x00          # LWLP5000 7-bit 주소
CFG_REG  = 0xAA
CFG_DATA = (0x00, 0x80)
MEAS_DELAY_MS = 35       # 변환 대기 ≥30 ms
SAMPLE_PERIOD = 0.2      # ★ 샘플 간격(초) — 0.2 s = 5 Hz

# ─────────────  보조 함수  ─────────────
def trigger_measure(bus: SMBus):
    bus.write_i2c_block_data(I2C_ADDR, CFG_REG, CFG_DATA)

def read_raw(bus: SMBus):
    try:
        bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]), rd := i2c_msg.read(I2C_ADDR, 6))
        b = list(rd)
        press24 = (b[0] << 16) | (b[1] << 8) | b[2]
        temp24  = (b[3] << 16) | (b[4] << 8) | b[5]
        return press24, temp24
    except OSError:
        return None, None

def conv_pressure(raw24):
    raw14 = raw24 >> 10
    if raw14 & 0x2000:
        raw14 -= 1 << 14
    return raw14 * 500.0 / 8192.0     # ±500 Pa FS

def conv_temperature(raw24):
    raw16 = raw24 >> 8
    if raw16 & 0x8000:
        raw16 -= 1 << 16
    return raw16 / 100.0              # 0.01 °C/LSB 가정

# ─────────────  메인 루프  ─────────────
print("LWLP5000 콘솔 로거 시작 — 주기:", SAMPLE_PERIOD, "s  (Ctrl-C 종료)")

with SMBus(1) as bus:
    try:
        while True:
            t0 = time.time()

            trigger_measure(bus)
            time.sleep(MEAS_DELAY_MS / 1000.0)

            p_raw, t_raw = read_raw(bus)
            if p_raw is not None:
                dp = conv_pressure(p_raw)
                tc = conv_temperature(t_raw)
                now = datetime.now().isoformat(sep=" ", timespec="milliseconds")
                print(f"[{now}]  ΔP = {dp:8.2f} Pa   Temp = {tc:6.2f} °C")
            else:
                print("I2C read error")

            # 남은 시간만큼 대기해 정확한 주기 유지
            delay = SAMPLE_PERIOD - (time.time() - t0)
            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n종료되었습니다.")
