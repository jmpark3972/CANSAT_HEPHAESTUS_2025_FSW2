#!/usr/bin/env python3
"""
Hybrid GPS App for CANSAT FSW - Enhanced Location System
하이브리드 GPS + WiFi + Cell Tower 위치 시스템 앱
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
from gps import hybrid_gps
from gps.hybrid_gps import LocationSource

# 전역 변수
HYBRID_GPSAPP_RUNSTATUS = False
LATITUDE = 0.0
LONGITUDE = 0.0
ALTITUDE = 0.0
ACCURACY = 100.0
LOCATION_SOURCE = LocationSource.GPS
SATELLITES = 0
HAS_FIX = False
WIFI_NETWORKS = []
CELL_TOWERS = []

# 로그 파일 경로
LOG_DIR = "logs"
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "hybrid_gps_high_freq.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hybrid_gps_hk.csv")
STATUS_LOG_PATH = os.path.join(LOG_DIR, "hybrid_gps_status.csv")

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[{appargs.GpsAppArg.AppName}-HYBRID] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[HYBRID-GPS] 로깅 실패: {e}")
        print(f"[HYBRID-GPS] 원본 메시지: {message}")

def emergency_log_to_file(log_type: str, message: str):
    """긴급 로그 파일에 기록"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f"[{timestamp}] [{log_type}] {message}\n"
        
        emergency_log_path = os.path.join(LOG_DIR, f"hybrid_gps_emergency_{log_type.lower()}.log")
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
def command_handler(Main_Queue: Queue, recv_msg: msgstructure.MsgStructure, hybrid_gps_instance):
    global HYBRID_GPSAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"HYBRID_GPSAPP TERMINATION DETECTED", "info".upper(), True)
        HYBRID_GPSAPP_RUNSTATUS = False
    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue: Queue):
    global HYBRID_GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, ACCURACY, LOCATION_SOURCE, SATELLITES, HAS_FIX
    while HYBRID_GPSAPP_RUNSTATUS:
        try:
            gpsHK = msgstructure.MsgStructure()
            hk_payload = f"run={HYBRID_GPSAPP_RUNSTATUS},lat={LATITUDE:.6f},lon={LONGITUDE:.6f},alt={ALTITUDE:.1f},acc={ACCURACY:.1f},source={LOCATION_SOURCE.value},sats={SATELLITES},has_fix={HAS_FIX}"
            status = msgstructure.send_msg(Main_Queue, gpsHK, appargs.GpsAppArg.AppID, appargs.HkAppArg.AppID, appargs.GpsAppArg.MID_SendHK, hk_payload)
            
            if status:
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, HYBRID_GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, ACCURACY, LOCATION_SOURCE.value, SATELLITES, HAS_FIX]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "latitude", "longitude", "altitude", "accuracy", "source", "satellites", "has_fix"], hk_row)
                
        except Exception as e:
            safe_log(f"HK send error: {e}", "error".upper(), True)
            
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not HYBRID_GPSAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def hybrid_gpsapp_init():
    """하이브리드 GPS 시스템 초기화"""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializing Hybrid GPS app", "info".upper(), True)

        # 하이브리드 GPS 시스템 초기화
        hybrid_system = hybrid_gps.init_hybrid_gps()
        
        if not hybrid_system:
            safe_log("Hybrid GPS initialization failed", "error".upper(), True)
            return None
        
        safe_log("Hybrid GPS app initialization complete", "info".upper(), True)
        return hybrid_system

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None

# Termination
def hybrid_gpsapp_terminate(hybrid_gps_instance):
    global HYBRID_GPSAPP_RUNSTATUS

    HYBRID_GPSAPP_RUNSTATUS = False
    safe_log("Terminating Hybrid GPS app", "info".upper(), True)
    
    # 하이브리드 GPS 리소스 정리
    if hybrid_gps_instance:
        hybrid_gps.cleanup_hybrid_gps()
    
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

    safe_log("Terminating Hybrid GPS app complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################

def read_hybrid_gps_data(hybrid_gps_instance):
    """하이브리드 GPS 데이터 읽기 스레드"""
    global HYBRID_GPSAPP_RUNSTATUS, LATITUDE, LONGITUDE, ALTITUDE, ACCURACY, LOCATION_SOURCE, SATELLITES, HAS_FIX, WIFI_NETWORKS, CELL_TOWERS
    
    while HYBRID_GPSAPP_RUNSTATUS:
        try:
            # 하이브리드 위치 정보 읽기
            location_data = hybrid_gps.read_hybrid_location()
            
            if location_data:
                LATITUDE = location_data.latitude
                LONGITUDE = location_data.longitude
                ALTITUDE = location_data.altitude or 0.0
                ACCURACY = location_data.accuracy or 100.0
                LOCATION_SOURCE = location_data.source
                SATELLITES = location_data.satellites or 0
                HAS_FIX = True
                WIFI_NETWORKS = location_data.wifi_networks or []
                CELL_TOWERS = location_data.cell_towers or []
                
                safe_log(f"하이브리드 위치: {LATITUDE:.6f}, {LONGITUDE:.6f} (정확도: {ACCURACY:.1f}m, 소스: {LOCATION_SOURCE.value})", "debug".upper(), True)
            else:
                HAS_FIX = False
                # 마지막 알려진 위치 유지
                
        except Exception as e:
            safe_log(f"Hybrid GPS read error: {e}", "error".upper(), True)
        time.sleep(0.1)  # 10 Hz

def send_hybrid_gps_data(Main_Queue: Queue):
    global LATITUDE, LONGITUDE, ALTITUDE, ACCURACY, LOCATION_SOURCE, SATELLITES, HAS_FIX, WIFI_NETWORKS, CELL_TOWERS

    # Do not forget to use runstatus variable on a global scope
    global HYBRID_GPSAPP_RUNSTATUS

    # Create Message structure
    HybridGpsDataToFlightLogicMsg = msgstructure.MsgStructure()

    while HYBRID_GPSAPP_RUNSTATUS:
        try:
            # Send hybrid GPS data to Flight Logic in 10Hz
            gps_payload = f"{LATITUDE:.6f},{LONGITUDE:.6f},{ALTITUDE:.1f},{ACCURACY:.1f},{LOCATION_SOURCE.value},{SATELLITES},{HAS_FIX}"
            
            status = msgstructure.send_msg(Main_Queue,
                                          HybridGpsDataToFlightLogicMsg,
                                          appargs.GpsAppArg.AppID,
                                          appargs.FlightlogicAppArg.AppID,
                                          appargs.GpsAppArg.MID_SendGpsFlightLogicData,
                                          gps_payload)
            if status == False:
                safe_log("Error When sending Hybrid GPS Flight Logic Message", "error".upper(), True)

            # High frequency hybrid GPS data logging
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            gps_row = [timestamp, LATITUDE, LONGITUDE, ALTITUDE, ACCURACY, LOCATION_SOURCE.value, SATELLITES, HAS_FIX, len(WIFI_NETWORKS), len(CELL_TOWERS)]
            log_csv(HIGH_FREQ_LOG_PATH, ["timestamp", "latitude", "longitude", "altitude", "accuracy", "source", "satellites", "has_fix", "wifi_count", "cell_count"], gps_row)
            
        except Exception as e:
            safe_log(f"Hybrid GPS data send error: {e}", "error".upper(), True)
            
        time.sleep(0.1)  # 10 Hz
    return

def log_location_status(hybrid_gps_instance):
    """위치 시스템 상태 로깅 스레드"""
    global HYBRID_GPSAPP_RUNSTATUS
    
    while HYBRID_GPSAPP_RUNSTATUS:
        try:
            # 위치 시스템 상태 확인
            status = hybrid_gps.get_location_status()
            
            # 상태 로깅
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            status_row = [
                timestamp,
                status.get('gps_available', False),
                status.get('gps_has_fix', False),
                status.get('gps_satellites', 0),
                status.get('wifi_available', False),
                status.get('last_gps_fix', ''),
                status.get('last_wifi_fix', ''),
                status.get('wifi_cache_age', 0)
            ]
            log_csv(STATUS_LOG_PATH, ["timestamp", "gps_available", "gps_has_fix", "gps_satellites", "wifi_available", "last_gps_fix", "last_wifi_fix", "wifi_cache_age"], status_row)
            
        except Exception as e:
            safe_log(f"Status logging error: {e}", "error".upper(), True)
            
        time.sleep(5.0)  # 5초마다 상태 로깅
    return

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# 스레드 자동 재시작 래퍼
def resilient_thread(target, args=(), name=None):
    def wrapper():
        while HYBRID_GPSAPP_RUNSTATUS:
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
def hybrid_gpsapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global HYBRID_GPSAPP_RUNSTATUS
    HYBRID_GPSAPP_RUNSTATUS = True

    # Initialization Process
    hybrid_gps_instance = hybrid_gpsapp_init()

    if hybrid_gps_instance is None:
        safe_log("Hybrid GPS initialization failed, terminating app", "error".upper(), True)
        return

    # Spawn SB Message Listener Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendHybridGpsData_Thread"] = threading.Thread(target=send_hybrid_gps_data, args=(Main_Queue, ), name="SendHybridGpsData_Thread")
    thread_dict["StatusLogger_Thread"] = threading.Thread(target=log_location_status, args=(hybrid_gps_instance, ), name="StatusLogger_Thread")
    thread_dict["READ"] = resilient_thread(read_hybrid_gps_data, args=(hybrid_gps_instance, ), name="READ")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while HYBRID_GPSAPP_RUNSTATUS:
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
                command_handler(Main_Queue, recv_msg, hybrid_gps_instance)
            else:
                safe_log("Receiver MID does not match with hybrid gpsapp MID", "error".upper(), True)

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"hybrid_gpsapp error : {e}", "error".upper(), True)
        HYBRID_GPSAPP_RUNSTATUS = False

    # Termination Process after runloop
    hybrid_gpsapp_terminate(hybrid_gps_instance)

    return

# HybridGpsApp 클래스 (main.py 호환성)
class HybridGpsApp:
    def __init__(self):
        """HybridGpsApp 초기화"""
        try:
            self.app_id = appargs.GpsAppArg.AppID
            self.main_queue = Queue()
            self.main_pipe, child_pipe = connection.Pipe()
            hybrid_gpsapp_main(self.main_queue, self.main_pipe)
        except Exception as e:
            safe_log(f"HybridGpsApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """HybridGpsApp 중지"""
        global HYBRID_GPSAPP_RUNSTATUS
        HYBRID_GPSAPP_RUNSTATUS = False
