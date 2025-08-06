#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 카메라 모듈
Camera Module V2 (CSI) 지원
이중 로깅 시스템 통합
"""

import os
import sys
import time
import subprocess
import threading
import signal
import atexit
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging, appargs
from camera import camera_config

# 전역 변수
_camera_process: Optional[subprocess.Popen] = None
_recording_active: bool = False
_video_count: int = 0
_camera_status: str = "IDLE"
_recording_thread: Optional[threading.Thread] = None
_status_thread: Optional[threading.Thread] = None
_termination_requested: bool = False

# 설정 (camera_config에서 가져옴)
VIDEO_DIR = camera_config.VIDEO_DIR
TEMP_DIR = camera_config.VIDEO_TEMP_DIR
LOG_DIR = camera_config.VIDEO_LOG_DIR
DUAL_VIDEO_DIR = camera_config.DUAL_VIDEO_DIR
DUAL_TEMP_DIR = camera_config.DUAL_VIDEO_TEMP_DIR
DUAL_LOG_DIR = camera_config.DUAL_VIDEO_LOG_DIR
VIDEO_DURATION = camera_config.RECORDING_DURATION
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
    """필요한 디렉토리 생성 (이중 로깅 지원)"""
    try:
        # 메인 디렉토리 생성
        os.makedirs(VIDEO_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)
        os.makedirs(LOG_DIR, exist_ok=True)
        safe_log("메인 디렉토리 생성 완료", "INFO", True)
        
        # 서브 SD 카드 디렉토리 생성 (이중 로깅)
        if os.path.exists("/mnt/log_sd"):
            os.makedirs(DUAL_VIDEO_DIR, exist_ok=True)
            os.makedirs(DUAL_TEMP_DIR, exist_ok=True)
            os.makedirs(DUAL_LOG_DIR, exist_ok=True)
            safe_log("서브 SD 디렉토리 생성 완료 (이중 로깅 활성화)", "INFO", True)
        else:
            safe_log("서브 SD 카드가 마운트되지 않음 (단일 로깅 모드)", "WARNING", True)
        
        return True
    except Exception as e:
        safe_log(f"디렉토리 생성 실패: {e}", "ERROR", True)
        return False

def check_camera_hardware() -> bool:
    """카메라 하드웨어 확인 (Pi Camera v2 호환)"""
    try:
        # 방법 1: vcgencmd 사용 (v2에서도 동일)
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'detected=1' in result.stdout:
            safe_log("카메라 하드웨어 감지됨 (vcgencmd)", "INFO", True)
            return True
        
        # 방법 2: /proc/device-tree 확인 (v2용 경로)
        camera_node_v1 = Path('/proc/device-tree/soc/csi1')
        camera_node_v2 = Path('/proc/device-tree/soc/csi0')
        if camera_node_v1.exists() or camera_node_v2.exists():
            safe_log("카메라 하드웨어 감지됨 (device-tree)", "INFO", True)
            return True
        
        # 방법 3: dmesg에서 카메라 관련 메시지 확인
        result = subprocess.run(['dmesg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and ('camera' in result.stdout.lower() or 'csi' in result.stdout.lower()):
            safe_log("카메라 하드웨어 감지됨 (dmesg)", "INFO", True)
            return True
        
        # 방법 4: cam 명령어로 카메라 목록 확인 (libcamera-tools)
        try:
            result = subprocess.run(['cam', '-l'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and 'Available cameras:' in result.stdout:
                # 카메라가 감지되었는지 확인
                lines = result.stdout.strip().split('\n')
                if len(lines) > 1:  # "Available cameras:" 외에 다른 라인이 있으면 카메라가 있음
                    safe_log("카메라 하드웨어 감지됨 (cam)", "INFO", True)
                    return True
        except FileNotFoundError:
            pass
        
        # 방법 5: libcamera-hello 테스트 (v2 호환)
        try:
            result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                safe_log("카메라 하드웨어 감지됨 (libcamera)", "INFO", True)
                return True
        except FileNotFoundError:
            pass
        
        # 방법 6: raspistill 테스트 (v2 전용)
        try:
            result = subprocess.run(['raspistill', '--help'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                safe_log("카메라 하드웨어 감지됨 (raspistill)", "INFO", True)
                return True
        except FileNotFoundError:
            pass
        
        safe_log("카메라 하드웨어 감지되지 않음", "WARNING", True)
        safe_log("Pi Camera v2 설정 확인:", "INFO", True)
        safe_log("1. Pi Camera v2가 올바르게 연결되었는지 확인", "INFO", True)
        safe_log("2. CSI 케이블이 제대로 연결되었는지 확인", "INFO", True)
        safe_log("3. /boot/config.txt에 다음 설정 확인:", "INFO", True)
        safe_log("   camera_auto_detect=1", "INFO", True)
        safe_log("   또는", "INFO", True)
        safe_log("   dtoverlay=ov5647", "INFO", True)
        safe_log("4. 시스템 재부팅 후 다시 시도", "INFO", True)
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
    """FFmpeg 설치 확인 (cam 명령어 사용 시에는 선택사항)"""
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            safe_log("FFmpeg 설치 확인됨", "INFO", True)
            return True
        else:
            safe_log("FFmpeg 설치되지 않음 (cam 명령어 사용으로 대체 가능)", "WARNING", True)
            return False
    except Exception as e:
        safe_log(f"FFmpeg 확인 오류: {e} (cam 명령어 사용으로 대체 가능)", "WARNING", True)
        return False

def init_camera() -> Optional[subprocess.Popen]:
    """카메라 초기화"""
    global _camera_process, _recording_active, _video_count, _camera_status
    
    try:
        safe_log("카메라 초기화 시작", "INFO", True)
        
        # 디렉토리 생성
        if not ensure_directories():
            safe_log("디렉토리 생성 실패로 카메라 초기화 중단", "ERROR", True)
            return None
        
        # 하드웨어 확인 (경고로 처리하고 계속 진행)
        hardware_ok = check_camera_hardware()
        if not hardware_ok:
            safe_log("카메라 하드웨어 감지 실패, 하지만 계속 진행", "WARNING", True)
        
        # 드라이버 확인 (경고로 처리하고 계속 진행)
        driver_ok = check_camera_driver()
        if not driver_ok:
            safe_log("카메라 드라이버 감지 실패, 하지만 계속 진행", "WARNING", True)
        
        # FFmpeg 확인 (경고로 처리하고 계속 진행)
        ffmpeg_ok = check_ffmpeg()
        if not ffmpeg_ok:
            safe_log("FFmpeg 설치 확인 실패, 하지만 cam 명령어로 계속 진행", "WARNING", True)
        
        # 상태 초기화
        _recording_active = False
        _video_count = 0
        _camera_status = "READY" if (hardware_ok and driver_ok) else "LIMITED"
        
        if _camera_status == "LIMITED":
            safe_log("카메라가 제한된 모드로 초기화됨 (하드웨어/드라이버 문제)", "WARNING", True)
        else:
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
    """단일 비디오 녹화 (cam 명령어 사용, 이중 로깅 지원)"""
    global _video_count
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_filename = f"video_{timestamp}.mp4"
        final_path = os.path.join(VIDEO_DIR, final_filename)
        
        # cam 명령어로 비디오 녹화
        cam_cmd = [
            'cam',
            '-c', '0',  # 카메라 0번 사용
            '-C', str(duration),  # 지정된 시간만큼 캡처
            '-F', final_path,  # 파일로 저장
            '-s', 'width=1920,height=1080,pixelformat=NV12,role=video'  # 스트림 설정
        ]
        
        safe_log(f"녹화 시작: {duration}초 (cam)", "INFO", True)
        
        # cam 명령어 실행
        process = subprocess.Popen(cam_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        try:
            stdout, stderr = process.communicate(timeout=FFMPEG_TIMEOUT)
            
            if process.returncode == 0:
                if os.path.exists(final_path):
                    _video_count += 1
                    safe_log(f"녹화 완료: {final_filename}", "INFO", True)
                    
                    # 이중 로깅: 서브 SD 카드에 복사
                    if os.path.exists("/mnt/log_sd"):
                        try:
                            dual_path = os.path.join(DUAL_VIDEO_DIR, final_filename)
                            shutil.copy2(final_path, dual_path)
                            safe_log(f"서브 SD에 복사 완료: {dual_path}", "INFO", True)
                        except Exception as e:
                            safe_log(f"서브 SD 복사 실패: {e}", "WARNING", True)
                    
                    return True
                else:
                    safe_log("비디오 파일이 생성되지 않음", "ERROR", True)
                    return False
            else:
                safe_log(f"cam 명령어 오류: {stderr.decode()}", "ERROR", True)
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            safe_log("cam 명령어 타임아웃", "ERROR", True)
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