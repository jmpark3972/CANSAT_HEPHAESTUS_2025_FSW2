#!/usr/bin/env python3
"""
Pitot tube differential-pressure sensor 헬퍼 모듈
ΔP : ±500 Pa, 온도 : –40 ~ +85 °C (I2C, 35 ms 변환)
"""

import time
import os
from datetime import datetime
from smbus2 import SMBus, i2c_msg

# ──────────────────────────────────────────────────────────
# 1) 로그 파일 준비
# ──────────────────────────────────────────────────────────
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)

pitotlog_file = open(os.path.join(LOG_DIR, "pitot.txt"), "a")  # append mode

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    pitotlog_file.write(f"{t},{line}\n")
    pitotlog_file.flush()

# ──────────────────────────────────────────────────────────
# 2) Pitot 센서 설정
# ──────────────────────────────────────────────────────────
I2C_ADDR = 0x00      # 실제 센서 주소 (0x00 이면 General-Call)
FORCE_MODE = True    # addr 0x00 접근 시 커널 우회
MEAS_DELAY_MS = 35   # 변환 대기 ≥30 ms

# ──────────────────────────────────────────────────────────
# 3) Pitot 초기화 / 측정 / 종료
# ──────────────────────────────────────────────────────────
def init_pitot():
    """Pitot 센서 초기화 - Qwiic MUX 채널 2 사용"""
    try:
        # Qwiic Mux 초기화 및 채널 2 선택 (Pitot 위치)
        import board
        import busio
        from lib.qwiic_mux import QwiicMux
        
        i2c = busio.I2C(board.SCL, board.SDA)
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        mux.select_channel(2)  # Pitot는 채널 2에 연결
        time.sleep(0.1)  # 안정화 대기
        
        bus = SMBus(1)
        _log("Pitot sensor initialized successfully (MUX channel 2)")
        return bus, mux
    except Exception as e:
        _log(f"INIT_ERROR,{e}")
        return None, None

def read_pitot(bus):
    """Pitot 센서 데이터 읽기"""
    try:
        # 측정 트리거
        trigger_measure(bus)
        time.sleep(MEAS_DELAY_MS / 1000.0)
        
        # 데이터 읽기
        buf = read_7bytes(bus)
        dp, temp = convert(buf)
        
        # 값 반올림
        dp = round(dp, 2)
        temp = round(temp, 2)
        
        _log(f"{dp},{temp}")
        return dp, temp
        
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None, None

def terminate_pitot(bus):
    """Pitot 센서 종료"""
    try:
        if bus:
            bus.close()
        _log("Pitot sensor terminated")
    except Exception as e:
        _log(f"TERMINATE_ERROR,{e}")

# ──────────────────────────────────────────────────────────
# 4) Pitot 센서 내부 함수들
# ──────────────────────────────────────────────────────────
def trigger_measure(bus: SMBus):
    """측정 트리거 - 0xAA 레지스터에 0x0080 쓰면 1-shot 전환 시작"""
    bus.write_i2c_block_data(I2C_ADDR, 0xAA, [0x00, 0x80], force=FORCE_MODE)

def read_7bytes(bus: SMBus):
    """7바이트 데이터 읽기 - 1-byte dummy 주소 0x01 → 7-byte burst read"""
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]),
                 rd := i2c_msg.read(I2C_ADDR, 7))
    return list(rd)  # [status, P2, P1, P0, T2, T1, T0]

def convert(buf):
    """원시 데이터를 압력과 온도로 변환"""
    # ─ 압력 (14-bit, 2's-complement) ─
    rawP = ((buf[1] << 8) | buf[2]) >> 2     # [23:10]
    if rawP & 0x2000:                         # 부호 확장
        rawP -= 1 << 14
    dp = rawP * 500.0 / 8192.0               # ±500 Pa FS

    # ─ 온도 (16-bit, unsigned) ─
    rawT = (buf[4] << 8) | buf[5]            # [23:08]
    temp = (rawT / 65536.0) * 125.0 - 40.0   # –40 ~ +85 °C

    return dp, temp 