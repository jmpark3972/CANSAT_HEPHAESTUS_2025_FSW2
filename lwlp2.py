#!/usr/bin/env python3
import time, struct
from datetime import datetime
from smbus2 import SMBus, i2c_msg

I2C_ADDR = 0x00        # 그대로 사용. 실패 시 0x00→실제 주소로 교체
MEAS_DELAY = 0.035     # 35 ms ↑
PERIOD     = 0.2       # 0.2 s (5 Hz)

def trig(bus):
    bus.write_i2c_block_data(I2C_ADDR, 0xAA, [0x00, 0x80], force=True)

def read(bus):
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]),
                 rd := i2c_msg.read(I2C_ADDR, 6))
    d = list(rd)
    p_raw = (d[0]<<16)|(d[1]<<8)|d[2]
    t_raw = (d[3]<<16)|(d[4]<<8)|d[5]
    # 14-bit 압력 ±500 Pa, 16-bit 온도 0.01 °C/LSB 가정
    p = (((p_raw>>10)-0x4000) if p_raw&0x2000 else (p_raw>>10))*500/8192
    t = (((t_raw>>8) - 0x10000) if t_raw&0x8000 else (t_raw>>8))/100
    return p, t

with SMBus(1, force=True) as bus:
    print("LWLP5000 5 Hz read — Ctrl-C to quit")
    try:
        while True:
            t0 = time.time()
            trig(bus)
            time.sleep(MEAS_DELAY)
            try:
                dp, temp = read(bus)
                print(f"{datetime.now().isoformat(timespec='milliseconds')} "
                      f"ΔP={dp:8.2f} Pa  T={temp:6.2f} °C")
            except OSError:
                print("I²C read error")
            time.sleep(max(0, PERIOD-(time.time()-t0)))
    except KeyboardInterrupt:
        pass
