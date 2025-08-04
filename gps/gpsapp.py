# Python FSW V2 Gps App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[GPS] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[GPS] 로깅 실패: {e}")
        print(f"[GPS] 원본 메시지: {message}")

from lib import types

import signal
from multiprocessing import Queue, connection
import threading
import time

from gps import gps

# Runstatus of application. Application is terminated when false
GPSAPP_RUNSTATUS = True
gps_instance = None
######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global GPSAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"GPSAPP TERMINATION DETECTED", "info".upper(), True)
        GPSAPP_RUNSTATUS = False

    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue : Queue):
    global GPSAPP_RUNSTATUS
    while GPSAPP_RUNSTATUS:
        gpsHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, gpsHK, appargs.GpsAppArg.AppID, appargs.HkAppArg.AppID, appargs.GpsAppArg.MID_SendHK, str(GPSAPP_RUNSTATUS))
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
    global GPSAPP_RUNSTATUS
    global gps_instance
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializating gpsapp", "info".upper(), True)
        ## User Defined Initialization goes HERE
        gps_instance = gps.init_gps()
        safe_log("Gpsapp Initialization Complete", "info".upper(), True)
        return gps_instance
    except Exception as e:
        safe_log("Error during initialization", "error".upper(), True)
        GPSAPP_RUNSTATUS = False

# Termination
def gpsapp_terminate():
    global GPSAPP_RUNSTATUS
    global gps_instance
    GPSAPP_RUNSTATUS = False
    safe_log("Terminating gpsapp", "info".upper(), True)
    # Termination Process Comes Here

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

    if gps_instance is not None:
        gps.terminate_gps(gps_instance)
        gps_instance = None
        safe_log("GPS connection terminated", "info".upper(), True)

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    safe_log("Terminating gpsapp complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################


def read_gps_data(gps_instance):
    global GPS_LAT, GPS_LON, GPS_ALT, GPS_TIME, GPS_SATS, GPSAPP_RUNSTATUS
    while GPSAPP_RUNSTATUS:
        try:
            lat, lon, alt, time_str, sats = gps.read_gps(gps_instance)
            if lat is not None and lon is not None and alt is not None and time_str is not None and sats is not None:
                GPS_LAT, GPS_LON, GPS_ALT, GPS_TIME, GPS_SATS = lat, lon, alt, time_str, sats
        except Exception:
            # 에러 메시지 출력하지 않고, 이전 값 유지
            pass
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not GPSAPP_RUNSTATUS:
                break
            time.sleep(0.1)

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while GPSAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            # 더 빠른 종료를 위해 짧은 간격으로 체크
            for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
                if not GPSAPP_RUNSTATUS:
                    break
                time.sleep(0.1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

# This method is called from main app. Initialization, runloop process
def gpsapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global GPSAPP_RUNSTATUS
    GPSAPP_RUNSTATUS = True

    # Initialization Process
    gps_instance = gpsapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["READ"] = resilient_thread(read_gps_data, args=(gps_instance,), name="READ")

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
                
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from gpsapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.GpsAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg)
            else:
                safe_log("Receiver MID does not match with gpsapp MID", "error".upper(), True)

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"gpsapp error : {e}", "error".upper(), True)
        GPSAPP_RUNSTATUS = False

    # Termination Process after runloop
    gpsapp_terminate()

    return
