#!/usr/bin/env python3
"""
Dual Logging System for CANSAT
메인 SD카드와 추가 SD카드에 동시에 로그를 저장하는 시스템
"""

import os
import time
import threading
from datetime import datetime
from typing import TextIO, Optional
from multiprocessing import Lock
import subprocess
import shutil

class DualLogger:
    def __init__(self, primary_log_dir="logs", secondary_log_dir="/mnt/log_sd/logs"):
        """
        이중 로깅 시스템 초기화
        
        Args:
            primary_log_dir: 메인 SD카드의 로그 디렉토리
            secondary_log_dir: 추가 SD카드의 로그 디렉토리
        """
        self.primary_log_dir = primary_log_dir
        self.secondary_log_dir = secondary_log_dir
        self.mutex = Lock()
        
        # 로그 디렉토리 생성
        self._create_log_directories()
        
        # 로그 파일 핸들러
        self.primary_file: Optional[TextIO] = None
        self.secondary_file: Optional[TextIO] = None
        
        # 로그 파일 초기화
        self._init_log_files()
        
        # 백업 스레드
        self.backup_thread = None
        self.backup_running = False
        
        # 추가 SD카드 상태 확인
        self.secondary_sd_available = self._check_secondary_sd()
        
        print(f"이중 로깅 시스템 초기화 완료")
        print(f"메인 로그: {self.primary_log_dir}")
        print(f"보조 로그: {self.secondary_log_dir}")
        print(f"보조 SD카드 상태: {'사용 가능' if self.secondary_sd_available else '사용 불가'}")
    
    def _create_log_directories(self):
        """로그 디렉토리 생성"""
        try:
            os.makedirs(self.primary_log_dir, exist_ok=True)
            if self.secondary_sd_available:
                os.makedirs(self.secondary_log_dir, exist_ok=True)
        except Exception as e:
            print(f"로그 디렉토리 생성 오류: {e}")
    
    def _check_secondary_sd(self):
        """추가 SD카드 사용 가능 여부 확인"""
        try:
            # /mnt/log_sd 마운트 확인
            if not os.path.ismount("/mnt/log_sd"):
                print("추가 SD카드가 마운트되지 않음")
                return False
            
            # 쓰기 권한 확인
            test_file = os.path.join(self.secondary_log_dir, "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                return True
            except Exception:
                print("추가 SD카드에 쓰기 권한 없음")
                return False
                
        except Exception as e:
            print(f"추가 SD카드 확인 오류: {e}")
            return False
    
    def _init_log_files(self):
        """로그 파일 초기화"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 메인 로그 파일
        primary_filename = os.path.join(self.primary_log_dir, f"cansat_log_{timestamp}.txt")
        try:
            self.primary_file = open(primary_filename, 'w', encoding='utf-8')
            print(f"메인 로그 파일 생성: {primary_filename}")
        except Exception as e:
            print(f"메인 로그 파일 생성 오류: {e}")
            self.primary_file = None
        
        # 보조 로그 파일 (SD카드 사용 가능한 경우만)
        if self.secondary_sd_available:
            secondary_filename = os.path.join(self.secondary_log_dir, f"cansat_log_{timestamp}.txt")
            try:
                self.secondary_file = open(secondary_filename, 'w', encoding='utf-8')
                print(f"보조 로그 파일 생성: {secondary_filename}")
            except Exception as e:
                print(f"보조 로그 파일 생성 오류: {e}")
                self.secondary_file = None
    
    def log(self, text: str, print_logs: bool = False):
        """
        이중 로깅 수행
        
        Args:
            text: 로그할 텍스트
            print_logs: 콘솔 출력 여부
        """
        try:
            with self.mutex:
                timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
                log_entry = f'[{timestamp}] {text}\n'
                
                # 메인 로그 파일에 저장
                if self.primary_file:
                    try:
                        self.primary_file.write(log_entry)
                        self.primary_file.flush()
                    except Exception as e:
                        print(f"메인 로그 파일 쓰기 오류: {e}")
                
                # 보조 로그 파일에 저장
                if self.secondary_file and self.secondary_sd_available:
                    try:
                        self.secondary_file.write(log_entry)
                        self.secondary_file.flush()
                    except Exception as e:
                        print(f"보조 로그 파일 쓰기 오류: {e}")
                        # 보조 SD카드 오류 시 재시도
                        self._retry_secondary_sd()
                
                # 콘솔 출력
                if print_logs:
                    print(log_entry.rstrip())
                    
        except Exception as e:
            print(f"로깅 오류: {e}")
    
    def _retry_secondary_sd(self):
        """보조 SD카드 재시도"""
        try:
            # 보조 SD카드 상태 재확인
            if self._check_secondary_sd():
                # 새로운 로그 파일 생성
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                secondary_filename = os.path.join(self.secondary_log_dir, f"cansat_log_{timestamp}.txt")
                self.secondary_file = open(secondary_filename, 'w', encoding='utf-8')
                print(f"보조 로그 파일 재생성: {secondary_filename}")
            else:
                self.secondary_sd_available = False
                print("보조 SD카드 사용 불가로 설정")
        except Exception as e:
            print(f"보조 SD카드 재시도 오류: {e}")
            self.secondary_sd_available = False
    
    def start_backup_thread(self):
        """백업 스레드 시작 (주기적으로 메인 로그를 보조 SD카드에 복사)"""
        if not self.secondary_sd_available:
            return
        
        self.backup_running = True
        self.backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        self.backup_thread.start()
        print("백업 스레드 시작")
    
    def _backup_worker(self):
        """백업 작업 스레드"""
        while self.backup_running:
            try:
                time.sleep(30)  # 30초마다 백업
                self._backup_logs()
            except Exception as e:
                print(f"백업 작업 오류: {e}")
    
    def _backup_logs(self):
        """로그 파일 백업"""
        try:
            # 메인 로그 디렉토리의 모든 파일을 보조 SD카드로 복사
            for filename in os.listdir(self.primary_log_dir):
                if filename.endswith('.txt') or filename.endswith('.csv'):
                    primary_path = os.path.join(self.primary_log_dir, filename)
                    secondary_path = os.path.join(self.secondary_log_dir, filename)
                    
                    # 파일이 존재하지 않거나 크기가 다른 경우에만 복사
                    if not os.path.exists(secondary_path) or \
                       os.path.getsize(primary_path) != os.path.getsize(secondary_path):
                        shutil.copy2(primary_path, secondary_path)
                        print(f"로그 백업: {filename}")
                        
        except Exception as e:
            print(f"로그 백업 오류: {e}")
    
    def stop_backup_thread(self):
        """백업 스레드 중지"""
        self.backup_running = False
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        print("백업 스레드 중지")
    
    def close(self):
        """로깅 시스템 종료"""
        self.stop_backup_thread()
        
        if self.primary_file:
            self.primary_file.close()
        
        if self.secondary_file:
            self.secondary_file.close()
        
        print("이중 로깅 시스템 종료")

# 전역 이중 로거 인스턴스
dual_logger: Optional[DualLogger] = None

def init_dual_logging(primary_log_dir="logs", secondary_log_dir="/mnt/log_sd/logs"):
    """이중 로깅 시스템 초기화"""
    global dual_logger
    dual_logger = DualLogger(primary_log_dir, secondary_log_dir)
    dual_logger.start_backup_thread()
    return dual_logger

def logdata(target: TextIO, text: str, printlogs=False):
    """
    기존 로깅 함수와 호환되는 이중 로깅 함수
    """
    global dual_logger
    
    # 기존 방식으로도 로깅
    try:
        from multiprocessing import Lock
        mutex = Lock()
        with mutex:
            t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            string_to_write = f'[{t}] {text}'
            if printlogs:
                print(string_to_write)
            target.write(string_to_write + '\n')
            target.flush()
    except Exception as e:
        print(f"Error while Logging : {e}")
    
    # 이중 로깅 시스템에도 로깅
    if dual_logger:
        dual_logger.log(text, printlogs)

def close_dual_logging():
    """이중 로깅 시스템 종료"""
    global dual_logger
    if dual_logger:
        dual_logger.close()
        dual_logger = None 