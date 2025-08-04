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
from lib import events
from lib import appargs
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
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.info,
                        "Initializing firapp1")

        i2c, sensor = fir1.init_fir1()

        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.info,
                        "Firapp1 initialization complete")
        return i2c, sensor

    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.error,
                        f"Init error: {e}")
        return None, None

# ──────────────────────────────
# 2. 데이터 읽기
# ──────────────────────────────
def read_fir1_data(sensor):
    """FIR1 데이터 읽기 스레드."""
    global FIR1APP_RUNSTATUS, FIR1_AMB, FIR1_OBJ
    while FIR1APP_RUNSTATUS:
        try:
            amb, obj = fir1.read_fir1(sensor)
            if amb is not None and obj is not None:
                FIR1_AMB = amb
                FIR1_OBJ = obj
                events.LogEvent(appargs.FirApp1Arg.AppName,
                                events.EventType.info,
                                f"FIR1 데이터 읽기 성공: Ambient={amb:.2f}°C, Object={obj:.2f}°C")
            else:
                events.LogEvent(appargs.FirApp1Arg.AppName,
                                events.EventType.warning,
                                "FIR1 데이터 읽기 실패: None 값 반환")
        except Exception as e:
            events.LogEvent(appargs.FirApp1Arg.AppName,
                            events.EventType.error,
                            f"FIR1 read error: {e}")
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
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.info,
                        "Firapp1 terminated")
    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.error,
                        f"Terminate error: {e}")

# ──────────────────────────────
# 5. 메인 함수
# ──────────────────────────────
def firapp1_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    """FIR1 앱 메인 함수."""
    import threading
    
    # 초기화
    i2c, sensor = firapp1_init()
    
    if i2c is None or sensor is None:
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.error,
                        "FIR1 초기화 실패로 인한 종료")
        return
    
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
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.info,
                        "FIR1 앱 사용자 중단")
    finally:
        firapp1_terminate(i2c)
        events.LogEvent(appargs.FirApp1Arg.AppName,
                        events.EventType.info,
                        "FIR1 앱 종료") 