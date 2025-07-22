#!/usr/bin/env python3
# LWLP5000 differential-pressure sensor – 정확도 개선 버전
import time, struct
from datetime import datetime
from smbus2 import SMBus, i2c_msg

I2C_ADDR      = 0x00        # 실측 addr(0x00~0x07 스캔) → 고정 addr일 땐 그대로
FORCE_MODE    = True        # 0x00 접근엔 커널 우회 필요
MEAS_DELAY_MS = 35
PERIOD        = 0.2         # 5 Hz
P_MAX, P_MIN  =  500.0, -500.0
T_MAX, T_MIN  =   85.0,  -40.0

def trigger(bus):
    bus.write_i2c_block_data(I2C_ADDR, 0xAA, [0x00, 0x80], force=FORCE_MODE)

def read7(bus):
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]),
                 rd := i2c_msg.read(I2C_ADDR, 7))
    return list(rd)

def convert(buf):
    ph, pm, pl = buf[1:4]
    th, tm, tl = buf[4:7]

    raw_p = ((ph << 8) | pm) >> 2                # 14 bit
    if raw_p & 0x2000: raw_p -= 1 << 14          # sign
    p = (raw_p / 16384.0) * (P_MAX - P_MIN) + P_MIN

    raw_t = (th << 8) | tm                       # 16 bit
    if raw_t & 0x8000: raw_t -= 1 << 16
    t = (raw_t / 65536.0) * (T_MAX - T_MIN) + T_MIN
    return p, t

print("LWLP5000 5 Hz logger – Ctrl-C to quit")
with SMBus(1) as bus:
    drift = 0.0   # 압력 영점
    try:
        while True:
            t0 = time.time()
            trigger(bus)
            time.sleep(MEAS_DELAY_MS/1000.0)
            try:
                buf = read7(bus)
                dp, temp = convert(buf)
                if drift == 0.0:                 # 첫 값을 기준점으로
                    drift = dp
                dp -= drift

                ts = datetime.now().isoformat(timespec='milliseconds')
                print(f"[{ts}]  ΔP={dp:8.2f} Pa   T={temp:6.2f} °C")
            except OSError as e:
                print("I²C error:", e)

            time.sleep(max(0, PERIOD - (time.time()-t0)))
    except KeyboardInterrupt:
        pass
