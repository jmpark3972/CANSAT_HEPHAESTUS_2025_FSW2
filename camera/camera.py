# Python FSW V2 Camera Module
# Author : Hyeon Lee  (HEPHAESTUS)
# Raspberry Pi Camera Module v3 Wide 지원

import os
import time
import threading
import subprocess
from datetime import datetime
from pathlib import Path
import signal
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

from lib import events, appargs

# ──────────────────────────────
# 0. 글로벌 변수
# ──────────────────────────────
CAMERA_PROCESS = None
CAMERA_ACTIVE = False
RECORDING_THREAD = None
STOP_RECORDING = False

# 카메라 설정
CAMERA_RESOLUTION = "1920x1080"  # Full HD
CAMERA_FPS = 30
RECORDING_INTERVAL = 5  # 5초 주기
VIDEO_DURATION = 5  # 5초 녹화
VIDEO_FORMAT = "h264"
VIDEO_QUALITY = "23"  # h264 품질 (낮을수록 좋은 품질)

# 저장 경로
VIDEO_DIR = "/home/pi/cansat_videos"
TEMP_DIR = "/tmp/camera_temp"
LOG_DIR = "/home/pi/cansat_logs"

# ──────────────────────────────
# 1. 로깅 함수
# ──────────────────────────────
def log_camera_event(event_type: str, message: str):
    """카메라 전용 로그 기록."""
    try:
        # 로그 디렉토리 생성
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        # 로그 파일명 (날짜별)
        log_file = os.path.join(LOG_DIR, f"camera_{datetime.now().strftime('%Y-%m-%d')}.log")
        
        # 타임스탬프와 함께 로그 기록
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        log_entry = f"[{timestamp}] [{event_type}] {message}\n"
        
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(log_entry)
            
    except Exception as e:
        # 로그 기록 실패 시 기본 이벤트 로그 사용
        safe_log(f"Log write failed: {e}", "error".upper(), True)

def log_recording_start():
    """녹화 시작 로그."""
    log_camera_event("RECORDING_START", "Video recording started")
    safe_log("Camera recording started", "info".upper(), True)

def log_recording_stop():
    """녹화 종료 로그."""
    log_camera_event("RECORDING_STOP", "Video recording stopped")
    safe_log("Camera recording stopped", "info".upper(), True)

def log_file_created(filename: str, filesize: int):
    """파일 생성 로그."""
    log_camera_event("FILE_CREATED", f"Video file created: {filename} ({filesize} bytes)")
    safe_log(f"Video file created: {filename}", "info".upper(), True)

def log_error(error_msg: str):
    """오류 로그."""
    log_camera_event("ERROR", error_msg)
    safe_log(error_msg, "error".upper(), True)

def log_warning(warning_msg: str):
    """경고 로그."""
    log_camera_event("WARNING", warning_msg)
    safe_log(warning_msg, "warning".upper(), True)

def log_info(info_msg: str):
    """정보 로그."""
    log_camera_event("INFO", info_msg)
    safe_log(info_msg, "info".upper(), True)

# ──────────────────────────────
# 2. 초기화 및 종료
# ──────────────────────────────
def init_camera():
    """카메라 초기화 및 디렉토리 생성."""
    try:
        log_info("Starting camera initialization")
        
        # 디렉토리 생성
        Path(VIDEO_DIR).mkdir(parents=True, exist_ok=True)
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        Path(LOG_DIR).mkdir(parents=True, exist_ok=True)
        
        log_info(f"Directories created - Video: {VIDEO_DIR}, Temp: {TEMP_DIR}, Log: {LOG_DIR}")
        
        # 카메라 하드웨어 확인
        if not check_camera_hardware():
            log_error("Camera hardware not detected")
            return False
        
        # 카메라 드라이버 확인
        if not check_camera_driver():
            log_error("Camera driver not available")
            return False
        
        # 디스크 공간 확인
        disk_usage = get_disk_usage()
        if disk_usage > 90:  # 90% 이상 사용 시 경고
            log_warning(f"Low disk space: {disk_usage:.1f}% used")
        else:
            log_info(f"Disk space available: {100-disk_usage:.1f}% free")
        
        log_info("Camera initialization complete")
        return True
        
    except Exception as e:
        log_error(f"Camera init error: {e}")
        return False

def check_camera_hardware():
    """카메라 하드웨어 연결 확인."""
    try:
        # vcgencmd로 카메라 연결 상태 확인
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = result.stdout.strip()
            log_info(f"Camera hardware status: {output}")
            return "detected=1" in output
        log_error("Hardware check command failed")
        return False
    except Exception as e:
        log_error(f"Hardware check error: {e}")
        return False

def check_camera_driver():
    """카메라 드라이버 확인."""
    try:
        # /dev/video0 존재 확인
        if os.path.exists('/dev/video0'):
            log_info("Camera driver available (/dev/video0)")
            return True
        else:
            log_error("Camera driver not found (/dev/video0)")
            return False
    except Exception as e:
        log_error(f"Driver check error: {e}")
        return False

def terminate_camera():
    """카메라 종료."""
    global CAMERA_ACTIVE, STOP_RECORDING
    
    try:
        log_info("Starting camera termination")
        
        # 녹화 중지
        if CAMERA_ACTIVE:
            log_info("Stopping active recording")
            stop_recording()
        
        # 임시 파일 정리
        cleanup_temp_files()
        
        log_info("Camera termination complete")
        return True
        
    except Exception as e:
        log_error(f"Camera termination error: {e}")
        return False

# ──────────────────────────────
# 3. 녹화 제어
# ──────────────────────────────
def start_recording():
    """녹화 시작."""
    global CAMERA_ACTIVE, RECORDING_THREAD, STOP_RECORDING
    
    try:
        if CAMERA_ACTIVE:
            log_warning("Recording already active")
            return True
        
        log_info("Starting video recording")
        
        CAMERA_ACTIVE = True
        STOP_RECORDING = False
        
        # 녹화 스레드 시작
        RECORDING_THREAD = threading.Thread(target=recording_worker, daemon=True)
        RECORDING_THREAD.start()
        
        log_recording_start()
        return True
        
    except Exception as e:
        log_error(f"Start recording error: {e}")
        CAMERA_ACTIVE = False
        return False

def stop_recording():
    """녹화 중지."""
    global CAMERA_ACTIVE, STOP_RECORDING
    
    try:
        if not CAMERA_ACTIVE:
            log_info("Recording not active")
            return True
        
        log_info("Stopping video recording")
        
        STOP_RECORDING = True
        CAMERA_ACTIVE = False
        
        # 녹화 스레드 종료 대기
        if RECORDING_THREAD and RECORDING_THREAD.is_alive():
            RECORDING_THREAD.join(timeout=10)
            if RECORDING_THREAD.is_alive():
                log_warning("Recording thread did not terminate gracefully")
        
        log_recording_stop()
        return True
        
    except Exception as e:
        log_error(f"Stop recording error: {e}")
        return False

def recording_worker():
    """녹화 워커 스레드."""
    log_info("Recording worker thread started")
    
    while not STOP_RECORDING and CAMERA_ACTIVE:
        try:
            record_single_video()
            time.sleep(RECORDING_INTERVAL)
        except Exception as e:
            log_error(f"Recording worker error: {e}")
            time.sleep(1)
    
    log_info("Recording worker thread ended")

def record_single_video():
    """단일 비디오 녹화 (안전한 방식)."""
    try:
        # 파일명 생성 (타임스탬프)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"video_{timestamp}.{VIDEO_FORMAT}"
        temp_filepath = os.path.join(TEMP_DIR, f"temp_{filename}")
        final_filepath = os.path.join(VIDEO_DIR, filename)
        
        log_info(f"Starting video recording: {filename}")
        
        # ffmpeg 명령어 구성
        cmd = [
            'ffmpeg',
            '-f', 'v4l2',
            '-video_size', CAMERA_RESOLUTION,
            '-framerate', str(CAMERA_FPS),
            '-i', '/dev/video0',
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', VIDEO_QUALITY,
            '-t', str(VIDEO_DURATION),
            '-y',  # 기존 파일 덮어쓰기
            temp_filepath  # 임시 파일에 먼저 저장
        ]
        
        # ffmpeg 실행
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 타임아웃 설정 (VIDEO_DURATION + 3초)
        try:
            stdout, stderr = process.communicate(timeout=VIDEO_DURATION + 3)
            
            if process.returncode == 0:
                # 임시 파일 존재 및 크기 확인
                if os.path.exists(temp_filepath):
                    temp_filesize = os.path.getsize(temp_filepath)
                    
                    # 최소 파일 크기 확인 (1MB 이상)
                    if temp_filesize > 1024 * 1024:
                        # 안전하게 최종 위치로 이동
                        try:
                            os.rename(temp_filepath, final_filepath)
                            log_file_created(filename, temp_filesize)
                            
                            # 디스크 공간 확인
                            disk_usage = get_disk_usage()
                            if disk_usage > 95:  # 95% 이상 사용 시 경고
                                log_warning(f"Critical disk space: {disk_usage:.1f}% used")
                            elif disk_usage > 85:  # 85% 이상 사용 시 경고
                                log_warning(f"Low disk space: {disk_usage:.1f}% used")
                                
                        except OSError as e:
                            log_error(f"File move failed: {e}")
                            # 이동 실패 시 임시 파일을 최종 위치로 복사
                            try:
                                import shutil
                                shutil.copy2(temp_filepath, final_filepath)
                                os.remove(temp_filepath)
                                log_file_created(filename, temp_filesize)
                            except Exception as copy_error:
                                log_error(f"File copy failed: {copy_error}")
                    else:
                        log_error(f"Video file too small: {temp_filesize} bytes")
                        if os.path.exists(temp_filepath):
                            os.remove(temp_filepath)
                else:
                    log_error(f"Temp video file not created: {temp_filepath}")
            else:
                log_error(f"FFmpeg failed: {stderr.decode()}")
                # 실패 시 임시 파일 정리
                if os.path.exists(temp_filepath):
                    os.remove(temp_filepath)
                
        except subprocess.TimeoutExpired:
            process.kill()
            log_error(f"Video recording timeout: {filename}")
            # 타임아웃 시 임시 파일 정리
            if os.path.exists(temp_filepath):
                os.remove(temp_filepath)
            
    except Exception as e:
        log_error(f"Record single video error: {e}")
        # 예외 발생 시 임시 파일 정리
        if 'temp_filepath' in locals() and os.path.exists(temp_filepath):
            try:
                os.remove(temp_filepath)
            except:
                pass

def cleanup_temp_files():
    """임시 파일 정리."""
    try:
        temp_files = list(Path(TEMP_DIR).glob('*'))
        if temp_files:
            for temp_file in temp_files:
                temp_file.unlink()
            log_info(f"Cleaned up {len(temp_files)} temporary files")
        else:
            log_info("No temporary files to clean")
    except Exception as e:
        log_error(f"Cleanup error: {e}")

# ──────────────────────────────
# 4. 상태 조회
# ──────────────────────────────
def get_video_count():
    """저장된 비디오 파일 수 조회."""
    try:
        video_files = list(Path(VIDEO_DIR).glob(f'*.{VIDEO_FORMAT}'))
        count = len(video_files)
        log_info(f"Video count: {count}")
        return count
    except Exception as e:
        log_error(f"Get video count error: {e}")
        return 0

def get_camera_status():
    """카메라 상태 조회."""
    status = "IDLE"
    if CAMERA_ACTIVE:
        status = "RECORDING"
    elif CAMERA_PROCESS:
        status = "PROCESSING"
    
    log_info(f"Camera status: {status}")
    return status

def get_disk_usage():
    """디스크 사용량 조회 (%)."""
    try:
        statvfs = os.statvfs(VIDEO_DIR)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bavail * statvfs.f_frsize
        used_percent = ((total - free) / total) * 100
        return used_percent
    except Exception as e:
        log_error(f"Disk usage check error: {e}")
        return 0.0 