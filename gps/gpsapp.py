#!/usr/bin/env python3
"""
GPS App for CANSAT FSW - MAX-M10S Qwiic Version
MAX-M10S Qwiic GPS 모듈을 사용한 GPS 애플리케이션
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
from gps import gps_max_m10s

# 전역 변수
GPSAPP_RUNSTATUS = False
LATITUDE = 0.0
LONGITUDE = 0.0
ALTITUDE = 0.0
SPEED = 0.0
COURSE = 0.0
SATELLITES = 0
FIX_QUALITY = 0
HAS_FIX = False

# 로그 파일 경로
LOG_DIR = "logs"
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "gps_high_freq.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[{appargs.GpsAppArg.AppName}] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[GPS] 로깅 실패: {e}")
        print(f"[GPS] 원본 메시지: {message}")

def emergency_log_to_file(log_type: str, message: str):
    """긴급 로그 파일에 기록"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f"[{timestamp}] [{log_type}] {message}\n"
        
        emergency_log_path = os.path.join(LOG_DIR, f"gps_emergency_{log_type.lower()}.log")
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

######################################################
## FUNDAMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler(Main_Queue: Queue, recv_msg: msgstructure.MsgStructure, gps_instance):
    global GPSAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"GPSAPP TERMINATION DETECTED", "info".upper(), True)
        GPSAPP_RUNSTATUS = False
    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue: Queue):
    global GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, SPEED, COURSE, SATELLITES, FIX_QUALITY
    while GPSAPP_RUNSTATUS:
        try:
            gpsHK = msgstructure.MsgStructure()
            hk_payload = f"run={GPSAPP_RUNSTATUS},lat={LATITUDE:.6f},lon={LONGITUDE:.6f},alt={ALTITUDE:.1f},speed={SPEED:.1f},course={COURSE:.1f},sats={SATELLITES},fix={FIX_QUALITY},has_fix={HAS_FIX}"
            status = msgstructure.send_msg(Main_Queue, gpsHK, appargs.GpsAppArg.AppID, appargs.HkAppArg.AppID, appargs.GpsAppArg.MID_SendHK, hk_payload)
            
            if status:
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, SPEED, COURSE, SATELLITES, FIX_QUALITY, HAS_FIX]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "latitude", "longitude", "altitude", "speed", "course", "satellites", "fix_quality", "has_fix"], hk_row)
                
        except Exception as e:
            safe_log(f"HK send error: {e}", "error".upper(), True)
            
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not GPSAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def gpsapp_init():
    """MAX-M10S GPS 센서 초기화"""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializing GPS app (MAX-M10S Qwiic)", "info".upper(), True)

        # MAX-M10S GPS 센서 초기화
        i2c, gps = gps_max_m10s.init_gps()
        
        if gps is None:
            safe_log("GPS initialization failed", "error".upper(), True)
            return None, None
        
        safe_log("GPS app initialization complete", "info".upper(), True)
        return i2c, gps

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None

# Termination
def gpsapp_terminate(i2c_instance):
    global GPSAPP_RUNSTATUS

    GPSAPP_RUNSTATUS = False
    safe_log("Terminating GPS app", "info".upper(), True)
    
    # GPS 리소스 정리
    gps_max_m10s.terminate_gps(i2c_instance)
    
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

    safe_log("Terminating GPS app complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################

def read_gps_data(gps):
    """GPS 데이터 읽기 스레드"""
    global GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, SPEED, COURSE, SATELLITES, FIX_QUALITY, HAS_FIX
    while GPSAPP_RUNSTATUS:
        try:
            gps_data = gps_max_m10s.read_gps(gps)
            
            if gps_data and gps_data.get('has_fix'):
                LATITUDE = gps_data['latitude']
                LONGITUDE = gps_data['longitude']
                ALTITUDE = gps_data['altitude']
                SPEED = gps_data['speed']
                COURSE = gps_data['course']
                SATELLITES = gps_data['satellites']
                FIX_QUALITY = gps_data['fix_quality']
                HAS_FIX = True
            else:
                HAS_FIX = False
                if gps_data:
                    SATELLITES = gps_data.get('satellites', 0)
                
        except Exception as e:
            safe_log(f"GPS read error: {e}", "error".upper(), True)
        time.sleep(0.1)  # 10 Hz

def send_gps_data(Main_Queue: Queue):
    global LATITUDE, LONGITUDE, ALTITUDE, SPEED, COURSE, SATELLITES, FIX_QUALITY, HAS_FIX

    # Do not forget to use runstatus variable on a global scope
    global GPSAPP_RUNSTATUS

    # Create Message structure
    GpsDataToFlightLogicMsg = msgstructure.MsgStructure()

    while GPSAPP_RUNSTATUS:
        try:
            # Send GPS data to Flight Logic in 10Hz
            gps_payload = f"{LATITUDE:.6f},{LONGITUDE:.6f},{ALTITUDE:.1f},{SPEED:.1f},{COURSE:.1f},{SATELLITES},{FIX_QUALITY},{HAS_FIX}"
            
            status = msgstructure.send_msg(Main_Queue,
                                          GpsDataToFlightLogicMsg,
                                          appargs.GpsAppArg.AppID,
                                          appargs.FlightlogicAppArg.AppID,
                                          appargs.GpsAppArg.MID_SendGpsFlightLogicData,
                                          gps_payload)
            if status == False:
                safe_log("Error When sending GPS Flight Logic Message", "error".upper(), True)

            # High frequency GPS data logging
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            gps_row = [timestamp, LATITUDE, LONGITUDE, ALTITUDE, SPEED, COURSE, SATELLITES, FIX_QUALITY, HAS_FIX]
            log_csv(HIGH_FREQ_LOG_PATH, ["timestamp", "latitude", "longitude", "altitude", "speed", "course", "satellites", "fix_quality", "has_fix"], gps_row)
            
        except Exception as e:
            safe_log(f"GPS data send error: {e}", "error".upper(), True)
            
        time.sleep(0.1)  # 10 Hz
    return

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# 스레드 자동 재시작 래퍼
def resilient_thread(target, args=(), name=None):
    def wrapper():
        while GPSAPP_RUNSTATUS:
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
def gpsapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global GPSAPP_RUNSTATUS
    GPSAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, gps_instance = gpsapp_init()

    if gps_instance is None:
        safe_log("GPS initialization failed, terminating app", "error".upper(), True)
        return

    # Spawn SB Message Listener Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendGpsData_Thread"] = threading.Thread(target=send_gps_data, args=(Main_Queue, ), name="SendGpsData_Thread")
    thread_dict["READ"] = resilient_thread(read_gps_data, args=(gps_instance, ), name="READ")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while GPSAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            if Main_Pipe.poll(1.0):  # 1초 타임아웃
                try:
                    message = Main_Pipe.recv()
                except:
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            recv_msg = message
            
            # Validate Message, Skip this message if target AppID different from gpsapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.GpsAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(Main_Queue, recv_msg, gps_instance)
            else:
                safe_log("Receiver MID does not match with gpsapp MID", "error".upper(), True)

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"gpsapp error : {e}", "error".upper(), True)
        GPSAPP_RUNSTATUS = False

    # Termination Process after runloop
    gpsapp_terminate(i2c_instance)

    return

# GpsApp 클래스 (main.py 호환성)
class GpsApp:
    def __init__(self):
        """GpsApp 초기화"""
        try:
            self.app_id = appargs.GpsAppArg.AppID
            self.main_queue = Queue()
            self.main_pipe, child_pipe = connection.Pipe()
            gpsapp_main(self.main_queue, self.main_pipe)
        except Exception as e:
            safe_log(f"GpsApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """GpsApp 중지"""
        global GPSAPP_RUNSTATUS
        GPSAPP_RUNSTATUS = False
