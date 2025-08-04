# Python FSW V2 Imu App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types

import signal
from multiprocessing import Queue, connection
import threading
import time
import csv
import os
from datetime import datetime

# Import IMU sensor library
from imu import imu

# Runstatus of application. Application is terminated when false
IMUAPP_RUNSTATUS = True

# IMU 데이터 변수들
IMU_GYRO = (0.0, 0.0, 0.0)
IMU_ACCEL = (0.0, 0.0, 0.0)
IMU_MAG = (0.0, 0.0, 0.0)
IMU_EULER = (0.0, 0.0, 0.0)
IMU_TEMP = 0.0

# 개별 데이터 변수들
IMU_ROLL = 0.0
IMU_PITCH = 0.0
IMU_YAW = 0.0
IMU_ACCX = 0.0
IMU_ACCY = 0.0
IMU_ACCZ = 0.0
IMU_MAGX = 0.0
IMU_MAGY = 0.0
IMU_MAGZ = 0.0
IMU_GYRX = 0.0
IMU_GYRY = 0.0
IMU_GYRZ = 0.0

# 고주파수 로깅 시스템
LOG_DIR = "logs/imu"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
HIGH_FREQ_LOG_PATH = os.path.join(LOG_DIR, "high_freq_imu_log.csv")
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

def log_high_freq_imu_data(roll, pitch, yaw, accx, accy, accz, magx, magy, magz, gyrx, gyry, gyrz, temp):
    """고주파수 IMU 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(HIGH_FREQ_LOG_PATH):
            with open(HIGH_FREQ_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'roll', 'pitch', 'yaw', 'accx', 'accy', 'accz', 'magx', 'magy', 'magz', 'gyrx', 'gyry', 'gyrz', 'temp'])
        
        # 데이터 추가
        with open(HIGH_FREQ_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, roll, pitch, yaw, accx, accy, accz, magx, magy, magz, gyrx, gyry, gyrz, temp])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"High frequency IMU logging failed: {e}")

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

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global IMUAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"IMUAPP TERMINATION DETECTED")
        IMUAPP_RUNSTATUS = False

    else:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global IMUAPP_RUNSTATUS, IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_TEMP
    consecutive_hk_failures = 0
    max_hk_failures = 3
    
    while IMUAPP_RUNSTATUS:
        try:
            imuHK = msgstructure.MsgStructure()
            hk_payload = f"run={IMUAPP_RUNSTATUS},roll={IMU_ROLL:.2f},pitch={IMU_PITCH:.2f},yaw={IMU_YAW:.2f},temp={IMU_TEMP:.2f}"
            status = msgstructure.send_msg(Main_Queue, imuHK, appargs.ImuAppArg.AppID, appargs.HkAppArg.AppID, appargs.ImuAppArg.MID_SendHK, hk_payload)
            if status == False:
                consecutive_hk_failures += 1
                if consecutive_hk_failures <= max_hk_failures:
                    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Error sending HK message")
                elif consecutive_hk_failures == max_hk_failures + 1:
                    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.warning, f"HK send errors suppressed after {max_hk_failures} failures")
            else:
                consecutive_hk_failures = 0
                
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, IMUAPP_RUNSTATUS, IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_TEMP]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "roll", "pitch", "yaw", "temp"], hk_row)
                
        except Exception as e:
            consecutive_hk_failures += 1
            if consecutive_hk_failures <= max_hk_failures:
                events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Exception sending HK: {e}")
            elif consecutive_hk_failures == max_hk_failures + 1:
                events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.warning, f"HK send exceptions suppressed after {max_hk_failures} failures")
        
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not IMUAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def imuapp_init():
    """센서 초기화·시리얼 확인."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.ImuAppArg.AppName,
                        events.EventType.info,
                        "Initializing imuapp")

        # IMU 센서 초기화 (직접 I2C 연결)
        i2c, sensor = imu.init_imu()
        
        events.LogEvent(appargs.ImuAppArg.AppName,
                        events.EventType.info,
                        "Imuapp initialization complete")
        return i2c, sensor

    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName,
                        events.EventType.error,
                        f"Init error: {e}")
        return None, None

# Termination
def imuapp_terminate(i2c_instance):
    global IMUAPP_RUNSTATUS

    IMUAPP_RUNSTATUS = False
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp")
    
    try:
        imu.imu_terminate(i2c_instance)
    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Error terminating IMU: {e}")

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        try:
            thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
            if thread_dict[thread_name].is_alive():
                events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.warning, f"Thread {thread_name} did not terminate gracefully")
        except Exception as e:
            events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Error joining thread {thread_name}: {e}")
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

def read_imu_data(sensor):
    """IMU 데이터 읽기 스레드."""
    global IMUAPP_RUNSTATUS, IMU_GYRO, IMU_ACCEL, IMU_MAG, IMU_EULER, IMU_TEMP
    global IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_ACCX, IMU_ACCY, IMU_ACCZ, IMU_MAGX, IMU_MAGY, IMU_MAGZ, IMU_GYRX, IMU_GYRY, IMU_GYRZ
    
    while IMUAPP_RUNSTATUS:
        try:
            gyro, accel, mag, euler, temp = imu.read_sensor_data(sensor)
            if gyro is not None:
                IMU_GYRO = gyro
                IMU_ACCEL = accel
                IMU_MAG = mag
                IMU_EULER = euler
                IMU_TEMP = temp
                
                # 개별 변수들 업데이트
                if len(euler) >= 3:
                    IMU_ROLL = euler[0]
                    IMU_PITCH = euler[1]
                    IMU_YAW = euler[2]
                
                if len(accel) >= 3:
                    IMU_ACCX = accel[0]
                    IMU_ACCY = accel[1]
                    IMU_ACCZ = accel[2]
                
                if len(mag) >= 3:
                    IMU_MAGX = mag[0]
                    IMU_MAGY = mag[1]
                    IMU_MAGZ = mag[2]
                
                if len(gyro) >= 3:
                    IMU_GYRX = gyro[0]
                    IMU_GYRY = gyro[1]
                    IMU_GYRZ = gyro[2]
                    
        except Exception as e:
            events.LogEvent(appargs.ImuAppArg.AppName,
                            events.EventType.error,
                            f"IMU read error: {e}")
        time.sleep(0.1)  # 10 Hz

def send_imu_data(Main_Queue : Queue):
    global IMU_ROLL
    global IMU_PITCH
    global IMU_YAW
    global IMU_ACCX
    global IMU_ACCY
    global IMU_ACCZ
    global IMU_MAGX
    global IMU_MAGY
    global IMU_MAGZ
    global IMU_GYRX
    global IMU_GYRY
    global IMU_GYRZ
    global IMU_TEMP
    
    global IMUAPP_RUNSTATUS

    ImuDataToTlmMsg = msgstructure.MsgStructure()
    YawDataToMotorMsg = msgstructure.MsgStructure()
    
    send_counter = 0
    consecutive_send_failures = 0
    max_send_failures = 5

    while IMUAPP_RUNSTATUS:
        
        send_counter += 1

        # Send Yaw data to motor
        # msgstructure.send_msg(Main_Queue, 
        #                       YawDataToMotorMsg,
        #                       appargs.ImuAppArg.AppID,
        #                       appargs.MotorAppArg.AppID,
        #                       appargs.ImuAppArg.MID_SendYawData,
        #                       f"{IMU_YAW:.2f}")
        
        # Sending data to COMMS app occurs once a second

        if send_counter >= 10 :
            try:
                # Send telemetry message to COMM app
                status = msgstructure.send_msg(Main_Queue, 
                                            ImuDataToTlmMsg, 
                                            appargs.ImuAppArg.AppID,
                                            appargs.CommAppArg.AppID,
                                            appargs.ImuAppArg.MID_SendImuTlmData,
                                            f"{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f},{IMU_ACCX:.2f},{IMU_ACCY:.2f},{IMU_ACCZ:.2f},{IMU_MAGX:.2f},{IMU_MAGY:.2f},{IMU_MAGZ:.2f},{IMU_GYRX:.2f},{IMU_GYRY:.2f},{IMU_GYRZ:.2f},{IMU_TEMP:.2f}")
                if status == False:
                    consecutive_send_failures += 1
                    if consecutive_send_failures <= max_send_failures:
                        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Error When sending Imu Tlm Message")
                    elif consecutive_send_failures == max_send_failures + 1:
                        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.warning, f"IMU send errors suppressed after {max_send_failures} failures")
                else:
                    consecutive_send_failures = 0  # 성공 시 실패 횟수 리셋
            except Exception as e:
                consecutive_send_failures += 1
                if consecutive_send_failures <= max_send_failures:
                    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Exception when sending IMU data: {e}")
                elif consecutive_send_failures == max_send_failures + 1:
                    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.warning, f"IMU send exceptions suppressed after {max_send_failures} failures")
            
            send_counter = 0
            
        # Sleep 0.1 second (10Hz telemetry rate)
        time.sleep(0.1)

    return  


# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def imuapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global IMUAPP_RUNSTATUS
    IMUAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, imu_instance = imuapp_init()
    
    # 초기화 실패 시 종료
    if i2c_instance is None or imu_instance is None:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "IMU 초기화 실패로 인한 종료")
        return

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["ReadImuData_Thread"] = threading.Thread(target=read_imu_data, args=(imu_instance, ), name="ReadImuData_Thread")
    thread_dict["SendImuData_Thread"] = threading.Thread(target=send_imu_data, args=(Main_Queue, ), name="SendImuData_Thread")


    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while IMUAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            try:
                if Main_Pipe.poll(0.5):  # 0.5초 타임아웃으로 단축
                    try:
                        message = Main_Pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError):
                        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Pipe connection lost")
                        break
                    except Exception as e:
                        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Pipe receive error: {e}")
                        continue
                else:
                    # 타임아웃 시 루프 계속
                    continue
                    
                recv_msg = msgstructure.MsgStructure()

                # Unpack Message, Skip this message if unpacked message is not valid
                if msgstructure.unpack_msg(recv_msg, message) == False:
                    continue
                
                # Validate Message, Skip this message if target AppID different from imuapp's AppID
                # Exception when the message is from main app
                if recv_msg.receiver_app == appargs.ImuAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                    # Handle Command According to Message ID
                    command_handler(recv_msg)
                else:
                    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Receiver MID does not match with imuapp MID")
                    
            except Exception as e:
                events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"Main loop error: {e}")
                time.sleep(0.1)  # 에러 시 짧은 대기

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"imuapp error : {e}")
        IMUAPP_RUNSTATUS = False

    # Termination Process after runloop
    imuapp_terminate(i2c_instance)

    return
