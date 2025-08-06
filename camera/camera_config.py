# Camera Configuration File
# Author : Hyeon Lee  (HEPHAESTUS)

# ──────────────────────────────
# 카메라 하드웨어 설정
# ──────────────────────────────
CAMERA_DEVICE = "/dev/video0"  # 카메라 디바이스 경로
CAMERA_RESOLUTION = "1920x1080"  # 해상도 (1920x1080, 1280x720, 640x480)
CAMERA_FPS = 30  # 프레임레이트

# ──────────────────────────────
# 녹화 설정
# ──────────────────────────────
RECORDING_INTERVAL = 5  # 녹화 주기 (초)
VIDEO_DURATION = 5  # 각 비디오 길이 (초)
VIDEO_FORMAT = "h264"  # 비디오 포맷
VIDEO_QUALITY = "23"  # h264 품질 (낮을수록 좋은 품질, 18-28 권장)

# ──────────────────────────────
# 저장 경로
# ──────────────────────────────
VIDEO_DIR = "logs/cansat_videos"  # 최종 비디오 저장 경로
TEMP_DIR = "/tmp/camera_temp"  # 임시 파일 경로

# ──────────────────────────────
# 안전성 설정
# ──────────────────────────────
MAX_DISK_USAGE = 90.0  # 최대 디스크 사용량 (%)
PROCESS_TIMEOUT = 10  # 프로세스 타임아웃 (초)
MAX_RETRY_COUNT = 3  # 최대 재시도 횟수

# ──────────────────────────────
# 로깅 설정
# ──────────────────────────────
LOG_VIDEO_COUNT_INTERVAL = 10  # 비디오 수 로그 간격
ENABLE_DEBUG_LOGGING = False  # 디버그 로깅 활성화

# ──────────────────────────────
# 성능 최적화 설정
# ──────────────────────────────
ENABLE_HARDWARE_ACCELERATION = True  # 하드웨어 가속 사용
BUFFER_SIZE = 1024  # 버퍼 크기
THREAD_PRIORITY = "normal"  # 스레드 우선순위 (low, normal, high)

# ──────────────────────────────
# 환경별 설정
# ──────────────────────────────
# 개발 환경
DEV_SETTINGS = {
    "CAMERA_RESOLUTION": "1280x720",
    "CAMERA_FPS": 15,
    "RECORDING_INTERVAL": 10,
    "VIDEO_DURATION": 3,
    "ENABLE_DEBUG_LOGGING": True
}

# 프로덕션 환경
PROD_SETTINGS = {
    "CAMERA_RESOLUTION": "1920x1080",
    "CAMERA_FPS": 30,
    "RECORDING_INTERVAL": 5,
    "VIDEO_DURATION": 5,
    "ENABLE_DEBUG_LOGGING": False
}

# 테스트 환경
TEST_SETTINGS = {
    "CAMERA_RESOLUTION": "640x480",
    "CAMERA_FPS": 10,
    "RECORDING_INTERVAL": 2,
    "VIDEO_DURATION": 2,
    "ENABLE_DEBUG_LOGGING": True
}

def get_settings(environment="prod"):
    """환경별 설정 반환"""
    if environment == "dev":
        return DEV_SETTINGS
    elif environment == "test":
        return TEST_SETTINGS
    else:
        return PROD_SETTINGS

def apply_settings(settings_dict):
    """설정을 전역 변수에 적용"""
    global CAMERA_RESOLUTION, CAMERA_FPS, RECORDING_INTERVAL, VIDEO_DURATION, ENABLE_DEBUG_LOGGING
    
    for key, value in settings_dict.items():
        if key in globals():
            globals()[key] = value 