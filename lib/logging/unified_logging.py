#!/usr/bin/env python3
"""
Unified Logging System for CANSAT HEPHAESTUS 2025 FSW2
모든 모듈에서 일관된 로깅을 제공하는 통합 시스템
"""

import logging
import os
import sys
import time
import threading
import json
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

# Unified Logging System for CANSAT FSW
# Author: Hyeon Lee (HEPHAESTUS)
# Version: 2.0 - Enhanced for robustness and app termination resilience

import os
import sys
import time
import threading
import queue
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import atexit
import signal

# 글로벌 로깅 상태
_logging_initialized = False
_log_queue = queue.Queue(maxsize=1000)  # 로그 큐 크기 증가
_log_thread = None
_log_thread_running = False
_log_lock = threading.RLock()

# 로그 파일 경로
LOG_DIR = "logs"
MAIN_LOG_PATH = os.path.join(LOG_DIR, "main_system.log")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error.log")
DEBUG_LOG_PATH = os.path.join(LOG_DIR, "debug.log")
SYSTEM_STATUS_LOG_PATH = os.path.join(LOG_DIR, "system_status.log")

# 로그 레벨 정의
LOG_LEVELS = {
    "DEBUG": 0,
    "INFO": 1,
    "WARNING": 2,
    "ERROR": 3,
    "CRITICAL": 4
}

# 현재 로그 레벨 (환경변수에서 읽거나 기본값 사용)
_current_log_level = LOG_LEVELS.get(os.environ.get("LOG_LEVEL", "INFO").upper(), LOG_LEVELS["INFO"])

# 로그 버퍼 (메모리 기반 백업)
_log_buffer = []
_max_buffer_size = 1000  # 버퍼 크기 증가

# 프로세스 안전성을 위한 파일 핸들러
_file_handlers = {}
_file_locks = {}

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
        self._lock = threading.Lock()
        self._global_logger = None
        
        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)
        
        # 기본 로거 설정
        self._setup_root_logger()
        self._setup_global_logger()
    
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
    
    def _setup_global_logger(self):
        """전역 로거 설정"""
        self._global_logger = logging.getLogger('CANSAT')
        self._global_logger.setLevel(logging.DEBUG)
        
        # 파일 핸들러 추가
        log_file = os.path.join(self.log_dir, "cansat_system.log")
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self._global_logger.addHandler(file_handler)
    
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
        
        # 전역 로거에도 기록
        if self._global_logger:
            if level == LogLevel.DEBUG:
                self._global_logger.debug(f"[{name}] {message}")
            elif level == LogLevel.INFO:
                self._global_logger.info(f"[{name}] {message}")
            elif level == LogLevel.WARNING:
                self._global_logger.warning(f"[{name}] {message}")
            elif level == LogLevel.ERROR:
                self._global_logger.error(f"[{name}] {message}")
            elif level == LogLevel.CRITICAL:
                self._global_logger.critical(f"[{name}] {message}")
    
    def log_sensor_data(self, sensor_name: str, data: Dict[str, Any]):
        """센서 데이터 로깅"""
        self.log(sensor_name, LogLevel.INFO, "Sensor data", LogCategory.SENSOR, data)
    
    def log_system_event(self, event_type: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """시스템 이벤트 로깅"""
        self.log("SYSTEM", LogLevel.INFO, f"{event_type}: {message}", LogCategory.SYSTEM, extra_data)
    
    def log_error(self, module_name: str, error_message: str, context: str = ""):
        """오류 로깅"""
        message = error_message
        if context:
            message = f"{context}: {error_message}"
        self.log(module_name, LogLevel.ERROR, message, LogCategory.SYSTEM)
    
    def log_warning(self, module_name: str, warning_message: str, context: str = ""):
        """경고 로깅"""
        message = warning_message
        if context:
            message = f"{context}: {warning_message}"
        self.log(module_name, LogLevel.WARNING, message, LogCategory.SYSTEM)
    
    def log_info(self, module_name: str, info_message: str, context: str = ""):
        """정보 로깅"""
        message = info_message
        if context:
            message = f"{context}: {info_message}"
        self.log(module_name, LogLevel.INFO, message, LogCategory.SYSTEM)
    
    def log_debug(self, module_name: str, debug_message: str, context: str = ""):
        """디버그 로깅"""
        message = debug_message
        if context:
            message = f"{context}: {debug_message}"
        self.log(module_name, LogLevel.DEBUG, message, LogCategory.SYSTEM)
    
    def rotate_logs(self):
        """로그 파일 로테이션"""
        try:
            for logger_name, logger in self.loggers.items():
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        log_file = handler.baseFilename
                        self._rotate_log_file(log_file)
            
            # 전역 로거도 로테이션
            if self._global_logger:
                for handler in self._global_logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        log_file = handler.baseFilename
                        self._rotate_log_file(log_file)
                        
        except Exception as e:
            pass  # 로그 로테이션 오류: {e}
    
    def _rotate_log_file(self, log_file: str):
        """개별 로그 파일 로테이션"""
        try:
            if os.path.exists(log_file):
                file_size = os.path.getsize(log_file)
                if file_size > self.max_file_size:
                    # 백업 파일명 생성
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = f"{log_file}.{timestamp}"
                    
                    # 파일 이동
                    os.rename(log_file, backup_file)
                    
                    # 압축 (선택사항)
                    try:
                        import gzip
                        with open(backup_file, 'rb') as f_in:
                            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                                f_out.writelines(f_in)
                        os.remove(backup_file)  # 원본 파일 삭제
                    except ImportError:
                        pass  # gzip 모듈이 없으면 압축하지 않음
                        
        except Exception as e:
            pass  # 로그 파일 로테이션 오류 ({log_file}): {e}
    
    def _cleanup_old_backups(self, log_file: str):
        """오래된 백업 파일 정리"""
        try:
            log_dir = os.path.dirname(log_file)
            base_name = os.path.basename(log_file)
            
            # 30일 이상 된 백업 파일 삭제
            current_time = time.time()
            for filename in os.listdir(log_dir):
                if filename.startswith(base_name) and filename != base_name:
                    file_path = os.path.join(log_dir, filename)
                    if os.path.isfile(file_path):
                        file_age = current_time - os.path.getmtime(file_path)
                        if file_age > 30 * 24 * 3600:  # 30일
                            os.remove(file_path)
                            
        except Exception as e:
            pass  # 백업 파일 정리 오류: {e}
    
    def get_log_stats(self) -> Dict[str, Any]:
        """로그 통계 반환"""
        try:
            stats = {
                'total_loggers': len(self.loggers),
                'log_files': [],
                'total_size': 0,
                'oldest_log': None,
                'newest_log': None
            }
            
            for logger_name, logger in self.loggers.items():
                for handler in logger.handlers:
                    if isinstance(handler, logging.FileHandler):
                        log_file = handler.baseFilename
                        if os.path.exists(log_file):
                            file_size = os.path.getsize(log_file)
                            file_mtime = os.path.getmtime(log_file)
                            
                            stats['log_files'].append({
                                'name': logger_name,
                                'file': log_file,
                                'size': file_size,
                                'modified': datetime.fromtimestamp(file_mtime).isoformat()
                            })
                            
                            stats['total_size'] += file_size
                            
                            if stats['oldest_log'] is None or file_mtime < stats['oldest_log']:
                                stats['oldest_log'] = file_mtime
                            if stats['newest_log'] is None or file_mtime > stats['newest_log']:
                                stats['newest_log'] = file_mtime
            
            # 시간을 ISO 형식으로 변환
            if stats['oldest_log']:
                stats['oldest_log'] = datetime.fromtimestamp(stats['oldest_log']).isoformat()
            if stats['newest_log']:
                stats['newest_log'] = datetime.fromtimestamp(stats['newest_log']).isoformat()
            
            return stats
            
        except Exception as e:
            return {'error': str(e)}


# 전역 인스턴스
_unified_logger = None

def get_unified_logger() -> UnifiedLogger:
    """통합 로거 인스턴스 반환"""
    global _unified_logger
    if _unified_logger is None:
        _unified_logger = UnifiedLogger()
    return _unified_logger

# 기존 로깅 시스템과의 호환성을 위한 함수들
def safe_log(message: str, level: str = "INFO", printlogs: bool = True, app_name: str = "UNKNOWN"):
    """
    안전한 로깅 함수 - 앱 종료 시에도 로그 보존
    
    Args:
        message: 로그 메시지
        level: 로그 레벨 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        printlogs: 콘솔 출력 여부
        app_name: 앱 이름 (기본값: UNKNOWN)
    """
    try:
        # 로깅 시스템 초기화 확인
        if not _logging_initialized:
            _initialize_logging()
        
        # 메시지 큐에 추가 (비동기 처리)
        try:
            # level이 문자열이 아닌 경우 문자열로 변환
            level_str = str(level).upper() if level is not None else "INFO"
            _log_queue.put_nowait((
                datetime.now().isoformat(sep=' ', timespec='milliseconds'),
                level_str,
                app_name,
                message,
                printlogs
            ))
        except queue.Full:
            # 큐가 가득 찬 경우 버퍼에 직접 저장
            level_str = str(level).upper() if level is not None else "INFO"
            _log_buffer.append(f"[QUEUE_FULL] [{level_str}] [{app_name}] {message}")
            if len(_log_buffer) > _max_buffer_size:
                _log_buffer.pop(0)
            
            # 콘솔 출력
            if printlogs:
                try:
                    level_str = str(level).upper() if level is not None else "INFO"
                    print(f"[{level_str}] [{app_name}] {message}")
                except:
                    pass
        
    except Exception as e:
        # 로깅 시스템 자체에 문제가 있는 경우 최소한의 출력
        try:
            level_str = str(level).upper() if level is not None else "INFO"
            print(f"[LOGGING_ERROR] {e}")
            print(f"[ORIGINAL_MESSAGE] [{level_str}] [{app_name}] {message}")
        except:
            # 모든 출력이 실패한 경우 무시
            pass

def emergency_log(message: str, app_name: str = "EMERGENCY"):
    """
    긴급 로깅 함수 - 로깅 시스템이 실패해도 작동
    
    Args:
        message: 긴급 메시지
        app_name: 앱 이름
    """
    try:
        # 즉시 파일에 쓰기 시도
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        emergency_message = f"[{timestamp}] [EMERGENCY] [{app_name}] {message}"
        
        # 메인 로그 파일에 직접 쓰기
        _write_log_safe(MAIN_LOG_PATH, emergency_message)
        
        # 에러 로그에도 저장
        _write_log_safe(ERROR_LOG_PATH, emergency_message)
        
        # 콘솔 출력
        try:
            print(emergency_message)
        except:
            pass
            
    except Exception as e:
        # 모든 로깅이 실패한 경우 버퍼에 저장
        _log_buffer.append(f"[EMERGENCY_FAIL] [{app_name}] {message}")
        if len(_log_buffer) > _max_buffer_size:
            _log_buffer.pop(0)
        
        # 최후의 수단으로 print 시도
        try:
            print(f"[EMERGENCY] [{app_name}] {message}")
        except:
            pass

def get_log_buffer():
    """로그 버퍼 내용 반환 (디버깅용)"""
    return _log_buffer.copy()

def clear_log_buffer():
    """로그 버퍼 정리"""
    global _log_buffer
    _log_buffer.clear()

def flush_logs():
    """로그 버퍼를 파일에 강제 쓰기"""
    try:
        if _log_buffer:
            _write_log_safe(MAIN_LOG_PATH, f"[FLUSH] {len(_log_buffer)} buffered messages")
            for buffered_msg in _log_buffer:
                _write_log_safe(MAIN_LOG_PATH, buffered_msg)
            _log_buffer.clear()
    except Exception as e:
        # 플러시 실패 시에도 계속 진행
        pass

def log_sensor_data(sensor_name: str, data: Dict[str, Any]):
    """센서 데이터 로깅"""
    get_unified_logger().log_sensor_data(sensor_name, data)

def log_system_event(event_type: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
    """시스템 이벤트 로깅"""
    get_unified_logger().log_system_event(event_type, message, extra_data)

def log_error(module_name: str, error_message: str, context: str = ""):
    """오류 로깅"""
    get_unified_logger().log_error(module_name, error_message, context)

def log_warning(module_name: str, warning_message: str, context: str = ""):
    """경고 로깅"""
    get_unified_logger().log_warning(module_name, warning_message, context)

def log_info(module_name: str, info_message: str, context: str = ""):
    """정보 로깅"""
    get_unified_logger().log_info(module_name, info_message, context)

def log_debug(module_name: str, debug_message: str, context: str = ""):
    """디버그 로깅"""
    get_unified_logger().log_debug(module_name, debug_message, context) 

def _ensure_log_directory():
    """로그 디렉토리 생성"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
    except Exception as e:
        # 디렉토리 생성 실패 시에도 계속 진행
        pass

def _get_file_handler(filepath: str):
    """파일 핸들러 가져오기 (프로세스 안전)"""
    if filepath not in _file_handlers:
        try:
            _ensure_log_directory()
            _file_handlers[filepath] = open(filepath, 'a', encoding='utf-8', buffering=1)
            _file_locks[filepath] = threading.Lock()
        except Exception as e:
            # 파일 핸들러 생성 실패 시 None 반환
            return None, None
    return _file_handlers[filepath], _file_locks[filepath]

def _write_log_safe(filepath: str, message: str):
    """안전한 로그 쓰기 (파일 오류 시에도 계속 진행)"""
    try:
        handler, lock = _get_file_handler(filepath)
        if handler and lock:
            with lock:
                handler.write(message + '\n')
                handler.flush()  # 즉시 디스크에 쓰기
        else:
            # 파일 핸들러가 없으면 버퍼에 저장
            _log_buffer.append(f"[BUFFER] {message}")
            if len(_log_buffer) > _max_buffer_size:
                _log_buffer.pop(0)
    except Exception as e:
        # 파일 쓰기 실패 시에도 버퍼에 저장
        _log_buffer.append(f"[BUFFER-FAIL] {message}")
        if len(_log_buffer) > _max_buffer_size:
            _log_buffer.pop(0)

def _log_worker():
    """로그 워커 스레드 (백그라운드에서 로그 처리)"""
    global _log_thread_running
    _log_thread_running = True
    
    while _log_thread_running:
        try:
            # 큐에서 로그 메시지 가져오기 (타임아웃으로 종료 가능하게)
            try:
                log_entry = _log_queue.get(timeout=1.0)
            except queue.Empty:
                continue
            
            if log_entry is None:  # 종료 신호
                break
                
            timestamp, level, app_name, message, print_to_console = log_entry
            
            # 로그 레벨 체크
            if LOG_LEVELS.get(level.upper(), 0) < _current_log_level:
                continue
            
            # 타임스탬프가 있는 메시지 생성
            formatted_message = f"[{timestamp}] [{level.upper()}] [{app_name}] {message}"
            
            # 콘솔 출력
            if print_to_console:
                try:
                    print(formatted_message)
                except:
                    pass  # 콘솔 출력 실패 시 무시
            
            # 파일에 쓰기
            _write_log_safe(MAIN_LOG_PATH, formatted_message)
            
            # 에러 레벨 이상은 별도 에러 로그에 저장
            if level.upper() in ["ERROR", "CRITICAL"]:
                _write_log_safe(ERROR_LOG_PATH, formatted_message)
            
            # 디버그 레벨은 별도 디버그 로그에 저장
            if level.upper() == "DEBUG":
                _write_log_safe(DEBUG_LOG_PATH, formatted_message)
                
        except Exception as e:
            # 로그 워커에서 오류가 발생해도 계속 실행
            try:
                print(f"[LOG_WORKER_ERROR] {e}")
            except:
                pass
            time.sleep(0.1)
    
    # 종료 시 버퍼 내용을 파일에 저장
    try:
        if _log_buffer:
            _write_log_safe(MAIN_LOG_PATH, f"[BUFFER_DUMP] {len(_log_buffer)} buffered messages")
            for buffered_msg in _log_buffer:
                _write_log_safe(MAIN_LOG_PATH, buffered_msg)
    except:
        pass

def _initialize_logging():
    """로깅 시스템 초기화"""
    global _logging_initialized, _log_thread
    
    if _logging_initialized:
        return
    
    try:
        _ensure_log_directory()
        
        # 로그 워커 스레드 시작
        _log_thread = threading.Thread(target=_log_worker, daemon=True, name="LogWorker")
        _log_thread.start()
        
        # 종료 시 정리 함수 등록
        atexit.register(_cleanup_logging)
        
        # 시그널 핸들러 등록 (프로세스 종료 시 로그 보존)
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT, _signal_handler)
        
        _logging_initialized = True
        
        # 초기화 완료 로그
        _log_queue.put((
            datetime.now().isoformat(sep=' ', timespec='milliseconds'),
            "INFO",
            "LOGGING_SYSTEM",
            "Unified logging system initialized successfully",
            True
        ))
        
    except Exception as e:
        # 초기화 실패 시에도 기본 로깅은 가능하도록
        print(f"[LOGGING_INIT_ERROR] {e}")

def _signal_handler(signum, frame):
    """시그널 핸들러 (프로세스 종료 시 로그 보존)"""
    try:
        _cleanup_logging()
    except:
        pass
    sys.exit(0)

def _cleanup_logging():
    """로깅 시스템 정리"""
    global _log_thread_running, _file_handlers
    
    try:
        # 로그 워커 종료
        _log_thread_running = False
        _log_queue.put(None)  # 종료 신호
        
        if _log_thread and _log_thread.is_alive():
            _log_thread.join(timeout=5)
        
        # 파일 핸들러 정리
        for handler in _file_handlers.values():
            try:
                handler.close()
            except:
                pass
        _file_handlers.clear()
        _file_locks.clear()
        
    except Exception as e:
        # 정리 과정에서 오류가 발생해도 무시
        pass 