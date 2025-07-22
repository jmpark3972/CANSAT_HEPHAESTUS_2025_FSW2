#!/usr/bin/env python3
import time
from smbus2 import SMBus

ADDR = 0x5C
BUS  = 1          # /dev/i2c-1

def raw_read():
    with SMBus(BUS) as bus:
        # (1) pointer set
        bus.write_byte(ADDR, 0x00)
        time.sleep(0.04)            # 40 ms↑  (datasheet ≥2 ms지만 넉넉히)
        # (2) 5-byte burst read
        return bus.read_i2c_block_data(ADDR, 0x00, 5)

def read_dht12(retries=3):
    for _ in range(retries):
        b = raw_read()              # [H, Hdec, T, Tdec, CRC]
        if (sum(b[:4]) & 0xFF) == b[4]:
            hum =  b[0] + b[1] * 0.1
            tmp =  ((b[3] & 0x7F) * 0.1) + b[2]
            if b[3] & 0x80:         # sign bit
                tmp = -tmp
            return tmp, hum
        time.sleep(0.1)             # 잠깐 쉬고 재시도
    raise RuntimeError("DHT12 checksum fail")

if __name__ == "__main__":
    while True:
        try:
            t, h = read_dht12()
            print(f"{t:5.1f} °C  {h:5.1f} %")
        except Exception as e:
            print("read error:", e)
        time.sleep(2.1)             # 변환 주기(2 s)보다 길게
