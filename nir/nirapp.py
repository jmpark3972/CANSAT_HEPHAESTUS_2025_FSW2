# Python FSW V2 NIR App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types
from lib import prevstate

import signal
from multiprocessing import Queue, connection
import threading
import time

from nir import nir  # G-TPCO-035+INA333+ADS1115 기반 모듈

NIRAPP_RUNSTATUS = True
OFFSET_MUTEX = threading.Lock()

NIR_OFFSET = 0.0  # 보정값 (V)
NIR_VOLTAGE = 0.0
NIR_TEMP = 0.0

# SB 메시지 핸들러

def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    global NIRAPP_RUNSTATUS, NIR_OFFSET

    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        "NIRAPP termination detected")
        NIRAPP_RUNSTATUS = False
        return

    # 보정 명령: data == "<offset>" (V)
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            offset = float(recv.data)
        except Exception:
            events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                            "CAL cmd parse error")
            return
        with OFFSET_MUTEX:
            NIR_OFFSET = offset
        prevstate.update_nircal(NIR_OFFSET)
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        f"NIR offset set to {NIR_OFFSET}")
        return

    events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# HK 송신 스레드

def send_hk(main_q: Queue):
    while NIRAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(main_q, hk,
                              appargs.NirAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.NirAppArg.MID_SendHK,
                              str(NIRAPP_RUNSTATUS))
        time.sleep(1)

# 센서 데이터 읽기 스레드

def read_nir_data(chan):
    global NIR_VOLTAGE, NIR_TEMP, NIRAPP_RUNSTATUS, NIR_OFFSET
    while NIRAPP_RUNSTATUS:
        with OFFSET_MUTEX:
            voltage, temp = nir.read_nir(chan, NIR_OFFSET)
            NIR_VOLTAGE = voltage
            NIR_TEMP = temp
        time.sleep(0.2)

# 데이터 전송 스레드

def send_nir_data(main_q: Queue):
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()
    while NIRAPP_RUNSTATUS:
        # Flightlogic 10Hz
        msgstructure.send_msg(main_q, fl_msg,
                              appargs.NirAppArg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.NirAppArg.MID_SendNirFlightLogicData,
                              f"{NIR_TEMP}")
        # COMM 1Hz
        if cnt >= 10:
            status = msgstructure.send_msg(main_q, tlm_msg,
                                           appargs.NirAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.NirAppArg.MID_SendNirTlmData,
                                           f"{NIR_VOLTAGE},{NIR_TEMP}")
            if not status:
                events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                                "Error sending NIR TLM")
            cnt = 0
        cnt += 1
        time.sleep(0.1)

# 초기화/종료

def nirapp_init():
    global NIR_OFFSET
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        "Initializing nirapp")
        i2c, ads, chan = nir.init_nir()
        NIR_OFFSET = float(getattr(prevstate, "PREV_NIR_OFFSET", 0.0))
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        "Nirapp initialization complete")
        return i2c, ads, chan
    except Exception as e:
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                        f"Init error: {e}")
        return None, None, None

def nirapp_terminate(i2c):
    global NIRAPP_RUNSTATUS
    NIRAPP_RUNSTATUS = False
    events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                    "Terminating nirapp")
    nir.terminate_nir(i2c)
    for t in thread_dict.values():
        t.join()
    events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                    "Nirapp termination complete")

# 메인 엔트리
thread_dict: dict[str, threading.Thread] = {}
def nirapp_main(main_q: Queue, main_pipe: connection.Connection):
    global NIRAPP_RUNSTATUS
    NIRAPP_RUNSTATUS = True
    i2c, ads, chan = nirapp_init()
    if chan is None:
        return
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(main_q,), name="HK")
    thread_dict["READ"] = threading.Thread(target=read_nir_data, args=(chan,), name="READ")
    thread_dict["SEND"] = threading.Thread(target=send_nir_data, args=(main_q,), name="SEND")
    for t in thread_dict.values():
        t.start()
    try:
        while NIRAPP_RUNSTATUS:
            raw = main_pipe.recv()
            m = msgstructure.MsgStructure()
            if not msgstructure.unpack_msg(m, raw):
                continue
            if m.receiver_app in (appargs.NirAppArg.AppID, appargs.MainAppArg.AppID):
                command_handler(main_q, m)
            else:
                events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                                "Receiver MID mismatch")
    except Exception as e:
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                        f"nirapp error: {e}")
        NIRAPP_RUNSTATUS = False
    nirapp_terminate(i2c)
