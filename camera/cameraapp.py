# Python FSW V2 Camera App
# Author : Hyeon Lee  (HEPHAESTUS)
# Raspberry Pi Camera Module v3 Wide 지원

from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[Camera] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[Camera] 로깅 실패: {e}")
        print(f"[Camera] 원본 메시지: {message}")

from lib import appargs, msgstructure, logging, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection
from datetime import datetime
import os
from pathlib import Path

from camera import camera as cam

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
CAMERAAPP_RUNSTATUS = True

# 카메라 상태
CAMERA_STATUS = "IDLE"
VIDEO_COUNT = 0
DISK_USAGE = 0.0

# 로그 디렉토리
LOG_DIR = "/home/pi/cansat_logs"

# ──────────────────────────────
# 1. 로깅 함수
# ──────────────────────────────
def log_cameraapp_event(event_type: str, message: str):
    """카메라 앱 전용 로그 기록."""
    try:
        # 로그 디렉토리 생성
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        # 로그 파일명 (날짜별)
        log_file = os.path.join(LOG_DIR, f"cameraapp_{datetime.now().strftime('%Y-%m-%d')}.log")
        
        # 타임스탬프와 함께 로그 기록
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] [{event_type}] {message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    except Exception as e:
        # 로그 기록 실패 시 기본 이벤트 로그 사용
        safe_log(f"Log write failed: {e}", "error".upper(), True)

def log_app_info(info_msg: str):
    """앱 정보 로그."""
    log_cameraapp_event("INFO", info_msg)
    safe_log(info_msg, "info".upper(), True)

def log_app_error(error_msg: str):
    """앱 오류 로그."""
    log_cameraapp_event("ERROR", error_msg)
    safe_log(error_msg, "error".upper(), True)

def log_app_warning(warning_msg: str):
    """앱 경고 로그."""
    log_cameraapp_event("WARNING", warning_msg)
    safe_log(warning_msg, "warning".upper(), True)

def log_message_received(msg_id: int, sender: str = "Unknown"):
    """메시지 수신 로그."""
    log_cameraapp_event("MSG_RECEIVED", f"Message {msg_id} received from {sender}")

def log_message_sent(msg_id: int, receiver: str = "Unknown"):
    """메시지 송신 로그."""
    log_cameraapp_event("MSG_SENT", f"Message {msg_id} sent to {receiver}")

# ──────────────────────────────
# 2. 메시지 핸들러
# ──────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure):
    global CAMERAAPP_RUNSTATUS, CAMERA_STATUS

    # (1) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        log_message_received(recv_msg.MsgID, "MainApp")
        log_app_info("CAMERAAPP TERMINATION DETECTED")
        CAMERAAPP_RUNSTATUS = False
        return

    # (2) FlightLogic에서 카메라 활성화 명령
    elif recv_msg.MsgID == appargs.CameraAppArg.MID_CameraActivate:
        log_message_received(recv_msg.MsgID, "FlightLogic")
        log_app_info("Camera activation command received")
        
        if cam.start_recording():
            CAMERA_STATUS = "RECORDING"
            log_app_info("Camera recording started successfully")
        else:
            CAMERA_STATUS = "ERROR"
            log_app_error("Failed to start camera recording")
        return

    # (3) FlightLogic에서 카메라 비활성화 명령
    elif recv_msg.MsgID == appargs.CameraAppArg.MID_CameraDeactivate:
        log_message_received(recv_msg.MsgID, "FlightLogic")
        log_app_info("Camera deactivation command received")
        
        if cam.stop_recording():
            CAMERA_STATUS = "IDLE"
            log_app_info("Camera recording stopped successfully")
        else:
            CAMERA_STATUS = "ERROR"
            log_app_error("Failed to stop camera recording")
        return

    # (4) 기타 커맨드는 필요 시 확장
    log_app_error(f"MID {recv_msg.MsgID} not handled")

# ──────────────────────────────
# 3. HK 송신 스레드
# ──────────────────────────────
def send_hk(Main_Queue: Queue):
    log_app_info("HK transmission thread started")
    
    while CAMERAAPP_RUNSTATUS:
        try:
            hk = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, hk,
                                  appargs.CameraAppArg.AppID,
                                  appargs.HkAppArg.AppID,
                                  appargs.CameraAppArg.MID_SendHK,
                                  str(CAMERAAPP_RUNSTATUS))
            log_message_sent(appargs.CameraAppArg.MID_SendHK, "HKApp")
            time.sleep(1)
        except Exception as e:
            log_app_error(f"HK transmission error: {e}")
            time.sleep(1)
    
    log_app_info("HK transmission thread ended")

# ──────────────────────────────
# 4. 초기화 / 종료
# ──────────────────────────────
def cameraapp_init():
    """카메라 초기화."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        log_app_info("Initializing cameraapp")

        # 카메라 초기화
        if not cam.init_camera():
            log_app_error("Camera initialization failed")
            return False
        
        log_app_info("Cameraapp initialization complete")
        return True

    except Exception as e:
        log_app_error(f"Cameraapp init error: {e}")
        return False

def cameraapp_terminate():
    """카메라 앱 종료."""
    try:
        log_app_info("Starting cameraapp termination")

        # 카메라 종료
        if not cam.terminate_camera():
            log_app_warning("Camera termination had issues")

        log_app_info("Cameraapp termination complete")
        return True

    except Exception as e:
        log_app_error(f"Cameraapp termination error: {e}")
        return False

# ──────────────────────────────
# 5. 상태 업데이트 스레드
# ──────────────────────────────
def update_camera_status():
    """카메라 상태 업데이트 스레드."""
    global CAMERA_STATUS, VIDEO_COUNT, DISK_USAGE
    
    log_app_info("Camera status update thread started")
    
    while CAMERAAPP_RUNSTATUS:
        try:
            # 상태 업데이트
            old_status = CAMERA_STATUS
            CAMERA_STATUS = cam.get_camera_status()
            
            if old_status != CAMERA_STATUS:
                log_app_info(f"Camera status changed: {old_status} -> {CAMERA_STATUS}")
            
            # 비디오 수 업데이트
            old_count = VIDEO_COUNT
            VIDEO_COUNT = cam.get_video_count()
            
            if old_count != VIDEO_COUNT:
                log_app_info(f"Video count updated: {old_count} -> {VIDEO_COUNT}")
            
            # 디스크 사용량 업데이트
            old_usage = DISK_USAGE
            DISK_USAGE = cam.get_disk_usage()
            
            if abs(old_usage - DISK_USAGE) > 5:  # 5% 이상 변화 시 로그
                log_app_info(f"Disk usage updated: {old_usage:.1f}% -> {DISK_USAGE:.1f}%")
            
            time.sleep(5)  # 5초마다 업데이트
            
        except Exception as e:
            log_app_error(f"Status update error: {e}")
            time.sleep(5)
    
    log_app_info("Camera status update thread ended")

# ──────────────────────────────
# 6. 데이터 송신 스레드
# ──────────────────────────────
def send_camera_data(Main_Queue: Queue):
    """카메라 데이터 송신 스레드."""
    log_app_info("Camera data transmission thread started")
    
    while CAMERAAPP_RUNSTATUS:
        try:
            # 텔레메트리 데이터 (1 Hz)
            tlm_data = msgstructure.MsgStructure()
            tlm_msg = f"{CAMERA_STATUS},{VIDEO_COUNT},{DISK_USAGE:.1f}"
            msgstructure.send_msg(Main_Queue, tlm_data,
                                  appargs.CameraAppArg.AppID,
                                  appargs.TelemetryAppArg.AppID,
                                  appargs.CameraAppArg.MID_SendCameraTlmData,
                                  tlm_msg)
            log_message_sent(appargs.CameraAppArg.MID_SendCameraTlmData, "TelemetryApp")
            
            # FlightLogic 데이터 (5 Hz)
            fl_data = msgstructure.MsgStructure()
            fl_msg = f"{CAMERA_STATUS},{VIDEO_COUNT},{DISK_USAGE:.1f}"
            msgstructure.send_msg(Main_Queue, fl_data,
                                  appargs.CameraAppArg.AppID,
                                  appargs.FlightLogicAppArg.AppID,
                                  appargs.CameraAppArg.MID_SendCameraFlightLogicData,
                                  fl_msg)
            log_message_sent(appargs.CameraAppArg.MID_SendCameraFlightLogicData, "FlightLogicApp")
            
            time.sleep(1)  # 1초마다 전송
            
        except Exception as e:
            log_app_error(f"Data transmission error: {e}")
            time.sleep(1)
    
    log_app_info("Camera data transmission thread ended")

# ──────────────────────────────
# 7. 메인 함수
# ──────────────────────────────
def cameraapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    """카메라 앱 메인 함수."""
    global CAMERAAPP_RUNSTATUS
    
    try:
        log_app_info("Cameraapp main function started")
        
        # 초기화
        if not cameraapp_init():
            log_app_error("Cameraapp initialization failed")
            return
        
        # 스레드 시작
        hk_thread = threading.Thread(target=send_hk, args=(Main_Queue,), daemon=True)
        status_thread = threading.Thread(target=update_camera_status, daemon=True)
        data_thread = threading.Thread(target=send_camera_data, args=(Main_Queue,), daemon=True)
        
        hk_thread.start()
        status_thread.start()
        data_thread.start()
        
        log_app_info("All cameraapp threads started")
        
        # 메인 루프
        while CAMERAAPP_RUNSTATUS:
            try:
                # 메시지 수신
                if Main_Pipe.poll(0.1):
                    recv_msg = Main_Pipe.recv()
                    command_handler(Main_Queue, recv_msg)
                    
            except Exception as e:
                log_app_error(f"Main loop error: {e}")
                time.sleep(0.1)
        
        # 종료
        log_app_info("Cameraapp main loop ended, starting cleanup")
        cameraapp_terminate()
        
        log_app_info("Cameraapp main function completed")
        
    except Exception as e:
        log_app_error(f"Cameraapp main function error: {e}")
        cameraapp_terminate() 