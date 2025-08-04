#!/usr/bin/env python3
"""
Pitot 앱 - 차압 센서 데이터 수집 및 전송
"""

import time
import threading
from multiprocessing import Queue
from multiprocessing.connection import Connection
from lib import appargs, events, msgstructure, prevstate
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
import pitot

# ──────────────────────────────────────────────────────────
# 1) 전역 변수
# ──────────────────────────────────────────────────────────
PITOTAPP_RUNSTATUS = True
PITOT_BUS = None
PRESSURE_OFFSET = 0.0
TEMP_OFFSET = 0.0
OFFSET_MUTEX = threading.Lock()

# ──────────────────────────────────────────────────────────
# 2) 명령 처리
# ──────────────────────────────────────────────────────────
def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    global PITOTAPP_RUNSTATUS, PRESSURE_OFFSET, TEMP_OFFSET
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.info,
                        "PITOTAPP termination detected")
        PITOTAPP_RUNSTATUS = False
        return
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            pressure_off, temp_off = map(float, recv.data.split(','))
        except Exception:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                            "CAL cmd parse error")
            return
        with OFFSET_MUTEX:
            PRESSURE_OFFSET = pressure_off
            TEMP_OFFSET = temp_off
        prevstate.update_pitotcal(PRESSURE_OFFSET, TEMP_OFFSET)
        events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.info,
                        f"Pitot offset set to pressure={PRESSURE_OFFSET}, temp={TEMP_OFFSET}")
        return
    events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# ──────────────────────────────────────────────────────────
# 3) HK 전송 스레드
# ──────────────────────────────────────────────────────────
def send_hk(Main_Queue: Queue):
    while PITOTAPP_RUNSTATUS:
        try:
            hk_msg = msgstructure.MsgStructure()
            msgstructure.fill_msg(hk_msg, appargs.PitotAppArg.AppID, appargs.MainAppArg.AppID, appargs.PitotAppArg.MID_SendHK, "PITOT_HK_OK")
            Main_Queue.put(msgstructure.pack_msg(hk_msg))
            time.sleep(5.0)  # 5초마다 HK 전송
        except Exception as e:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                            f"HK send error: {e}")
            time.sleep(1.0)

# ──────────────────────────────────────────────────────────
# 4) Pitot 데이터 읽기 스레드
# ──────────────────────────────────────────────────────────
def read_pitot_data(Main_Queue: Queue):
    global PITOT_BUS
    while PITOTAPP_RUNSTATUS:
        try:
            if PITOT_BUS:
                dp, temp = pitot.read_pitot(PITOT_BUS)
                if dp is not None and temp is not None:
                    # 오프셋 적용
                    with OFFSET_MUTEX:
                        dp_cal = dp - PRESSURE_OFFSET
                        temp_cal = temp - TEMP_OFFSET
                    
                    # FlightLogic용 데이터 전송
                    flight_data = f"{dp_cal:.2f},{temp_cal:.2f}"
                    flight_msg = msgstructure.MsgStructure()
                    msgstructure.fill_msg(flight_msg, appargs.PitotAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.PitotAppArg.MID_SendPitotFlightLogicData, flight_data)
                    Main_Queue.put(msgstructure.pack_msg(flight_msg))
                    
                    # Telemetry용 데이터 전송
                    tlm_data = f"{dp_cal:.2f},{temp_cal:.2f}"
                    tlm_msg = msgstructure.MsgStructure()
                    msgstructure.fill_msg(tlm_msg, appargs.PitotAppArg.AppID, appargs.CommAppArg.AppID, appargs.PitotAppArg.MID_SendPitotTlmData, tlm_data)
                    Main_Queue.put(msgstructure.pack_msg(tlm_msg))
            
            time.sleep(0.2)  # 5Hz (200ms 간격)
            
        except Exception as e:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                            f"Pitot read error: {e}")
            time.sleep(1.0)

# ──────────────────────────────────────────────────────────
# 5) 메인 함수들
# ──────────────────────────────────────────────────────────
def pitotapp_init():
    """Pitot 앱 초기화"""
    global PITOT_BUS, PRESSURE_OFFSET, TEMP_OFFSET
    
    # 캘리브레이션 오프셋 로드
    PRESSURE_OFFSET = getattr(prevstate, "PREV_PITOT_POFF", 0.0)
    TEMP_OFFSET = getattr(prevstate, "PREV_PITOT_TOFF", 0.0)
    
    # Pitot 센서 초기화
    PITOT_BUS, PITOT_MUX = pitot.init_pitot()
    if not PITOT_BUS:
        events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                        "Pitot sensor initialization failed")
        return False
    
    events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.info,
                    "PITOTAPP initialized successfully")
    return True

def pitotapp_terminate():
    """Pitot 앱 종료"""
    global PITOT_BUS, PITOT_MUX
    if PITOT_BUS:
        pitot.terminate_pitot(PITOT_BUS)
        PITOT_BUS = None
    
    # Close MUX connection
    if PITOT_MUX:
        try:
            PITOT_MUX.close()
        except Exception as e:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error, f"MUX 종료 오류: {e}")
    
    events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.info,
                    "PITOTAPP terminated")

def resilient_thread(target_func, *args):
    """안정적인 스레드 실행"""
    while PITOTAPP_RUNSTATUS:
        try:
            target_func(*args)
        except Exception as e:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                            f"Thread error: {e}")
            time.sleep(1.0)

def pitotapp_main(Main_Queue: Queue, recv: Connection):
    """Pitot 앱 메인 함수"""
    global PITOTAPP_RUNSTATUS
    
    # 초기화
    if not pitotapp_init():
        return
    
    # 스레드 시작
    hk_thread = threading.Thread(target=resilient_thread, args=(send_hk, Main_Queue))
    pitot_thread = threading.Thread(target=resilient_thread, args=(read_pitot_data, Main_Queue))
    
    hk_thread.daemon = True
    pitot_thread.daemon = True
    
    hk_thread.start()
    pitot_thread.start()
    
    # 메인 루프
    while PITOTAPP_RUNSTATUS:
        try:
            if recv.poll(0.1):  # 100ms 타임아웃
                try:
                    msg = recv.recv()
                    command_handler(Main_Queue, msg)
                except (EOFError, ConnectionResetError, BrokenPipeError) as e:
                    events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                                    f"Connection error: {e}")
                    break  # 연결이 끊어졌으면 루프 종료
        except KeyboardInterrupt:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.info,
                            "KeyboardInterrupt detected in pitotapp")
            break
        except Exception as e:
            events.LogEvent(appargs.PitotAppArg.AppName, events.EventType.error,
                            f"Main loop error: {e}")
            time.sleep(0.1)
    
    # 종료
    pitotapp_terminate() 