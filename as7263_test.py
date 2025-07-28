#!/usr/bin/env python3
import time, board, busio
from adafruit_as726x import AS726x_I2C

# ─────────────── I²C 초기화 ───────────────
i2c     = busio.I2C(board.SCL, board.SDA)
sensor  = AS726x_I2C(i2c)

sensor.conversion_mode     = sensor.MODE_2   # 모든 밴드 연속 측정
sensor.driver_led_current  = 12.5            # mA 12.5 25 50 100
sensor.indicator_led_current = 2             # mA 1 2 4 8
sensor.driver_led          = True
sensor.indicator_led       = False

wavelengths = ["610 nm", "680 nm", "730 nm", "760 nm", "810 nm", "860 nm"]

sensor.integration_time = 10
sensor.gain             = 16

#print("AS7263 running — Ctrl-C to stop")
#sensor.driver_led      = False   # 센서 창 바로 아래 광원
#sensor.indicator_led   = False   # 보드 상태 LED
try:
    while True:
        if sensor.data_ready:
            raw = [sensor.read_channel(idx) for idx in range(1, 7)]  # 1~6
            print("  ".join(f"{wl}:{v:5d}" for wl, v in zip(wavelengths, raw)))
            cal = [sensor.read_calibrated_value(i) for i in range(1, 7)]
            #print("Calibrated:", ["{:.3f}".format(c) for c in cal])
            #dark = [sensor.read_channel(i) for i in range(1,7)]
            #white= [sensor.read_channel(i) for i in range(1,7)]
            #k = [(w-d) for w,d in zip(white, dark)]       # 스케일 팩터 분모
            #sample= [sensor.read_channel(i) for i in range(1,7)]
            #reflectance = [(s-d)/k_i for s,d,k_i in zip(sample, dark, k)]

        time.sleep(0.2)

except KeyboardInterrupt:
    pass
finally:
    sensor.driver_led = False
    print("\nStopped.")
