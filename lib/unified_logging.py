#!/usr/bin/env python3
"""
Unified Logging System for CANSAT HEPHAESTUS 2025 FSW2
모든 모듈에서 일관된 로깅을 제공
"""

import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
import threading
import json

class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogCategory(Enum):
    SYSTEM = "SYSTEM"
    SENSOR = "SENSOR"
    COMMUNICATION = "COMM"
    FLIGHT_LOGIC = "FLIGHT"
    CAMERA = "CAMERA"
    MOTOR = "MOTOR"
    GPS = "GPS"
    IMU = "IMU"
    THERMAL = "THERMAL"
    GENERAL = "GENERAL"

class UnifiedLogger:
    """통합 로깅 시스템"""
    
    def __init__(self):
        self.loggers: Dict[str, logging.Logger] = {}
        self.log_dir = "logs"
        self.max_file_size = 10 * 1024 * 1024  # 10MB
        self.backup_count = 5
        self._lock = threading.Lock()
        
        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 기본 로거 설정
        self._setup_root_logger()
    
    def _setup_root_logger(self):
        """루트 로거 설정"""
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)
        
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
    
    def get_logger(self, name: str, category: LogCategory = LogCategory.GENERAL) -> logging.Logger:
        """로거 가져오기 또는 생성"""
        with self._lock:
            if name not in self.loggers:
                logger = logging.getLogger(name)
                logger.setLevel(logging.DEBUG)
                
                # 파일 핸들러 추가
                log_file = os.path.join(self.log_dir, f"{category.value.lower()}_{name}.log")
                file_handler = logging.FileHandler(log_file, encoding='utf-8')
                file_handler.setLevel(logging.DEBUG)
                
                file_formatter = logging.Formatter(
                    '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S'
                )
                file_handler.setFormatter(file_formatter)
                logger.addHandler(file_handler)
                
                self.loggers[name] = logger
            
            return self.loggers[name]
    
    def log(self, name: str, level: LogLevel, message: str, 
            category: LogCategory = LogCategory.GENERAL, 
            extra_data: Optional[Dict[str, Any]] = None):
        """통합 로깅 함수"""
        logger = self.get_logger(name, category)
        
        # 추가 데이터가 있으면 JSON 형태로 추가
        if extra_data:
            message = f"{message} | {json.dumps(extra_data, ensure_ascii=False)}"
        
        if level == LogLevel.DEBUG:
            logger.debug(message)
        elif level == LogLevel.INFO:
            logger.info(message)
        elif level == LogLevel.WARNING:
            logger.warning(message)
        elif level == LogLevel.ERROR:
            logger.error(message)
        elif level == LogLevel.CRITICAL:
            logger.critical(message)
    
    def log_sensor_data(self, sensor_name: str, data: Dict[str, Any]):
        """센서 데이터 로깅"""
        self.log(sensor_name, LogLevel.INFO, "Sensor data", 
                LogCategory.SENSOR, data)
    
    def log_system_event(self, event_type: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """시스템 이벤트 로깅"""
        self.log("SYSTEM", LogLevel.INFO, f"[{event_type}] {message}", 
                LogCategory.SYSTEM, extra_data)
    
    def log_error(self, module_name: str, error_message: str, context: str = ""):
        """오류 로깅"""
        message = f"{error_message}"
        if context:
            message = f"[{context}] {message}"
        
        self.log(module_name, LogLevel.ERROR, message, LogCategory.GENERAL)
    
    def log_warning(self, module_name: str, warning_message: str, context: str = ""):
        """경고 로깅"""
        message = f"{warning_message}"
        if context:
            message = f"[{context}] {message}"
        
        self.log(module_name, LogLevel.WARNING, message, LogCategory.GENERAL)
    
    def log_info(self, module_name: str, info_message: str, context: str = ""):
        """정보 로깅"""
        message = f"{info_message}"
        if context:
            message = f"[{context}] {message}"
        
        self.log(module_name, LogLevel.INFO, message, LogCategory.GENERAL)
    
    def log_debug(self, module_name: str, debug_message: str, context: str = ""):
        """디버그 로깅"""
        message = f"{debug_message}"
        if context:
            message = f"[{context}] {message}"
        
        self.log(module_name, LogLevel.DEBUG, message, LogCategory.GENERAL)
    
    def rotate_logs(self):
        """로그 파일 로테이션"""
        with self._lock:
            for name, logger in self.loggers.items():
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        try:
                            # 파일 크기 확인
                            if os.path.exists(handler.baseFilename):
                                file_size = os.path.getsize(handler.baseFilename)
                                if file_size > self.max_file_size:
                                    # 로그 파일 압축 및 백업
                                    self._rotate_log_file(handler.baseFilename)
                        except Exception as e:
                            print(f"Log rotation error for {name}: {e}")
    
    def _rotate_log_file(self, log_file: str):
        """개별 로그 파일 로테이션"""
        try:
            import gzip
            import shutil
            
            # 백업 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{log_file}.{timestamp}.gz"
            
            # 현재 로그 파일을 압축하여 백업
            with open(log_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 원본 파일 비우기
            open(log_file, 'w').close()
            
            # 오래된 백업 파일 정리
            self._cleanup_old_backups(log_file)
            
        except Exception as e:
            print(f"Log file rotation failed: {e}")
    
    def _cleanup_old_backups(self, log_file: str):
        """오래된 백업 파일 정리"""
        try:
            import glob
            
            # 백업 파일 패턴
            backup_pattern = f"{log_file}.*.gz"
            backup_files = glob.glob(backup_pattern)
            
            # 파일 수가 백업 개수를 초과하면 오래된 것부터 삭제
            if len(backup_files) > self.backup_count:
                backup_files.sort(key=os.path.getmtime)
                files_to_delete = backup_files[:-self.backup_count]
                
                for file_to_delete in files_to_delete:
                    try:
                        os.remove(file_to_delete)
                    except Exception as e:
                        print(f"Failed to delete old backup {file_to_delete}: {e}")
                        
        except Exception as e:
            print(f"Backup cleanup failed: {e}")
    
    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 정보"""
        stats = {
            'total_loggers': len(self.loggers),
            'log_files': {},
            'total_size': 0
        }
        
        for name, logger in self.loggers.items():
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    try:
                        if os.path.exists(handler.baseFilename):
                            file_size = os.path.getsize(handler.baseFilename)
                            stats['log_files'][name] = {
                                'file': handler.baseFilename,
                                'size': file_size,
                                'size_mb': round(file_size / (1024 * 1024), 2)
                            }
                            stats['total_size'] += file_size
                    except Exception:
                        pass
        
        stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
        return stats

# 전역 로거 인스턴스
unified_logger = UnifiedLogger()

def get_unified_logger() -> UnifiedLogger:
    """전역 로거 반환"""
    return unified_logger

def safe_log(message: str, level: str = "INFO", printlogs: bool = True, 
             module_name: str = "GENERAL", category: LogCategory = LogCategory.GENERAL):
    """안전한 로깅 함수 (기존 safe_log 호환성)"""
    try:
        log_level = LogLevel(level.upper())
        unified_logger.log(module_name, log_level, message, category)
        
        if printlogs:
            # 콘솔에도 출력
            print(f"[{module_name}] [{level}] {message}")
    except Exception as e:
        # 로깅 실패 시 최소한 콘솔에 출력
        print(f"[{module_name}] 로깅 실패: {e}")
        print(f"[{module_name}] 원본 메시지: {message}")

def log_sensor_data(sensor_name: str, data: Dict[str, Any]):
    """센서 데이터 로깅 (편의 함수)"""
    unified_logger.log_sensor_data(sensor_name, data)

def log_system_event(event_type: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
    """시스템 이벤트 로깅 (편의 함수)"""
    unified_logger.log_system_event(event_type, message, extra_data)

def log_error(module_name: str, error_message: str, context: str = ""):
    """오류 로깅 (편의 함수)"""
    unified_logger.log_error(module_name, error_message, context)

def log_warning(module_name: str, warning_message: str, context: str = ""):
    """경고 로깅 (편의 함수)"""
    unified_logger.log_warning(module_name, warning_message, context)

def log_info(module_name: str, info_message: str, context: str = ""):
    """정보 로깅 (편의 함수)"""
    unified_logger.log_info(module_name, info_message, context)

def log_debug(module_name: str, debug_message: str, context: str = ""):
    """디버그 로깅 (편의 함수)"""
    unified_logger.log_debug(module_name, debug_message, context) 