#!/usr/bin/env python3
"""
System Utilities for CANSAT FSW
시스템 유틸리티 함수들
"""

import os
import time
import threading
from typing import Dict, List, Optional, Tuple

def now_epoch() -> float:
    """현재 시간을 epoch으로 반환"""
    return time.time()

def now_iso() -> str:
    """현재 시간을 ISO 형식으로 반환"""
    return time.strftime("%Y-%m-%d %H:%M:%S")

def safe(val) -> float:
    """안전한 값 반환 (None이면 0 반환)"""
    return val if val is not None else 0

def ensure_directory(path: str) -> bool:
    """디렉토리가 존재하는지 확인하고 없으면 생성"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False

def get_file_size_mb(filepath: str) -> float:
    """파일 크기를 MB 단위로 반환"""
    try:
        if os.path.exists(filepath):
            return os.path.getsize(filepath) / (1024 * 1024)
        return 0.0
    except Exception:
        return 0.0

def is_process_alive(process) -> bool:
    """프로세스가 살아있는지 확인"""
    try:
        return process is not None and process.is_alive()
    except Exception:
        return False

def safe_thread_join(thread: threading.Thread, timeout: float = 3.0) -> bool:
    """안전한 스레드 종료 대기"""
    try:
        if thread and thread.is_alive():
            thread.join(timeout=timeout)
            return not thread.is_alive()
        return True
    except Exception:
        return False

def format_bytes(bytes_value: int) -> str:
    """바이트를 읽기 쉬운 형태로 변환"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.1f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.1f} TB"

def format_duration(seconds: float) -> str:
    """초를 읽기 쉬운 형태로 변환"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"

def create_timestamp() -> str:
    """타임스탬프 생성"""
    return time.strftime("%Y%m%d_%H%M%S")

def validate_file_path(filepath: str) -> bool:
    """파일 경로 유효성 검사"""
    try:
        # 경로가 유효한지 확인
        os.path.normpath(filepath)
        return True
    except Exception:
        return False

def get_available_disk_space(path: str = "/") -> float:
    """사용 가능한 디스크 공간을 GB 단위로 반환"""
    try:
        statvfs = os.statvfs(path)
        free_bytes = statvfs.f_frsize * statvfs.f_bavail
        return free_bytes / (1024 * 1024 * 1024)
    except Exception:
        return 0.0

def is_file_readable(filepath: str) -> bool:
    """파일이 읽기 가능한지 확인"""
    try:
        return os.path.exists(filepath) and os.access(filepath, os.R_OK)
    except Exception:
        return False

def is_file_writable(filepath: str) -> bool:
    """파일이 쓰기 가능한지 확인"""
    try:
        directory = os.path.dirname(filepath)
        if not directory:
            directory = "."
        return os.access(directory, os.W_OK)
    except Exception:
        return False 