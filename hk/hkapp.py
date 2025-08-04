# Python FSW V2 Hk App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[HK] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[HK] 로깅 실패: {e}")
        print(f"[HK] 원본 메시지: {message}")

from lib import types

import os
import signal
from multiprocessing import Queue, connection
import threading
import time
import sys

# Runstatus of application. Application is terminated when false
HKAPP_RUNSTATUS = True

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

hk_dict = {}

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global HKAPP_RUNSTATUS
    global hk_dict

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"HKAPP TERMINATION DETECTED", "info".upper(), True)
        HKAPP_RUNSTATUS = False

    else:
        if recv_msg.sender_app not in hk_dict:
            hk_dict[recv_msg.sender_app] = 0
        else:
            hk_dict[recv_msg.sender_app] += 1
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def hkapp_init():
    global HKAPP_RUNSTATUS
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializating hkapp", "info".upper(), True)
        ## User Defined Initialization goes HERE
        safe_log("hkapp Initialization Complete", "info".upper(), True)

    except:
        safe_log("Error during initialization", "error".upper(), True)

# Termination
def hkapp_terminate():
    global HKAPP_RUNSTATUS

    HKAPP_RUNSTATUS = False
    safe_log("Terminating hkapp", "info".upper(), True)
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

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    safe_log("Terminating hkapp complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################

def print_hk_status():
    global HKAPP_RUNSTATUS

    while HKAPP_RUNSTATUS:
        #print(hk_dict)
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not HKAPP_RUNSTATUS:
                break
            time.sleep(0.1)

    return

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while HKAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            # 더 빠른 종료를 위해 짧은 간격으로 체크
            for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
                if not HKAPP_RUNSTATUS:
                    break
                time.sleep(0.1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

# This method is called from main app. Initialization, runloop process
def hkapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global HKAPP_RUNSTATUS
    HKAPP_RUNSTATUS = True

    # Initialization Process
    hkapp_init()

    thread_dict["PrintHKStat_Thread"] = resilient_thread(target=print_hk_status, name="PrintHKStat_Thread")

    #Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while HKAPP_RUNSTATUS:
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
            
            # Validate Message, Skip this message if target AppID different from hkapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.HkAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg)
            else:
                safe_log("Receiver MID does not match with hkapp MID", "error".upper(), True)

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"hkapp error : {e}", "error".upper(), True)
        HKAPP_RUNSTATUS = False

    # Termination Process after runloop
    hkapp_terminate()

    return