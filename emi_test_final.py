#!/usr/bin/env python3
# three_sensor_logger.py
# ─────────────────────────────────────────────────────────
#  * DHT11       : 온·습도  (GPIO 4)
#  * MLX90614    : IR 온도계, Tamb/Tobj  (I²C 0x5A)
#  * MLX90640    : 24×32 열화상  (I²C 0x33) ─> 터미널 프린트만
#  ▸ 모든 루프(기본 1 초)마다 CSV에
#      timestamp, dht_temp, dht_rh, mlx14_tamb, mlx14_tobj
#    을 한 줄씩 append
#  ▸ 파일은 날짜별로 분리돼 SD 카드 관리가 편리
# ─────────────────────────────────────────────────────────

import time, csv, os
from datetime import datetime
from pathlib import Path

import board, busio
import adafruit_dht
import adafruit_mlx90614
import adafruit_mlx90640

# ───────────── 설정 ─────────────
LOOP_PERIOD_S   = 1          # 루프·로그·프린트 주기 (초)
PRINT_ASCIIART  = False      # MLX90640 기호 히트맵 출력 여부
PRINT_GRID      = True       # MLX90640 정수 그리드 출력 여부
DATA_DIR        = Path("./logs")   # CSV 저장 폴더

FRAME_SIZE = 24 * 32
frame = [0.0] * FRAME_SIZE

DATA_DIR.mkdir(exist_ok=True)

# ───────────── 초기화 ─────────────
dht    = adafruit_dht.DHT11(board.D4)
i2c    = busio.I2C(board.SCL, board.SDA, frequency=100_000)
mlx14  = adafruit_mlx90614.MLX90614(i2c)
mlx40  = adafruit_mlx90640.MLX90640(i2c, address=0x33)
mlx40.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ

def csv_path_for_today() -> Path:
    return DATA_DIR / f"{datetime.now():%Y-%m-%d-%h-%m}_5_temp_log.csv"

def ensure_header(path: Path):
    if not path.exists():
        with path.open("w", newline="") as f:
            csv.writer(f).writerow(
                ["timestamp", "dht_C", "dht_RH", "mlx14_Tamb_C", "mlx14_Tobj_C"]
            )

# ───────────── 메인 루프 ─────────────
try:
    t0 = time.time()
    while True:
        ts = datetime.now().isoformat(sep=" ", timespec="seconds")

        # ── DHT11 ──────────────────────────────────────
        try:
            dht_t, dht_rh = dht.temperature, dht.humidity
        except RuntimeError as e:
            print(f"[DHT11] {e}")
            dht_t = dht_rh = None

        # ── MLX90614 ───────────────────────────────────
        try:
            tamb, tobj = mlx14.ambient_temperature, mlx14.object_temperature
        except Exception as e:
            print(f"[MLX90614] {e}")
            tamb = tobj = None

        # ── 콘솔 출력 ──────────────────────────────────
        print(f"{ts} | "
              f"DHT {dht_t if dht_t is not None else '---'} °C "
              f"{dht_rh if dht_rh is not None else '--'} %RH | "
              f"MLX14 Tamb {tamb if tamb is not None else '--'} °C "
              f"Tobj {tobj if tobj is not None else '--'} °C")

        # ── CSV 저장 ───────────────────────────────────
        if None not in (dht_t, dht_rh, tamb, tobj):
            log_file = csv_path_for_today()
            ensure_header(log_file)
            with log_file.open("a", newline="") as f:
                csv.writer(f).writerow([ts, dht_t, dht_rh, tamb, tobj])

        # ── MLX90640 표시 (옵션) ───────────────────────
        try:
            mlx40.getFrame(frame)
            #if PRINT_GRID:
                #for h in range(24):
                    #print("".join(f"{int(frame[h*32+w]):4d}" for w in range(32)))
                #print()
            #elif PRINT_ASCIIART:
                #for h in range(24):
                    #row = ""
                    #for w in range(32):
                     #   t = frame[h*32 + w]
                      #  row += (
                       #     " " if t < 20 else
                        #    "." if t < 23 else
                         #   "-" if t < 25 else
                          #  "*" if t < 27 else
                           # "+" if t < 29 else
                            #"x" if t < 31 else
                            #"%" if t < 33 else
                            #"#" if t < 35 else
                            #"X" if t < 37 else
                            #"&"
                        #)
                    #print(row)
                #print()
        except ValueError:
            print("[MLX90640] Frame error")

        # ── 루프 주기 일정하게 맞추기 ─────────────────
        sleep_for = LOOP_PERIOD_S - ((time.time() - t0) % LOOP_PERIOD_S)
        time.sleep(max(0.0, sleep_for))
except KeyboardInterrupt:
    print("종료합니다.")
