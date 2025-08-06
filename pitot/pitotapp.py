#!/usr/bin/env python3
"""
Pitot 앱 - 차압 센서 데이터 수집 및 전송
"""

import time
import threading
from multiprocessing import Queue
from multiprocessing.connection import Connection
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[Pitot] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[Pitot] 로깅 실패: {e}")
        print(f"[Pitot] 원본 메시지: {message}")

from lib import appargs, msgstructure, prevstate
import sys
import os
import csv
from datetime import datetime
sys.path.insert(0, os.path.dirname(__file__))
import pitot

# ──────────────────────────────────────────────────────────
# 1) 전역 변수
# ──────────────────────────────────────────────────────────
PITOTAPP_RUNSTATUS = True

# 고주파수 로깅 시스템
LOG_DIR = "logs/pitot"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "high_freq_pitot_log.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.csv")

# 강제 종료 시에도 로그를 저장하기 위한 플래그
_emergency_logging_enabled = True

def emergency_log_to_file(log_type: str, message: str):
    """강제 종료 시에도 파일에 로그를 저장하는 함수"""
    global _emergency_logging_enabled
    if not _emergency_logging_enabled:
        return
        
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f"[{timestamp}] {log_type}: {message}\n"
        
        if log_type == "HIGH_FREQ":
            with open(HIGH_FREQ_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        elif log_type == "ERROR":
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
    except Exception as e:
        print(f"Emergency logging failed: {e}")

def log_high_freq_pitot_data(pressure, temperature):
    """고주파수 Pitot 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(HIGH_FREQ_LOG_PATH):
            with open(HIGH_FREQ_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'pressure', 'temperature'])
        
        # 데이터 추가
        with open(HIGH_FREQ_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, pressure, temperature])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"High frequency pitot logging failed: {e}")

def log_csv(filepath: str, headers: list, data: list):
    """CSV 파일에 데이터를 로깅하는 함수"""
    try:
        # CSV 헤더가 없으면 생성
        if not os.path.exists(filepath):
            with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(headers)
        
        # 데이터 추가
        with open(filepath, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(data)
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"CSV logging failed: {e}")
PITOT_BUS = None
PITOT_MUX = None
PRESSURE_OFFSET = 0.0
TEMP_OFFSET = 0.0
PITOT_PRESSURE = 0.0
PITOT_TEMP = 0.0
OFFSET_MUTEX = threading.Lock()

# ──────────────────────────────────────────────────────────
# 2) 명령 처리
# ──────────────────────────────────────────────────────────
def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    global PITOTAPP_RUNSTATUS, PRESSURE_OFFSET, TEMP_OFFSET
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        safe_log("PITOTAPP termination detected", "info".upper(), True)
        PITOTAPP_RUNSTATUS = False
        return
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            pressure_off, temp_off = map(float, recv.data.split(','))
        except Exception:
            safe_log("CAL cmd parse error", "error".upper(), True)
            return
        with OFFSET_MUTEX:
            PRESSURE_OFFSET = pressure_off
            TEMP_OFFSET = temp_off
        prevstate.update_pitotcal(PRESSURE_OFFSET, TEMP_OFFSET)
        safe_log(f"Pitot offset set to pressure={PRESSURE_OFFSET}, temp={TEMP_OFFSET}", "info".upper(), True)
        return
    safe_log(f"Unhandled MID {recv.MsgID}", "error".upper(), True)

# ──────────────────────────────────────────────────────────
# 3) HK 전송 스레드
# ──────────────────────────────────────────────────────────
def send_hk(Main_Queue: Queue):
    global PITOT_PRESSURE, PITOT_TEMP
    while PITOTAPP_RUNSTATUS:
        try:
            hk_msg = msgstructure.MsgStructure()
            hk_payload = f"run={PITOTAPP_RUNSTATUS},pressure={PITOT_PRESSURE:.2f},temp={PITOT_TEMP:.2f}"
            msgstructure.fill_msg(hk_msg, appargs.PitotAppArg.AppID, appargs.MainAppArg.AppID, appargs.PitotAppArg.MID_SendHK, hk_payload)
            status = Main_Queue.put(msgstructure.pack_msg(hk_msg))
            
            if status:
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, PITOTAPP_RUNSTATUS, PITOT_PRESSURE, PITOT_TEMP]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "pressure", "temperature"], hk_row)
                
            time.sleep(5.0)  # 5초마다 HK 전송
        except Exception as e:
            safe_log(f"HK send error: {e}", "error".upper(), True)
            time.sleep(1.0)

# ──────────────────────────────────────────────────────────
# 4) Pitot 데이터 읽기 스레드
# ──────────────────────────────────────────────────────────
def read_pitot_data(Main_Queue: Queue):
    global PITOT_BUS, PITOT_MUX, PITOT_PRESSURE, PITOT_TEMP
    while PITOTAPP_RUNSTATUS:
        try:
            if PITOT_BUS:
                dp, temp = pitot.read_pitot(PITOT_BUS, PITOT_MUX)
                if dp is not None and temp is not None:
                    # 오프셋 적용
                    with OFFSET_MUTEX:
                        dp_cal = dp - PRESSURE_OFFSET
                        temp_cal = temp - TEMP_OFFSET
                        
                    # 전역 변수 업데이트
                    PITOT_PRESSURE = dp_cal
                    PITOT_TEMP = temp_cal
                    
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
                    
                    # 고주파수 로깅 (20Hz)
                    log_high_freq_pitot_data(dp_cal, temp_cal)
                else:
                    # 센서 읽기 실패 시 기본값으로 로깅
                    log_high_freq_pitot_data(0.0, 0.0)
                    # 전역 변수도 기본값으로 설정
                    PITOT_PRESSURE = 0.0
                    PITOT_TEMP = 0.0
            else:
                # PITOT_BUS가 None인 경우 기본값으로 로깅
                log_high_freq_pitot_data(0.0, 0.0)
                PITOT_PRESSURE = 0.0
                PITOT_TEMP = 0.0
            
            time.sleep(0.05)  # 20Hz (50ms 간격)
            
        except Exception as e:
            safe_log(f"Pitot read error: {e}", "error".upper(), True)
            # 오류 발생 시에도 기본값 설정
            PITOT_PRESSURE = 0.0
            PITOT_TEMP = 0.0
            time.sleep(1.0)

# ──────────────────────────────────────────────────────────
# 5) 메인 함수들
# ──────────────────────────────────────────────────────────
def pitotapp_init():
    """Pitot 앱 초기화"""
    global PITOT_BUS, PITOT_MUX, PRESSURE_OFFSET, TEMP_OFFSET
    
    # 설정에서 캘리브레이션 오프셋 로드
    try:
        from lib import config
        temp_offset = config.get('PITOT.TEMP_CALIBRATION_OFFSET', -60.0)
        PRESSURE_OFFSET = getattr(prevstate, "PREV_PITOT_POFF", 0.0)
        TEMP_OFFSET = getattr(prevstate, "PREV_PITOT_TOFF", temp_offset)
        safe_log(f"Pitot temperature calibration offset loaded: {TEMP_OFFSET}°C", "info".upper(), True)
    except Exception as e:
        safe_log(f"Failed to load pitot calibration from config: {e}", "warning".upper(), True)
        # 기본값 사용
        PRESSURE_OFFSET = getattr(prevstate, "PREV_PITOT_POFF", 0.0)
        TEMP_OFFSET = getattr(prevstate, "PREV_PITOT_TOFF", -60.0)
    
    # Pitot 센서 초기화
    PITOT_BUS, PITOT_MUX = pitot.init_pitot()
    if not PITOT_BUS:
        safe_log("Pitot sensor initialization failed", "error".upper(), True)
        return False
    
    safe_log("PITOTAPP initialized successfully", "info".upper(), True)
    return True

def pitotapp_terminate():
    """Pitot 앱 종료"""
    global PITOT_BUS, PITOT_MUX
    if PITOT_BUS:
        pitot.terminate_pitot(PITOT_BUS)
        PITOT_BUS = None
    
    safe_log("PITOTAPP terminated", "info".upper(), True)

def resilient_thread(target_func, *args):
    """안정적인 스레드 실행"""
    while PITOTAPP_RUNSTATUS:
        try:
            target_func(*args)
        except Exception as e:
            safe_log(f"Thread error: {e}", "error".upper(), True)
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
                    safe_log(f"Connection error: {e}", "error".upper(), True)
                    break  # 연결이 끊어졌으면 루프 종료
        except KeyboardInterrupt:
            safe_log("KeyboardInterrupt detected in pitotapp", "info".upper(), True)
            break
        except Exception as e:
            safe_log(f"Main loop error: {e}", "error".upper(), True)
            time.sleep(0.1)
    
    # 종료
    pitotapp_terminate() 