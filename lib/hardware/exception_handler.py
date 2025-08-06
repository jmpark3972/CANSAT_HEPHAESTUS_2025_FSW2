#!/usr/bin/env python3
"""
Exception Handler for CANSAT HEPHAESTUS 2025 FSW2
표준화된 예외 처리 시스템
"""

import traceback
import sys
from typing import Optional, Callable, Any, Dict
from enum import Enum
import time
import threading
from functools import wraps

class ExceptionSeverity(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ExceptionCategory(Enum):
    HARDWARE = "HARDWARE"
    NETWORK = "NETWORK"
    DATA_PROCESSING = "DATA_PROCESSING"
    MEMORY = "MEMORY"
    THREADING = "THREADING"
    CONFIGURATION = "CONFIGURATION"
    UNKNOWN = "UNKNOWN"

class CansatException(Exception):
    """CANSAT 전용 예외 클래스"""
    
    def __init__(self, message: str, severity: ExceptionSeverity = ExceptionSeverity.MEDIUM,
                 category: ExceptionCategory = ExceptionCategory.UNKNOWN,
                 context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.severity = severity
        self.category = category
        self.context = context or {}
        self.timestamp = time.time()
        self.traceback = traceback.format_exc()

class HardwareException(CansatException):
    """하드웨어 관련 예외"""
    def __init__(self, message: str, device: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ExceptionSeverity.HIGH, ExceptionCategory.HARDWARE, context)
        self.device = device

class SensorException(CansatException):
    """센서 관련 예외"""
    def __init__(self, message: str, sensor_type: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ExceptionSeverity.MEDIUM, ExceptionCategory.HARDWARE, context)
        self.sensor_type = sensor_type

class DataProcessingException(CansatException):
    """데이터 처리 관련 예외"""
    def __init__(self, message: str, data_type: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ExceptionSeverity.MEDIUM, ExceptionCategory.DATA_PROCESSING, context)
        self.data_type = data_type

class NetworkException(CansatException):
    """네트워크 관련 예외"""
    def __init__(self, message: str, connection_type: str = "", context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ExceptionSeverity.HIGH, ExceptionCategory.NETWORK, context)
        self.connection_type = connection_type

class ExceptionHandler:
    """예외 처리 핸들러"""
    
    def __init__(self):
        self.error_count = 0
        self.error_history = []
        self.max_history = 100
        self.recovery_strategies: Dict[ExceptionCategory, Callable] = {}
        self._lock = threading.Lock()
        
        # 기본 복구 전략 등록
        self._register_default_recovery_strategies()
    
    def _register_default_recovery_strategies(self):
        """기본 복구 전략 등록"""
        self.recovery_strategies[ExceptionCategory.HARDWARE] = self._hardware_recovery
        self.recovery_strategies[ExceptionCategory.NETWORK] = self._network_recovery
        self.recovery_strategies[ExceptionCategory.DATA_PROCESSING] = self._data_processing_recovery
        self.recovery_strategies[ExceptionCategory.MEMORY] = self._memory_recovery
        self.recovery_strategies[ExceptionCategory.THREADING] = self._threading_recovery
    
    def handle_exception(self, exception: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
        """예외 처리"""
        with self._lock:
            self.error_count += 1
            
            # 예외 정보 기록
            error_info = {
                'timestamp': time.time(),
                'exception_type': type(exception).__name__,
                'message': str(exception),
                'traceback': traceback.format_exc(),
                'context': context or {},
                'severity': ExceptionSeverity.MEDIUM,
                'category': ExceptionCategory.UNKNOWN
            }
            
            # CANSAT 예외인 경우 추가 정보 추출
            if isinstance(exception, CansatException):
                error_info['severity'] = exception.severity
                error_info['category'] = exception.category
                error_info['context'].update(exception.context)
            
            # 오류 히스토리에 추가
            self.error_history.append(error_info)
            if len(self.error_history) > self.max_history:
                self.error_history.pop(0)
            
            # 심각도에 따른 처리
            if error_info['severity'] == ExceptionSeverity.CRITICAL:
                return self._handle_critical_exception(exception, error_info)
            elif error_info['severity'] == ExceptionSeverity.HIGH:
                return self._handle_high_severity_exception(exception, error_info)
            elif error_info['severity'] == ExceptionSeverity.MEDIUM:
                return self._handle_medium_severity_exception(exception, error_info)
            else:
                return self._handle_low_severity_exception(exception, error_info)
    
    def _handle_critical_exception(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """치명적 예외 처리"""
        print(f"🚨 CRITICAL ERROR: {exception}")
        print(f"Category: {error_info['category'].value}")
        print(f"Context: {error_info['context']}")
        
        # 시스템 종료 고려
        if self.error_count > 10:
            print("Too many critical errors, considering system shutdown")
            return False
        
        return True
    
    def _handle_high_severity_exception(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """높은 심각도 예외 처리"""
        print(f"⚠️ HIGH SEVERITY ERROR: {exception}")
        
        # 복구 전략 시도
        category = error_info['category']
        if category in self.recovery_strategies:
            try:
                return self.recovery_strategies[category](exception, error_info)
            except Exception as recovery_error:
                print(f"Recovery strategy failed: {recovery_error}")
        
        return False
    
    def _handle_medium_severity_exception(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """중간 심각도 예외 처리"""
        print(f"⚠️ MEDIUM SEVERITY ERROR: {exception}")
        
        # 복구 전략 시도
        category = error_info['category']
        if category in self.recovery_strategies:
            try:
                return self.recovery_strategies[category](exception, error_info)
            except Exception as recovery_error:
                print(f"Recovery strategy failed: {recovery_error}")
        
        return True  # 계속 진행
    
    def _handle_low_severity_exception(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """낮은 심각도 예외 처리"""
        print(f"ℹ️ LOW SEVERITY ERROR: {exception}")
        return True  # 계속 진행
    
    def _hardware_recovery(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """하드웨어 복구 전략"""
        print("Attempting hardware recovery...")
        
        # I2C 버스 재시작 시도
        if 'i2c' in str(exception).lower() or 'sensor' in str(exception).lower():
            try:
                from lib.i2c_manager import restart_i2c_bus
                if restart_i2c_bus():
                    print("I2C bus restart successful")
                    return True
            except Exception as e:
                print(f"I2C bus restart failed: {e}")
        
        return False
    
    def _network_recovery(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """네트워크 복구 전략"""
        print("Attempting network recovery...")
        
        # 연결 재시도
        time.sleep(1)
        return True
    
    def _data_processing_recovery(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """데이터 처리 복구 전략"""
        print("Attempting data processing recovery...")
        
        # 기본값 사용
        return True
    
    def _memory_recovery(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """메모리 복구 전략"""
        print("Attempting memory recovery...")
        
        # 가비지 컬렉션 강제 실행
        import gc
        gc.collect()
        
        return True
    
    def _threading_recovery(self, exception: Exception, error_info: Dict[str, Any]) -> bool:
        """스레딩 복구 전략"""
        print("Attempting threading recovery...")
        
        # 스레드 재시작 고려
        return True
    
    def get_error_stats(self) -> Dict[str, Any]:
        """오류 통계 정보"""
        with self._lock:
            stats = {
                'total_errors': self.error_count,
                'recent_errors': len(self.error_history),
                'severity_distribution': {},
                'category_distribution': {},
                'recent_errors_list': self.error_history[-10:]  # 최근 10개
            }
            
            # 심각도별 분포
            for error in self.error_history:
                severity = error['severity'].value
                stats['severity_distribution'][severity] = stats['severity_distribution'].get(severity, 0) + 1
            
            # 카테고리별 분포
            for error in self.error_history:
                category = error['category'].value
                stats['category_distribution'][category] = stats['category_distribution'].get(category, 0) + 1
            
            return stats
    
    def clear_history(self):
        """오류 히스토리 정리"""
        with self._lock:
            self.error_history.clear()

# 전역 예외 핸들러
exception_handler = ExceptionHandler()

def get_exception_handler() -> ExceptionHandler:
    """전역 예외 핸들러 반환"""
    return exception_handler

def handle_exception(exception: Exception, context: Optional[Dict[str, Any]] = None) -> bool:
    """예외 처리 (편의 함수)"""
    return exception_handler.handle_exception(exception, context)

def safe_execute(func: Callable, *args, context: Optional[Dict[str, Any]] = None, 
                default_return: Any = None, **kwargs) -> Any:
    """안전한 함수 실행 데코레이터"""
    try:
        return func(*args, **kwargs)
    except Exception as e:
        handle_exception(e, context)
        return default_return

def exception_safe(func: Callable) -> Callable:
    """예외 안전 데코레이터"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            handle_exception(e, {'function': func.__name__})
            return None
    return wrapper

def retry_on_exception(max_retries: int = 3, delay: float = 1.0, 
                      exceptions: tuple = (Exception,)) -> Callable:
    """재시도 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        print(f"Attempt {attempt + 1} failed: {e}, retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        print(f"All {max_retries} attempts failed")
            
            # 모든 재시도 실패
            handle_exception(last_exception, {
                'function': func.__name__,
                'max_retries': max_retries,
                'attempts': max_retries
            })
            return None
        
        return wrapper
    return decorator 