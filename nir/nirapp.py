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

# NIR 센서 보정 상수
V_IN = 3.300      # 분압 전원
R_REF = 1000.0    # 직렬 기준저항
ALPHA_NI = 0.006178  # 6178 ppm/K
SENS_IR = 0.0034   # [V/°C] - 실측해 맞춘 감도

NIR_OFFSET = 40.0  # 보정값 (V) - 손/책상 온도 보정
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

def read_nir_data(chan0, chan1):
    global NIR_VOLTAGE, NIR_TEMP, NIRAPP_RUNSTATUS, NIR_OFFSET
    while NIRAPP_RUNSTATUS:
        try:
            with OFFSET_MUTEX:
                # 센서에서 전압 읽기
                v_tp = nir.read_nir(chan0, chan1)  # 열전소자 전압 (이미 Vout-1.65V)
                v_rtd = chan1.voltage  # RTD 노드 전압
                
                NIR_VOLTAGE = v_tp
                
                # RTD 온도 계산
                r_rtd = R_REF * v_rtd / (V_IN - v_rtd)
                t_rtd = (r_rtd / 1000.0 - 1.0) / ALPHA_NI  # 1차 근사
                
                # 열전소자(NIR) 대상 온도 계산 (정확한 보정식)
                t_obj = (v_tp / SENS_IR) + t_rtd + NIR_OFFSET
                
                NIR_TEMP = t_obj  # 최종 온도값
        except Exception as e:
            NIR_VOLTAGE = 0.0
            NIR_TEMP = 0.0
            events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error, f"NIR read error: {e}")
        time.sleep(0.2)

# 데이터 전송 스레드

def send_nir_data(main_q: Queue):
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()
    while NIRAPP_RUNSTATUS:
        # Flightlogic 10Hz
        # msgstructure.send_msg(main_q, fl_msg,
        #                       appargs.NirAppArg.AppID,
        #                       appargs.FlightlogicAppArg.AppID,
        #                       appargs.NirAppArg.MID_SendNirFlightLogicData,
        #                       f"{NIR_VOLTAGE},{NIR_TEMP}")
        # COMM 1Hz
        status = msgstructure.send_msg(main_q, tlm_msg,
                                       appargs.NirAppArg.AppID,
                                       appargs.CommAppArg.AppID,
                                       appargs.NirAppArg.MID_SendNirTlmData,
                                       f"{NIR_VOLTAGE:.5f},{NIR_TEMP:.2f}")
        if not status:
            events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                            "Error sending NIR TLM")
        time.sleep(0.1)

# 초기화/종료

def nirapp_init():
    global NIR_OFFSET
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        "Initializing nirapp")
        i2c, ads, chan0, chan1 = nir.init_nir()
        NIR_OFFSET = float(getattr(prevstate, "PREV_NIR_OFFSET", 0.0))
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.info,
                        "Nirapp initialization complete")
        return i2c, ads, chan0, chan1
    except Exception as e:
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                        f"Init error: {e}")
        return None, None, None, None

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
    i2c, ads, chan0, chan1 = nirapp_init()
    if chan0 is None:
        return
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(main_q,), name="HK")
    thread_dict["READ"] = threading.Thread(target=read_nir_data, args=(chan0, chan1), name="READ")
    thread_dict["SEND"] = threading.Thread(target=send_nir_data, args=(main_q,), name="SEND")
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()
    try:
        while NIRAPP_RUNSTATUS:
            try:
                raw = main_pipe.recv()
                m = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(m, raw):
                    continue
                if m.receiver_app in (appargs.NirAppArg.AppID, appargs.MainAppArg.AppID):
                    command_handler(main_q, m)
                else:
                    events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                                    "Receiver MID mismatch")
            except (EOFError, ConnectionResetError, BrokenPipeError) as e:
                events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                                f"Connection error: {e}")
                break  # 연결이 끊어졌으면 루프 종료
    except Exception as e:
        events.LogEvent(appargs.NirAppArg.AppName, events.EventType.error,
                        f"nirapp error: {e}")
        NIRAPP_RUNSTATUS = False
    nirapp_terminate(i2c)
