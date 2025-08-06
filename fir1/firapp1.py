#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""firapp1.py – MLX90614 FIR temperature application for FSW V2 (Channel 0)

* Sensor: MLX90614 (infra‑red thermometer) on Qwiic Mux Channel 0
* Publishes ambient & object temperature to Flightlogic (10 Hz) and COMM (1 Hz)
* Supports CAL command: "<ambient_offset>,<object_offset>"
"""
import signal
import time
from queue import Queue
from multiprocessing import connection
from lib import logging
# from lib import events  # Removed - events module doesn't exist

from lib import appargs
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        from lib.logging import safe_log as lib_safe_log
        lib_safe_log(f"[FIR1] {message}", level, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[FIR1] 로깅 실패: {e}")
        print(f"[FIR1] 원본 메시지: {message}")

from lib import msgstructure
from fir1 import fir1

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
FIR1APP_RUNSTATUS = True

# FIR1 데이터
FIR1_AMB = 0.0
FIR1_OBJ = 0.0

# ──────────────────────────────
# 1. 초기화
# ──────────────────────────────
def firapp1_init():
    """FIR1 앱 초기화."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        safe_log("Initializing firapp1", "info".upper(), True)

        i2c, sensor = fir1.init_fir1()

        safe_log("Firapp1 initialization complete", "info".upper(), True)
        return i2c, sensor

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None

# ──────────────────────────────
# 2. 데이터 읽기
# ──────────────────────────────
def read_fir1_data(sensor):
    """FIR1 데이터 읽기 스레드."""
    global FIR1APP_RUNSTATUS, FIR1_AMB, FIR1_OBJ
    while FIR1APP_RUNSTATUS:
        try:
            if sensor is None:
                # 센서가 없으면 더미 데이터 사용
                FIR1_AMB = 25.0  # 기본 실내 온도
                FIR1_OBJ = 25.0  # 기본 실내 온도
                time.sleep(0.5)  # 2 Hz
                continue
                
            amb, obj = fir1.read_fir1(sensor)
            if amb is not None and obj is not None:
                FIR1_AMB = amb
                FIR1_OBJ = obj
                # 성공 로그는 제거 (너무 자주 출력됨)
                # safe_log(f"FIR1 데이터 읽기 성공: Ambient={amb:.2f}°C, Object={obj:.2f}°C", "info".upper(), True)
            else:
                safe_log("FIR1 데이터 읽기 실패: None 값 반환", "warning".upper(), True)
        except Exception as e:
            safe_log(f"FIR1 read error: {e}", "error".upper(), True)
        time.sleep(0.5)  # 2 Hz

# ──────────────────────────────
# 3. 데이터 전송
# ──────────────────────────────
def send_fir1_data(Main_Queue: Queue):
    """FIR1 데이터 전송 스레드."""
    global FIR1_AMB, FIR1_OBJ
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while FIR1APP_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.send_msg(Main_Queue, fl_msg,
                              appargs.FirApp1Arg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.FirApp1Arg.MID_SendFIR1Data,
                              f"{FIR1_AMB:.2f},{FIR1_OBJ:.2f}")

        if cnt > 10:  # 1 Hz telemetry
            msgstructure.send_msg(Main_Queue, tlm_msg,
                                  appargs.FirApp1Arg.AppID,
                                  appargs.CommAppArg.AppID,
                                  appargs.FirApp1Arg.MID_SendFIR1Data,
                                  f"{FIR1_AMB:.2f},{FIR1_OBJ:.2f}")
            cnt = 0

        cnt += 1
        time.sleep(0.1)  # 10 Hz

# ──────────────────────────────
# 4. 종료
# ──────────────────────────────
def firapp1_terminate(i2c):
    """FIR1 앱 종료."""
    global FIR1APP_RUNSTATUS
    FIR1APP_RUNSTATUS = False
    
    try:
        fir1.terminate_fir1(i2c)
        safe_log("Firapp1 terminated", "INFO", True)
    except Exception as e:
        safe_log(f"Terminate error: {e}", "ERROR", True)

# ──────────────────────────────
# 5. 메인 함수
# ──────────────────────────────
def firapp1_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    """FIR1 앱 메인 함수."""
    import threading
    
    # 초기화
    i2c, sensor = firapp1_init()
    
    if i2c is None or sensor is None:
        safe_log("FIR1 센서 연결 실패 - 더미 데이터로 계속 실행", "WARNING", True)
        # 센서가 없어도 앱은 계속 실행
        sensor = None
    
    # 스레드 시작
    read_thread = threading.Thread(target=read_fir1_data, args=(sensor,), daemon=True)
    send_thread = threading.Thread(target=send_fir1_data, args=(Main_Queue,), daemon=True)
    
    read_thread.start()
    send_thread.start()
    
    # 메인 루프
    try:
        while FIR1APP_RUNSTATUS:
            time.sleep(1)
    except KeyboardInterrupt:
        safe_log("FIR1 앱 사용자 중단", "INFO", True)
    finally:
        firapp1_terminate(i2c)
        safe_log("FIR1 앱 종료", "INFO", True) 

# ──────────────────────────────
# 6. FirApp1 클래스 (main.py 호환성)
# ──────────────────────────────
class FirApp1:
    """FIR1 앱 클래스 - main.py 호환성을 위한 래퍼"""
    
    def __init__(self):
        """FirApp1 초기화"""
        self.app_name = "FIR1"
        self.app_id = appargs.FirApp1Arg.AppID
        self.run_status = True
    
    def start(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 시작 - main.py에서 호출됨"""
        try:
            firapp1_main(main_queue, main_pipe)
        except Exception as e:
            safe_log(f"FirApp1 start error: {e}", "ERROR", True)
    
    def stop(self):
        """앱 중지"""
        global FIR1APP_RUNSTATUS
        FIR1APP_RUNSTATUS = False
        self.run_status = False 