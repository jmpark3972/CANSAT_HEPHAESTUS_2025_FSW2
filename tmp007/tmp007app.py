# Python FSW V2 TMP007 App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[TMP007] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[TMP007] 로깅 실패: {e}")
        print(f"[TMP007] 원본 메시지: {message}")

from lib import types

import signal
from multiprocessing import Queue, connection
import threading
import time
import os
import csv
from datetime import datetime

# Import TMP007 sensor library
from tmp007 import tmp007

# Runstatus of application. Application is terminated when false
TMP007APP_RUNSTATUS = True

# 강화된 로깅 시스템
LOG_DIR = "logs/tmp007"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "high_freq_tmp007_log.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")
SENSOR_LOG_PATH = os.path.join(LOG_DIR, "sensor_log.csv")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.csv")

# 강제 종료 시에도 로그를 저장하기 위한 플래그
_emergency_logging_enabled = True

# 데이터 전송 통계
data_transmission_stats = {
    'packets_sent': 0,
    'packets_failed': 0,
    'last_successful_transmission': None,
    'consecutive_failures': 0,
    'max_consecutive_failures': 0
}

# TMP007 센서 데이터
TMP007_OBJECT_TEMP = 0.0
TMP007_DIE_TEMP = 0.0
TMP007_VOLTAGE = 0.0
TMP007_STATUS = {}

######################################################
## 강화된 로깅 시스템                                ##
######################################################

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
        elif log_type == "SENSOR":
            with open(SENSOR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        elif log_type == "ERROR":
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
    except Exception as e:
        print(f"Emergency logging failed: {e}")

def log_high_freq_tmp007_data(object_temp, die_temp, voltage):
    """고주파수 TMP007 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(HIGH_FREQ_LOG_PATH):
            with open(HIGH_FREQ_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'object_temp', 'die_temp', 'voltage'])
        
        # 데이터 추가
        with open(HIGH_FREQ_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, object_temp, die_temp, voltage])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"High frequency TMP007 logging failed: {e}")

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

def log_sensor_data(sensor_type: str, data: dict):
    """센서 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(SENSOR_LOG_PATH):
            with open(SENSOR_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'sensor_type', 'data'])
        
        # 데이터 추가
        with open(SENSOR_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, sensor_type, str(data)])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"Sensor logging failed: {e}")

def log_error(error_msg: str, context: str = ""):
    """오류를 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        full_msg = f"{error_msg} | Context: {context}" if context else error_msg
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'error_message'])
        
        # 데이터 추가
        with open(ERROR_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, full_msg])
            
    except Exception as e:
        print(f"Error logging failed: {e}")

def get_transmission_stats():
    """전송 통계 반환"""
    global data_transmission_stats
    return data_transmission_stats.copy()

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global TMP007APP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"TMP007APP TERMINATION DETECTED", "info".upper(), True)
        TMP007APP_RUNSTATUS = False

    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue : Queue):
    global TMP007APP_RUNSTATUS, TMP007_OBJECT_TEMP, TMP007_DIE_TEMP, TMP007_VOLTAGE
    consecutive_hk_failures = 0
    max_hk_failures = 3
    
    while TMP007APP_RUNSTATUS:
        try:
            tmp007HK = msgstructure.MsgStructure()
            hk_payload = f"run={TMP007APP_RUNSTATUS},obj_temp={TMP007_OBJECT_TEMP:.2f},die_temp={TMP007_DIE_TEMP:.2f},voltage={TMP007_VOLTAGE:.2f}"
            status = msgstructure.send_msg(Main_Queue, tmp007HK, appargs.Tmp007AppArg.AppID, appargs.HkAppArg.AppID, appargs.Tmp007AppArg.MID_SendHK, hk_payload)
            if status == False:
                consecutive_hk_failures += 1
                if consecutive_hk_failures <= max_hk_failures:
                    safe_log("Error sending HK message", "error".upper(), True)
                elif consecutive_hk_failures == max_hk_failures + 1:
                    safe_log(f"HK send errors suppressed after {max_hk_failures} failures", "warning".upper(), True)
            else:
                consecutive_hk_failures = 0
                
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, TMP007APP_RUNSTATUS, TMP007_OBJECT_TEMP, TMP007_DIE_TEMP, TMP007_VOLTAGE]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "object_temp", "die_temp", "voltage"], hk_row)
        except Exception as e:
            consecutive_hk_failures += 1
            if consecutive_hk_failures <= max_hk_failures:
                safe_log(f"Exception sending HK: {e}", "error".upper(), True)
            elif consecutive_hk_failures == max_hk_failures + 1:
                safe_log(f"HK send exceptions suppressed after {max_hk_failures} failures", "warning".upper(), True)
        
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not TMP007APP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def tmp007app_init():
    global TMP007APP_RUNSTATUS
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializating tmp007app", "info".upper(), True)
        ## User Defined Initialization goes HERE
        
        #Initialize TMP007 Sensor
        i2c_instance, tmp007_instance = tmp007.init_tmp007()
        
        safe_log("Tmp007app Initialization Complete", "info".upper(), True)
        return i2c_instance, tmp007_instance
    
    except Exception as e:
        safe_log(f"Error during initialization: {e}", "error".upper(), True)
        TMP007APP_RUNSTATUS = False
        return None, None

# Termination
def tmp007app_terminate(i2c_instance):
    global TMP007APP_RUNSTATUS
    TMP007APP_RUNSTATUS = False
    safe_log("Terminating tmp007app", "info".upper(), True)
    
    # Close MUX connection
    # MUX 관련 코드 제거됨
    
    tmp007.terminate_tmp007(i2c_instance)
    
    # Join Each Thread to make sure all threads terminates
    for t in thread_dict.values():
        t.join()
    
    safe_log("Terminating tmp007app complete", "info".upper(), True)

######################################################
## USER METHOD                                      ##
######################################################

# Put user-defined methods here!

def read_tmp007_data(tmp007_instance):
    global TMP007_OBJECT_TEMP, TMP007_DIE_TEMP, TMP007_VOLTAGE, TMP007_STATUS
    
    consecutive_failures = 0
    max_failures = 10
    
    while TMP007APP_RUNSTATUS:
        try:
            # TMP007 센서 데이터 읽기
            data = tmp007.read_tmp007_data(tmp007_instance)
            
            if data is not None:
                TMP007_OBJECT_TEMP = data['object_temperature']
                TMP007_DIE_TEMP = data['die_temperature']
                TMP007_VOLTAGE = data['voltage']
                TMP007_STATUS = data['status']
                
                # 센서 데이터 로깅
                log_sensor_data("TMP007", data)
                
                # 고주파수 로깅 (10Hz)
                log_high_freq_tmp007_data(TMP007_OBJECT_TEMP, TMP007_DIE_TEMP, TMP007_VOLTAGE)
                
                consecutive_failures = 0  # 성공 시 실패 횟수 리셋
            else:
                consecutive_failures += 1
                if consecutive_failures <= max_failures:
                    safe_log("TMP007 data read failed", "error".upper(), True)
                elif consecutive_failures == max_failures + 1:
                    safe_log(f"TMP007 read errors suppressed after {max_failures} failures", "warning".upper(), True)
                
                # 기본값 설정
                TMP007_OBJECT_TEMP = TMP007_DIE_TEMP = TMP007_VOLTAGE = 0.0
                TMP007_STATUS = {}
                
                # 오류 시 더 긴 대기
                time.sleep(0.1)
                continue
                
        except Exception as e:
            consecutive_failures += 1
            if consecutive_failures <= max_failures:
                safe_log(f"TMP007 read error: {e}", "error".upper(), True)
            elif consecutive_failures == max_failures + 1:
                safe_log(f"TMP007 read errors suppressed after {max_failures} failures", "warning".upper(), True)
            
            # 기본값 설정
            TMP007_OBJECT_TEMP = TMP007_DIE_TEMP = TMP007_VOLTAGE = 0.0
            TMP007_STATUS = {}
            
            # 오류 시 더 긴 대기
            time.sleep(0.1)
            continue
            
        # TMP007 runs on 10Hz (0.1초 간격) for maximum data collection
        time.sleep(0.1)
    return

def send_tmp007_data(Main_Queue : Queue):
    global TMP007APP_RUNSTATUS, TMP007_OBJECT_TEMP, TMP007_DIE_TEMP, TMP007_VOLTAGE
    
    send_counter = 0
    consecutive_send_failures = 0
    max_send_failures = 5

    while TMP007APP_RUNSTATUS:
        send_counter += 1

        if send_counter >= 4 :  # 1초마다 전송 (4Hz)
            try:
                # Send telemetry message to COMM app
                Tmp007DataToTlmMsg = msgstructure.MsgStructure()
                status = msgstructure.send_msg(Main_Queue, 
                                            Tmp007DataToTlmMsg, 
                                            appargs.Tmp007AppArg.AppID,
                                            appargs.CommAppArg.AppID,
                                            appargs.Tmp007AppArg.MID_SendTmp007TlmData,
                                            f"{TMP007_OBJECT_TEMP:.2f},{TMP007_DIE_TEMP:.2f},{TMP007_VOLTAGE:.2f}")
                if status == False:
                    consecutive_send_failures += 1
                    if consecutive_send_failures <= max_send_failures:
                        safe_log("Error When sending TMP007 Tlm Message", "error".upper(), True)
                    elif consecutive_send_failures == max_send_failures + 1:
                        safe_log(f"TMP007 send errors suppressed after {max_send_failures} failures", "warning".upper(), True)
                else:
                    consecutive_send_failures = 0  # 성공 시 실패 횟수 리셋
            except Exception as e:
                consecutive_send_failures += 1
                if consecutive_send_failures <= max_send_failures:
                    safe_log(f"Exception when sending TMP007 data: {e}", "error".upper(), True)
                elif consecutive_send_failures == max_send_failures + 1:
                    safe_log(f"TMP007 send exceptions suppressed after {max_send_failures} failures", "warning".upper(), True)
            
            # Send data to FlightLogic app (4Hz)
            try:
                Tmp007DataToFlightLogicMsg = msgstructure.MsgStructure()
                status = msgstructure.send_msg(Main_Queue, 
                                            Tmp007DataToFlightLogicMsg, 
                                            appargs.Tmp007AppArg.AppID,
                                            appargs.FlightlogicAppArg.AppID,
                                            appargs.Tmp007AppArg.MID_SendTmp007FlightLogicData,
                                            f"{TMP007_OBJECT_TEMP:.2f},{TMP007_DIE_TEMP:.2f},{TMP007_VOLTAGE:.2f}")
                if status == False:
                    safe_log("Error When sending TMP007 FlightLogic Message", "error".upper(), True)
            except Exception as e:
                safe_log(f"Exception when sending TMP007 FlightLogic data: {e}", "error".upper(), True)
            
            send_counter = 0
            
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not TMP007APP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def tmp007app_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global TMP007APP_RUNSTATUS
    TMP007APP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, tmp007_instance = tmp007app_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["Tmp007Reader_Thread"] = threading.Thread(target=read_tmp007_data, args=(tmp007_instance, ), name="Tmp007Reader_Thread")
    thread_dict["Tmp007Sender_Thread"] = threading.Thread(target=send_tmp007_data, args=(Main_Queue, ), name="Tmp007Sender_Thread")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while TMP007APP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            try:
                if Main_Pipe.poll(0.5):  # 0.5초 타임아웃으로 단축
                    try:
                        message = Main_Pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError):
                        safe_log("Pipe connection lost", "error".upper(), True)
                        log_error("Pipe connection lost", "tmp007app_main")
                        break
                    except Exception as e:
                        safe_log(f"Pipe receive error: {e}", "error".upper(), True)
                        log_error(f"Pipe receive error: {e}", "tmp007app_main")
                        continue
                else:
                    # 타임아웃 시 루프 계속
                    continue
                    
                recv_msg = msgstructure.MsgStructure()

                # Unpack Message, Skip this message if unpacked message is not valid
                if msgstructure.unpack_msg(recv_msg, message) == False:
                    continue
                
                # Validate Message, Skip this message if target AppID different from tmp007app's AppID
                # Exception when the message is from main app
                if recv_msg.receiver_app == appargs.Tmp007AppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                    # Handle Command According to Message ID
                    command_handler(recv_msg)
                else:
                    safe_log("Receiver MID does not match with tmp007app MID", "error".upper(), True)
                    
            except Exception as e:
                safe_log(f"Main loop error: {e}", "error".upper(), True)
                log_error(f"Main loop error: {e}", "tmp007app_main")
                time.sleep(0.1)  # 에러 시 짧은 대기

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"tmp007app error : {e}", "error".upper(), True)
        log_error(f"Critical tmp007app error: {e}", "tmp007app_main")
        TMP007APP_RUNSTATUS = False

    # Termination Process after runloop
    tmp007app_terminate(i2c_instance)

    return 