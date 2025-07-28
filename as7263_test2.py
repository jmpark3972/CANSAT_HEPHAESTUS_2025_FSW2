#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AS7263 NIR Spectral Sensor
 · Auto-Exposure · Dark/White user calibration · Real-time reflectance
 D : dark  |  W : white  |  q : quit
"""
import time, sys, json, pathlib, select
from datetime import datetime
import board, busio
from adafruit_as726x import AS726x_I2C

# ────────── 0. Sensor init ──────────
i2c  = busio.I2C(board.SCL, board.SDA)
sens = AS726x_I2C(i2c)

sens.driver_led    = False          # 내부 LED OFF
sens.indicator_led = False
sens.gain          = 3.7            # 1 / 3.7 / 16 / 64
sens.integration_time = 28          # 밀리초(ms) 초기치

WLABEL = ["610", "680", "730", "760", "810", "860"]   # nm

# ────────── 1. Cal file I/O ──────────
CFG = pathlib.Path("as7263_cal.json")
def save_cal(dark, white):
    CFG.write_text(json.dumps({"dark": dark, "white": white}, indent=2))
    print("✓ calibration saved:", CFG.resolve())
def load_cal(): return json.loads(CFG.read_text()).values() if CFG.exists() else (None, None)
dark_ref, white_ref = load_cal()

# ────────── 2. Helpers ──────────
def read_raw():         return [sens.read_channel(i) for i in range(1, 7)]
def avg_reads(n=5):
    vals = [0]*6
    for _ in range(n):
        while not sens.data_ready: time.sleep(0.003)
        v = read_raw();  vals = [a+b for a, b in zip(vals, v)]
    return [round(a/n) for a in vals]

def reflect(samp, dark, white):
    return [(s-d)/(w-d) if w!=d else 0 for s, d, w in zip(samp, dark, white)]

# ────────── 3. Auto-Exposure (ms) ──────────
def auto_exposure(target=8_000, tol=1_500,
                  it_min=2.8, it_max=714, gain=3.7):
    sens.gain = gain
    it = 28                   # 시작 28 ms
    while True:
        sens.integration_time = it
        time.sleep(0.1)
        vmax = max(read_raw())
        if abs(vmax-target) <= tol: break
        it = max(it_min, it/2) if vmax>target else min(it_max, it*2)
        if it in (it_min, it_max): break
    print(f"[AUTO] gain={gain}×  IT={it:.1f} ms  vmax≈{vmax}")
auto_exposure()

# ────────── 4. UI banner ──────────
print("\n── AS7263 ──  D:dark  W:white  q:quit ──")
if dark_ref and white_ref: print("(calibration loaded)\n")

# ────────── 5. Main loop ──────────
try:
    while True:
        # key press?
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            k = sys.stdin.readline().strip().lower()
            if k == "d":
                print("> DARK…"); dark_ref = avg_reads(10); print("  ", dark_ref)
                if white_ref: save_cal(dark_ref, white_ref)
            elif k == "w":
                print("> WHITE…"); white_ref = avg_reads(10); print("  ", white_ref)
                if dark_ref:  save_cal(dark_ref, white_ref)
            elif k == "q": break

        # measurement
        if sens.data_ready:
            raw = read_raw()
            msg_raw = " ".join(f"{wl}:{v:5d}" for wl, v in zip(WLABEL, raw))
            if dark_ref and white_ref:
                refl = reflect(raw, dark_ref, white_ref)
                msg_re = " ".join(f"{wl}:{r:4.2f}" for wl, r in zip(WLABEL, refl))
                print(f"{datetime.now().strftime('%H:%M:%S')} | {msg_raw} | R {msg_re}")
            else:
                print(f"{datetime.now().strftime('%H:%M:%S')} | {msg_raw}")
        time.sleep(0.05)

except KeyboardInterrupt:
    pass
finally:
    sens.driver_led = False
    print("\nBye!")
