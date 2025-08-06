#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 기본 앱 클래스
모든 앱에서 공통으로 사용하는 기능들을 제공하는 기본 클래스
"""

import signal
import threading
import time
from multiprocessing import Queue, connection
from typing import Optional, Dict, Any, Callable
from abc import ABC, abstractmethod

from .core import appargs, msgstructure, types, prevstate
from .logging import safe_log


class BaseApp(ABC):
    """모든 앱의 기본 클래스"""
    
    def __init__(self, app_name: str, app_id: types.AppID):
        self.app_name = app_name
        self.app_id = app_id
        self.run_status = True
        self.threads: Dict[str, threading.Thread] = {}
        self.mutex = threading.Lock()
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        
        # 로깅 초기화
        self._setup_logging()
    
    def _setup_logging(self):
        """로깅 시스템 설정"""
        try:
            # 통합 로깅 시스템 사용
            from lib.logging import safe_log as unified_safe_log
            self.safe_log = lambda msg, level="INFO", printlogs=True: unified_safe_log(
                msg, level, printlogs, self.app_name
            )
        except ImportError:
            # 폴백: 기본 로깅 시스템 사용
            def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
                try:
                    formatted_message = f"[{self.app_name}] [{level}] {message}"
                    print(f"[{self.app_name}] {formatted_message}")
                except Exception as e:
                    print(f"[{self.app_name}] 로깅 실패: {e}")
                    print(f"[{self.app_name}] 원본 메시지: {message}")
            self.safe_log = safe_log
    
    def command_handler(self, main_queue: Queue, recv_msg: msgstructure.MsgStructure, **kwargs):
        """기본 명령 핸들러 - 하위 클래스에서 오버라이드"""
        # 프로세스 종료 처리
        if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
            self.safe_log(f"{self.app_name.upper()} TERMINATION DETECTED", "INFO", True)
            self.run_status = False
            return
        
        # 기본적으로 처리되지 않은 메시지 로깅
        self.safe_log(f"MID {recv_msg.MsgID} not handled", "ERROR", True)
    
    def send_hk(self, main_queue: Queue):
        """하우스키핑 데이터 전송 - 하위 클래스에서 오버라이드"""
        while self.run_status:
            hk = msgstructure.MsgStructure()
            msgstructure.send_msg(main_queue, hk,
                                  self.app_id,
                                  appargs.HkAppArg.AppID,
                                  self._get_hk_mid(),
                                  str(self.run_status))
            time.sleep(1)
    
    def resilient_thread(self, target: Callable, args=(), name=None):
        """안정적인 스레드 실행 래퍼"""
        def wrapper():
            while self.run_status:
                try:
                    target(*args)
                except Exception as e:
                    self.safe_log(f"Resilient thread error: {e}", "WARNING", False)
                    time.sleep(0.1)  # 오류 발생 시 짧은 대기
                
                # 더 빠른 종료를 위해 짧은 간격으로 체크
                for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
                    if not self.run_status:
                        break
                    time.sleep(0.1)
        
        thread = threading.Thread(target=wrapper, daemon=True, name=name)
        self.threads[name or target.__name__] = thread
        return thread
    
    def start_thread(self, target: Callable, args=(), name=None):
        """스레드 시작"""
        thread = self.resilient_thread(target, args, name)
        thread.start()
        return thread
    
    def stop_all_threads(self):
        """모든 스레드 종료"""
        self.run_status = False
        
        for thread_name, thread in self.threads.items():
            if thread.is_alive():
                self.safe_log(f"Joining thread: {thread_name}", "INFO", True)
                thread.join(timeout=1.0)
                if thread.is_alive():
                    self.safe_log(f"Thread {thread_name} did not terminate gracefully", "WARNING", True)
    
    @abstractmethod
    def _get_hk_mid(self) -> int:
        """하우스키핑 메시지 ID 반환 - 하위 클래스에서 구현"""
        pass
    
    @abstractmethod
    def app_init(self, **kwargs):
        """앱 초기화 - 하위 클래스에서 구현"""
        pass
    
    @abstractmethod
    def app_terminate(self, **kwargs):
        """앱 종료 - 하위 클래스에서 구현"""
        pass
    
    @abstractmethod
    def app_main_loop(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 메인 루프 - 하위 클래스에서 구현"""
        pass
    
    def app_main(self, main_queue: Queue, main_pipe: connection.Connection):
        """앱 메인 함수 - 표준 구현"""
        try:
            self.safe_log(f"Initializing {self.app_name}", "INFO", True)
            
            # 앱 초기화
            init_result = self.app_init()
            if init_result is False:  # 초기화 실패
                self.safe_log(f"{self.app_name} initialization failed", "ERROR", True)
                return
            
            self.safe_log(f"{self.app_name} initialization complete", "INFO", True)
            
            # 메인 루프 실행
            self.app_main_loop(main_queue, main_pipe)
            
        except KeyboardInterrupt:
            self.safe_log(f"KeyboardInterrupt in {self.app_name}", "INFO", True)
        except Exception as e:
            self.safe_log(f"Critical error in {self.app_name}: {e}", "ERROR", True)
        finally:
            # 앱 종료
            try:
                self.app_terminate()
                self.stop_all_threads()
                self.safe_log(f"{self.app_name} termination complete", "INFO", True)
            except Exception as e:
                self.safe_log(f"Error during {self.app_name} termination: {e}", "ERROR", True)


class SensorApp(BaseApp):
    """센서 앱의 기본 클래스"""
    
    def __init__(self, app_name: str, app_id: types.AppID):
        super().__init__(app_name, app_id)
        self.sensor_device = None
        self.data_mutex = threading.Lock()
    
    def send_sensor_data(self, main_queue: Queue, data_func: Callable, target_app: types.AppID, 
                        target_mid: int, interval: float = 1.0):
        """센서 데이터 전송"""
        while self.run_status:
            try:
                with self.data_mutex:
                    data = data_func()
                
                if data is not None:
                    msg = msgstructure.MsgStructure()
                    msgstructure.send_msg(main_queue, msg,
                                          self.app_id,
                                          target_app,
                                          target_mid,
                                          str(data))
                
                time.sleep(interval)
                
            except Exception as e:
                self.safe_log(f"Sensor data send error: {e}", "WARNING", False)
                time.sleep(interval)
    
    def calibrate_sensor(self, offset_value: float, offset_key: str):
        """센서 보정"""
        try:
            with self.data_mutex:
                # 통합 오프셋 시스템에 저장
                from lib.offsets import set_offset
                set_offset(offset_key, offset_value)
                self.safe_log(f"센서 오프셋 저장됨: {offset_key} = {offset_value}", "INFO", True)
                
                # 기존 호환성을 위해 prevstate도 업데이트
                if hasattr(prevstate, f'update_{offset_key.lower()}'):
                    getattr(prevstate, f'update_{offset_key.lower()}')(offset_value)
                    
        except Exception as e:
            self.safe_log(f"센서 보정 실패: {e}", "ERROR", True)


class CommunicationApp(BaseApp):
    """통신 앱의 기본 클래스"""
    
    def __init__(self, app_name: str, app_id: types.AppID):
        super().__init__(app_name, app_id)
        self.comm_device = None
        self.transmission_stats = {
            'sent': 0,
            'received': 0,
            'errors': 0,
            'last_transmission': None
        }
    
    def update_transmission_stats(self, sent: bool = False, received: bool = False, error: bool = False):
        """전송 통계 업데이트"""
        with self.mutex:
            if sent:
                self.transmission_stats['sent'] += 1
            if received:
                self.transmission_stats['received'] += 1
            if error:
                self.transmission_stats['errors'] += 1
            self.transmission_stats['last_transmission'] = time.time()
    
    def get_transmission_stats(self) -> Dict[str, Any]:
        """전송 통계 반환"""
        with self.mutex:
            return self.transmission_stats.copy()


# 유틸리티 함수들
def create_app_instance(app_class: type, app_name: str, app_id: types.AppID, **kwargs):
    """앱 인스턴스 생성 헬퍼 함수"""
    return app_class(app_name, app_id, **kwargs)


def run_app(app_instance: BaseApp, main_queue: Queue, main_pipe: connection.Connection):
    """앱 실행 헬퍼 함수"""
    app_instance.app_main(main_queue, main_pipe) 