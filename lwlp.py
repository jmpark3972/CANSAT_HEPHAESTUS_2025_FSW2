#!/usr/bin/env python3
# LWLP5000 differential-pressure sensor – 5 Hz 콘솔 로거
# ΔP : ±500 Pa,  온도 : –40 ~ +85 °C  (I2C, 35 ms 변환)

import time
from datetime import datetime
from smbus2 import SMBus, i2c_msg

# ─── 사용자 설정 ────────────────────────────────────────────────
I2C_ADDR      = 0x00    # 실제 센서 주소 (0x00 이면 General-Call)
FORCE_MODE    = True    # addr 0x00 접근 시 커널 우회
PERIOD_SEC    = 0.20    # 샘플 간격 0.2 s → 5 Hz
MEAS_DELAY_MS = 35      # 변환 대기 ≥30 ms
# ───────────────────────────────────────────────────────────────

def trigger_measure(bus: SMBus):
    # 0xAA 레지스터에 0x0080 쓰면 1-shot 전환 시작 (DFRobot 자료)
    bus.write_i2c_block_data(I2C_ADDR, 0xAA, [0x00, 0x80], force=FORCE_MODE)

def read_7bytes(bus: SMBus):
    # 1-byte dummy 주소 0x01 → 7-byte burst read
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]),
                 rd := i2c_msg.read(I2C_ADDR, 7))
    return list(rd)        # [status, P2, P1, P0, T2, T1, T0]

def convert(buf):
    # ─ 압력 (14-bit, 2’s-complement) ─
    rawP = ((buf[1] << 8) | buf[2]) >> 2     # [23:10]
    if rawP & 0x2000:                         # 부호 확장
        rawP -= 1 << 14
    dp = rawP * 500.0 / 8192.0               # ±500 Pa FS

    # ─ 온도 (16-bit, unsigned) ─
    rawT = (buf[4] << 8) | buf[5]            # [23:08]
    temp = (rawT / 65536.0) * 125.0 - 40.0   # –40 ~ +85 °C

    return dp, temp

print("LWLP5000 5 Hz logger  —  Ctrl-C to quit")
with SMBus(1) as bus:
    drift = None                              # 압력 영점
    try:
        while True:
            t0 = time.time()

            trigger_measure(bus)
            time.sleep(MEAS_DELAY_MS / 1000.0)

            try:
                buf = read_7bytes(bus)
                dp, temp = convert(buf)

                if drift is None:             # 첫 샘플을 0 Pa 기준
                    drift = dp
                dp -= drift

                ts = datetime.now().isoformat(timespec='milliseconds')
                print(f"[{ts}]  ΔP = {dp:8.2f} Pa   T = {temp:6.2f} °C")

            except OSError as e:
                print("I²C read error:", e)

            # 정확한 주기 유지
            delay = PERIOD_SEC - (time.time() - t0)
            if delay > 0:
                time.sleep(delay)

    except KeyboardInterrupt:
        print("\n종료되었습니다.")
