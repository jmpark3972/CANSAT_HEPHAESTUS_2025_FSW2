#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 카메라 설정
Camera Module V2 (CSI) 지원
이중 로깅 시스템 통합
"""

import os
from lib import config

# 카메라 하드웨어 설정
CAMERA_MODULE = "Camera Module V2"  # CSI 카메라
CAMERA_INTERFACE = "CSI"  # Camera Serial Interface

# 비디오 설정
VIDEO_DIR = "logs/cansat_videos"
VIDEO_TEMP_DIR = "logs/cansat_camera_temp"
VIDEO_LOG_DIR = "logs/cansat_camera_logs"

# 이중 로깅 설정
DUAL_VIDEO_DIR = "/mnt/log_sd/cansat_videos"
DUAL_VIDEO_TEMP_DIR = "/mnt/log_sd/cansat_camera_temp"
DUAL_VIDEO_LOG_DIR = "/mnt/log_sd/cansat_camera_logs"

# 비디오 품질 설정
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_BITRATE = "5000k"
VIDEO_FORMAT = "mp4"

# 녹화 설정
RECORDING_DURATION = 60  # 초
MAX_VIDEO_SIZE_MB = 100  # MB

# 카메라 감지 설정
CAMERA_DETECTION_METHODS = [
    "dmesg",      # 커널 메시지 확인
    "device_tree", # 디바이스 트리 확인
    "libcamera",   # libcamera 도구 확인
    "video_devices" # /dev/video* 확인
]

# libcamera 설정
LIBCAMERA_CMD = "cam"
LIBCAMERA_OPTIONS = [
    "--width", str(VIDEO_WIDTH),
    "--height", str(VIDEO_HEIGHT),
    "--framerate", str(VIDEO_FPS),
    "--codec", "h264",
    "--bitrate", VIDEO_BITRATE
]

# FFmpeg 설정 (대체 옵션)
FFMPEG_CMD = "ffmpeg"
FFMPEG_OPTIONS = [
    "-f", "v4l2",
    "-video_size", f"{VIDEO_WIDTH}x{VIDEO_HEIGHT}",
    "-framerate", str(VIDEO_FPS),
    "-i", "/dev/video0",
    "-c:v", "libx264",
    "-b:v", VIDEO_BITRATE,
    "-preset", "ultrafast",
    "-tune", "zerolatency"
]

# 카메라 상태
CAMERA_STATUS = {
    "INITIALIZING": "INITIALIZING",
    "READY": "READY",
    "RECORDING": "RECORDING",
    "ERROR": "ERROR",
    "LIMITED": "LIMITED"  # 제한된 기능으로 작동
}

def get_video_directories():
    """비디오 디렉토리 목록 반환"""
    directories = {
        "main": {
            "video": VIDEO_DIR,
            "temp": VIDEO_TEMP_DIR,
            "log": VIDEO_LOG_DIR
        }
    }
    
    # 서브 SD 카드가 마운트되어 있으면 추가
    if os.path.exists("/mnt/log_sd"):
        directories["sub"] = {
            "video": DUAL_VIDEO_DIR,
            "temp": DUAL_VIDEO_TEMP_DIR,
            "log": DUAL_VIDEO_LOG_DIR
        }
    
    return directories

def ensure_video_directories():
    """비디오 디렉토리 생성"""
    directories = get_video_directories()
    
    for location, dirs in directories.items():
        for dir_type, dir_path in dirs.items():
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ {location} {dir_type} 디렉토리 생성: {dir_path}")
            except Exception as e:
                print(f"❌ {location} {dir_type} 디렉토리 생성 실패: {e}")

def get_camera_config():
    """카메라 설정 반환"""
    return {
        "module": CAMERA_MODULE,
        "interface": CAMERA_INTERFACE,
        "video": {
            "width": VIDEO_WIDTH,
            "height": VIDEO_HEIGHT,
            "fps": VIDEO_FPS,
            "bitrate": VIDEO_BITRATE,
            "format": VIDEO_FORMAT
        },
        "recording": {
            "duration": RECORDING_DURATION,
            "max_size_mb": MAX_VIDEO_SIZE_MB
        },
        "directories": get_video_directories()
    }

def is_dual_logging_available():
    """이중 로깅 사용 가능 여부 확인"""
    return os.path.exists("/mnt/log_sd")

def get_logging_mode():
    """로깅 모드 반환"""
    if is_dual_logging_available():
        return "DUAL"
    else:
        return "SINGLE" 