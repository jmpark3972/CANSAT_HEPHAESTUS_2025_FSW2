#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""thermisapp.py – ADS1115 thermistor temperature application for FSW V2

* Sensor: ADS1115 with thermistor
* Publishes temperature to Flightlogic (10 Hz) and COMM (1 Hz)
* Supports CAL command: "<temperature_offset>"
"""
import board, busio
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[Thermis] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[Thermis] 로깅 실패: {e}")
        print(f"[Thermis] 원본 메시지: {message}")

from lib import appargs, msgstructure, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from thermis import thermis  # helper module created earlier


# ──────────────────────────────────────────────
# Globals & Locks
# ──────────────────────────────────────────────
THERMISAPP_RUNSTATUS = True

OFFSET_MUTEX = threading.Lock()  # protect offset update & sensor access

# 통합 오프셋 관리 시스템 사용
try:
    from lib.offsets import get_thermis_offset
    TEMP_OFFSET = get_thermis_offset()
    safe_log(f"Thermis 오프셋 로드됨: {TEMP_OFFSET}°C", "info".upper(), True)
except Exception as e:
    TEMP_OFFSET = 50.0  # 기본값
    safe_log(f"Thermis 오프셋 로드 실패, 기본값 사용: {e}", "warning".upper(), True)

TEMP = 0.0

# ──────────────────────────────────────────────
# Command handler
# ──────────────────────────────────────────────

def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    """Handle SB messages addressed to ThermisApp."""
    global THERMISAPP_RUNSTATUS, TEMP_OFFSET

    # Terminate process
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        safe_log("THERMISAPP termination detected", "info".upper(), True)
        THERMISAPP_RUNSTATUS = False
        return

    # Calibration: data == "<temp_off>"
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            temp_off = float(recv.data)
        except Exception as e:
            safe_log(f"CAL cmd parse error: {e}", "error".upper(), True)
            return

        with OFFSET_MUTEX:
            TEMP_OFFSET = temp_off
            
            # 통합 오프셋 시스템에 저장
            try:
                from lib.offsets import set_offset
                set_offset("THERMIS.TEMPERATURE_OFFSET", TEMP_OFFSET)
                safe_log(f"Thermis 오프셋이 통합 시스템에 저장됨: {TEMP_OFFSET}°C", "info".upper(), True)
            except Exception as e:
                safe_log(f"통합 오프셋 시스템 저장 실패: {e}", "warning".upper(), True)
        
        # 기존 호환성을 위해 prevstate도 업데이트
        prevstate.update_thermiscal(TEMP_OFFSET)  # must exist in prevstate
        safe_log(f"THERMIS offset set to temp={TEMP_OFFSET}", "info".upper(), True)
        return

    safe_log(f"Unhandled MID {recv.MsgID}", "error".upper(), True)

# ──────────────────────────────────────────────
# HK thread
# ──────────────────────────────────────────────

def send_hk(main_q: Queue):
    while THERMISAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(main_q, hk,
                              appargs.ThermisAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermisAppArg.MID_SendHK,
                              str(THERMISAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────────────────────
# Sensor threads
# ──────────────────────────────────────────────

def read_thermis_data(chan):
    global TEMP
    while THERMISAPP_RUNSTATUS:
        with OFFSET_MUTEX:
            temp = thermis.read_thermis(chan)  # returns None on error
            if temp is not None:
                TEMP = round(temp - TEMP_OFFSET, 2)
        time.sleep(0.2)  # ADS1115 ~2Hz default


def send_thermis_data(main_q: Queue):
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while THERMISAPP_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.send_msg(main_q, fl_msg,
                              appargs.ThermisAppArg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.ThermisAppArg.MID_SendThermisFlightLogicData,
                              f"{TEMP}")

        # COMM 1 Hz
        if cnt >= 10:
            status = msgstructure.send_msg(main_q, tlm_msg,
                                           appargs.ThermisAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.ThermisAppArg.MID_SendThermisTlmData,
                                           f"{TEMP}")
            if not status:
                safe_log("Error sending Thermis TLM", "error".upper(), True)
            cnt = 0
        cnt += 1
        time.sleep(0.1)

# ──────────────────────────────────────────────
# Init / Terminate
# ──────────────────────────────────────────────

def thermisapp_init():
    global TEMP_OFFSET
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        safe_log("Initializing thermisapp", "info".upper(), True)

        i2c, chan = thermis.init_thermis()

        # previous calibration (if any)
        TEMP_OFFSET = float(getattr(prevstate, "PREV_THERMIS_OFF", 0.0))

        safe_log("Thermisapp initialization complete", "info".upper(), True)
        return i2c, chan

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None


def thermisapp_terminate(i2c):
    global THERMISAPP_RUNSTATUS
    THERMISAPP_RUNSTATUS = False
    safe_log("Terminating thermisapp", "info".upper(), True)
    
    thermis.terminate_thermis(i2c)
    for t in thread_dict.values():
        t.join()
    safe_log("Thermisapp termination complete", "info".upper(), True)

# ──────────────────────────────────────────────
# Main entry
# ──────────────────────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while THERMISAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception as e:
                safe_log(f"스레드 실행 오류: {e}", "WARNING")
            time.sleep(1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

def thermisapp_main(main_q: Queue, main_pipe: connection.Connection):
    global THERMISAPP_RUNSTATUS
    THERMISAPP_RUNSTATUS = True

    i2c, chan = thermisapp_init()
    if chan is None:
        return

    # spawn threads
    thread_dict["HK"] = resilient_thread(send_hk, args=(main_q,), name="HK")
    thread_dict["READ"] = resilient_thread(read_thermis_data, args=(chan,), name="READ")
    thread_dict["SEND"] = threading.Thread(target=send_thermis_data, args=(main_q,), name="SEND")
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while THERMISAPP_RUNSTATUS:
            # Non-blocking receive with timeout
            if main_pipe.poll(1.0):  # 1초 타임아웃
                try:
                    raw = main_pipe.recv()
                except Exception as e:
                    # 에러 시 루프 계속
                    safe_log(f"메시지 수신 오류: {e}", "WARNING")
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            m = raw
            if m.receiver_app in (appargs.ThermisAppArg.AppID, appargs.MainAppArg.AppID):
                command_handler(main_q, m)
            else:
                safe_log("Receiver MID mismatch", "error".upper(), True)
    except Exception as e:
        safe_log(f"thermisapp error: {e}", "error".upper(), True)
        THERMISAPP_RUNSTATUS = False

    thermisapp_terminate(i2c) 