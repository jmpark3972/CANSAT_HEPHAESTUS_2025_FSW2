# Python FSW V2 Hk App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[HK] [{level}] {message}"
        from lib.logging import safe_log as lib_safe_log
        lib_safe_log(f"[HK] {message}", level, printlogs)
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

    except Exception as e:
        safe_log(f"Error during initialization: {e}", "error".upper(), True)

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
            try:
                # Receive Message From Pipe with timeout
                # Non-blocking receive with timeout
                if Main_Pipe.poll(0.1):  # 0.1초 타임아웃으로 더 빠른 반응
                    try:
                        message = Main_Pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError) as e:
                        safe_log(f"Pipe connection lost: {e}", "warning".upper(), True)
                        # 연결이 끊어져도 로깅은 계속
                        time.sleep(0.1)
                        continue
                    except Exception as e:
                        safe_log(f"Pipe receive error: {e}", "warning".upper(), False)
                        # 에러 시 루프 계속
                        time.sleep(0.1)
                        continue
                else:
                    # 타임아웃 시 루프 계속 (더 짧은 간격)
                    time.sleep(0.01)
                    continue
                
            # 메시지 언패킹
            try:
                if isinstance(message, bytes):
                    # 바이트 메시지를 문자열로 디코드
                    message_str = message.decode('utf-8')
                elif isinstance(message, str):
                    message_str = message
                else:
                    safe_log(f"Unknown message type: {type(message)}", "warning".upper(), True)
                    continue
                
                # 메시지 언패킹
                recv_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(recv_msg, message_str):
                    safe_log("Failed to unpack message", "warning".upper(), True)
                    continue
                    
            except Exception as e:
                safe_log(f"Message unpacking error: {e}", "warning".upper(), True)
                continue
            
            # Validate Message, Skip this message if target AppID different from hkapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.HkAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg)
            else:
                safe_log("Receiver MID does not match with hkapp MID", "error".upper(), True)

    # If error occurs, terminate app gracefully
    except (KeyboardInterrupt, SystemExit):
        safe_log("HK app received termination signal", "info".upper(), True)
        HKAPP_RUNSTATUS = False
    except Exception as e:
        safe_log(f"hkapp critical error : {e}", "error".upper(), True)
        HKAPP_RUNSTATUS = False
        # 치명적 오류 발생 시에도 로깅은 계속
        try:
            safe_log("HK app attempting graceful shutdown", "info".upper(), True)
        except:
            pass

    # Termination Process after runloop
    try:
        hkapp_terminate()
    except Exception as e:
        # 종료 과정에서 오류가 발생해도 최소한의 로깅 시도
        try:
            print(f"[HK] Termination error: {e}")
        except:
            pass

    return

# ──────────────────────────────
# HKApp 클래스 (main.py 호환성)
# ──────────────────────────────
class HKApp:
    """HK 앱 클래스 - main.py 호환성을 위한 래퍼"""
    
    def __init__(self):
        """HKApp 초기화"""
        self.app_name = "HK"
        self.app_id = appargs.HkAppArg.AppID
        self.run_status = True
    
    def start(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 시작 - main.py에서 호출됨"""
        try:
            hkapp_main(main_queue, main_pipe)
        except Exception as e:
            safe_log(f"HKApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """앱 중지"""
        global HKAPP_RUNSTATUS
        HKAPP_RUNSTATUS = False
        self.run_status = False