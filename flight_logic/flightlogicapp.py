# Python FSW V2 Flightlogic App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import types
from lib import prevstate
from lib import config

import signal
from multiprocessing import Queue, connection
import threading
import time
import os
import csv
from datetime import datetime

# Runstatus of application. Application is terminated when false
FLIGHTLOGICAPP_RUNSTATUS = True

# ──────────────────────────────
# 1. 모터 제어 설정
# ──────────────────────────────
# MG996R 서보모터 펄스 설정
MOTOR_OPEN_PULSE = 500    # 0도 (열림)
MOTOR_CLOSE_PULSE = 2500  # 180도 (닫힘)

# 모터 제어 조건
THERMIS_TEMP_THRESHOLD = 35.0  # Thermis 온도 임계값 (°C)
MOTOR_CLOSE_ALT_THRESHOLD = 70.0  # 모터 완전 닫음 고도 (m)
RECENT_ALT_CHECK_LEN = 5  # 최근 고도 체크 개수

# ──────────────────────────────
# 2. 현재 환경 측정값
# ──────────────────────────────
CURRENT_TEMP: float = 0.0  # DHT11 temperature (°C)
CURRENT_THERMIS_TEMP: float = 0.0  # Thermis temperature (°C)
MOTOR_TARGET_PULSE: int = -1  # 마지막으로 실제 서보에 지시한 각도 (스팸 방지용)

# ──────────────────────────────
# 3. 카메라 제어 변수
# ──────────────────────────────
CAMERA_ACTIVE: bool = False  # 카메라 활성화 상태
CAMERA_STATUS: str = "IDLE"  # 카메라 상태
CAMERA_VIDEO_COUNT: int = 0  # 저장된 비디오 파일 수
CAMERA_DISK_USAGE: float = 0.0  # 디스크 사용량 (%)
CAMERA_ACTIVATION_TIME: float = 0.0  # 카메라 활성화 시간
CAMERA_DEACTIVATION_TIME: float = 0.0  # 카메라 비활성화 시간

# ──────────────────────────────
# 4. 상태 관리 변수
# ──────────────────────────────
STATE_LIST = ["발사대 대기", "상승", "최고점", "하강", "모터 완전 닫음", "착륙"]
CURRENT_STATE = 0

# Simulation Mode Flags
SIMULATION_ENABLE = False
SIMULATION_ACTIVATE = False

# Variable used in state determination
MAX_ALT = 0
recent_alt = []  # 최근 고도 데이터 (5개 유지)

# 고도 초기화 플래그
ALTITUDE_INITIALIZED = False
INITIAL_ALTITUDE = 0.0

# 상태 전환 카운터
BAROMETER_ASCENT_COUNTER = 0
BAROMETER_DESCENT_COUNTER = 0
BAROMETER_APOGEE_COUNTER = 0
BAROMETER_MOTOR_CLOSE_COUNTER = 0
BAROMETER_LANDED_COUNTER = 0

# 이벤트 로깅 플래그
DESCENT_EVENT_LOGGED = False
CLOSE_EVENT_LOGGED = False

# ──────────────────────────────
# 5. 센서 데이터 저장
# ──────────────────────────────
LAST_GPS = None
LAST_IMU_ROLL = 0.0
LAST_IMU_PITCH = 0.0
LAST_BAROMETER = 0.0
LAST_FIR1 = None
LAST_THERMAL = None

# ──────────────────────────────
# 6. 강화된 로깅 시스템
# ──────────────────────────────
LOG_DIR = "logs/flight_logic"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")
STATE_LOG_PATH = os.path.join(LOG_DIR, "state_log.csv")
SENSOR_LOG_PATH = os.path.join(LOG_DIR, "sensor_log.csv")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.csv")
MOTOR_LOG_PATH = os.path.join(LOG_DIR, "motor_log.csv")

# 강제 종료 시에도 로그를 저장하기 위한 플래그
_emergency_logging_enabled = True

# 데이터 전송 통계
data_transmission_stats = {
    'motor_commands_sent': 0,
    'motor_commands_failed': 0,
    'state_updates_sent': 0,
    'state_updates_failed': 0,
    'last_successful_motor_command': None,
    'last_successful_state_update': None,
    'consecutive_motor_failures': 0,
    'consecutive_state_failures': 0
}

# ──────────────────────────────
# 7. 로깅 함수들 (lib/logging.py 사용)
# ──────────────────────────────
def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[{appargs.FlightlogicAppArg.AppName}] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[FLIGHT_LOGIC] 로깅 실패: {e}")
        print(f"[FLIGHT_LOGIC] 원본 메시지: {message}")

def emergency_log_to_file(log_type: str, message: str):
    """강제 종료 시에도 파일에 로그를 저장하는 함수"""
    global _emergency_logging_enabled
    if not _emergency_logging_enabled:
        return
        
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f"[{timestamp}] {log_type}: {message}\n"
        
        if log_type == "STATE":
            with open(STATE_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        elif log_type == "SENSOR":
            with open(SENSOR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        elif log_type == "ERROR":
            with open(ERROR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
        elif log_type == "MOTOR":
            with open(MOTOR_LOG_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
    except Exception as e:
        print(f"Emergency logging failed: {e}")

def log_state_change(old_state: str, new_state: str, reason: str = ""):
    """상태 변경을 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(STATE_LOG_PATH):
            with open(STATE_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'old_state', 'new_state', 'reason'])
        
        # 데이터 추가
        with open(STATE_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, old_state, new_state, reason])
            
        # lib/logging.py 사용
        safe_log(f"State change: {old_state} → {new_state} ({reason})", "INFO", True)
        
    except Exception as e:
        emergency_log_to_file("ERROR", f"State change logging failed: {e}")

def log_motor_command(pulse: int, success: bool = True, context: str = ""):
    """모터 명령을 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(MOTOR_LOG_PATH):
            with open(MOTOR_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'pulse', 'angle_deg', 'success', 'context'])
        
        # 각도 계산
        angle_deg = int((pulse - 500) * 180 / 2000)  # 500~2500 → 0~180도
        
        # 데이터 추가
        with open(MOTOR_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, pulse, angle_deg, success, context])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"Motor command logging failed: {e}")

def log_sensor_data(sensor_type: str, data: dict):
    """센서 데이터를 로깅"""
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
        emergency_log_to_file("ERROR", f"Sensor data logging failed: {e}")

def log_error(error_msg: str, context: str = ""):
    """오류를 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(ERROR_LOG_PATH):
            with open(ERROR_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'error', 'context'])
        
        # 데이터 추가
        with open(ERROR_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, error_msg, context])
            
        # lib/logging.py 사용
        safe_log(f"Error: {error_msg} (Context: {context})", "ERROR", True)
        
    except Exception as e:
        emergency_log_to_file("ERROR", f"Error logging failed: {e}")

def get_transmission_stats():
    """전송 통계 반환"""
    return data_transmission_stats

def log_system_event(event_type: str, message: str):
    """시스템 이벤트를 로깅"""
    try:
        safe_log(f"[{event_type}] {message}", "INFO", True)
    except Exception as e:
        emergency_log_to_file("ERROR", f"System event logging failed: {e}")

# ──────────────────────────────
# 8. 유틸리티 함수들
# ──────────────────────────────
def now_epoch():
    """현재 시간을 epoch으로 반환"""
    return time.time()

def now_iso():
    """현재 시간을 ISO 형식으로 반환"""
    return datetime.now().isoformat(sep=' ', timespec='milliseconds')

def safe(val):
    """안전한 값 반환 (None이면 0 반환)"""
    return val if val is not None else 0

def log_csv(filepath: str, headers: list, data: list):
    """CSV 파일에 데이터 로깅"""
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

# ──────────────────────────────
# 9. 모터 제어 함수
# ──────────────────────────────
def set_motor_pulse(Main_Queue: Queue, pulse: int) -> None:
    """MG996R 모터에 펄스 명령 전송"""
    global MOTOR_TARGET_PULSE, CLOSE_EVENT_LOGGED, LAST_BAROMETER, data_transmission_stats
    
    # 이미 같은 펄스로 지시했다면 스킵
    if pulse == MOTOR_TARGET_PULSE:
        return
    
    MOTOR_TARGET_PULSE = pulse
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            msg = msgstructure.MsgStructure()
            success = msgstructure.send_msg(Main_Queue, msg,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.MotorAppArg.AppID,
                              appargs.FlightlogicAppArg.MID_SetServoAngle,
                              str(pulse))
            
            if success:
                # 성공 시 통계 업데이트
                data_transmission_stats['motor_commands_sent'] += 1
                data_transmission_stats['last_successful_motor_command'] = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                data_transmission_stats['consecutive_motor_failures'] = 0
                break  # 성공 시 루프 종료
            else:
                raise Exception("Message send failed")
                
        except Exception as e:
            retry_count += 1
            data_transmission_stats['motor_commands_failed'] += 1
            data_transmission_stats['consecutive_motor_failures'] += 1
            
            if retry_count >= max_retries:
                # 최종 실패 시에만 조용히 처리 (로그 출력하지 않음)
                return
    
    # 모터 상태 로깅 (조용히 처리)
    if pulse == MOTOR_OPEN_PULSE:
        CLOSE_EVENT_LOGGED = False
    elif pulse == MOTOR_CLOSE_PULSE:
        # 완전히 닫힘 시점에 센서 데이터 저장 (로그 없이)
        if not CLOSE_EVENT_LOGGED:
            try:
                close_data = {
                    "time": time.time(),
                    "gps": LAST_GPS,
                    "imu_roll": LAST_IMU_ROLL,
                    "imu_pitch": LAST_IMU_PITCH,
                    "barometer": LAST_BAROMETER,
                    "temp": CURRENT_TEMP,
                    "thermis_temp": CURRENT_THERMIS_TEMP,
                    "fir1": LAST_FIR1,
                    "thermal": LAST_THERMAL
                }
                # 로그 출력하지 않음
                CLOSE_EVENT_LOGGED = True
            except Exception as e:
                # 조용히 처리
                pass
    
    # 모터 상태를 Comm 앱으로 전송
    send_motor_status_to_comm(Main_Queue, pulse)

def send_motor_status_to_comm(Main_Queue: Queue, pulse: int):
    """모터 상태를 Comm 앱으로 전송"""
    try:
        # 펄스값을 0(열림)/1(닫힘)으로 변환
        motor_status = 0 if pulse == MOTOR_OPEN_PULSE else 1
        
        msg = msgstructure.MsgStructure()
        success = msgstructure.send_msg(Main_Queue, msg,
                          appargs.FlightlogicAppArg.AppID,
                          appargs.CommAppArg.AppID,
                          appargs.FlightlogicAppArg.MID_SendMotorStatus,
                          str(motor_status))
        
        # 성공/실패 모두 조용히 처리 (로그 출력하지 않음)
            
    except Exception as e:
        # 조용히 처리 (로그 출력하지 않음)
        pass

def update_motor_logic(Main_Queue: Queue):
    """온도/고도 조건에 따라 모터 제어"""
    global CURRENT_STATE, MOTOR_CLOSE_ALT_THRESHOLD, RECENT_ALT_CHECK_LEN
    
    # 하강 상태 (State 3)에서 70m 이하일 때는 무조건 모터 닫음
    if CURRENT_STATE == 3:  # 하강 상태
        if len(recent_alt) >= RECENT_ALT_CHECK_LEN and all(alt <= MOTOR_CLOSE_ALT_THRESHOLD for alt in recent_alt[-RECENT_ALT_CHECK_LEN:]):
            set_motor_pulse(Main_Queue, MOTOR_CLOSE_PULSE)  # 180도 (닫힘)
            return
    
    # 모터 완전 닫음 상태 (State 4)에서는 항상 닫힘
    if CURRENT_STATE == 4:
        set_motor_pulse(Main_Queue, MOTOR_CLOSE_PULSE)  # 180도 (닫힘)
        return
    
    # 상승 상태 (State 1) 또는 하강 상태 (State 3)에서 Thermis 온도에 따른 제어
    if CURRENT_STATE == 1 or CURRENT_STATE == 3:  # 상승 또는 하강 상태
        if CURRENT_THERMIS_TEMP >= THERMIS_TEMP_THRESHOLD:  # 35°C 이상
            set_motor_pulse(Main_Queue, MOTOR_OPEN_PULSE)  # 0도 (열림)
        else:  # 35°C 이하
            set_motor_pulse(Main_Queue, MOTOR_CLOSE_PULSE)  # 180도 (닫힘)
        return
    
    # 최고점 상태 (State 2)에서는 기본적으로 열림 (페이로드 방출 준비)
    if CURRENT_STATE == 2:
        set_motor_pulse(Main_Queue, MOTOR_OPEN_PULSE)  # 0도 (열림)
        return
    
    # 발사대 대기 상태 (State 0)에서는 기본적으로 닫힘
    if CURRENT_STATE == 0:
        set_motor_pulse(Main_Queue, MOTOR_CLOSE_PULSE)  # 180도 (닫힘)
        return

# ──────────────────────────────
# 10. 카메라 제어 함수
# ──────────────────────────────
def activate_camera(Main_Queue: Queue) -> bool:
    """카메라 활성화"""
    global CAMERA_ACTIVE, CAMERA_ACTIVATION_TIME
    
    try:
        if CAMERA_ACTIVE:
            safe_log("Camera already active", "WARNING", True)
            return True
        
        # 카메라 앱에 활성화 명령 전송
        camera_msg = msgstructure.MsgStructure()
        success = msgstructure.send_msg(Main_Queue, camera_msg,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.CameraAppArg.AppID,
                              appargs.CameraAppArg.MID_CameraActivate,
                              "")
        
        if success:
            CAMERA_ACTIVE = True
            CAMERA_ACTIVATION_TIME = time.time()
            log_system_event("CAMERA", "Camera activation command sent successfully")
            return True
        else:
            log_error("Failed to send camera activation command", "activate_camera")
            return False
            
    except Exception as e:
        log_error(f"Camera activation error: {e}", "activate_camera")
        return False

def deactivate_camera(Main_Queue: Queue) -> bool:
    """카메라 비활성화"""
    global CAMERA_ACTIVE, CAMERA_DEACTIVATION_TIME
    
    try:
        if not CAMERA_ACTIVE:
            safe_log("Camera already inactive", "WARNING", True)
            return True
        
        # 카메라 앱에 비활성화 명령 전송
        camera_msg = msgstructure.MsgStructure()
        success = msgstructure.send_msg(Main_Queue, camera_msg,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.CameraAppArg.AppID,
                              appargs.CameraAppArg.MID_CameraDeactivate,
                              "")
        
        if success:
            CAMERA_ACTIVE = False
            CAMERA_DEACTIVATION_TIME = time.time()
            log_system_event("CAMERA", "Camera deactivation command sent successfully")
            return True
        else:
            log_error("Failed to send camera deactivation command", "deactivate_camera")
            return False
            
    except Exception as e:
        log_error(f"Camera deactivation error: {e}", "deactivate_camera")
        return False

# ──────────────────────────────
# 11. 메시지 핸들러
# ──────────────────────────────
def command_handler(recv_msg: msgstructure.MsgStructure, Main_Queue: Queue):
    """메시지 핸들러"""
    global CURRENT_TEMP, CURRENT_THERMIS_TEMP, CAMERA_ACTIVE, CAMERA_STATUS, CAMERA_VIDEO_COUNT, CAMERA_DISK_USAGE
    global LAST_GPS, LAST_IMU_ROLL, LAST_IMU_PITCH, LAST_BAROMETER, LAST_FIR1, LAST_THERMAL
    
    try:
        # 프로세스 종료 명령
        if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
            safe_log("TERMINATION DETECTED", "INFO", True)
            global FLIGHTLOGICAPP_RUNSTATUS
            FLIGHTLOGICAPP_RUNSTATUS = False
            return
        
        # DHT11 온도 데이터
        elif recv_msg.MsgID == appargs.ThermoAppArg.MID_SendThermoFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 2:
                    CURRENT_TEMP = float(data[0])
                    log_sensor_data("DHT11", {"temperature": CURRENT_TEMP, "humidity": data[1]})
            except Exception as e:
                log_error(f"DHT11 data parsing error: {e}", "command_handler")
        
        # Thermis 온도 데이터
        elif recv_msg.MsgID == appargs.ThermisAppArg.MID_SendThermisFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 1:
                    CURRENT_THERMIS_TEMP = float(data[0])
                    log_sensor_data("Thermis", {"temperature": CURRENT_THERMIS_TEMP})
            except Exception as e:
                log_error(f"Thermis data parsing error: {e}", "command_handler")
        
        # IMU 데이터
        elif recv_msg.MsgID == appargs.ImuAppArg.MID_SendImuFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 3:
                    LAST_IMU_ROLL = float(data[0])
                    LAST_IMU_PITCH = float(data[1])
                    log_sensor_data("IMU", {"roll": LAST_IMU_ROLL, "pitch": LAST_IMU_PITCH, "yaw": data[2]})
            except Exception as e:
                log_error(f"IMU data parsing error: {e}", "command_handler")
        
        # GPS 데이터
        elif recv_msg.MsgID == appargs.GpsAppArg.MID_SendGpsTlmData:
            try:
                LAST_GPS = recv_msg.data
                log_sensor_data("GPS", {"data": LAST_GPS})
            except Exception as e:
                log_error(f"GPS data parsing error: {e}", "command_handler")
        
        # Barometer 데이터
        elif recv_msg.MsgID == appargs.BarometerAppArg.MID_SendBarometerFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 1:
                    altitude = float(data[0])
                    LAST_BAROMETER = altitude
                    barometer_logic(Main_Queue, altitude)
                    log_sensor_data("Barometer", {"altitude": altitude})
            except Exception as e:
                log_error(f"Barometer data parsing error: {e}", "command_handler")
        
        # FIR1 데이터
        elif recv_msg.MsgID == appargs.FirApp1Arg.MID_SendFIR1Data:
            try:
                LAST_FIR1 = recv_msg.data
                log_sensor_data("FIR1", {"data": LAST_FIR1})
            except Exception as e:
                log_error(f"FIR1 data parsing error: {e}", "command_handler")
        
        # Thermal Camera 데이터
        elif recv_msg.MsgID == appargs.ThermalcameraAppArg.MID_SendCamFlightLogicData:
            try:
                LAST_THERMAL = recv_msg.data
                log_sensor_data("Thermal", {"data": LAST_THERMAL})
            except Exception as e:
                log_error(f"Thermal data parsing error: {e}", "command_handler")
        
        # Camera 상태 데이터
        elif recv_msg.MsgID == appargs.CameraAppArg.MID_SendCameraFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 4:
                    CAMERA_STATUS = data[0]
                    CAMERA_VIDEO_COUNT = int(data[1])
                    CAMERA_DISK_USAGE = float(data[2])
                    
                    # 디스크 사용량 경고
                    if CAMERA_DISK_USAGE > 95:
                        log_error(f"Critical disk space: {CAMERA_DISK_USAGE:.1f}%", "camera_status")
                    elif CAMERA_DISK_USAGE > 85:
                        log_error(f"Low disk space: {CAMERA_DISK_USAGE:.1f}%", "camera_status")
                        
            except Exception as e:
                log_error(f"Camera status parsing error: {e}", "command_handler")
        
        # Pitot 데이터 (2503)
        elif recv_msg.MsgID == appargs.PitotAppArg.MID_SendPitotFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 2:
                    pressure = float(data[0])
                    temp = float(data[1])
                    log_sensor_data("Pitot", {"pressure": pressure, "temperature": temp})
            except Exception as e:
                log_error(f"Pitot data parsing error: {e}", "command_handler")
        
        # TMP007 데이터 (2603)
        elif recv_msg.MsgID == appargs.Tmp007AppArg.MID_SendTmp007FlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 3:
                    object_temp = float(data[0])
                    die_temp = float(data[1])
                    voltage = float(data[2])
                    log_sensor_data("TMP007", {"object_temp": object_temp, "die_temp": die_temp, "voltage": voltage})
            except Exception as e:
                log_error(f"TMP007 data parsing error: {e}", "command_handler")
        
        # GPS FlightLogic 데이터 (1203)
        elif recv_msg.MsgID == appargs.GpsAppArg.MID_SendGpsFlightLogicData:
            try:
                data = recv_msg.data.split(',')
                if len(data) >= 5:
                    lat = float(data[0])
                    lon = float(data[1])
                    alt = float(data[2])
                    time_str = data[3]
                    sats = int(data[4])
                    log_sensor_data("GPS_FL", {"lat": lat, "lon": lon, "alt": alt, "time": time_str, "sats": sats})
            except Exception as e:
                log_error(f"GPS FlightLogic data parsing error: {e}", "command_handler")
        
        # 기타 메시지
        else:
            log_error(f"Unknown message ID: {recv_msg.MsgID}", "command_handler")
            
    except Exception as e:
        log_error(f"Command handler error: {e}", "command_handler")

# ──────────────────────────────
# 12. HK 송신 함수
# ──────────────────────────────
def send_hk(Main_Queue: Queue):
    """HK 데이터 송신"""
    while FLIGHTLOGICAPP_RUNSTATUS:
        try:
            hk_msg = msgstructure.MsgStructure()
            success = msgstructure.send_msg(Main_Queue, hk_msg,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.FlightlogicAppArg.MID_SendHK,
                              str(FLIGHTLOGICAPP_RUNSTATUS))
            
            if success:
                data_transmission_stats['state_updates_sent'] += 1
                data_transmission_stats['last_successful_state_update'] = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                data_transmission_stats['consecutive_state_failures'] = 0
            else:
                data_transmission_stats['state_updates_failed'] += 1
                data_transmission_stats['consecutive_state_failures'] += 1
                
            time.sleep(1)
        except Exception as e:
            log_error(f"HK transmission error: {e}", "send_hk")
            time.sleep(1)

# ──────────────────────────────
# 13. 고도 로직 함수
# ──────────────────────────────
def barometer_logic(Main_Queue: Queue, altitude: float):
    """고도에 따른 상태 전환 로직"""
    global MAX_ALT, MOTOR_CLOSE_ALT_THRESHOLD, CURRENT_STATE
    global BAROMETER_ASCENT_COUNTER, BAROMETER_DESCENT_COUNTER
    global BAROMETER_APOGEE_COUNTER, BAROMETER_MOTOR_CLOSE_COUNTER, BAROMETER_LANDED_COUNTER
    global recent_alt, ALTITUDE_INITIALIZED, INITIAL_ALTITUDE

    # 고도 초기화 (첫 번째 고도 데이터)
    if not ALTITUDE_INITIALIZED:
        INITIAL_ALTITUDE = altitude
        ALTITUDE_INITIALIZED = True
        safe_log(f"고도 초기화: {INITIAL_ALTITUDE}m", "INFO", True)
        
        # 초기 고도를 0으로 설정 (상대 고도 계산)
        altitude = 0.0
        safe_log("상대 고도 계산 시작 (초기 고도를 0m로 설정)", "INFO", True)
    else:
        # 상대 고도 계산 (초기 고도 대비)
        altitude = altitude - INITIAL_ALTITUDE

    # recent_alt 길이 5로 유지
    recent_alt.append(altitude)
    if len(recent_alt) > 5:
        recent_alt.pop(0)

    # 최대 고도 업데이트
    if len(recent_alt) > 2:
        sorted_alts = sorted(recent_alt, reverse=True)
        second_max = sorted_alts[1]

        if sorted_alts[1] > MAX_ALT:
            MAX_ALT = second_max
            prevstate.update_maxalt(second_max)

    # 최소 3개 데이터가 있을 때만 로직 실행
    if len(recent_alt) < 3:
        return

    # 카운터 초기화
    if BAROMETER_ASCENT_COUNTER <= 0:
        BAROMETER_ASCENT_COUNTER = 0
    if BAROMETER_APOGEE_COUNTER <= 0:
        BAROMETER_APOGEE_COUNTER = 0
    if BAROMETER_DESCENT_COUNTER <= 0:
        BAROMETER_DESCENT_COUNTER = 0
    if BAROMETER_MOTOR_CLOSE_COUNTER <= 0:
        BAROMETER_MOTOR_CLOSE_COUNTER = 0
    if BAROMETER_LANDED_COUNTER <= 0:
        BAROMETER_LANDED_COUNTER = 0
        
    # 발사대 대기 상태 (State 0)
    if CURRENT_STATE == 0:
        # 75m 이상일 때 상승 카운터 증가
        if altitude > 75:
            BAROMETER_ASCENT_COUNTER += 1
        else:
            BAROMETER_ASCENT_COUNTER -= 2
        
        # 3회 연속 75m 이상이면 상승 상태로 전환
        if BAROMETER_ASCENT_COUNTER >= 3:
            ascent_state_transition(Main_Queue)
    
    # 상승 상태 (State 1)
    if CURRENT_STATE == 1:
        # 최대 고도보다 20m 낮을 때 하강 카운터 증가
        if altitude <= MAX_ALT - 20:
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2
        
        # 최대 고도 근처에서 최고점 카운터 증가
        if altitude < MAX_ALT - 0.25 and altitude > MAX_ALT - 20:
            BAROMETER_APOGEE_COUNTER += 1
        else:
            BAROMETER_APOGEE_COUNTER -= 2

        # 하강 조건 확인
        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

        # 최고점 조건 확인
        if BAROMETER_APOGEE_COUNTER >= 2:
            apogee_state_transition(Main_Queue)

    # 최고점 상태 (State 2)
    if CURRENT_STATE == 2:
        # 하강 조건 확인
        if altitude <= MAX_ALT - 20:
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2

        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

    # 하강 상태 (State 3)
    if CURRENT_STATE == 3:
        # 70m 이하일 때 모터 닫음 카운터 증가
        if altitude <= MOTOR_CLOSE_ALT_THRESHOLD:
            BAROMETER_MOTOR_CLOSE_COUNTER += 1
        else:
            BAROMETER_MOTOR_CLOSE_COUNTER -= 2

        # 2회 연속 70m 이하면 모터 완전 닫음 상태로 전환
        if BAROMETER_MOTOR_CLOSE_COUNTER >= 2:
            motor_close_state_transition(Main_Queue)
    
    # 모터 완전 닫음 상태 (State 4)
    if CURRENT_STATE == 4:
        # 15m 이하일 때 착륙 카운터 증가
        if altitude <= 15:
            BAROMETER_LANDED_COUNTER += 1
        else:
            BAROMETER_LANDED_COUNTER -= 2

        # 3회 연속 15m 이하면 착륙 상태로 전환
        if BAROMETER_LANDED_COUNTER >= 3:
            landed_state_transition(Main_Queue)

# ──────────────────────────────
# 14. 상태 전환 함수들
# ──────────────────────────────
def log_and_update_state(state: int, log_msg: str):
    """상태 변경 및 로깅"""
    global CURRENT_STATE
    old_state = CURRENT_STATE
    CURRENT_STATE = state
    
    try:
        log_state_change(STATE_LIST[old_state], STATE_LIST[state], log_msg)
        log_system_event("STATE_CHANGE", f"State {old_state} -> {state}: {log_msg}")
        safe_log(log_msg, "INFO", True)
        prevstate.update_prevstate(CURRENT_STATE)
    except Exception as e:
        log_error(f"State change logging failed: {e}", "log_and_update_state")

def launchpad_state_transition(Main_Queue: Queue):
    """발사대 대기 상태로 전환"""
    global MAX_ALT, recent_alt
    log_and_update_state(0, "CHANGED STATE TO LAUNCHPAD STANDBY")
    MAX_ALT = 0
    recent_alt.clear()

def ascent_state_transition(Main_Queue: Queue):
    """상승 상태로 전환"""
    log_and_update_state(1, "CHANGED STATE TO ASCENT")
    
    # 상승 시 카메라 활성화
    if activate_camera(Main_Queue):
        safe_log("Camera activated for ascent phase", "INFO", True)
    else:
        safe_log("Failed to activate camera for ascent phase", "ERROR", True)

def apogee_state_transition(Main_Queue: Queue):
    """최고점 상태로 전환"""
    log_and_update_state(2, "CHANGED STATE TO APOGEE")

def descent_state_transition(Main_Queue: Queue):
    """하강 상태로 전환"""
    global DESCENT_EVENT_LOGGED, LAST_BAROMETER
    log_and_update_state(3, "CHANGED STATE TO DESCENT")
    
    if not DESCENT_EVENT_LOGGED:
        LAST_BAROMETER = recent_alt[-1] if recent_alt else None
        descent_data = {
            "epoch": now_epoch(),
            "iso": now_iso(),
            "gps": safe(LAST_GPS),
            "imu_roll": safe(LAST_IMU_ROLL),
            "imu_pitch": safe(LAST_IMU_PITCH),
            "barometer": safe(LAST_BAROMETER),
            "temp": safe(CURRENT_TEMP),
            "thermis_temp": safe(CURRENT_THERMIS_TEMP),
            "fir1": safe(LAST_FIR1),
            "thermal": safe(LAST_THERMAL)
        }
        log_system_event("DESCENT_EVENT", f"Descent initiated with data: {descent_data}")
        safe_log(f"DESCENT_EVENT: {descent_data}", "INFO", True)
        DESCENT_EVENT_LOGGED = True

def motor_close_state_transition(Main_Queue: Queue):
    """모터 완전 닫음 상태로 전환"""
    log_and_update_state(4, "CHANGED STATE TO MOTOR FULLY CLOSED")

def landed_state_transition(Main_Queue: Queue):
    """착륙 상태로 전환"""
    log_and_update_state(5, "CHANGED STATE TO LANDED")
    
    # 착륙 후 30초 대기 후 카메라 비활성화
    def delayed_camera_deactivation():
        time.sleep(30)  # 30초 대기
        if deactivate_camera(Main_Queue):
            safe_log("Camera deactivated after 30 seconds from landing", "INFO", True)
        else:
            safe_log("Failed to deactivate camera after landing", "ERROR", True)
    
    # 별도 스레드에서 카메라 비활성화 실행
    deactivation_thread = threading.Thread(target=delayed_camera_deactivation, daemon=True)
    deactivation_thread.start()

# ──────────────────────────────
# 15. 초기화 및 종료 함수
# ──────────────────────────────
def flightlogicapp_init(Main_Queue: Queue):
    """Flight Logic 앱 초기화"""
    try:
        global FLIGHTLOGICAPP_RUNSTATUS, CURRENT_STATE, MAX_ALT, MOTOR_CLOSE_ALT_THRESHOLD
        global ALTITUDE_INITIALIZED, INITIAL_ALTITUDE
        
        # 키보드 인터럽트 비활성화
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializing flightlogicapp", "INFO", True)
        
        # 이전 상태 복구
        CURRENT_STATE = int(prevstate.PREV_STATE)
        MAX_ALT = float(prevstate.PREV_MAX_ALT)
        MOTOR_CLOSE_ALT_THRESHOLD = 70  # 고정값 70m
        
        # 고도 초기화 플래그 리셋
        ALTITUDE_INITIALIZED = False
        INITIAL_ALTITUDE = 0.0

        # 상태에 따른 초기화
        if CURRENT_STATE == 0:
            launchpad_state_transition(Main_Queue)
        elif CURRENT_STATE == 1:
            ascent_state_transition(Main_Queue)
        elif CURRENT_STATE == 2:
            apogee_state_transition(Main_Queue)
        elif CURRENT_STATE == 3:
            descent_state_transition(Main_Queue)
        elif CURRENT_STATE == 4:
            motor_close_state_transition(Main_Queue)
        elif CURRENT_STATE == 5:
            landed_state_transition(Main_Queue)
            
        safe_log(f"Setting Current state to {CURRENT_STATE}", "INFO", True)
        safe_log("Flightlogicapp Initialization Complete", "INFO", True)
        
    except Exception as e:
        safe_log(f"Error during initialization: {type(e).__name__}: {e}", "ERROR", True)
        FLIGHTLOGICAPP_RUNSTATUS = False

def flightlogicapp_terminate():
    """Flight Logic 앱 종료"""
    global FLIGHTLOGICAPP_RUNSTATUS, _emergency_logging_enabled

    FLIGHTLOGICAPP_RUNSTATUS = False
    _emergency_logging_enabled = False
    
    safe_log("Terminating flightlogicapp", "INFO", True)
    
    # 스레드 종료 대기
    for thread_name in thread_dict:
        safe_log(f"Terminating thread {thread_name}", "INFO", True)
        try:
            thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
            if thread_dict[thread_name].is_alive():
                safe_log(f"Thread {thread_name} did not terminate gracefully", "WARNING", True)
        except Exception as e:
            safe_log(f"Error joining thread {thread_name}: {e}", "ERROR", True)
        safe_log(f"Terminating thread {thread_name} Complete", "INFO", True)

    safe_log("Terminating flightlogicapp complete", "INFO", True)
    return

# ──────────────────────────────
# 16. 메인 함수
# ──────────────────────────────
thread_dict = {}

def flightlogicapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    """Flight Logic 앱 메인 함수"""
    global FLIGHTLOGICAPP_RUNSTATUS, thread_dict
    
    try:
        # 초기화
        flightlogicapp_init(Main_Queue)
        
        # 스레드 생성 및 시작
        thread_dict["HK"] = threading.Thread(target=send_hk, args=(Main_Queue,), daemon=True)
        thread_dict["MOTOR_LOGIC"] = threading.Thread(target=lambda: update_motor_logic_loop(Main_Queue), daemon=True)
        
        for thread_name, thread in thread_dict.items():
            thread.start()
            safe_log(f"Started {thread_name} thread", "INFO", True)
        
        # 메인 루프
        while FLIGHTLOGICAPP_RUNSTATUS:
            try:
                # 메시지 수신
                if Main_Pipe.poll(0.1):
                    recv_msg = Main_Pipe.recv()
                    
                    # Validate Message, Skip this message if target AppID different from flightlogicapp's AppID
                    if recv_msg.receiver_app == appargs.FlightlogicAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                        command_handler(recv_msg, Main_Queue)
                    else:
                        safe_log(f"Receiver MID does not match with flightlogicapp MID: {recv_msg.receiver_app}", "error".upper(), True)
                    
            except Exception as e:
                log_error(f"Main loop error: {e}", "flightlogicapp_main")
                time.sleep(0.1)
        
        # 종료
        flightlogicapp_terminate()
        
    except Exception as e:
        log_error(f"Flight Logic main error: {e}", "flightlogicapp_main")
        flightlogicapp_terminate()

def update_motor_logic_loop(Main_Queue: Queue):
    """모터 제어 로직 루프"""
    while FLIGHTLOGICAPP_RUNSTATUS:
        try:
            update_motor_logic(Main_Queue)
            time.sleep(0.1)  # 10Hz로 모터 제어 업데이트
        except Exception as e:
            # 모터 로직 오류는 조용히 처리 (로그 출력하지 않음)
            time.sleep(0.1) 