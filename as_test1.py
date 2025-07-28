# as7263_sparkfun_test.py  (CPython 전용)

from as7263 import AS7263          # ← 반드시 'as7263' 모듈!
import time

sensor = AS7263()                  # I²C 0x49, 내부에서 자동 init

# ── 감도 최저로 세팅 (포화 해제용) ─────────────────────
sensor.set_gain(0)                 # 0,1,2,3 ⇒ 1× / 3.7× / 16× / 64×
sensor.set_integration_time(3)     # 3×2.8 ms ≈ 8 ms  (2–255 가능)
sensor.set_measurement_mode(2)     # 0=All 1-shot · 2=All continuous
sensor.set_illumination_led(0)     # 0=OFF, 1=ON  (창 바로 밑 LED)

labels = ["610","680","730","760","810","860"]

print("AS7263 SparkFun driver – Calibrated values (Ctrl-C to quit)")
try:
    while True:
        if sensor.data_available():
            vals = sensor.get_calibrated_values()   # [R,S,T,U,V,W]
            print(" ".join(f"{l}:{v:6.2f}" for l,v in zip(labels, vals)))
        time.sleep(0.3)
except KeyboardInterrupt:
    pass
finally:
    sensor.set_illumination_led(0)
