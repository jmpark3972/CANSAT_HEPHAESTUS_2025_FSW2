#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AS7263 Quick Test  –  Auto-Exposure + Raw & Calibrated stream
  • driver LED OFF  (외부 광원·환경광 확인용)
  • gain 고정(1×) + integration_time(ms) 자동 탐색
  • 포화·저신호 방지 후 0.1 s 간격으로 값 출력
     → 스페이스바 : 노출 재조정
     → q          : 종료
"""

import time, sys, select
from datetime import datetime
import board, busio
from adafruit_as726x import AS726x_I2C

# ───────────────────────── Sensor init
i2c  = busio.I2C(board.SCL, board.SDA)
s    = AS726x_I2C(i2c)

s.driver_led    = False          # 내부 LED 끔
s.indicator_led = False
s.gain          = 1              # 최소 Gain
s.integration_time = 3         # ms (최소값)

WL = ["610", "680", "730", "760", "810", "860"]

# ───────────────────────── Helpers
def read_raw():  # 6채널 원시값
    return [s.read_channel(i) for i in range(1, 7)]

def auto_exposure(target=8000, tol=500,
                  it_min=3, it_max=714):
    """Gain=1 고정, integration_time(ms)만 조정해 vmax≈target 맞춤."""
    it = it_min
    while True:
        s.integration_time = it
        time.sleep(0.1)
        vmax = max(read_raw())
        if abs(vmax - target) <= tol:
            break
        it = it * 2 if vmax < target else it / 2
        it = max(it_min, min(it, it_max))
        if it in (it_min, it_max):
            break
    print(f"[AUTO] IT={it:.1f} ms  vmax≈{vmax}")
    return it

def banner():
    print("\n── AS7263 Quick Test ──")
    print("  <space> : auto-exposure 재실행")
    print("  q       : quit\n")

# ───────────────────────── Main
if __name__ == "__main__":
    auto_exposure()
    banner()

    try:
        while True:
            # 키 입력(논블로킹)
            if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                key = sys.stdin.readline().strip().lower()
                if key == "q":
                    break
                elif key == "":
                    auto_exposure()

            if s.data_ready:
                raw = read_raw()
                cal = [s.read_calibrated_value(i) for i in range(1, 7)]

                raw_str = " ".join(f"{wl}:{v:5d}" for wl, v in zip(WL, raw))
                cal_str = " ".join(f"{wl}:{v:5.2f}" for wl, v in zip(WL, cal))
                print(f"{datetime.now().strftime('%H:%M:%S')} | {raw_str} | CAL {cal_str}")

            time.sleep(0.05)

    except KeyboardInterrupt:
        pass
    finally:
        s.driver_led = False
        print("\nBye!")
