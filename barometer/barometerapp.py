# Python FSW V2 Barometer App
# Author : Hyeon Lee

import signal
import time
from queue import Queue
from lib import events
from lib import appargs
from lib import msgstructure
from barometer import barometer

import threading
import csv
import os
from datetime import datetime

# Runstatus of application. Application is terminated when false
BAROMETERAPP_RUNSTATUS = True

# 고주파수 로깅 시스템
LOG_DIR = "logs/barometer"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "high_freq_barometer_log.csv")
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

def log_high_freq_barometer_data(pressure, temperature, altitude):
    """고주파수 Barometer 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(HIGH_FREQ_LOG_PATH):
            with open(HIGH_FREQ_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'pressure', 'temperature', 'altitude'])
        
        # 데이터 추가
        with open(HIGH_FREQ_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, pressure, temperature, altitude])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"High frequency barometer logging failed: {e}")

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

# Mutex to prevent two process sharing the same barometer instance
OFFSET_MUTEX = threading.Lock()

# Mutex to prevent sending of logic data when resetting
MAXALT_RESET_MUTEX = threading.Lock()

# MUX instance for channel 4 management
BAROMETER_MUX = None

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
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"BAROMETERAPP TERMINATION DETECTED")
        BAROMETERAPP_RUNSTATUS = False

    # Calibrate Barometer when calibrate command is input
    if recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        
        # Use mutex to prevent multiple thread accessing barometer instance at the same time
        with OFFSET_MUTEX:
            caldata = barometer.read_barometer(barometer_instance, 0)
            # altitude is the third index
            BAROMETER_OFFSET = float(caldata[2])

        # Use mutex to prevent the barometer process sending the wrong maxalt
        with MAXALT_RESET_MUTEX:
            ResetBarometerMaxAltCmd = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, ResetBarometerMaxAltCmd, appargs.BarometerAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.BarometerAppArg.MID_ResetBarometerMaxAlt, "")

            # sleep for 0.5 seconds to ensure the max alt reset. Since the mutex is holding, no barometer data can be sent to flightlogic
            time.sleep(0.5)

        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Barometer offset changed to {BAROMETER_OFFSET}")

        prevstate.update_altcal(BAROMETER_OFFSET)

    else:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
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
            events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"HK send error: {e}")
            
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

        events.LogEvent(appargs.BarometerAppArg.AppName,
                        events.EventType.info,
                        "Initializing barometerapp")

        # Barometer 센서 초기화 (직접 I2C 연결)
        i2c, bmp = barometer.init_barometer()
        
        events.LogEvent(appargs.BarometerAppArg.AppName,
                        events.EventType.info,
                        "Barometerapp initialization complete")
        return i2c, bmp

    except Exception as e:
        events.LogEvent(appargs.BarometerAppArg.AppName,
                        events.EventType.error,
                        f"Init error: {e}")
        return None, None

# Termination
def barometerapp_terminate(i2c_instance):
    global BAROMETERAPP_RUNSTATUS, BAROMETER_MUX

    BAROMETERAPP_RUNSTATUS = False
    events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Terminating barometerapp")
    # Termination Process Comes Here

    # Close MUX connection
    if BAROMETER_MUX:
        try:
            BAROMETER_MUX.close()
        except Exception as e:
            events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"MUX 종료 오류: {e}")

    barometer.terminate_barometer(i2c_instance)
    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        try:
            thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
            if thread_dict[thread_name].is_alive():
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.warning, f"Thread {thread_name} did not terminate gracefully")
        except Exception as e:
            events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"Error joining thread {thread_name}: {e}")
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Terminating barometerapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################
PRESSURE = 0
TEMPERATURE = 0
ALTITUDE = 0
# Set the offset of baromter
BAROMETER_OFFSET = 0

def read_barometer_data(bmp):
    """Barometer 데이터 읽기 스레드."""
    global BAROMETERAPP_RUNSTATUS, BAROMETER_ALTITUDE, BAROMETER_TEMPERATURE, BAROMETER_PRESSURE
    while BAROMETERAPP_RUNSTATUS:
        try:
            pressure, temperature, altitude = barometer.read_barometer(bmp, 0)
            BAROMETER_PRESSURE = pressure
            BAROMETER_TEMPERATURE = temperature
            BAROMETER_ALTITUDE = altitude
        except Exception as e:
            events.LogEvent(appargs.BarometerAppArg.AppName,
                            events.EventType.error,
                            f"Barometer read error: {e}")
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
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Error When sending Barometer Flight Logic Message")

        if msg_send_count > 10 : 
            # Send telemetry message to COMM app in 1Hz
            status = msgstructure.send_msg(Main_Queue, 
                                        BarometerDataToTlmMsg, 
                                        appargs.BarometerAppArg.AppID,
                                        appargs.CommAppArg.AppID,
                                        appargs.BarometerAppArg.MID_SendBarometerTlmData,
                                        f"{PRESSURE},{TEMPERATURE},{ALTITUDE}")
            if status == False:
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Error When sending Barometer Tlm Message")

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
                except:
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from barometerapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.BarometerAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(Main_Queue, recv_msg, barometer_instance)
            else:
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Receiver MID does not match with barometerapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"barometerapp error : {e}")
        BAROMETERAPP_RUNSTATUS = False

    # Termination Process after runloop
    barometerapp_terminate(i2c_instance)

    return
