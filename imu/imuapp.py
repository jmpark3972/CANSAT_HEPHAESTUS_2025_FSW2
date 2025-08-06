# Python FSW V2 Imu App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[{appargs.ImuAppArg.AppName}] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[IMU] 로깅 실패: {e}")
        print(f"[IMU] 원본 메시지: {message}")

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
        safe_log(f"IMUAPP TERMINATION DETECTED", "info".upper(), True)
        IMUAPP_RUNSTATUS = False

    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
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
                    safe_log("Error sending HK message", "error".upper(), True)
                elif consecutive_hk_failures == max_hk_failures + 1:
                    safe_log(f"HK send errors suppressed after {max_hk_failures} failures", "warning".upper(), True)
            else:
                consecutive_hk_failures = 0
                
                # HK 데이터 로깅
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                hk_row = [timestamp, IMUAPP_RUNSTATUS, IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_TEMP]
                log_csv(HK_LOG_PATH, ["timestamp", "run", "roll", "pitch", "yaw", "temp"], hk_row)
                
        except Exception as e:
            consecutive_hk_failures += 1
            if consecutive_hk_failures <= max_hk_failures:
                safe_log(f"Exception sending HK: {e}", "error".upper(), True)
            elif consecutive_hk_failures == max_hk_failures + 1:
                safe_log(f"HK send exceptions suppressed after {max_hk_failures} failures", "warning".upper(), True)
        
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

        safe_log("Initializing imuapp", "info".upper(), True)

        # IMU 센서 초기화 (직접 I2C 연결)
        i2c, sensor = imu.init_imu()
        
        if i2c and sensor:
            safe_log("Imuapp initialization complete", "info".upper(), True)
        else:
            safe_log("IMU 센서 초기화 실패, 기본값으로 작동", "warning".upper(), True)
        
        return i2c, sensor

    except Exception as e:
        safe_log(f"Init error: {e}, 기본값으로 작동", "warning".upper(), True)
        return None, None

# Termination
def imuapp_terminate(i2c_instance):
    global IMUAPP_RUNSTATUS

    try:
        safe_log("Starting imuapp termination", "info".upper(), True)
        
        # 1단계: 실행 상태 중지
        IMUAPP_RUNSTATUS = False
        safe_log("IMU app run status set to False", "info".upper(), True)
        
        # 2단계: 스레드 종료 대기
        safe_log("Waiting for threads to terminate...", "info".upper(), True)
        time.sleep(2.0)  # 스레드들이 종료될 시간을 줌
        
        # 3단계: IMU 하드웨어 종료
        safe_log("Terminating IMU hardware...", "info".upper(), True)
        try:
            imu.imu_terminate(i2c_instance)
            safe_log("IMU hardware terminated successfully", "info".upper(), True)
        except Exception as e:
            safe_log(f"Error terminating IMU hardware: {e}", "error".upper(), True)

        # 4단계: 스레드 강제 종료
        safe_log("Force terminating remaining threads...", "info".upper(), True)
        for thread_name in thread_dict:
            safe_log(f"Terminating thread {thread_name}", "info".upper(), True)
            try:
                thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
                if thread_dict[thread_name].is_alive():
                    safe_log(f"Thread {thread_name} did not terminate gracefully", "warning".upper(), True)
                    # 강제 종료는 하지 않음 (스레드가 자연스럽게 종료되도록)
            except Exception as e:
                safe_log(f"Error joining thread {thread_name}: {e}", "error".upper(), True)
            safe_log(f"Thread {thread_name} termination complete", "info".upper(), True)

        # 5단계: 리소스 정리
        safe_log("Cleaning up resources...", "info".upper(), True)
        try:
            # 전역 변수 정리
            global IMU_GYRO, IMU_ACCEL, IMU_MAG, IMU_EULER, IMU_TEMP
            global IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_ACCX, IMU_ACCY, IMU_ACCZ
            global IMU_MAGX, IMU_MAGY, IMU_MAGZ, IMU_GYRX, IMU_GYRY, IMU_GYRZ
            
            # 기본값으로 리셋
            IMU_GYRO = (0.0, 0.0, 0.0)
            IMU_ACCEL = (0.0, 0.0, 0.0)
            IMU_MAG = (0.0, 0.0, 0.0)
            IMU_EULER = (0.0, 0.0, 0.0)
            IMU_TEMP = 0.0
            IMU_ROLL = IMU_PITCH = IMU_YAW = 0.0
            IMU_ACCX = IMU_ACCY = IMU_ACCZ = 0.0
            IMU_MAGX = IMU_MAGY = IMU_MAGZ = 0.0
            IMU_GYRX = IMU_GYRY = IMU_GYRZ = 0.0
            
            safe_log("Global variables reset to default values", "info".upper(), True)
        except Exception as cleanup_error:
            safe_log(f"Resource cleanup error: {cleanup_error}", "error".upper(), True)

        safe_log("Imuapp termination complete", "info".upper(), True)
        return True

    except Exception as e:
        safe_log(f"Imuapp termination error: {e}", "error".upper(), True)
        return False

######################################################
## USER METHOD                                      ##
######################################################

def read_imu_data(sensor):
    """IMU 데이터 읽기 스레드."""
    global IMUAPP_RUNSTATUS, IMU_GYRO, IMU_ACCEL, IMU_MAG, IMU_EULER, IMU_TEMP
    global IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_ACCX, IMU_ACCY, IMU_ACCZ, IMU_MAGX, IMU_MAGY, IMU_MAGZ, IMU_GYRX, IMU_GYRY, IMU_GYRZ
    global IMU_ADVANCED_DATA
    
    while IMUAPP_RUNSTATUS:
        try:
            # 센서가 None인 경우 기본값 유지
            if sensor is None:
                time.sleep(0.1)
                continue
                
            # 고급 데이터 읽기 시도
            result = imu.read_sensor_data(sensor)
            if result and len(result) >= 10:
                gyro, accel, mag, euler, temp, quaternion, linear_accel, gravity, calibration, system_status = result
                
                # 데이터가 유효한 경우 업데이트
                if gyro is not None and accel is not None and mag is not None and euler is not None:
                    IMU_GYRO = gyro
                    IMU_ACCEL = accel
                    IMU_MAG = mag
                    IMU_EULER = euler
                    IMU_TEMP = temp if temp is not None else 0.0
                    
                    # 고급 데이터 저장
                    IMU_ADVANCED_DATA = {
                        'quaternion': quaternion,
                        'linear_accel': linear_accel,
                        'gravity': gravity,
                        'calibration': calibration,
                        'system_status': system_status
                    }
                    
                    # 개별 변수들 업데이트
                    if len(euler) >= 3:
                        IMU_ROLL = euler[0] if euler[0] is not None else 0.0
                        IMU_PITCH = euler[1] if euler[1] is not None else 0.0
                        IMU_YAW = euler[2] if euler[2] is not None else 0.0
                    
                    if len(accel) >= 3:
                        IMU_ACCX = accel[0] if accel[0] is not None else 0.0
                        IMU_ACCY = accel[1] if accel[1] is not None else 0.0
                        IMU_ACCZ = accel[2] if accel[2] is not None else 0.0
                    
                    if len(mag) >= 3:
                        IMU_MAGX = mag[0] if mag[0] is not None else 0.0
                        IMU_MAGY = mag[1] if mag[1] is not None else 0.0
                        IMU_MAGZ = mag[2] if mag[2] is not None else 0.0
                    
                    if len(gyro) >= 3:
                        IMU_GYRX = gyro[0] if gyro[0] is not None else 0.0
                        IMU_GYRY = gyro[1] if gyro[1] is not None else 0.0
                        IMU_GYRZ = gyro[2] if gyro[2] is not None else 0.0
                else:
                    # 데이터가 None인 경우 기본값 유지 (이전 값 보존)
                    # 센서 오류 시에도 시스템이 계속 작동하도록 함
                    pass
            else:
                # 기본 데이터 읽기 (fallback)
                gyro, accel, mag, euler, temp = imu.read_sensor_data(sensor)
                if gyro is not None and accel is not None and mag is not None and euler is not None:
                    IMU_GYRO = gyro
                    IMU_ACCEL = accel
                    IMU_MAG = mag
                    IMU_EULER = euler
                    IMU_TEMP = temp if temp is not None else 0.0
                    IMU_ADVANCED_DATA = {}  # 기본값
                    
                    # 개별 변수들 업데이트 (기존 로직)
                    if len(euler) >= 3:
                        IMU_ROLL = euler[0] if euler[0] is not None else 0.0
                        IMU_PITCH = euler[1] if euler[1] is not None else 0.0
                        IMU_YAW = euler[2] if euler[2] is not None else 0.0
                    
                    if len(accel) >= 3:
                        IMU_ACCX = accel[0] if accel[0] is not None else 0.0
                        IMU_ACCY = accel[1] if accel[1] is not None else 0.0
                        IMU_ACCZ = accel[2] if accel[2] is not None else 0.0
                    
                    if len(mag) >= 3:
                        IMU_MAGX = mag[0] if mag[0] is not None else 0.0
                        IMU_MAGY = mag[1] if mag[1] is not None else 0.0
                        IMU_MAGZ = mag[2] if mag[2] is not None else 0.0
                    
                    if len(gyro) >= 3:
                        IMU_GYRX = gyro[0] if gyro[0] is not None else 0.0
                        IMU_GYRY = gyro[1] if gyro[1] is not None else 0.0
                        IMU_GYRZ = gyro[2] if gyro[2] is not None else 0.0
                    
        except Exception as e:
            safe_log(f"IMU read error: {e}", "error".upper(), True)
            # 오류 발생 시에도 기본값 유지
            pass
            
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
    ImuDataToFlightLogicMsg = msgstructure.MsgStructure()
    YawDataToMotorMsg = msgstructure.MsgStructure()
    
    send_counter = 0
    consecutive_send_failures = 0
    max_send_failures = 5

    while IMUAPP_RUNSTATUS:
        
        send_counter += 1

        # Send IMU data to FlightLogic (10Hz)
        try:
            status = msgstructure.send_msg(Main_Queue, 
                                        ImuDataToFlightLogicMsg,
                                        appargs.ImuAppArg.AppID,
                                        appargs.FlightlogicAppArg.AppID,
                                        appargs.ImuAppArg.MID_SendImuFlightLogicData,
                                        f"{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f}")
            if status == False:
                safe_log("Error When sending IMU FlightLogic Message", "error".upper(), True)
        except Exception as e:
            safe_log(f"Exception when sending IMU FlightLogic data: {e}", "error".upper(), True)

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
                # 기본 데이터만 텔레메트리 전송 (고급 데이터는 로그에만 저장)
                tlm_data = f"{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f},{IMU_ACCX:.2f},{IMU_ACCY:.2f},{IMU_ACCZ:.2f},{IMU_MAGX:.2f},{IMU_MAGY:.2f},{IMU_MAGZ:.2f},{IMU_GYRX:.2f},{IMU_GYRY:.2f},{IMU_GYRZ:.2f},{IMU_TEMP:.2f}"
                
                # 고급 데이터 로깅
                if hasattr(imu, 'IMU_ADVANCED_DATA') and IMU_ADVANCED_DATA:
                    quat = IMU_ADVANCED_DATA.get('quaternion', (1.0, 0.0, 0.0, 0.0))
                    lin_acc = IMU_ADVANCED_DATA.get('linear_accel', (0.0, 0.0, 0.0))
                    grav = IMU_ADVANCED_DATA.get('gravity', (0.0, 0.0, 0.0))
                    cal = IMU_ADVANCED_DATA.get('calibration', (0, 0, 0, 0))
                    sys_status = IMU_ADVANCED_DATA.get('system_status', 0)
                    
                    safe_log(f"IMU Advanced Data - Quat: ({quat[0]:.4f},{quat[1]:.4f},{quat[2]:.4f},{quat[3]:.4f}), LinAcc: ({lin_acc[0]:.4f},{lin_acc[1]:.4f},{lin_acc[2]:.4f}), Gravity: ({grav[0]:.4f},{grav[1]:.4f},{grav[2]:.4f}), Cal: {cal}, SysStatus: {sys_status}", "debug".upper(), False)
                
                status = msgstructure.send_msg(Main_Queue, 
                                            ImuDataToTlmMsg, 
                                            appargs.ImuAppArg.AppID,
                                            appargs.CommAppArg.AppID,
                                            appargs.ImuAppArg.MID_SendImuTlmData,
                                            tlm_data)
                if status == False:
                    consecutive_send_failures += 1
                    if consecutive_send_failures <= max_send_failures:
                        safe_log("Error When sending Imu Tlm Message", "error".upper(), True)
                    elif consecutive_send_failures == max_send_failures + 1:
                        safe_log(f"IMU send errors suppressed after {max_send_failures} failures", "warning".upper(), True)
                else:
                    consecutive_send_failures = 0  # 성공 시 실패 횟수 리셋
            except Exception as e:
                consecutive_send_failures += 1
                if consecutive_send_failures <= max_send_failures:
                    safe_log(f"Exception when sending IMU data: {e}", "error".upper(), True)
                elif consecutive_send_failures == max_send_failures + 1:
                    safe_log(f"IMU send exceptions suppressed after {max_send_failures} failures", "warning".upper(), True)
            
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
        safe_log("IMU 초기화 실패로 인한 종료", "error".upper(), True)
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
                        safe_log("Pipe connection lost", "error".upper(), True)
                        break
                    except Exception as e:
                        safe_log(f"Pipe receive error: {e}", "error".upper(), True)
                        continue
                else:
                    # 타임아웃 시 루프 계속
                    continue
                    
                recv_msg = message
                
                # Validate Message, Skip this message if target AppID different from imuapp's AppID
                # Exception when the message is from main app
                if recv_msg.receiver_app == appargs.ImuAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                    # Handle Command According to Message ID
                    command_handler(recv_msg)
                else:
                    safe_log("Receiver MID does not match with imuapp MID", "error".upper(), True)
                    
            except Exception as e:
                safe_log(f"Main loop error: {e}", "error".upper(), True)
                time.sleep(0.1)  # 에러 시 짧은 대기

    # If error occurs, terminate app
    except Exception as e:
        safe_log(f"imuapp error : {e}", "error".upper(), True)
        IMUAPP_RUNSTATUS = False

    # Termination Process after runloop
    imuapp_terminate(i2c_instance)

    return
