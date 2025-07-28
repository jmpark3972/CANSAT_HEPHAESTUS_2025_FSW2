#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AS7263 NIR Spectral Sensor – User-Level Calibration Demo
  1) press D → record dark reference (센서 뚜껑 덮거나 암실)
  2) press W → record white reference (Spectralon®·백색표준판)
  3) 이후 자동으로 샘플 reflectance(0–1)를 실시간 출력
  q → quit
"""

import time, sys, json, pathlib, board, busio
import select
from datetime import datetime
from adafruit_as726x import AS726x_I2C

###############################################################################
# 0. 센서 초기화
###############################################################################
i2c     = busio.I2C(board.SCL, board.SDA)
sens    = AS726x_I2C(i2c)

sens.driver_led           = False   # 내부 LED OFF (외부 조명만 사용)
sens.indicator_led        = False
sens.integration_time     = 10      # 2.8 ms × 10 ≈ 28 ms (노출)
sens.gain                 = 16      # 1·3.7·16·64 배 중 16×

WLABEL = ["610", "680", "730", "760", "810", "860"]  # nm

###############################################################################
# 1. 보정용 데이터 저장/불러오기
###############################################################################
CFG_FILE = pathlib.Path("as7263_cal.json")

def save_calibration(dark, white):
    CFG_FILE.write_text(json.dumps({"dark": dark, "white": white}, indent=2))
    print(f"✓ Calibration saved  → {CFG_FILE.resolve()}")

def load_calibration():
    if CFG_FILE.exists():
        cfg = json.loads(CFG_FILE.read_text())
        return cfg["dark"], cfg["white"]
    return None, None

dark_ref, white_ref = load_calibration()

###############################################################################
# 2. 헬퍼 함수
###############################################################################
def read_raw():
    return [sens.read_channel(i) for i in range(1, 7)]  # 1~6

def avg_reads(n=5, delay=0.05):
    acc = [0]*6
    for _ in range(n):
        while not sens.data_ready:
            time.sleep(0.01)
        r = read_raw()
        acc = [a+v for a, v in zip(acc, r)]
        time.sleep(delay)
    return [round(a/n) for a in acc]

def reflectance(sample, dark, white):
    return [(s-d)/(w-d) if w-d else 0 for s, d, w in zip(sample, dark, white)]

def banner():
    print("\n────────  AS7263 Calibrated Measurement  ────────")
    print("  D : dark reference  |  W : white reference")
    print("  q : quit program")
    if dark_ref and white_ref:
        print("  (calibration loaded from file)")
    print("─────────────────────────────────────────────────\n")

###############################################################################
# 3. 메인 루프
###############################################################################
banner()
try:
    while True:
        # ── 사용자가 키 입력했는지 확인 (non-blocking)
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            key = sys.stdin.readline().strip().lower()
            if key == "d":
                print("> Cover sensor → 측정 중…")
                dark_ref = avg_reads(10)
                print("  DARK :", dark_ref)
                if white_ref: save_calibration(dark_ref, white_ref)
            elif key == "w":
                print("> White standard → 측정 중…")
                white_ref = avg_reads(10)
                print("  WHITE:", white_ref)
                if dark_ref:  save_calibration(dark_ref, white_ref)
            elif key == "q":
                break

        # ── 보정값이 준비됐다면 샘플 반사율 계산
        if dark_ref and white_ref and sens.data_ready:
            raw = read_raw()
            refl = reflectance(raw, dark_ref, white_ref)
            ts   = datetime.now().strftime("%H:%M:%S")
            raw_s  = " ".join(f"{w}:{v:5d}" for w, v in zip(WLABEL, raw))
            refl_s = " ".join(f"{w}:{r:4.2f}" for w, r in zip(WLABEL, refl))
            print(f"{ts} | {raw_s}  |  REFLECT {refl_s}")
        time.sleep(0.05)

except KeyboardInterrupt:
    pass
finally:
    sens.driver_led = False
    print("\nBye!")
