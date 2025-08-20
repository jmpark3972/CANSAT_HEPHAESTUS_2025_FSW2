# Python FSW V2 Thermo-Camera App
# Author : Hyeon Lee  (HEPHAESTUS)

from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[ThermalCamera] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[ThermalCamera] 로깅 실패: {e}")
        print(f"[ThermalCamera] 원본 메시지: {message}")

from lib import appargs, msgstructure, logging, prevstate
import signal, threading, time, os, csv
from multiprocessing import Queue, connection
from datetime import datetime

from thermal_camera import thermo_camera as tcam

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
THERMOCAMAPP_RUNSTATUS = True

# Thermal camera data
THERMAL_AVG = 0.0
THERMAL_MIN = 0.0
THERMAL_MAX = 0.0
THERMAL_FULL_DATA = None  # 738개 픽셀 전체 데이터

# ──────────────────────────────
# 1. 강화된 로깅 시스템
# ──────────────────────────────
LOG_DIR = "logs/thermal_camera"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로들
THERMAL_DATA_LOG_PATH = os.path.join(LOG_DIR, "thermal_data.csv")
THERMAL_STATS_LOG_PATH = os.path.join(LOG_DIR, "thermal_stats.csv")
THERMAL_PIXEL_LOG_PATH = os.path.join(LOG_DIR, "thermal_pixels.csv")

# CSV 헤더 정의
THERMAL_DATA_HEADERS = ["timestamp", "epoch", "min_temp", "max_temp", "avg_temp", "pixel_count"]
THERMAL_STATS_HEADERS = ["timestamp", "epoch", "min_temp", "max_temp", "avg_temp", "std_dev", "hot_pixels", "cold_pixels"]
THERMAL_PIXEL_HEADERS = ["timestamp", "epoch", "pixel_index", "row", "col", "temperature"]

def log_thermal_data(min_temp: float, max_temp: float, avg_temp: float, temps: list):
    """열화상 데이터를 CSV로 로깅"""
    try:
        timestamp = datetime.now().isoformat()
        epoch = time.time()
        
        # 기본 데이터 로깅
        with open(THERMAL_DATA_LOG_PATH, 'a', newline='') as f:
            writer = csv.writer(f)
            if os.path.getsize(THERMAL_DATA_LOG_PATH) == 0:  # 파일이 비어있으면 헤더 추가
                writer.writerow(THERMAL_DATA_HEADERS)
            writer.writerow([timestamp, epoch, min_temp, max_temp, avg_temp, len(temps)])
        
        # 통계 데이터 로깅
        if temps:
            import numpy as np
            temp_array = np.array(temps)
            std_dev = np.std(temp_array)
            hot_pixels = np.sum(temp_array > avg_temp + std_dev)
            cold_pixels = np.sum(temp_array < avg_temp - std_dev)
            
            with open(THERMAL_STATS_LOG_PATH, 'a', newline='') as f:
                writer = csv.writer(f)
                if os.path.getsize(THERMAL_STATS_LOG_PATH) == 0:
                    writer.writerow(THERMAL_STATS_HEADERS)
                writer.writerow([timestamp, epoch, min_temp, max_temp, avg_temp, std_dev, hot_pixels, cold_pixels])
        
        # 개별 픽셀 데이터 로깅 (선택적 - 용량이 클 수 있음)
        # 파일 크기 제한: 100MB (약 50만 행)
        if temps and len(temps) == 768:  # 24x32 = 768 픽셀
            file_size = os.path.getsize(THERMAL_PIXEL_LOG_PATH) if os.path.exists(THERMAL_PIXEL_LOG_PATH) else 0
            max_size = 100 * 1024 * 1024  # 100MB
            
            if file_size < max_size:
                with open(THERMAL_PIXEL_LOG_PATH, 'a', newline='') as f:
                    writer = csv.writer(f)
                    if file_size == 0:  # 파일이 비어있으면 헤더 추가
                        writer.writerow(THERMAL_PIXEL_HEADERS)
                    
                    for i, temp in enumerate(temps):
                        row = i // 32  # 32열
                        col = i % 32   # 32행
                        writer.writerow([timestamp, epoch, i, row, col, temp])
            else:
                safe_log("Thermal pixel log file size limit reached (100MB)", "WARNING", True)
                    
    except Exception as e:
        safe_log(f"Thermal data logging error: {e}", "ERROR", True)

def get_log_stats():
    """로그 파일 통계 반환"""
    try:
        stats = {}
        for log_file in [THERMAL_DATA_LOG_PATH, THERMAL_STATS_LOG_PATH, THERMAL_PIXEL_LOG_PATH]:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    stats[os.path.basename(log_file)] = len(lines) - 1  # 헤더 제외
                
                # 파일 크기 정보 추가
                file_size = os.path.getsize(log_file)
                stats[f"{os.path.basename(log_file)}_size_mb"] = round(file_size / (1024 * 1024), 2)
            else:
                stats[os.path.basename(log_file)] = 0
                stats[f"{os.path.basename(log_file)}_size_mb"] = 0
        return stats
    except Exception as e:
        safe_log(f"Log stats error: {e}", "ERROR", True)
        return {}

def backup_logs():
    """로그 파일 백업"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(LOG_DIR, f"backup_{timestamp}")
        os.makedirs(backup_dir, exist_ok=True)
        
        for log_file in [THERMAL_DATA_LOG_PATH, THERMAL_STATS_LOG_PATH, THERMAL_PIXEL_LOG_PATH]:
            if os.path.exists(log_file):
                import shutil
                backup_path = os.path.join(backup_dir, os.path.basename(log_file))
                shutil.copy2(log_file, backup_path)
                safe_log(f"Backed up {log_file} to {backup_path}", "INFO", True)
        
        return backup_dir
    except Exception as e:
        safe_log(f"Log backup error: {e}", "ERROR", True)
        return None

# ──────────────────────────────
# 2. 메시지 핸들러
# ──────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure):
    global THERMOCAMAPP_RUNSTATUS

    # (1) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        safe_log("THERMOCAMAPP TERMINATION DETECTED", "info".upper(), True)
        THERMOCAMAPP_RUNSTATUS = False
        return

    # (2) 로그 통계 요청 (새로운 명령어)
    elif recv_msg.MsgID == appargs.ThermalcameraAppArg.MID_GetLogStats:
        stats = get_log_stats()
        stats_msg = f"Log stats: {stats}"
        safe_log(stats_msg, "INFO", True)
        
        # HK 앱으로 로그 통계 전송
        hk_msg = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, hk_msg,
                              appargs.ThermalcameraAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermalcameraAppArg.MID_SendLogStats,
                              str(stats))
        return

    # (3) 기타 커맨드는 필요 시 확장
    safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)

# ──────────────────────────────
# 2. HK 송신 스레드
# ──────────────────────────────
def send_hk(Main_Queue: Queue):
    while THERMOCAMAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, hk,
                              appargs.ThermalcameraAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermalcameraAppArg.MID_SendHK,
                              str(THERMOCAMAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────
# 3. 초기화 / 종료
# ──────────────────────────────
def thermocamapp_init():
    """센서 초기화·시리얼 확인."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        safe_log("Initializing thermocamapp", "info".upper(), True)

        # MLX90640 start (기본 2 Hz)
        i2c, cam = tcam.init_thermal_camera()
        
        safe_log("Thermocamapp initialization complete", "info".upper(), True)
        return i2c, cam

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None

def thermocamapp_terminate(i2c):
    """스레드 합류 후 I²C 종료."""
    global THERMOCAMAPP_RUNSTATUS
    THERMOCAMAPP_RUNSTATUS = False

    safe_log("Terminating thermocamapp", "info".upper(), True)

    tcam.terminate_cam(i2c)

    for t in thread_dict.values():
        t.join()

    safe_log("Thermocamapp termination complete", "info".upper(), True)

# ──────────────────────────────
# 4. 센서 읽기 / 데이터 송신
# ──────────────────────────────
MIN_T, MAX_T, AVG_T = 0.0, 0.0, 0.0

def read_cam_data(cam):
    """MLX90640 데이터 읽기 스레드."""
    global THERMOCAMAPP_RUNSTATUS, THERMAL_AVG, THERMAL_MIN, THERMAL_MAX, THERMAL_FULL_DATA
    while THERMOCAMAPP_RUNSTATUS:
        try:
            # channel_guard를 사용하여 안전하게 센서 읽기
            data = tcam.read_cam(cam)
            if data and len(data) >= 4:  # min, max, avg, temps 순서
                THERMAL_MIN, THERMAL_MAX, THERMAL_AVG, temps = data
                THERMAL_FULL_DATA = temps  # 768개 픽셀 데이터
                
                # 상세 로깅 (2Hz로 실행되므로 로그 파일이 커질 수 있음)
                log_thermal_data(THERMAL_MIN, THERMAL_MAX, THERMAL_AVG, temps)
                
                safe_log(f"Thermal data: min={THERMAL_MIN:.1f}°C, max={THERMAL_MAX:.1f}°C, avg={THERMAL_AVG:.1f}°C, pixels={len(temps)}", "DEBUG", False)
                
        except Exception as e:
            safe_log(f"Thermal camera read error: {e}", "error".upper(), True)
        time.sleep(0.5)  # 2 Hz

def send_cam_data(Main_Queue: Queue):
    global THERMAL_AVG, THERMAL_MIN, THERMAL_MAX
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while THERMOCAMAPP_RUNSTATUS:
        try:
            # None 값 체크 및 기본값 설정
            avg_val = THERMAL_AVG if THERMAL_AVG is not None else 0.0
            min_val = THERMAL_MIN if THERMAL_MIN is not None else 0.0
            max_val = THERMAL_MAX if THERMAL_MAX is not None else 0.0
            
            # Flightlogic 10 Hz
            msgstructure.send_msg(Main_Queue, fl_msg,
                                  appargs.ThermalcameraAppArg.AppID,
                                  appargs.FlightlogicAppArg.AppID,
                                  appargs.ThermalcameraAppArg.MID_SendCamFlightLogicData,
                                  f"{avg_val:.2f},{min_val:.2f},{max_val:.2f}")

            if cnt > 10:  # 1 Hz telemetry
                msgstructure.send_msg(Main_Queue, tlm_msg,
                                      appargs.ThermalcameraAppArg.AppID,
                                      appargs.CommAppArg.AppID,
                                      appargs.ThermalcameraAppArg.MID_SendCamTlmData,
                                      f"{avg_val:.2f},{min_val:.2f},{max_val:.2f}")
                cnt = 0

            cnt += 1
            time.sleep(0.1)  # 10 Hz
            
        except Exception as e:
            safe_log(f"send_cam_data error: {e}", "ERROR", True)
            time.sleep(0.1)  # 오류 시에도 계속 실행

# ──────────────────────────────
# 5. 메인 엔트리
# ──────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    try:
        target(*args)
    except Exception as e:
        safe_log(f"Thread {name} error: {e}", "error".upper(), True)
    return None

def thermocamapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global THERMOCAMAPP_RUNSTATUS
    THERMOCAMAPP_RUNSTATUS = True

    i2c, cam = thermocamapp_init()
    if cam is None:
        return  # 초기화 실패 시 바로 종료

    # 스레드 생성
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(Main_Queue,),
                                         name="HKSender_Thread", daemon=True)
    thread_dict["READ"] = threading.Thread(target=read_cam_data, args=(cam,),
                                           name="ReadCamData_Thread", daemon=True)
    thread_dict["SEND"] = threading.Thread(target=send_cam_data, args=(Main_Queue,),
                                           name="SendCamData_Thread", daemon=True)

    for t in thread_dict.values():
        t.start()

    try:
        while THERMOCAMAPP_RUNSTATUS:
            # Non-blocking receive with timeout
            if Main_Pipe.poll(1.0):  # 1초 타임아웃
                try:
                    raw = Main_Pipe.recv()
                except Exception as e:
                    # 에러 시 루프 계속
                    safe_log(f"메시지 수신 오류: {e}", "WARNING")
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            m = raw

            target_apps = (appargs.ThermalcameraAppArg.AppID, appargs.MainAppArg.AppID)
            if m.receiver_app in target_apps:
                command_handler(Main_Queue, m)
            else:
                safe_log("Receiver MID mismatch", "error".upper(), True)

    except Exception as e:
        safe_log(f"thermocamapp error: {e}", "error".upper(), True)
        THERMOCAMAPP_RUNSTATUS = False

    thermocamapp_terminate(i2c)
