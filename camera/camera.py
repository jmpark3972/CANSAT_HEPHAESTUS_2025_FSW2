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

# ──────────────────────────────
# 1. 초기화 및 종료
# ──────────────────────────────
def init_camera():
    """카메라 초기화 및 디렉토리 생성."""
    try:
        # 디렉토리 생성
        Path(VIDEO_DIR).mkdir(parents=True, exist_ok=True)
        Path(TEMP_DIR).mkdir(parents=True, exist_ok=True)
        
        # 카메라 하드웨어 확인
        if not check_camera_hardware():
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           "Camera hardware not detected")
            return False
        
        # 카메라 드라이버 확인
        if not check_camera_driver():
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           "Camera driver not available")
            return False
        
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.info,
                       "Camera initialization complete")
        return True
        
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Camera init error: {e}")
        return False

def check_camera_hardware():
    """카메라 하드웨어 연결 확인."""
    try:
        # vcgencmd로 카메라 연결 상태 확인
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            output = result.stdout.strip()
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.info,
                           f"Camera hardware status: {output}")
            return "detected=1" in output
        return False
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Hardware check error: {e}")
        return False

def check_camera_driver():
    """카메라 드라이버 확인."""
    try:
        # /dev/video0 존재 확인
        if os.path.exists('/dev/video0'):
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.info,
                           "Camera driver available")
            return True
        else:
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           "Camera driver not found")
            return False
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Driver check error: {e}")
        return False

def terminate_camera():
    """카메라 종료 및 정리."""
    global CAMERA_PROCESS, CAMERA_ACTIVE, STOP_RECORDING
    
    try:
        CAMERA_ACTIVE = False
        STOP_RECORDING = True
        
        # 녹화 스레드 종료 대기
        if RECORDING_THREAD and RECORDING_THREAD.is_alive():
            RECORDING_THREAD.join(timeout=10)
        
        # 실행 중인 프로세스 종료
        if CAMERA_PROCESS:
            try:
                CAMERA_PROCESS.terminate()
                CAMERA_PROCESS.wait(timeout=5)
            except subprocess.TimeoutExpired:
                CAMERA_PROCESS.kill()
            except Exception as e:
                events.LogEvent(appargs.CameraAppArg.AppName,
                               events.EventType.error,
                               f"Process termination error: {e}")
        
        # 임시 파일 정리
        cleanup_temp_files()
        
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.info,
                       "Camera termination complete")
        
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Termination error: {e}")

# ──────────────────────────────
# 2. 녹화 기능
# ──────────────────────────────
def start_recording():
    """카메라 녹화 시작."""
    global CAMERA_ACTIVE, RECORDING_THREAD, STOP_RECORDING
    
    if CAMERA_ACTIVE:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.warning,
                       "Camera already active")
        return False
    
    try:
        CAMERA_ACTIVE = True
        STOP_RECORDING = False
        
        # 녹화 스레드 시작
        RECORDING_THREAD = threading.Thread(target=recording_worker, daemon=True)
        RECORDING_THREAD.start()
        
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.info,
                       "Camera recording started")
        return True
        
    except Exception as e:
        CAMERA_ACTIVE = False
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Start recording error: {e}")
        return False

def stop_recording():
    """카메라 녹화 중지."""
    global CAMERA_ACTIVE, STOP_RECORDING
    
    try:
        CAMERA_ACTIVE = False
        STOP_RECORDING = True
        
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.info,
                       "Camera recording stopped")
        return True
        
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Stop recording error: {e}")
        return False

def recording_worker():
    """녹화 워커 스레드."""
    global CAMERA_PROCESS, STOP_RECORDING
    
    while CAMERA_ACTIVE and not STOP_RECORDING:
        try:
            # 5초 주기로 녹화
            record_single_video()
            time.sleep(RECORDING_INTERVAL)
            
        except Exception as e:
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           f"Recording worker error: {e}")
            time.sleep(1)  # 에러 시 잠시 대기

def record_single_video():
    """단일 비디오 녹화."""
    global CAMERA_PROCESS
    
    try:
        # 타임스탬프로 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_file = f"{TEMP_DIR}/temp_{timestamp}.{VIDEO_FORMAT}"
        final_file = f"{VIDEO_DIR}/video_{timestamp}.{VIDEO_FORMAT}"
        
        # ffmpeg로 녹화
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
            '-y',  # 덮어쓰기
            temp_file
        ]
        
        # 프로세스 실행
        CAMERA_PROCESS = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid  # 프로세스 그룹 생성
        )
        
        # 녹화 완료 대기
        CAMERA_PROCESS.wait(timeout=VIDEO_DURATION + 5)
        
        # 파일 이동
        if os.path.exists(temp_file):
            os.rename(temp_file, final_file)
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.info,
                           f"Video saved: {final_file}")
        else:
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           "Video file not created")
        
    except subprocess.TimeoutExpired:
        # 타임아웃 시 프로세스 강제 종료
        if CAMERA_PROCESS:
            try:
                os.killpg(os.getpgid(CAMERA_PROCESS.pid), signal.SIGKILL)
            except:
                pass
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       "Video recording timeout")
        
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Video recording error: {e}")

# ──────────────────────────────
# 3. 유틸리티 함수
# ──────────────────────────────
def cleanup_temp_files():
    """임시 파일 정리."""
    try:
        for file in Path(TEMP_DIR).glob("*"):
            try:
                file.unlink()
            except:
                pass
    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                       events.EventType.error,
                       f"Cleanup error: {e}")

def get_video_count():
    """저장된 비디오 파일 수 반환."""
    try:
        return len(list(Path(VIDEO_DIR).glob(f"*.{VIDEO_FORMAT}")))
    except:
        return 0

def get_camera_status():
    """카메라 상태 반환."""
    return {
        'active': CAMERA_ACTIVE,
        'video_count': get_video_count(),
        'recording_thread_alive': RECORDING_THREAD.is_alive() if RECORDING_THREAD else False
    }

def get_disk_usage():
    """디스크 사용량 확인."""
    try:
        stat = os.statvfs(VIDEO_DIR)
        free_space = stat.f_frsize * stat.f_bavail
        total_space = stat.f_frsize * stat.f_blocks
        used_space = total_space - free_space
        usage_percent = (used_space / total_space) * 100
        
        return {
            'free_gb': free_space / (1024**3),
            'total_gb': total_space / (1024**3),
            'usage_percent': usage_percent
        }
    except:
        return {'free_gb': 0, 'total_gb': 0, 'usage_percent': 0} 