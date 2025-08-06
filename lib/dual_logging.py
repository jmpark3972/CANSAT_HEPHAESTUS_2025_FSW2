#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 이중 로깅 시스템
메인 SD 카드와 서브 SD 카드에 동시에 로그를 저장
강제 종료 시에도 데이터 보호
"""

import os
import sys
import time
import threading
import queue
import signal
import atexit
from datetime import datetime
from pathlib import Path
import json

class DualLogger:
    def __init__(self):
        self.main_log_dir = "logs"
        self.sub_log_dir = "/mnt/log_sd/cansat_logs"
        self.log_queue = queue.Queue()
        self.running = True
        self.worker_thread = None
        self.buffer_size = 100
        self.flush_interval = 5  # 5초마다 플러시
        
        # 로그 레벨
        self.levels = {
            'DEBUG': 0,
            'INFO': 1,
            'WARNING': 2,
            'ERROR': 3,
            'CRITICAL': 4
        }
        
        self.current_level = 'INFO'
        
        # 초기화
        self._setup_directories()
        self._start_worker()
        self._setup_signal_handlers()
        
    def _setup_directories(self):
        """로그 디렉토리 설정"""
        try:
            # 메인 로그 디렉토리
            os.makedirs(self.main_log_dir, exist_ok=True)
            
            # 서브 로그 디렉토리 (SPI SD 카드)
            if os.path.exists("/mnt/log_sd"):
                os.makedirs(self.sub_log_dir, exist_ok=True)
                print(f"✅ 서브 로그 디렉토리 생성: {self.sub_log_dir}")
            else:
                print("⚠️ 서브 로그 디렉토리(/mnt/log_sd)를 찾을 수 없습니다")
                
        except Exception as e:
            print(f"❌ 로그 디렉토리 설정 실패: {e}")
    
    def _start_worker(self):
        """워커 스레드 시작"""
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
    def _worker_loop(self):
        """로그 처리 워커 루프"""
        buffer = []
        last_flush = time.time()
        
        while self.running:
            try:
                # 큐에서 로그 메시지 가져오기 (1초 타임아웃)
                try:
                    log_entry = self.log_queue.get(timeout=1)
                    buffer.append(log_entry)
                except queue.Empty:
                    pass
                
                # 버퍼가 가득 차거나 시간이 지나면 플러시
                current_time = time.time()
                if (len(buffer) >= self.buffer_size or 
                    (current_time - last_flush) >= self.flush_interval):
                    if buffer:
                        self._flush_buffer(buffer)
                        buffer = []
                        last_flush = current_time
                        
            except Exception as e:
                print(f"워커 루프 오류: {e}")
                time.sleep(1)
        
        # 종료 시 남은 버퍼 플러시
        if buffer:
            self._flush_buffer(buffer)
    
    def _flush_buffer(self, buffer):
        """버퍼를 파일에 플러시"""
        if not buffer:
            return
            
        try:
            # 현재 날짜로 파일명 생성
            date_str = datetime.now().strftime("%Y-%m-%d")
            main_log_file = os.path.join(self.main_log_dir, f"{date_str}_dual_log.txt")
            
            # 메인 SD에 로그 저장
            with open(main_log_file, 'a', encoding='utf-8') as f:
                for entry in buffer:
                    f.write(entry + '\n')
                    f.flush()  # 즉시 디스크에 쓰기
                    os.fsync(f.fileno())  # 강제 동기화
            
            # 서브 SD에 로그 저장 (SPI SD 카드)
            if os.path.exists("/mnt/log_sd"):
                sub_log_file = os.path.join(self.sub_log_dir, f"{date_str}_dual_log.txt")
                try:
                    with open(sub_log_file, 'a', encoding='utf-8') as f:
                        for entry in buffer:
                            f.write(entry + '\n')
                            f.flush()  # 즉시 디스크에 쓰기
                            os.fsync(f.fileno())  # 강제 동기화
                except Exception as e:
                    print(f"서브 SD 로그 저장 실패: {e}")
                    
        except Exception as e:
            print(f"로그 플러시 실패: {e}")
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self._cleanup)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n시그널 {signum} 수신, 로깅 시스템 종료 중...")
        self.shutdown()
    
    def _cleanup(self):
        """정리 작업"""
        self.shutdown()
    
    def shutdown(self):
        """로깅 시스템 종료"""
        print("이중 로깅 시스템 종료 중...")
        self.running = False
        
        # 남은 로그 처리
        remaining_logs = []
        while not self.log_queue.empty():
            try:
                remaining_logs.append(self.log_queue.get_nowait())
            except queue.Empty:
                break
        
        if remaining_logs:
            self._flush_buffer(remaining_logs)
        
        # 워커 스레드 종료 대기
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        
        print("이중 로깅 시스템 종료 완료")
    
    def log(self, level, message, source="SYSTEM", data=None):
        """로그 메시지 기록"""
        if self.levels.get(level, 0) < self.levels.get(self.current_level, 0):
            return
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 기본 로그 엔트리
        log_entry = f"[{timestamp}] [{level}] [{source}] {message}"
        
        # 추가 데이터가 있으면 JSON으로 추가
        if data:
            try:
                data_json = json.dumps(data, ensure_ascii=False)
                log_entry += f" | DATA: {data_json}"
            except:
                log_entry += f" | DATA: {str(data)}"
        
        # 큐에 추가
        try:
            self.log_queue.put(log_entry, timeout=1)
        except queue.Full:
            print(f"로그 큐가 가득 찼습니다: {log_entry[:100]}...")
    
    def debug(self, message, source="SYSTEM", data=None):
        self.log('DEBUG', message, source, data)
    
    def info(self, message, source="SYSTEM", data=None):
        self.log('INFO', message, source, data)
    
    def warning(self, message, source="SYSTEM", data=None):
        self.log('WARNING', message, source, data)
    
    def error(self, message, source="SYSTEM", data=None):
        self.log('ERROR', message, source, data)
    
    def critical(self, message, source="SYSTEM", data=None):
        self.log('CRITICAL', message, source, data)
    
    def sensor_data(self, sensor_name, data):
        """센서 데이터 로깅"""
        self.log('INFO', f"Sensor data: {sensor_name}", "SENSOR", data)
    
    def system_event(self, event_type, event_data):
        """시스템 이벤트 로깅"""
        self.log('INFO', f"System event: {event_type}", "SYSTEM", event_data)
    
    def emergency_save(self, data, filename=None):
        """긴급 데이터 저장 (강제 종료 시)"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"emergency_{timestamp}.json"
        
        try:
            # 메인 SD에 저장
            main_path = os.path.join(self.main_log_dir, filename)
            with open(main_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            # 서브 SD에 저장
            if os.path.exists("/mnt/log_sd"):
                sub_path = os.path.join(self.sub_log_dir, filename)
                with open(sub_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                    
            print(f"긴급 데이터 저장 완료: {filename}")
            
        except Exception as e:
            print(f"긴급 데이터 저장 실패: {e}")

# 전역 인스턴스
dual_logger = DualLogger()

# 편의 함수들
def log(level, message, source="SYSTEM", data=None):
    dual_logger.log(level, message, source, data)

def debug(message, source="SYSTEM", data=None):
    dual_logger.debug(message, source, data)

def info(message, source="SYSTEM", data=None):
    dual_logger.info(message, source, data)

def warning(message, source="SYSTEM", data=None):
    dual_logger.warning(message, source, data)

def error(message, source="SYSTEM", data=None):
    dual_logger.error(message, source, data)

def critical(message, source="SYSTEM", data=None):
    dual_logger.critical(message, source, data)

def sensor_data(sensor_name, data):
    dual_logger.sensor_data(sensor_name, data)

def system_event(event_type, event_data):
    dual_logger.system_event(event_type, event_data)

def emergency_save(data, filename=None):
    dual_logger.emergency_save(data, filename)

def shutdown():
    dual_logger.shutdown() 