#!/usr/bin/env python3
"""
Camera Module for CANSAT FSW
Raspberry Pi Camera Module v3 Wide 지원
"""

import os
import sys
import time
import subprocess
import threading
import signal
import atexit
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging, appargs

# 전역 변수
_camera_process: Optional[subprocess.Popen] = None
_recording_active: bool = False
_video_count: int = 0
_camera_status: str = "IDLE"
_recording_thread: Optional[threading.Thread] = None
_status_thread: Optional[threading.Thread] = None
_termination_requested: bool = False

# 설정
VIDEO_DIR = "/home/pi/cansat_videos"
TEMP_DIR = "/tmp/cansat_camera"
LOG_DIR = "/home/pi/cansat_logs"
VIDEO_DURATION = 5  # 5초 단위로 녹화
FFMPEG_TIMEOUT = 30  # FFmpeg 타임아웃 (초)

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수"""
    try:
        formatted_message = f"[Camera] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        print(f"[Camera] 로깅 실패: {e}")
        print(f"[Camera] 원본 메시지: {message}")

def ensure_directories():
    """필요한 디렉토리 생성"""
    try:
        os.makedirs(VIDEO_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        safe_log("디렉토리 생성 완료", "INFO", True)
        return True
    except Exception as e:
        safe_log(f"디렉토리 생성 실패: {e}", "ERROR", True)
        return False

def check_camera_hardware() -> bool:
    """카메라 하드웨어 확인"""
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'detected=1' in result.stdout:
            safe_log("카메라 하드웨어 감지됨", "INFO", True)
            return True
        else:
            safe_log("카메라 하드웨어 감지되지 않음", "ERROR", True)
            return False
    except Exception as e:
        safe_log(f"카메라 하드웨어 확인 오류: {e}", "ERROR", True)
        return False

def check_camera_driver() -> bool:
    """카메라 드라이버 확인"""
    try:
        video_devices = list(Path('/dev').glob('video*'))
        if video_devices:
            safe_log(f"비디오 디바이스 발견: {[str(d) for d in video_devices]}", "INFO", True)
            return True
        else:
            safe_log("비디오 디바이스 없음", "ERROR", True)
            return False
    except Exception as e:
        safe_log(f"카메라 드라이버 확인 오류: {e}", "ERROR", True)
        return False

def check_ffmpeg() -> bool:
    """FFmpeg 설치 확인"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            safe_log("FFmpeg 설치 확인됨", "INFO", True)
            return True
        else:
            safe_log("FFmpeg 설치되지 않음", "ERROR", True)
            return False
    except Exception as e:
        safe_log(f"FFmpeg 확인 오류: {e}", "ERROR", True)
        return False

def init_camera() -> Optional[subprocess.Popen]:
    """카메라 초기화"""
    global _camera_process, _recording_active, _video_count, _camera_status
    
    try:
        safe_log("카메라 초기화 시작", "INFO", True)
        
        # 디렉토리 생성
        if not ensure_directories():
            return None
        
        # 하드웨어 확인
        if not check_camera_hardware():
            return None
        
        # 드라이버 확인
        if not check_camera_driver():
            return None
        
        # FFmpeg 확인
        if not check_ffmpeg():
            return None
        
        # 상태 초기화
        _recording_active = False
        _video_count = 0
        _camera_status = "READY"
        
        safe_log("카메라 초기화 완료", "INFO", True)
        return subprocess.Popen(['echo', 'camera_ready'], stdout=subprocess.PIPE)
        
    except Exception as e:
        safe_log(f"카메라 초기화 오류: {e}", "ERROR", True)
        return None

def terminate_camera():
    """카메라 종료"""
    global _camera_process, _recording_active, _termination_requested
    
    try:
        safe_log("카메라 종료 시작", "INFO", True)
        
        _termination_requested = True
        _recording_active = False
        
        # 녹화 스레드 종료 대기
        if _recording_thread and _recording_thread.is_alive():
            _recording_thread.join(timeout=5)
        
        # 상태 스레드 종료 대기
        if _status_thread and _status_thread.is_alive():
            _status_thread.join(timeout=5)
        
        # 카메라 프로세스 종료
        if _camera_process:
            _camera_process.terminate()
            _camera_process.wait(timeout=5)
        
        safe_log("카메라 종료 완료", "INFO", True)
        
    except Exception as e:
        safe_log(f"카메라 종료 오류: {e}", "ERROR", True)

def record_single_video(camera_process: subprocess.Popen, duration: int = VIDEO_DURATION) -> bool:
    """단일 비디오 녹화"""
    global _video_count
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"temp_{timestamp}.mp4"
        final_filename = f"video_{timestamp}.mp4"
        
        temp_path = os.path.join(TEMP_DIR, temp_filename)
        final_path = os.path.join(VIDEO_DIR, final_filename)
        
        # FFmpeg 명령어 구성
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'v4l2',
            '-video_size', '1920x1080',
            '-framerate', '30',
            '-i', '/dev/video0',
            '-t', str(duration),
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-y',  # 기존 파일 덮어쓰기
            temp_path
        ]
        
        safe_log(f"녹화 시작: {duration}초", "INFO", True)
        
        # FFmpeg 실행
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            stdout, stderr = process.communicate(timeout=FFMPEG_TIMEOUT)
            
            if process.returncode == 0:
                # 임시 파일을 최종 위치로 이동
                if os.path.exists(temp_path):
                    os.rename(temp_path, final_path)
                    _video_count += 1
                    safe_log(f"녹화 완료: {final_filename}", "INFO", True)
                    return True
                else:
                    safe_log("임시 파일이 생성되지 않음", "ERROR", True)
                    return False
            else:
                safe_log(f"FFmpeg 오류: {stderr.decode()}", "ERROR", True)
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            safe_log("FFmpeg 타임아웃", "ERROR", True)
            return False
            
    except Exception as e:
        safe_log(f"녹화 오류: {e}", "ERROR", True)
        return False

def get_camera_status(camera_process: subprocess.Popen) -> str:
    """카메라 상태 반환"""
    global _camera_status, _recording_active
    return _camera_status

def get_disk_usage() -> float:
    """디스크 사용량 반환 (%)"""
    try:
        result = subprocess.run(['df', VIDEO_DIR], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    usage_str = parts[4].replace('%', '')
                    return float(usage_str)
        return 0.0
    except Exception as e:
        safe_log(f"디스크 사용량 확인 오류: {e}", "ERROR", True)
        return 0.0

def get_video_count() -> int:
    """녹화된 비디오 파일 수 반환"""
    global _video_count
    return _video_count

# 종료 시 정리
atexit.register(terminate_camera)
signal.signal(signal.SIGTERM, lambda signum, frame: terminate_camera())
signal.signal(signal.SIGINT, lambda signum, frame: terminate_camera()) 