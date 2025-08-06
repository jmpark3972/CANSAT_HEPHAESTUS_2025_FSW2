# Python FSW V2 Imu App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[{appargs.ImuAppArg.AppName}] [{level}] {message}"
        from lib.logging import safe_log as lib_safe_log
        lib_safe_log(f"[IMU] {message}", level, printlogs)
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

# 센서 상태 추적
_sensor_healthy = True
_sensor_error_count = 0
_last_sensor_error_time = 0
_sensor_recovery_attempts = 0
_max_sensor_recovery_attempts = 5

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
        safe_log(f"CSV 로깅 실패: {e}", "ERROR", True)
        emergency_log_to_file("ERROR", f"CSV logging failed: {e}")

def command_handler (recv_msg : msgstructure.MsgStructure):
    """명령 처리 함수"""
    global IMUAPP_RUNSTATUS
    
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        safe_log("Termination command received", "INFO", True)
        IMUAPP_RUNSTATUS = False
    else:
        safe_log(f"Unknown command: {recv_msg.MsgID}", "WARNING", True)

def send_hk(Main_Queue : Queue):
    """하우스키핑 메시지 전송"""
    global IMUAPP_RUNSTATUS
    
    while IMUAPP_RUNSTATUS:
        try:
            # 하우스키핑 메시지 생성
            hk_msg = msgstructure.MsgStructure()
            msgstructure.fill_msg(hk_msg, appargs.ImuAppArg.AppID, appargs.HkAppArg.AppID, appargs.HkAppArg.MID_Housekeeping, "")
            
            # 메시지 패킹 및 전송
            packed_msg = msgstructure.pack_msg(hk_msg)
            Main_Queue.put(packed_msg)
            
            # 하우스키핑 데이터 로깅
            hk_data = [
                datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                IMU_TEMP,
                IMU_ROLL,
                IMU_PITCH,
                IMU_YAW,
                IMU_ACCX,
                IMU_ACCY,
                IMU_ACCZ,
                IMU_MAGX,
                IMU_MAGY,
                IMU_MAGZ,
                IMU_GYRX,
                IMU_GYRY,
                IMU_GYRZ,
                _sensor_healthy,
                _sensor_error_count
            ]
            
            hk_headers = ["timestamp", "temp", "roll", "pitch", "yaw", "accx", "accy", "accz", "magx", "magy", "magz", "gyrx", "gyry", "gyrz", "sensor_healthy", "error_count"]
            log_csv(HK_LOG_PATH, hk_headers, hk_data)
            
            time.sleep(1.0)  # 1초마다 하우스키핑
            
        except Exception as e:
            safe_log(f"HK 전송 오류: {e}", "ERROR", True)
            emergency_log_to_file("ERROR", f"HK transmission error: {e}")
            time.sleep(1.0)  # 오류 시에도 계속 시도

def imuapp_init():
    """IMU 앱 초기화"""
    global _sensor_healthy, _sensor_error_count, _sensor_recovery_attempts
    
    try:
        safe_log("IMU 앱 초기화 시작", "INFO", True)
        
        # IMU 센서 초기화
        i2c_instance, imu_instance = imu.init_imu()
        
        if i2c_instance is not None and imu_instance is not None:
            safe_log("IMU 센서 초기화 성공", "INFO", True)
            _sensor_healthy = True
            _sensor_error_count = 0
            _sensor_recovery_attempts = 0
            return i2c_instance, imu_instance
        else:
            safe_log("IMU 센서 초기화 실패 - 더미 데이터 모드로 실행", "WARNING", True)
            _sensor_healthy = False
            return None, None
            
    except Exception as e:
        safe_log(f"IMU 앱 초기화 오류: {e}", "ERROR", True)
        emergency_log_to_file("ERROR", f"IMU app initialization error: {e}")
        _sensor_healthy = False
        return None, None

def imuapp_terminate(i2c_instance):
    """IMU 앱 종료"""
    global _emergency_logging_enabled
    
    try:
        safe_log("IMU 앱 종료 시작", "INFO", True)
        
        # 긴급 로깅 비활성화
        _emergency_logging_enabled = False
        
        # I2C 연결 종료
        if i2c_instance is not None:
            try:
                imu.imu_terminate(i2c_instance)
                safe_log("I2C 연결 종료 완료", "INFO", True)
            except Exception as e:
                safe_log(f"I2C 종료 오류: {e}", "WARNING", True)
        
        safe_log("IMU 앱 종료 완료", "INFO", True)
        
    except Exception as e:
        safe_log(f"IMU 앱 종료 오류: {e}", "ERROR", True)

def read_imu_data(sensor):
    """IMU 데이터 읽기 스레드 (개선된 버전)"""
    global IMUAPP_RUNSTATUS, IMU_GYRO, IMU_ACCEL, IMU_MAG, IMU_EULER, IMU_TEMP
    global IMU_ROLL, IMU_PITCH, IMU_YAW, IMU_ACCX, IMU_ACCY, IMU_ACCZ, IMU_MAGX, IMU_MAGY, IMU_MAGZ, IMU_GYRX, IMU_GYRY, IMU_GYRZ
    global IMU_ADVANCED_DATA, _sensor_healthy, _sensor_error_count, _last_sensor_error_time, _sensor_recovery_attempts
    
    consecutive_errors = 0
    max_consecutive_errors = 10
    
    while IMUAPP_RUNSTATUS:
        try:
            # 센서가 None인 경우 더미 데이터 사용
            if sensor is None:
                # 더미 데이터 설정 (정지 상태)
                IMU_GYRO = (0.0, 0.0, 0.0)
                IMU_ACCEL = (0.0, 0.0, 9.81)  # 중력만 작용
                IMU_MAG = (0.0, 0.0, 0.0)
                IMU_EULER = (0.0, 0.0, 0.0)
                IMU_TEMP = 25.0  # 기본 실내 온도
                
                # 개별 변수들도 더미 데이터로 설정
                IMU_ROLL = IMU_PITCH = IMU_YAW = 0.0
                IMU_ACCX = IMU_ACCY = 0.0
                IMU_ACCZ = 9.81  # 중력
                IMU_MAGX = IMU_MAGY = IMU_MAGZ = 0.0
                IMU_GYRX = IMU_GYRY = IMU_GYRZ = 0.0
                
                # 고급 데이터도 더미로 설정
                IMU_ADVANCED_DATA = {
                    'quaternion': (1.0, 0.0, 0.0, 0.0),
                    'linear_accel': (0.0, 0.0, 0.0),
                    'gravity': (0.0, 0.0, 9.81),
                    'calibration': (0, 0, 0),
                    'system_status': 0
                }
                
                # 더미 데이터 로깅
                high_freq_data = [
                    datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                    "DUMMY",
                    IMU_TEMP,
                    IMU_ROLL, IMU_PITCH, IMU_YAW,
                    IMU_ACCX, IMU_ACCY, IMU_ACCZ,
                    IMU_MAGX, IMU_MAGY, IMU_MAGZ,
                    IMU_GYRX, IMU_GYRY, IMU_GYRZ,
                    _sensor_healthy,
                    consecutive_errors
                ]
                
                high_freq_headers = ["timestamp", "data_type", "temp", "roll", "pitch", "yaw", 
                                   "accx", "accy", "accz", "magx", "magy", "magz", 
                                   "gyrx", "gyry", "gyrz", "sensor_healthy", "error_count"]
                log_csv(HIGH_FREQ_LOG_PATH, high_freq_headers, high_freq_data)
                
                time.sleep(0.1)  # 10 Hz
                continue
                
            # 실제 센서 데이터 읽기
            try:
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
                        
                        # 센서 상태 업데이트
                        _sensor_healthy = True
                        consecutive_errors = 0
                        _sensor_error_count = 0
                        
                        # 성공적인 데이터 로깅
                        high_freq_data = [
                            datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                            "SENSOR",
                            IMU_TEMP,
                            IMU_ROLL, IMU_PITCH, IMU_YAW,
                            IMU_ACCX, IMU_ACCY, IMU_ACCZ,
                            IMU_MAGX, IMU_MAGY, IMU_MAGZ,
                            IMU_GYRX, IMU_GYRY, IMU_GYRZ,
                            _sensor_healthy,
                            consecutive_errors
                        ]
                        
                        high_freq_headers = ["timestamp", "data_type", "temp", "roll", "pitch", "yaw", 
                                           "accx", "accy", "accz", "magx", "magy", "magz", 
                                           "gyrx", "gyry", "gyrz", "sensor_healthy", "error_count"]
                        log_csv(HIGH_FREQ_LOG_PATH, high_freq_headers, high_freq_data)
                        
                    else:
                        # 데이터가 None인 경우 이전 값 유지하고 오류 카운트 증가
                        consecutive_errors += 1
                        _sensor_error_count += 1
                        _last_sensor_error_time = time.time()
                        
                        if consecutive_errors >= max_consecutive_errors:
                            _sensor_healthy = False
                            safe_log(f"IMU 센서 데이터 연속 {consecutive_errors}회 실패 - 센서 비정상 상태", "WARNING", True)
                        
                        # 오류 상태 로깅
                        high_freq_data = [
                            datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                            "ERROR",
                            IMU_TEMP,
                            IMU_ROLL, IMU_PITCH, IMU_YAW,
                            IMU_ACCX, IMU_ACCY, IMU_ACCZ,
                            IMU_MAGX, IMU_MAGY, IMU_MAGZ,
                            IMU_GYRX, IMU_GYRY, IMU_GYRZ,
                            _sensor_healthy,
                            consecutive_errors
                        ]
                        
                        high_freq_headers = ["timestamp", "data_type", "temp", "roll", "pitch", "yaw", 
                                           "accx", "accy", "accz", "magx", "magy", "magz", 
                                           "gyrx", "gyry", "gyrz", "sensor_healthy", "error_count"]
                        log_csv(HIGH_FREQ_LOG_PATH, high_freq_headers, high_freq_data)
                        
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
                        
                        # 센서 상태 업데이트
                        _sensor_healthy = True
                        consecutive_errors = 0
                        
                    else:
                        # fallback도 실패한 경우
                        consecutive_errors += 1
                        _sensor_error_count += 1
                        _last_sensor_error_time = time.time()
                        
                        if consecutive_errors >= max_consecutive_errors:
                            _sensor_healthy = False
                            safe_log(f"IMU 센서 fallback 데이터도 실패 - 센서 비정상 상태", "WARNING", True)
                        
            except Exception as e:
                consecutive_errors += 1
                _sensor_error_count += 1
                _last_sensor_error_time = time.time()
                
                # I/O 오류 특별 처리
                if "Input/output error" in str(e) or "[Errno 5]" in str(e):
                    safe_log(f"IMU I/O 오류 발생: {e}", "ERROR", True)
                    emergency_log_to_file("ERROR", f"IMU I/O error: {e}")
                    
                    # I/O 오류 시 센서 재초기화 시도
                    if _sensor_recovery_attempts < _max_sensor_recovery_attempts:
                        _sensor_recovery_attempts += 1
                        safe_log(f"IMU 센서 재초기화 시도 {_sensor_recovery_attempts}/{_max_sensor_recovery_attempts}", "WARNING", True)
                        try:
                            # 센서 재초기화
                            i2c_instance, new_sensor = imuapp_init()
                            if new_sensor is not None:
                                sensor = new_sensor
                                safe_log("IMU 센서 재초기화 성공", "INFO", True)
                                _sensor_healthy = True
                                consecutive_errors = 0
                            else:
                                safe_log("IMU 센서 재초기화 실패", "ERROR", True)
                        except Exception as recovery_error:
                            safe_log(f"IMU 센서 재초기화 오류: {recovery_error}", "ERROR", True)
                else:
                    safe_log(f"IMU 읽기 오류: {e}", "ERROR", True)
                
                if consecutive_errors >= max_consecutive_errors:
                    _sensor_healthy = False
                    safe_log(f"IMU 센서 연속 {consecutive_errors}회 오류 - 센서 비정상 상태", "WARNING", True)
                
                # 오류 상태 로깅
                high_freq_data = [
                    datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                    "ERROR",
                    IMU_TEMP,
                    IMU_ROLL, IMU_PITCH, IMU_YAW,
                    IMU_ACCX, IMU_ACCY, IMU_ACCZ,
                    IMU_MAGX, IMU_MAGY, IMU_MAGZ,
                    IMU_GYRX, IMU_GYRY, IMU_GYRZ,
                    _sensor_healthy,
                    consecutive_errors
                ]
                
                high_freq_headers = ["timestamp", "data_type", "temp", "roll", "pitch", "yaw", 
                                   "accx", "accy", "accz", "magx", "magy", "magz", 
                                   "gyrx", "gyry", "gyrz", "sensor_healthy", "error_count"]
                log_csv(HIGH_FREQ_LOG_PATH, high_freq_headers, high_freq_data)
            
        except Exception as e:
            safe_log(f"IMU 데이터 읽기 스레드 오류: {e}", "ERROR", True)
            emergency_log_to_file("ERROR", f"IMU data reading thread error: {e}")
            time.sleep(0.5)  # 오류 시 더 긴 대기
            
        time.sleep(0.1)  # 10 Hz

def send_imu_data(Main_Queue : Queue):
    """IMU 데이터 전송 스레드"""
    global IMUAPP_RUNSTATUS
    
    while IMUAPP_RUNSTATUS:
        try:
            # IMU 데이터 메시지 생성
            imu_msg = msgstructure.MsgStructure()
            
            # 데이터 문자열 생성
            imu_data_str = f"{IMU_TEMP:.2f},{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f},{IMU_ACCX:.2f},{IMU_ACCY:.2f},{IMU_ACCZ:.2f},{IMU_MAGX:.2f},{IMU_MAGY:.2f},{IMU_MAGZ:.2f},{IMU_GYRX:.2f},{IMU_GYRY:.2f},{IMU_GYRZ:.2f}"
            
            msgstructure.fill_msg(imu_msg, appargs.ImuAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.ImuAppArg.MID_ImuData, imu_data_str)
            
            # 메시지 패킹 및 전송
            packed_msg = msgstructure.pack_msg(imu_msg)
            Main_Queue.put(packed_msg)
            
            time.sleep(0.1)  # 10 Hz
            
        except Exception as e:
            safe_log(f"IMU 데이터 전송 오류: {e}", "ERROR", True)
            emergency_log_to_file("ERROR", f"IMU data transmission error: {e}")
            time.sleep(0.5)  # 오류 시 더 긴 대기

def imuapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global IMUAPP_RUNSTATUS
    IMUAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, imu_instance = imuapp_init()
    
    # 초기화 실패 시 더미 데이터로 계속 실행
    if i2c_instance is None or imu_instance is None:
        safe_log("IMU 센서 연결 실패 - 더미 데이터로 계속 실행", "WARNING", True)
        imu_instance = None  # 센서가 없음을 표시

    # 스레드 딕셔너리
    thread_dict = {}

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["ReadImuData_Thread"] = threading.Thread(target=read_imu_data, args=(imu_instance, ), name="ReadImuData_Thread")
    thread_dict["SendImuData_Thread"] = threading.Thread(target=send_imu_data, args=(Main_Queue, ), name="SendImuData_Thread")

    # Spawn Each Threads
    for t in thread_dict.values():
        t.daemon = True  # 메인 프로세스 종료 시 함께 종료
        t.start()

    try:
        while IMUAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            try:
                if Main_Pipe.poll(0.5):  # 0.5초 타임아웃으로 단축
                    try:
                        message = Main_Pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError) as e:
                        safe_log(f"Pipe connection lost: {e}", "warning".upper(), True)
                        # 연결이 끊어져도 로깅은 계속
                        time.sleep(1)
                        continue
                    except Exception as e:
                        safe_log(f"Pipe receive error: {e}", "warning".upper(), False)
                        # 에러 시 루프 계속
                        time.sleep(0.5)
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

    # If error occurs, terminate app gracefully
    except (KeyboardInterrupt, SystemExit):
        safe_log("IMU app received termination signal", "info".upper(), True)
        IMUAPP_RUNSTATUS = False
    except Exception as e:
        safe_log(f"imuapp critical error : {e}", "error".upper(), True)
        IMUAPP_RUNSTATUS = False
        # 치명적 오류 발생 시에도 로깅은 계속
        try:
            safe_log("IMU app attempting graceful shutdown", "info".upper(), True)
        except:
            pass

    # Termination Process after runloop
    try:
        imuapp_terminate(i2c_instance)
    except Exception as e:
        # 종료 과정에서 오류가 발생해도 최소한의 로깅 시도
        try:
            print(f"[IMU] Termination error: {e}")
        except:
            pass

    return

# ──────────────────────────────
# ImuApp 클래스 (main.py 호환성)
# ──────────────────────────────
class ImuApp:
    """IMU 앱 클래스 - main.py 호환성을 위한 래퍼"""
    
    def __init__(self):
        """ImuApp 초기화"""
        self.app_name = "IMU"
        self.app_id = appargs.ImuAppArg.AppID
        self.run_status = True
    
    def start(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 시작 - main.py에서 호출됨"""
        try:
            imuapp_main(main_queue, main_pipe)
        except Exception as e:
            safe_log(f"ImuApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """앱 중지"""
        global IMUAPP_RUNSTATUS
        IMUAPP_RUNSTATUS = False
        self.run_status = False
