#!/usr/bin/env python3
"""
Barometer App for CANSAT FSW
BMP280 센서를 사용한 고도 측정
"""

import os
import sys
import time
import threading
import csv
import signal
from datetime import datetime
from multiprocessing import Queue, Process, connection
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import appargs, msgstructure, logging, types, prevstate
from barometer import barometer

# 전역 변수
BAROMETERAPP_RUNSTATUS = False
PRESSURE = 0.0
TEMPERATURE = 0.0
ALTITUDE = 0.0
MAXALT_RESET_MUTEX = threading.Lock()

# 로그 파일 경로
LOG_DIR = "logs"
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "barometer_high_freq.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        from lib.logging import safe_log as lib_safe_log
        lib_safe_log(f"[{appargs.BarometerAppArg.AppName}] {message}", level, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[Barometer] 로깅 실패: {e}")
        print(f"[Barometer] 원본 메시지: {message}")

def emergency_log_to_file(log_type: str, message: str):
    """긴급 로그 파일에 기록"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f"[{timestamp}] [{log_type}] {message}\n"
        
        emergency_log_path = os.path.join(LOG_DIR, f"barometer_emergency_{log_type.lower()}.log")
        with open(emergency_log_path, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            f.flush()
    except Exception as e:
        print(f"Emergency logging failed: {e}")

def log_csv(filepath: str, headers: list, data: list):
    """CSV 파일에 데이터를 로깅하는 함수"""
    try:
        # 파일이 없으면 헤더 생성
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

# Mutex to prevent two process sharing the same barometer instance
OFFSET_MUTEX = threading.Lock()

# Mutex to prevent sending of logic data when resetting
MAXALT_RESET_MUTEX = threading.Lock()

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (Main_Queue:Queue, recv_msg : msgstructure.MsgStructure, barometer_instance):
    global BAROMETERAPP_RUNSTATUS
    global BAROMETER_OFFSET
    global MAXALT_RESET_MUTEX

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"BAROMETERAPP TERMINATION DETECTED", "info".upper(), True)
        BAROMETERAPP_RUNSTATUS = False

    # Calibrate Barometer when calibrate command is input
    if recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        
        # Use mutex to prevent multiple thread accessing barometer instance at the same time
        with OFFSET_MUTEX:
            caldata = barometer.read_barometer(barometer_instance, 0)
            # altitude is the third index
            BAROMETER_OFFSET = float(caldata[2])
            
            # 통합 오프셋 시스템에 저장
            try:
                from lib.offsets import set_offset
                set_offset("BAROMETER.ALTITUDE_OFFSET", BAROMETER_OFFSET)
                safe_log(f"Barometer 오프셋이 통합 시스템에 저장됨: {BAROMETER_OFFSET}m", "info".upper(), True)
            except Exception as e:
                safe_log(f"통합 오프셋 시스템 저장 실패: {e}", "warning".upper(), True)

        # Use mutex to prevent the barometer process sending the wrong maxalt
        with MAXALT_RESET_MUTEX:
            ResetBarometerMaxAltCmd = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, ResetBarometerMaxAltCmd, appargs.BarometerAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.BarometerAppArg.MID_ResetBarometerMaxAlt, "")

            # sleep for 0.5 seconds to ensure the max alt reset. Since the mutex is holding, no barometer data can be sent to flightlogic
            time.sleep(0.5)

        safe_log(f"Barometer offset changed to {BAROMETER_OFFSET}", "info".upper(), True)

        # 기존 호환성을 위해 prevstate도 업데이트
        prevstate.update_altcal(BAROMETER_OFFSET)

    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue : Queue):
    global BAROMETERAPP_RUNSTATUS, PRESSURE, TEMPERATURE, ALTITUDE
    while BAROMETERAPP_RUNSTATUS:
        try:
            barometerHK = msgstructure.MsgStructure()
            hk_payload = f"run={BAROMETERAPP_RUNSTATUS},pressure={PRESSURE:.2f},temp={TEMPERATURE:.2f},alt={ALTITUDE:.2f}"
            status = msgstructure.send_msg(Main_Queue, barometerHK, appargs.BarometerAppArg.AppID, appargs.HkAppArg.AppID, appargs.BarometerAppArg.MID_SendHK, hk_payload)
            
            if status:
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, BAROMETERAPP_RUNSTATUS, PRESSURE, TEMPERATURE, ALTITUDE]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "pressure", "temperature", "altitude"], hk_row)
                
        except Exception as e:
            safe_log(f"HK send error: {e}", "error".upper(), True)
            
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not BAROMETERAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def barometerapp_init():
    """센서 초기화·시리얼 확인."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializing barometerapp", "info".upper(), True)

        # Barometer 센서 초기화 (직접 I2C 연결)
        i2c, bmp = barometer.init_barometer()
        
        safe_log("Barometerapp initialization complete", "info".upper(), True)
        return i2c, bmp

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None

# Termination
def barometerapp_terminate(i2c_instance):
    global BAROMETERAPP_RUNSTATUS

    BAROMETERAPP_RUNSTATUS = False
    safe_log("Terminating barometerapp", "info".upper(), True)
    # Termination Process Comes Here

    barometer.terminate_barometer(i2c_instance)
    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        safe_log(f"Terminating thread {thread_name}", "info".upper(), True)
        try:
            thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
            if thread_dict[thread_name].is_alive():
                safe_log(f"Thread {thread_name} did not terminate gracefully", "warning".upper(), True)
        except Exception as e:
            safe_log(f"Error joining thread {thread_name}: {e}", "error".upper(), True)
        safe_log(f"Terminating thread {thread_name} Complete", "info".upper(), True)

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    safe_log("Terminating barometerapp complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################
PRESSURE = 0
TEMPERATURE = 0
ALTITUDE = 0
# 통합 오프셋 관리 시스템 사용
try:
    from lib.offsets import get_barometer_offset
    BAROMETER_OFFSET = get_barometer_offset()
    safe_log(f"Barometer 오프셋 로드됨: {BAROMETER_OFFSET}m", "info".upper(), True)
except Exception as e:
    BAROMETER_OFFSET = 0
    safe_log(f"Barometer 오프셋 로드 실패, 기본값 사용: {e}", "warning".upper(), True)

def read_barometer_data(bmp):
    """Barometer 데이터 읽기 스레드."""
    global BAROMETERAPP_RUNSTATUS, PRESSURE, TEMPERATURE, ALTITUDE, SEA_LEVEL_PRESSURE, RESOLUTION_INFO
    while BAROMETERAPP_RUNSTATUS:
        try:
            if bmp is None:
                # 센서가 없으면 더미 데이터 사용
                PRESSURE = 1013.25  # 표준 대기압 (hPa)
                TEMPERATURE = 25.0  # 기본 실내 온도 (°C)
                ALTITUDE = 0.0 + BAROMETER_OFFSET  # 기본 고도 + 오프셋
                SEA_LEVEL_PRESSURE = 1013.25  # 표준 대기압
                RESOLUTION_INFO = None
                time.sleep(0.1)  # 10 Hz
                continue
                
            # 고급 데이터 읽기
            result = barometer.read_barometer_advanced(bmp, 0)
            if result and len(result) >= 5:
                pressure, temperature, altitude, sea_level_pressure, resolution_info = result
                PRESSURE = pressure
                TEMPERATURE = temperature
                ALTITUDE = altitude
                SEA_LEVEL_PRESSURE = sea_level_pressure
                RESOLUTION_INFO = resolution_info
            else:
                # 기본 데이터 읽기 (fallback)
                pressure, temperature, altitude = barometer.read_barometer(bmp, 0)
                PRESSURE = pressure
                TEMPERATURE = temperature
                ALTITUDE = altitude
                SEA_LEVEL_PRESSURE = pressure  # 기본값
                RESOLUTION_INFO = None
        except Exception as e:
            safe_log(f"Barometer read error: {e}", "error".upper(), True)
        time.sleep(0.1)  # 10 Hz

def send_barometer_data(Main_Queue : Queue):
    global PRESSURE
    global TEMPERATURE
    global ALTITUDE
    global MAXALT_RESET_MUTEX

    # Do not forget to use runstatus variable on a global scope
    global BAROMETERAPP_RUNSTATUS

    # Create Message structure
    BarometerDataToTlmMsg = msgstructure.MsgStructure()
    BarometerDataToFlightLogicMsg = msgstructure.MsgStructure()

    msg_send_count = 0

    while BAROMETERAPP_RUNSTATUS:
        
        with MAXALT_RESET_MUTEX:
            # Send Message to Flight Logic in 10Hz
            status = msgstructure.send_msg(Main_Queue,
                                            BarometerDataToFlightLogicMsg,
                                            appargs.BarometerAppArg.AppID,
                                            appargs.FlightlogicAppArg.AppID,
                                            appargs.BarometerAppArg.MID_SendBarometerFlightLogicData,
                                            f"{ALTITUDE}")
            if status == False:
                safe_log("Error When sending Barometer Flight Logic Message", "error".upper(), True)

        if msg_send_count > 10 : 
            # Send telemetry message to COMM app in 1Hz
            # 기본 데이터만 텔레메트리 전송 (고급 데이터는 로그에만 저장)
            tlm_data = f"{PRESSURE},{TEMPERATURE},{ALTITUDE}"
            
            status = msgstructure.send_msg(Main_Queue, 
                                        BarometerDataToTlmMsg, 
                                        appargs.BarometerAppArg.AppID,
                                        appargs.CommAppArg.AppID,
                                        appargs.BarometerAppArg.MID_SendBarometerTlmData,
                                        tlm_data)
            if status == False:
                safe_log("Error When sending Barometer Tlm Message", "error".upper(), True)
            
            # 고급 데이터 로깅
            if RESOLUTION_INFO is not None:
                pressure_res = RESOLUTION_INFO.get('pressure_resolution', 0.01)
                temp_res = RESOLUTION_INFO.get('temperature_resolution', 0.01)
                safe_log(f"Barometer Advanced Data - SeaLevelPressure: {SEA_LEVEL_PRESSURE:.2f}hPa, PressureRes: {pressure_res}hPa, TempRes: {temp_res}°C", "debug".upper(), False)

            msg_send_count = 0
        
        # Increment message send counter, Sleep 1 second
        msg_send_count += 1
        time.sleep(0.1)
    return

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while BAROMETERAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            time.sleep(1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

# This method is called from main app. Initialization, runloop process
def barometerapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global BAROMETERAPP_RUNSTATUS
    BAROMETERAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, barometer_instance = barometerapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendBarometerData_Thread"] = threading.Thread(target=send_barometer_data, args=(Main_Queue, ), name="SendBarometerData_Thread")
    thread_dict["READ"] = resilient_thread(read_barometer_data, args=(barometer_instance, ), name="READ")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while BAROMETERAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            if Main_Pipe.poll(1.0):  # 1초 타임아웃
                try:
                    message = Main_Pipe.recv()
                except Exception as e:
                    safe_log(f"Pipe receive error: {e}", "warning".upper(), False)
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            recv_msg = message
            
            # Validate Message, Skip this message if target AppID different from barometerapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.BarometerAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(Main_Queue, recv_msg, barometer_instance)
            else:
                safe_log("Receiver MID does not match with barometerapp MID", "error".upper(), True)

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"barometerapp error : {e}", "error".upper(), True)
        BAROMETERAPP_RUNSTATUS = False

    # Termination Process after runloop
    barometerapp_terminate(i2c_instance)

    return

# ──────────────────────────────
# BarometerApp 클래스 (main.py 호환성)
# ──────────────────────────────
class BarometerApp:
    """Barometer 앱 클래스 - main.py 호환성을 위한 래퍼"""
    
    def __init__(self):
        """BarometerApp 초기화"""
        self.app_name = "Barometer"
        self.app_id = appargs.BarometerAppArg.AppID
        self.run_status = True
    
    def start(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 시작 - main.py에서 호출됨"""
        try:
            barometerapp_main(main_queue, main_pipe)
        except Exception as e:
            safe_log(f"BarometerApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """앱 중지"""
        global BAROMETERAPP_RUNSTATUS
        BAROMETERAPP_RUNSTATUS = False
        self.run_status = False
