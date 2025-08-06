# Python FSW V2 Comm App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging

# 로그 레벨을 DEBUG로 설정 (환경변수 설정)
import os
os.environ["LOG_LEVEL"] = "DEBUG"

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        from lib.logging import safe_log as lib_safe_log
        lib_safe_log(f"[Comm] {message}", level, printlogs)
        
        # DEBUG 레벨일 때는 항상 콘솔에 출력 (메인 프로세스에서도 볼 수 있도록)
        if level.upper() == "DEBUG" or os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG":
            print(f"[Comm-DEBUG] {message}")
            
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[Comm] 로깅 실패: {e}")
        print(f"[Comm] 원본 메시지: {message}")

from lib import types
from lib import config

import signal
from multiprocessing import Queue, connection
import threading
import time
import re

from datetime import datetime, timedelta
from comm import uartserial
from comm import xbeereset

import os
# Runstatus of application. Application is terminated when false
COMMAPP_RUNSTATUS = True

# Team ID of each conf
_TEAMID_PAYLOAD = 3139

_TEAMID_CONTAINER = 7777

_TEAMID_ROCKET = 8888

TEAMID = 3139

# Timedelta for ST command, initially set to 0
ST_timedelta :timedelta = timedelta(seconds=0)

# 통합 오프셋 관리 시스템 사용
try:
    from lib.offsets import get_comm_offset
    SIMP_OFFSET = get_comm_offset()
    safe_log(f"통신 SIMP 오프셋 로드됨: {SIMP_OFFSET}", "info".upper(), True)
except Exception as e:
    SIMP_OFFSET = 0
    safe_log(f"통신 SIMP 오프셋 로드 실패, 기본값 사용: {e}", "warning".upper(), True)

# 강화된 로깅 및 데이터 전송 시스템
import os
import csv
from datetime import datetime

# 로그 디렉토리 생성
LOG_DIR = "logs/comm"
os.makedirs(LOG_DIR, exist_ok=True)

# 텔레메트리 로그 파일
TLM_LOG_PATH = os.path.join(LOG_DIR, "telemetry_log.csv")
CMD_LOG_PATH = os.path.join(LOG_DIR, "command_log.csv")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.csv")

# 데이터 전송 통계
transmission_stats = {
    'packets_sent': 0,
    'packets_failed': 0,
    'last_successful_transmission': None,
    'consecutive_failures': 0,
    'max_consecutive_failures': 0
}

# 강제 종료 시에도 로그를 저장하기 위한 플래그
_emergency_logging_enabled = True

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
        
        if log_type == "TELEMETRY":
            from lib.logging import safe_write_to_file
            safe_write_to_file(TLM_LOG_PATH, log_entry, max_size_mb=5)
        elif log_type == "COMMAND":
            from lib.logging import safe_write_to_file
            safe_write_to_file(CMD_LOG_PATH, log_entry, max_size_mb=2)
        elif log_type == "ERROR":
            from lib.logging import safe_write_to_file
            safe_write_to_file(ERROR_LOG_PATH, log_entry, max_size_mb=2)
    except Exception as e:
        print(f"Emergency logging failed: {e}")

def log_telemetry_data(tlm_data_str: str, success: bool = True):
    """텔레메트리 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(TLM_LOG_PATH):
            with open(TLM_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'telemetry_data', 'transmission_success'])
        
        # 데이터 추가
        with open(TLM_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, tlm_data_str.strip(), success])
            
        # 전송 통계 업데이트
        global transmission_stats
        if success:
            transmission_stats['packets_sent'] += 1
            transmission_stats['last_successful_transmission'] = timestamp
            transmission_stats['consecutive_failures'] = 0
        else:
            transmission_stats['packets_failed'] += 1
            transmission_stats['consecutive_failures'] += 1
            transmission_stats['max_consecutive_failures'] = max(
                transmission_stats['max_consecutive_failures'], 
                transmission_stats['consecutive_failures']
            )
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"Telemetry logging failed: {e}")

def log_command_received(cmd: str, source: str = "unknown"):
    """수신된 명령을 로깅"""
    try:
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        
        # CSV 헤더가 없으면 생성
        if not os.path.exists(CMD_LOG_PATH):
            with open(CMD_LOG_PATH, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['timestamp', 'command', 'source'])
        
        # 데이터 추가
        with open(CMD_LOG_PATH, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([timestamp, cmd, source])
            
    except Exception as e:
        emergency_log_to_file("ERROR", f"Command logging failed: {e}")

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
    global transmission_stats
    return transmission_stats.copy()

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def safe_float(value, default=0.0):
    """안전한 float 변환 함수"""
    try:
        return float(value)
    except (ValueError, TypeError):
        # 경고 메시지 제거 - 조용히 기본값 반환
        return default

def command_handler (recv_msg : msgstructure.MsgStructure):
    global COMMAPP_RUNSTATUS
    global tlm_data

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        safe_log(f"COMMAPP TERMINATION DETECTED", "info".upper(), True)
        COMMAPP_RUNSTATUS = False

    # Receive Telemetry Data from Apps

    # Receive Barometer Data
    elif recv_msg.MsgID == appargs.BarometerAppArg.MID_SendBarometerTlmData:
        sep_data = recv_msg.data.split(",")
        
        # Check the length of separated data
        if (len(sep_data) == 3):  # 기본 데이터
            # If simulation mode, ignore the pressure and altitude data
            if (tlm_data.mode == "F"):
                tlm_data.pressure = safe_float(sep_data[0])
                tlm_data.altitude = safe_float(sep_data[2])
            tlm_data.temperature = safe_float(sep_data[1])
            # 고급 데이터는 로그에만 저장 (텔레메트리에는 전송하지 않음)
        else:
            safe_log(f"ERROR receiving barometer, expected 3 fields, got {len(sep_data)}", "error".upper(), True)
            return

    # Receive IMU Data
    elif recv_msg.MsgID == appargs.ImuAppArg.MID_SendImuTlmData:
        sep_data = recv_msg.data.split(",")

        # Check the length of separated data
        if (len(sep_data) == 13):  # 기본 데이터
            tlm_data.filtered_roll = safe_float(sep_data[0])
            tlm_data.filtered_pitch = safe_float(sep_data[1])
            tlm_data.filtered_yaw = safe_float(sep_data[2])
            
            tlm_data.acc_roll = safe_float(sep_data[3])
            tlm_data.acc_pitch = safe_float(sep_data[4])
            tlm_data.acc_yaw = safe_float(sep_data[5])

            tlm_data.mag_roll = safe_float(sep_data[6])
            tlm_data.mag_pitch = safe_float(sep_data[7])
            tlm_data.mag_yaw = safe_float(sep_data[8])
        
            tlm_data.gyro_roll = safe_float(sep_data[9])
            tlm_data.gyro_pitch = safe_float(sep_data[10])
            tlm_data.gyro_yaw = safe_float(sep_data[11])
            
            tlm_data.imu_temperature = safe_float(sep_data[12])
            
            # 고급 데이터는 로그에만 저장 (텔레메트리에는 전송하지 않음)
        else:
            safe_log(f"ERROR receiving IMU, expected 13 fields, got {len(sep_data)}", "error".upper(), True)
            return

    # Receive GPS Data
    elif recv_msg.MsgID == appargs.GpsAppArg.MID_SendGpsTlmData:
        sep_data = recv_msg.data.split(",")

        # Check the length of separated data
        if (len(sep_data) == 5):  # 기본 데이터
            tlm_data.gps_time = str(sep_data[0])
            tlm_data.gps_alt = safe_float(sep_data[1])
            tlm_data.gps_lat = safe_float(sep_data[2])
            tlm_data.gps_lon = safe_float(sep_data[3])
            try:
                tlm_data.gps_sats = int(float(sep_data[4]))  # float을 거쳐서 안전하게 변환
            except (ValueError, TypeError):
                safe_log(f"Invalid GPS satellites value: {sep_data[4]}, using default: 0", "warning".upper(), True)
                tlm_data.gps_sats = 0
            # 고급 데이터는 로그에만 저장 (텔레메트리에는 전송하지 않음)
        else:
            safe_log(f"ERROR receiving GPS, expected 5 fields, got {len(sep_data)}", "error".upper(), True)
            return

    # Receive Voltage Sensor Data
    #elif recv_msg.MsgID == appargs.VoltageAppArg.MID_SendVoltageTlmData:
    #    tlm_data.voltage = float(recv_msg.data)
    
    # Receive Tachometer Data
    #elif recv_msg.MsgID == appargs.TachometerAppArg.MID_SendDegPerSec:
    #    tlm_data.rot_rate = float(recv_msg.data)

    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_SendCurrentStateToTlm:
        tlm_data.state = recv_msg.data

    # Receive Simulation Status Data
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_SendSimulationStatustoTlm:
        tlm_data.mode = recv_msg.data

    elif recv_msg.MsgID == appargs.ThermoAppArg.MID_SendThermoTlmData:
        sep_data = recv_msg.data.split(",")
        if len(sep_data) == 2:
            tlm_data.thermo_temp = float(sep_data[0])
            tlm_data.thermo_humi = float(sep_data[1])

    # FIR1 데이터 수신
    elif recv_msg.MsgID == appargs.FirApp1Arg.MID_SendFIR1Data:
        sep_data = recv_msg.data.split(",")
        tlm_data.fir1_amb = float(sep_data[0])
        tlm_data.fir1_obj = float(sep_data[1])

    # Receive TMP007 Data
    elif recv_msg.MsgID == appargs.Tmp007AppArg.MID_SendTmp007TlmData:
        sep_data = recv_msg.data.split(",")
        if len(sep_data) == 3:
            tlm_data.tmp007_object_temp = safe_float(sep_data[0])
            tlm_data.tmp007_die_temp = safe_float(sep_data[1])
            tlm_data.tmp007_voltage = safe_float(sep_data[2])
        else:
            safe_log(f"ERROR receiving TMP007, expected 3 fields, got {len(sep_data)}", "error".upper(), True)



    elif recv_msg.MsgID == appargs.ThermalcameraAppArg.MID_SendCamTlmData:
        sep_data = recv_msg.data.split(",")
        if len(sep_data) == 3:  # 기본 데이터
            tlm_data.thermal_camera_avg = float(sep_data[0])
            tlm_data.thermal_camera_min = float(sep_data[1])
            tlm_data.thermal_camera_max = float(sep_data[2])
            # 고급 데이터는 로그에만 저장 (텔레메트리에는 전송하지 않음)

    elif recv_msg.MsgID == appargs.ThermisAppArg.MID_SendThermisTlmData:
        sep_data = recv_msg.data.split(",")
        if len(sep_data) == 1:
            tlm_data.thermis_temp = float(sep_data[0])



    # 모터 상태 수신
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_SendMotorStatus:
        try:
            tlm_data.motor_status = int(recv_msg.data)
        except (ValueError, TypeError):
            tlm_data.motor_status = 1  # 기본값: 닫힘

    else:
        safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)
    return

def send_hk(Main_Queue : Queue):
    global COMMAPP_RUNSTATUS
    while COMMAPP_RUNSTATUS:
        commHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, commHK, appargs.CommAppArg.AppID, appargs.HkAppArg.AppID, appargs.CommAppArg.MID_SendHK, str(COMMAPP_RUNSTATUS))
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not COMMAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def commapp_init():
    global COMMAPP_RUNSTATUS
    global TEAMID

    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializating commapp", "info".upper(), True)
        ## User Defined Initialization goes HERE

        serial_instance = uartserial.init_serial()

        # Set the command header
        selected_config = config.FSW_CONF

        # Payload : CMD / 3139
        if selected_config == config.CONF_PAYLOAD:
            TEAMID = _TEAMID_PAYLOAD

        # Container : CONT / 7777
        elif selected_config == config.CONF_CONTAINER:
            TEAMID = _TEAMID_CONTAINER

        # Rocket : RKT / 8888
        elif selected_config == config.CONF_ROCKET:
            TEAMID = _TEAMID_ROCKET

        else :
            safe_log("Wrong Configuration initializing commapp", "error".upper(), True)

        tlm_data.team_id = TEAMID

        # Reset the XBee
        safe_log("Sending XBEE reset pulse...", "info".upper(), True)
        xbeereset.send_reset_pulse()

        # Initialize 
        safe_log("Commapp Initialization Complete", "info".upper(), True)

        return serial_instance
    
    except Exception as e:
        safe_log(f"Error during initialization : {e}", "error".upper(), True)
        COMMAPP_RUNSTATUS = False

# Termination
def commapp_terminate(serial_instance):
    global COMMAPP_RUNSTATUS

    COMMAPP_RUNSTATUS = False
    safe_log("Terminating commapp", "info".upper(), True)
    # Termination Process Comes Here

    uartserial.terminate_serial(serial_instance)

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
    safe_log("Terminating commapp complete", "info".upper(), True)
    return

######################################################
## USER METHOD                                      ##
######################################################

# Put user-defined methods here!

class _tlm_data_format:
    team_id :int = 3139
    mission_time : str = "00:00:00"
    packet_count : int = 0
    mode : str = "F"
    state : str = "발사대 대기"
    altitude : float = 0.0
    temperature : float = 0.0
    pressure : float = 0.0
    voltage : float = 0.0
    gyro_roll : float = 0.0
    gyro_pitch : float = 0.0
    gyro_yaw : float = 0.0
    acc_roll : float = 0.0
    acc_pitch : float = 0.0
    acc_yaw : float = 0.0
    mag_roll : float = 0.0
    mag_pitch : float = 0.0
    mag_yaw : float = 0.0
    rot_rate : float = 0.0
    gps_lat : float = 0.0
    gps_lon : float = 0.0
    gps_alt : float = 0.0
    gps_time : str = "00:00:00"
    gps_sats : int = 0
    filtered_roll : float = 0.0
    filtered_pitch : float = 0.0
    filtered_yaw : float = 0.0
    cmd_echo : str = "None"
    thermo_temp: float = 0.0
    thermo_humi: float = 0.0
    fir1_amb: float = 0.0
    fir1_obj: float = 0.0

    thermal_camera_avg: float = 0.0
    thermal_camera_min: float = 0.0
    thermal_camera_max: float = 0.0
    thermis_temp: float = 0.0
    tmp007_object_temp: float = 0.0
    tmp007_die_temp: float = 0.0
    tmp007_voltage: float = 0.0
    imu_temperature: float = 0.0
    motor_status: int = 1  # 0=열림, 1=닫힘
    
    # 고급 데이터 필드들 (로그에만 저장, 텔레메트리에는 전송하지 않음)
    # Thermal Camera 추가 데이터
    thermal_camera_max_gradient: float = 0.0
    thermal_camera_avg_gradient: float = 0.0
    thermal_camera_std_temp: float = 0.0
    thermal_camera_hot_pixels: int = 0
    thermal_camera_cold_pixels: int = 0
    
    # Barometer 추가 데이터
    barometer_sea_level_pressure: float = 0.0
    barometer_pressure_resolution: float = 0.01
    barometer_temperature_resolution: float = 0.01
    
    # GPS 추가 데이터
    gps_hdop: float = 0.0
    gps_vdop: float = 0.0
    gps_ground_speed: float = 0.0
    gps_course: float = 0.0
    gps_quality: int = 0
    gps_fix_type: int = 0
    
    # IMU 추가 데이터
    imu_quaternion_w: float = 1.0
    imu_quaternion_x: float = 0.0
    imu_quaternion_y: float = 0.0
    imu_quaternion_z: float = 0.0
    imu_linear_accel_x: float = 0.0
    imu_linear_accel_y: float = 0.0
    imu_linear_accel_z: float = 0.0
    imu_gravity_x: float = 0.0
    imu_gravity_y: float = 0.0
    imu_gravity_z: float = 0.0
    imu_calibration_system: int = 0
    imu_calibration_gyro: int = 0
    imu_calibration_accel: int = 0
    imu_calibration_mag: int = 0
    imu_system_status: int = 0

tlm_data = _tlm_data_format()
TELEMETRY_ENABLE = True

# This function Sends telemetry to Ground Station
def send_tlm(serial_instance):
    global COMMAPP_RUNSTATUS
    global tlm_data
    global TELEMETRY_ENABLE

    consecutive_failures = 0
    max_failures_before_log = 5

    while COMMAPP_RUNSTATUS:
        try:
            current_time = get_current_time()
            tlm_data.mission_time = current_time.strftime("%H:%M:%S")

            if TELEMETRY_ENABLE:
                tlm_data.packet_count += 1

            tlm_to_send = ",".join([str(tlm_data.team_id),
                        tlm_data.mission_time,
                        str(tlm_data.packet_count),
                        tlm_data.mode,
                        tlm_data.state,
                        f"{tlm_data.altitude:.2f}",
                        f"{tlm_data.temperature:.2f}",
                        f"{0.1 * tlm_data.pressure:.2f}", # from hPa to kPa
                        f"{tlm_data.voltage:.2f}",
                        f"{tlm_data.gyro_roll:.4f}",
                        f"{tlm_data.gyro_pitch:.4f}",
                        f"{tlm_data.gyro_yaw:.4f}",
                        f"{tlm_data.acc_roll:.4f}",
                        f"{tlm_data.acc_pitch:.4f}",
                        f"{tlm_data.acc_yaw:.4f}",
                        f"{0.01 * tlm_data.mag_roll:.4f}", # from microT to G
                        f"{0.01 * tlm_data.mag_pitch:.4f}",
                        f"{0.01 * tlm_data.mag_yaw:.4f}",
                        f"{tlm_data.rot_rate:.2f}",
                        str(tlm_data.gps_time),
                        f"{tlm_data.gps_alt:.2f}",
                        f"{tlm_data.gps_lat:.2f}",
                        f"{tlm_data.gps_lon:.2f}",
                        str(tlm_data.gps_sats),
                        tlm_data.cmd_echo,
                        #f','
                        f"{tlm_data.filtered_roll:.4f}",
                        f"{tlm_data.filtered_pitch:.4f}",
                        f"{tlm_data.filtered_yaw:.4f}",
                        f"{tlm_data.thermo_temp:.2f}",
                        f"{tlm_data.thermo_humi:.2f}",
                        f"{tlm_data.fir1_amb:.2f}",
                        f"{tlm_data.fir1_obj:.2f}",
                        f"{tlm_data.thermal_camera_avg:.2f}",
                        f"{tlm_data.thermal_camera_min:.2f}",
                        f"{tlm_data.thermal_camera_max:.2f}",
                        f"{tlm_data.thermis_temp:.2f}",
                        f"{tlm_data.tmp007_object_temp:.2f}",
                        f"{tlm_data.tmp007_die_temp:.2f}",
                        f"{tlm_data.tmp007_voltage:.2f}",
                        f"{tlm_data.imu_temperature:.2f}",
                        str(tlm_data.motor_status),
                        # 추가된 고급 데이터 필드들
                        f"{tlm_data.thermal_camera_max_gradient:.3f}",
                        f"{tlm_data.thermal_camera_avg_gradient:.3f}",
                        f"{tlm_data.thermal_camera_std_temp:.2f}",
                        str(tlm_data.thermal_camera_hot_pixels),
                        str(tlm_data.thermal_camera_cold_pixels),
                        f"{tlm_data.barometer_sea_level_pressure:.2f}",
                        f"{tlm_data.barometer_pressure_resolution:.3f}",
                        f"{tlm_data.barometer_temperature_resolution:.3f}",
                        f"{tlm_data.gps_hdop:.2f}",
                        f"{tlm_data.gps_vdop:.2f}",
                        f"{tlm_data.gps_ground_speed:.2f}",
                        f"{tlm_data.gps_course:.1f}",
                        str(tlm_data.gps_quality),
                        str(tlm_data.gps_fix_type),
                        f"{tlm_data.imu_quaternion_w:.4f}",
                        f"{tlm_data.imu_quaternion_x:.4f}",
                        f"{tlm_data.imu_quaternion_y:.4f}",
                        f"{tlm_data.imu_quaternion_z:.4f}",
                        f"{tlm_data.imu_linear_accel_x:.4f}",
                        f"{tlm_data.imu_linear_accel_y:.4f}",
                        f"{tlm_data.imu_linear_accel_z:.4f}",
                        f"{tlm_data.imu_gravity_x:.4f}",
                        f"{tlm_data.imu_gravity_y:.4f}",
                        f"{tlm_data.imu_gravity_z:.4f}",
                        str(tlm_data.imu_calibration_system),
                        str(tlm_data.imu_calibration_gyro),
                        str(tlm_data.imu_calibration_accel),
                        str(tlm_data.imu_calibration_mag),
                        str(tlm_data.imu_system_status)])+"\n"

            # DEBUG 모드일 때만 디버그 텍스트 출력
            if os.environ.get("LOG_LEVEL", "INFO").upper() == "DEBUG":
                tlm_debug_text = f"\n=== TELEMETRY DEBUG INFO ===\n" \
                        f"ID : {tlm_data.team_id} TIME : {tlm_data.mission_time}, PCK_CNT : {tlm_data.packet_count}, MODE : {tlm_data.mode}, STATE : {tlm_data.state}\n"\
                        f"Barometer : Altitude({tlm_data.altitude}), Temperature({tlm_data.temperature}), Pressure({tlm_data.pressure}), SeaLevelP({tlm_data.barometer_sea_level_pressure})\n" \
                         f"Thermo : Temperature({tlm_data.thermo_temp}), Humidity({tlm_data.thermo_humi})\n" \
                         f"TMP007 : Object({tlm_data.tmp007_object_temp}), Die({tlm_data.tmp007_die_temp}), Voltage({tlm_data.tmp007_voltage})\n" \
                         f"Thermis : Temperature({tlm_data.thermis_temp})\n" \
                         f"FIR1 : Ambient({tlm_data.fir1_amb}), Object({tlm_data.fir1_obj})\n" \
                         f"GPS : Time({tlm_data.gps_time}), Alt({tlm_data.gps_alt}), Lat({tlm_data.gps_lat}), Lon({tlm_data.gps_lon}), Sats({tlm_data.gps_sats})\n" \
                         f"IMU : Temp({tlm_data.imu_temperature}), Roll({tlm_data.filtered_roll}), Pitch({tlm_data.filtered_pitch}), Yaw({tlm_data.filtered_yaw})\n" \
                         f"Motor : Status({tlm_data.motor_status})\n" \
                         f"CMD Echo : {tlm_data.cmd_echo}\n" \
                         f"=== END DEBUG INFO ===\n"
                
                safe_log(tlm_debug_text, "debug".upper(), True)

            # Only send telemetry when telemetry is enabled
            if TELEMETRY_ENABLE:
                try:
                    uartserial.send_serial_data(serial_instance, tlm_to_send)
                    consecutive_failures = 0  # 성공 시 실패 횟수 리셋
                    # 강화된 로깅 - 전송 성공 시에만 로그에 저장
                    log_telemetry_data(tlm_to_send, success=True)
                except Exception as e:
                    consecutive_failures += 1
                    log_telemetry_data(tlm_to_send, success=False)
                    log_error(f"Telemetry transmission failed: {e}", "send_tlm")
                    
                    if consecutive_failures <= max_failures_before_log:
                        safe_log(f"Telemetry transmission failed: {e}", "error".upper(), True)
                    elif consecutive_failures == max_failures_before_log + 1:
                        safe_log(f"Telemetry transmission errors suppressed after {max_failures_before_log} failures", "warning".upper(), True)

        except Exception as e:
            consecutive_failures += 1
            log_error(f"Telemetry generation failed: {e}", "send_tlm")
            if consecutive_failures <= max_failures_before_log:
                safe_log(f"Telemetry generation failed: {e}", "error".upper(), True)
            elif consecutive_failures == max_failures_before_log + 1:
                safe_log(f"Telemetry generation errors suppressed after {max_failures_before_log} failures", "warning".upper(), True)

        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not COMMAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

# Import regular expression module
import re

def cmd_cx(option:str, Main_Queue:Queue):
    global TELEMETRY_ENABLE
    global tlm_data

    if option == "ON":
        safe_log("Enabling Telemetry", "info".upper(), True)
        TELEMETRY_ENABLE = True
    
    if option == "OFF":
        safe_log("Disabling Telemetry", "info".upper(), True)
        TELEMETRY_ENABLE = False
        tlm_data.packet_count = 0

    return

def cmd_debug(option:str, Main_Queue:Queue):
    """디버그 출력 제어 명령"""
    if option == "ON":
        os.environ["LOG_LEVEL"] = "DEBUG"
        safe_log("Debug output enabled", "info".upper(), True)
        safe_log("🔍 DEBUG MODE ACTIVATED - Detailed CommApp output will be shown", "debug".upper(), True)
        # 메인 프로세스에도 디버그 상태 전달
        debug_msg = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, debug_msg, appargs.CommAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_SendHK, "DEBUG_ON")
    elif option == "OFF":
        os.environ["LOG_LEVEL"] = "INFO"
        safe_log("Debug output disabled", "info".upper(), True)
        safe_log("🔍 DEBUG MODE DEACTIVATED - CommApp debug output hidden", "debug".upper(), True)
        # 메인 프로세스에도 디버그 상태 전달
        debug_msg = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, debug_msg, appargs.CommAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_SendHK, "DEBUG_OFF")
    else:
        safe_log(f"Debug command option '{option}' not recognized. Use 'ON' or 'OFF'", "warning".upper(), True)
    return

def cmd_st(option:str, Main_Queue:Queue):

    safe_log("Setting Time", "info".upper(), True)
    set_timedelta(option)

    return

def cmd_sim(option:str, Main_Queue:Queue):
    RouteSimCmdMsg = msgstructure.MsgStructure()

    # Route the simulation command to flightlogic app
    msgstructure.send_msg(Main_Queue, RouteSimCmdMsg, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_SIM, option)
    return

def cmd_simp(option:str, Main_Queue:Queue):
    global tlm_data
    global SIMP_OFFSET

    RouteSimpCmdMsg = msgstructure.MsgStructure()
    
    sea_level_pressure = 1013.25

    recv_simp = float(option) / 100
    recv_alt = 44307.7 * (1 - (recv_simp / sea_level_pressure) ** 0.190284)

    tlm_data.pressure = recv_simp
    tlm_data.altitude = recv_alt - SIMP_OFFSET

    # Route the simulation pressure value to flightlogic app
    msgstructure.send_msg(Main_Queue, RouteSimpCmdMsg, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_SIMP, str(tlm_data.altitude))
    
    return

def cmd_cal(option:str, Main_Queue:Queue):
    global tlm_data
    global SIMP_OFFSET

    # If flight mod
    if tlm_data.mode == "F":
        RouteCalCmdMsg = msgstructure.MsgStructure()

        # Route The Calibration command to Baromter app
        msgstructure.send_msg(Main_Queue, RouteCalCmdMsg, appargs.CommAppArg.AppID, appargs.BarometerAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_CAL, "")
    
    # If simulation mode
    if tlm_data.mode == "S":
        SIMP_OFFSET = tlm_data.altitude
        
        # 통합 오프셋 시스템에 저장
        try:
            from lib.offsets import set_offset
            set_offset("COMM.SIMP_OFFSET", SIMP_OFFSET)
            safe_log(f"통신 SIMP 오프셋이 통합 시스템에 저장됨: {SIMP_OFFSET}", "info".upper(), True)
        except Exception as e:
            safe_log(f"통합 오프셋 시스템 저장 실패: {e}", "warning".upper(), True)
        
        ResetBarometerMaxAltCmd = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, ResetBarometerMaxAltCmd, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.BarometerAppArg.MID_ResetBarometerMaxAlt, "")

    return

def cmd_mec(option:str, Main_Queue:Queue):
    RouteMecCmdMsg = msgstructure.MsgStructure()

    # Route the mechanism activation command to motor app
    msgstructure.send_msg(Main_Queue, RouteMecCmdMsg, appargs.CommAppArg.AppID, appargs.MotorAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_MEC, option)

    return

def cmd_ss(option:str, Main_Queue:Queue):

    RouteSsCmdMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, RouteSsCmdMsg, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_SS, option)

    return
"""
def cmd_rbt(option:str, Main_Queue:Queue):
    
    safe_log("RBT command received. Restarting...", "info".upper(), True)
    os.system('systemctl reboot -i')
    return
"""
def cmd_rbt(Main_Queue: Queue):
    safe_log("RBT command received. Restarting…", "info".upper(), True)
    os.system("systemctl reboot -i")
        
def cmd_cam(option:str, Main_Queue:Queue):

    RouteCamCmdMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, RouteCamCmdMsg, appargs.CommAppArg.AppID, appargs.ThermalcameraAppArg.AppID, appargs.CommAppArg.MID_RouteCmd_CAM, option)
    return

# This fuction reads command from Ground Station
def read_cmd(Main_Queue:Queue, serial_instance):
    global COMMAPP_RUNSTATUS
    global tlm_data
    global TEAMID

    # Regular expression for commands

    # Payload Telemetry ON/OFF
    cx_re_header = f"CMD,{TEAMID},CX," 
    cx_re_option = "(ON|OFF)$"

    # Set time
    st_re_header = f"CMD,{TEAMID},ST,"
    st_re_option = "(([01]\d|2[0-3])(:[0-5]\d){2}|GPS)$"

    # Simulation Mode
    sim_re_header = f"CMD,{TEAMID},SIM," # Simulation mode control
    sim_re_option = "(ENABLE|ACTIVATE|DISABLE)$"

    # Simulated pressure
    simp_re_header = f"CMD,{TEAMID},SIMP,"
    simp_re_option = "\d{5,6}$"

    # Altitude Calibration
    cal_re_header = f"CMD,{TEAMID},CAL"
    cal_re_option = "$"

    # Mechanism activation
    mec_re_header = f"CMD,{TEAMID},MEC,MOTOR,"
    mec_re_option = "(ON|OFF)$"

    # Set State
    ss_re_header = f"CMD,{TEAMID},SS,"
    ss_re_option = "\d{1}$"
    
    rbt_re_header = f"CMD,{TEAMID},RBT"
    rbt_re_option = "$"

    # Camera Control
    cam_re_header = f"CMD,{TEAMID},CAM,"
    cam_re_option = "(ON|OFF)$"

    # Debug Control
    debug_re_header = f"CMD,{TEAMID},DEBUG,"
    debug_re_option = "(ON|OFF)$"

    while COMMAPP_RUNSTATUS:
        try:
            rcv_cmd = uartserial.receive_serial_data(serial_instance)

            # When Timeout Occurs ; empty data is read, continue
            if not rcv_cmd or rcv_cmd == None:
                continue
            
            # Filter out GPS NMEA sentences and related fragments
            if (rcv_cmd.startswith('$') or 
                rcv_cmd.startswith('GPGGA') or 
                rcv_cmd.startswith('GPGSA') or 
                rcv_cmd.startswith('GPRMC') or 
                rcv_cmd.startswith('GPVTG') or
                rcv_cmd.startswith('GPGSV') or
                rcv_cmd.startswith('RMC') or
                rcv_cmd.startswith('PVTG') or
                rcv_cmd.startswith('8,31,28') or  # GPS 데이터 패턴
                ',' in rcv_cmd and ('GPGGA' in rcv_cmd or 'GPGSA' in rcv_cmd or 'GPRMC' in rcv_cmd or 'GPVTG' in rcv_cmd or '5.03,4.93' in rcv_cmd)):
                continue
            
            # 강화된 명령 로깅
            log_command_received(rcv_cmd, "serial")
            safe_log(f"Received Command : {rcv_cmd}", "info".upper(), True)
            
            # Validate commmand using regex

            # cx
            if re.fullmatch(cx_re_header+cx_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                # Parse the option
                option = re.search(cx_re_option, rcv_cmd).group()
                cmd_cx(option, Main_Queue)

            # st
            elif re.fullmatch(st_re_header+st_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                option = re.search(st_re_option, rcv_cmd).group()
                cmd_st(option, Main_Queue)

            # sim
            elif re.fullmatch(sim_re_header+sim_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                option = re.search(sim_re_option, rcv_cmd).group()
                cmd_sim(option, Main_Queue)

            # simp
            elif re.fullmatch(simp_re_header+simp_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                option = re.search(simp_re_option, rcv_cmd).group()
                cmd_simp(option, Main_Queue)

            # cal
            elif re.fullmatch(cal_re_header+cal_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                # Calibration command has no option
                option = ""
                cmd_cal(option, Main_Queue)

            # mec
            elif re.fullmatch(mec_re_header+mec_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                option = re.search(mec_re_option, rcv_cmd).group()
                cmd_mec(option, Main_Queue)
            
            #ss
            elif re.fullmatch(ss_re_header+ss_re_option, rcv_cmd):

                # Change the CMD Echo String
                set_cmdecho(rcv_cmd)

                option = re.search(ss_re_option, rcv_cmd).group()

                cmd_ss(option, Main_Queue)
            
            #elif re.fullmatch(rbt_re_header+rbt_re_option, rcv_cmd):
            #    set_cmdecho(rcv_cmd)

                # Reboot
            #    cmd_rbt(option, Main_Queue)
            
            
            elif re.fullmatch(rbt_re_header + rbt_re_option, rcv_cmd):
                set_cmdecho(rcv_cmd)
                cmd_rbt(Main_Queue)


            elif re.fullmatch(cam_re_header+cam_re_option, rcv_cmd):
                set_cmdecho(rcv_cmd)

                option = re.search(cam_re_option, rcv_cmd).group()
                
                # Activate Camera
                cmd_cam(option, Main_Queue)

            # debug
            elif re.fullmatch(debug_re_header+debug_re_option, rcv_cmd):
                set_cmdecho(rcv_cmd)

                option = re.search(debug_re_option, rcv_cmd).group()
                
                # Control Debug Output
                cmd_debug(option, Main_Queue)

            else:
                safe_log(f"Invalid command {rcv_cmd}", "error".upper(), True)

        except Exception as e:
                safe_log(f"Error receiving command, Sleeping 1 second :  {e}", "error".upper(), True)
                time.sleep(1)

    return

def set_cmdecho(cmd_str:str):
    global tlm_data
    #remove comma from command
    tlm_data.cmd_echo = cmd_str.replace(",","")

# Get the current time with timedelta applied
def get_current_time() -> datetime :
    global ST_timedelta

    current_time = datetime.now()

    return current_time - ST_timedelta

# Set the timedelta to given timestr
def set_timedelta(timestr:str) :
    global ST_timedelta
    global tlm_data

    curtime = datetime.now()
    # Timestr is always given in HH:MM:SS format or "GPS"
    if timestr == "GPS":
        h,m,s = map(int, tlm_data.gps_time.split(":"))
        gps_delta = curtime
        gps_delta = gps_delta.replace(hour=h, minute=m, second=s)

        ST_timedelta = curtime - gps_delta

    else:
        h, m, s = map(int, timestr.split(":"))
        timestr_delta = curtime

        timestr_delta = timestr_delta.replace(hour=h, minute=m, second=s)

        ST_timedelta = curtime - timestr_delta
    return
        
######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def commapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global COMMAPP_RUNSTATUS
    COMMAPP_RUNSTATUS = True

    # Initialization Process
    serial_instance = commapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["TlmSender_Thread"] = threading.Thread(target=send_tlm, args=(serial_instance, ), name="TlmSender_Thread")
    thread_dict["CmdReader_Thread"] = threading.Thread(target=read_cmd, args=(Main_Queue, serial_instance), name="CmdReader_Thread")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while COMMAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            try:
                if Main_Pipe.poll(0.5):  # 0.5초 타임아웃으로 단축
                    try:
                        message = Main_Pipe.recv()
                    except (EOFError, BrokenPipeError, ConnectionResetError) as e:
                        safe_log(f"Pipe connection lost: {e}", "warning".upper(), True)
                        log_error(f"Pipe connection lost: {e}", "commapp_main")
                        # 연결이 끊어져도 로깅은 계속
                        time.sleep(1)
                        continue
                    except Exception as e:
                        safe_log(f"Pipe receive error: {e}", "warning".upper(), False)
                        log_error(f"Pipe receive error: {e}", "commapp_main")
                        # 에러 시 루프 계속
                        time.sleep(0.5)
                        continue
                else:
                    # 타임아웃 시 루프 계속
                    continue
                    
                recv_msg = message
                
                # Validate Message, Skip this message if target AppID different from commapp's AppID
                # Exception when the message is from main app
                if recv_msg.receiver_app == appargs.CommAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                    # Handle Command According to Message ID
                    command_handler(recv_msg)
                else:
                    safe_log("Receiver MID does not match with commapp MID", "error".upper(), True)
                    
            except Exception as e:
                safe_log(f"Main loop error: {e}", "error".upper(), True)
                log_error(f"Main loop error: {e}", "commapp_main")
                time.sleep(0.1)  # 에러 시 짧은 대기

    # If error occurs, terminate app gracefully
    except (KeyboardInterrupt, SystemExit):
        safe_log("Comm app received termination signal", "info".upper(), True)
        COMMAPP_RUNSTATUS = False
    except Exception as e:
        safe_log(f"commapp critical error : {e}", "error".upper(), True)
        log_error(f"Critical commapp error: {e}", "commapp_main")
        COMMAPP_RUNSTATUS = False
        # 치명적 오류 발생 시에도 로깅은 계속
        try:
            safe_log("Comm app attempting graceful shutdown", "info".upper(), True)
        except:
            pass

    # Termination Process after runloop
    try:
        commapp_terminate(serial_instance)
    except Exception as e:
        # 종료 과정에서 오류가 발생해도 최소한의 로깅 시도
        try:
            print(f"[Comm] Termination error: {e}")
        except:
            pass

    return

# ──────────────────────────────
# CommApp 클래스 (main.py 호환성)
# ──────────────────────────────
class CommApp:
    """Comm 앱 클래스 - main.py 호환성을 위한 래퍼"""
    
    def __init__(self):
        """CommApp 초기화"""
        self.app_name = "Comm"
        self.app_id = appargs.CommAppArg.AppID
        self.run_status = True
    
    def start(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 시작 - main.py에서 호출됨"""
        try:
            commapp_main(main_queue, main_pipe)
        except Exception as e:
            safe_log(f"CommApp start error: {e}", "ERROR", True)
    
    def stop(self):
        """앱 중지"""
        global COMMAPP_RUNSTATUS
        COMMAPP_RUNSTATUS = False
        self.run_status = False
