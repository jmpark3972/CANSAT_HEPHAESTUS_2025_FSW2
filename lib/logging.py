#!/usr/bin/env python3
"""
CANSAT FSW 통합 로깅 시스템
이중 로깅 (주 SD카드 + 보조 SD카드) 지원
"""

import os
import sys
import time
import shutil
import threading
import signal
import atexit
from datetime import datetime
from typing import TextIO, Type
from pathlib import Path

# 전역 변수
_dual_logger = None
mutex = threading.Lock()

class DualLogger:
    """이중 로깅 시스템 클래스"""
    
    def __init__(self, primary_log_dir="logs", secondary_log_dir="/mnt/log_sd/logs"):
        """이중 로깅 시스템 초기화"""
        self.primary_log_dir = primary_log_dir
        self.secondary_log_dir = secondary_log_dir
        self.primary_log_file = None
        self.secondary_log_file = None
        self.backup_thread = None
        self.recovery_thread = None
        self.running = True
        
        # 로그 디렉토리 생성
        self._create_log_directories()
        
        # 로그 파일 초기화
        self._init_log_files()
        
        # 시그널 핸들러 설정
        self._setup_signal_handlers()
        
        # 종료 시 정리 함수 등록
        atexit.register(self._cleanup_on_exit)
        
        # 백업 및 복구 스레드 시작
        self.start_backup_thread()
        self.start_recovery_thread()
    
    def _setup_signal_handlers(self):
        """시그널 핸들러 설정"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"시그널 {signum} 수신, 로깅 시스템 종료 중...")
        self._emergency_save()
        self.close()
        sys.exit(0)
    
    def _emergency_save(self):
        """긴급 저장"""
        try:
            if self.primary_log_file:
                self.primary_log_file.flush()
            if self.secondary_log_file:
                self.secondary_log_file.flush()
        except Exception as e:
            print(f"긴급 저장 오류: {e}")
    
    def _cleanup_on_exit(self):
        """종료 시 정리"""
        try:
            self.close()
        except Exception as e:
            print(f"종료 시 정리 오류: {e}")
    
    def _create_log_directories(self):
        """로그 디렉토리 생성"""
        try:
            # 주 로그 디렉토리 생성
            os.makedirs(self.primary_log_dir, exist_ok=True)
            
            # 보조 로그 디렉토리 확인 및 생성
            if self._check_secondary_sd():
                os.makedirs(self.secondary_log_dir, exist_ok=True)
                print(f"이중 로깅 시스템 활성화: {self.secondary_log_dir}")
            else:
                print("보조 SD카드가 마운트되지 않음, 단일 로깅 모드")
                
        except Exception as e:
            print(f"로그 디렉토리 생성 오류: {e}")
    
    def _check_secondary_sd(self):
        """보조 SD카드 상태 확인"""
        try:
            # 보조 SD카드 마운트 확인
            if os.path.exists(self.secondary_log_dir):
                # 쓰기 권한 확인
                test_file = os.path.join(self.secondary_log_dir, "test_write.tmp")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    return True
                except Exception as e:
                    print(f"파일 쓰기 테스트 오류: {e}")
                    return False
            return False
        except Exception as e:
            print(f"보조 SD카드 확인 오류: {e}")
            return False
    
    def _init_log_files(self):
        """로그 파일 초기화"""
        try:
            # 주 로그 파일
            primary_log_path = os.path.join(self.primary_log_dir, "system.log")
            self.primary_log_file = open(primary_log_path, 'a', encoding='utf-8')
            
            # 보조 로그 파일 (가능한 경우)
            if self._check_secondary_sd():
                secondary_log_path = os.path.join(self.secondary_log_dir, "system.log")
                self.secondary_log_file = open(secondary_log_path, 'a', encoding='utf-8')
                
        except Exception as e:
            print(f"로그 파일 초기화 오류: {e}")
    
    def _write_to_files(self, log_entry):
        """로그 파일에 쓰기"""
        try:
            # 주 로그 파일에 쓰기
            if self.primary_log_file:
                self.primary_log_file.write(log_entry + '\n')
                self.primary_log_file.flush()
            
            # 보조 로그 파일에 쓰기 (가능한 경우)
            if self.secondary_log_file:
                try:
                    self.secondary_log_file.write(log_entry + '\n')
                    self.secondary_log_file.flush()
                except Exception as e:
                    print(f"보조 로그 파일 쓰기 오류: {e}")
                    # 보조 파일 재생성 시도
                    self._recreate_secondary_file()
                    
        except Exception as e:
            print(f"로그 파일 쓰기 오류: {e}")
            # 주 파일 재생성 시도
            self._recreate_primary_file()
    
    def _recreate_primary_file(self):
        """주 로그 파일 재생성"""
        try:
            if self.primary_log_file:
                self.primary_log_file.close()
            primary_log_path = os.path.join(self.primary_log_dir, "system.log")
            self.primary_log_file = open(primary_log_path, 'a', encoding='utf-8')
        except Exception as e:
            print(f"주 로그 파일 재생성 오류: {e}")
    
    def _recreate_secondary_file(self):
        """보조 로그 파일 재생성"""
        try:
            if self.secondary_log_file:
                self.secondary_log_file.close()
            if self._check_secondary_sd():
                secondary_log_path = os.path.join(self.secondary_log_dir, "system.log")
                self.secondary_log_file = open(secondary_log_path, 'a', encoding='utf-8')
        except Exception as e:
            print(f"보조 로그 파일 재생성 오류: {e}")
    
    def log(self, text: str, printlogs: bool = False):
        """로그 메시지 기록"""
        try:
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            log_entry = f"[{timestamp}] {text}"
            
            # 콘솔 출력 (필요한 경우)
            if printlogs:
                print(log_entry)
            
            # 파일에 쓰기
            self._write_to_files(log_entry)
            
        except Exception as e:
            print(f"로깅 오류: {e}")
    
    def start_backup_thread(self):
        """백업 스레드 시작"""
        self.backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
        self.backup_thread.start()
    
    def start_recovery_thread(self):
        """복구 스레드 시작"""
        self.recovery_thread = threading.Thread(target=self._recovery_worker, daemon=True)
        self.recovery_thread.start()
    
    def _backup_worker(self):
        """백업 작업자 스레드"""
        while self.running:
            try:
                time.sleep(300)  # 5분마다 백업
                self._backup_logs()
            except Exception as e:
                print(f"백업 스레드 오류: {e}")
    
    def _recovery_worker(self):
        """복구 작업자 스레드"""
        while self.running:
            try:
                time.sleep(60)  # 1분마다 복구 체크
                self._check_and_recover()
            except Exception as e:
                print(f"복구 스레드 오류: {e}")
    
    def _check_and_recover(self):
        """복구 체크 및 실행"""
        try:
            # 보조 SD카드 상태 확인
            if not self._check_secondary_sd() and self.secondary_log_file:
                print("보조 SD카드 연결 끊김 감지")
                self.secondary_log_file = None
            elif self._check_secondary_sd() and not self.secondary_log_file:
                print("보조 SD카드 재연결 감지")
                self._recreate_secondary_file()
        except Exception as e:
            print(f"복구 체크 오류: {e}")
    
    def _backup_logs(self):
        """로그 백업"""
        try:
            # 주 로그 백업
            if self.primary_log_file:
                primary_log_path = os.path.join(self.primary_log_dir, "system.log")
                if os.path.exists(primary_log_path):
                    backup_path = os.path.join(self.primary_log_dir, f"system_backup_{int(time.time())}.log")
                    shutil.copy2(primary_log_path, backup_path)
            
            # 보조 로그 백업
            if self.secondary_log_file and self._check_secondary_sd():
                secondary_log_path = os.path.join(self.secondary_log_dir, "system.log")
                if os.path.exists(secondary_log_path):
                    backup_path = os.path.join(self.secondary_log_dir, f"system_backup_{int(time.time())}.log")
                    shutil.copy2(secondary_log_path, backup_path)
                    
        except Exception as e:
            print(f"로그 백업 오류: {e}")
    
    def close(self):
        """로깅 시스템 종료"""
        self.running = False
        
        if self.primary_log_file:
            try:
                self.primary_log_file.close()
            except Exception as e:
                print(f"주 로그 파일 닫기 오류: {e}")
        
        if self.secondary_log_file:
            try:
                self.secondary_log_file.close()
            except Exception as e:
                print(f"보조 로그 파일 닫기 오류: {e}")

# 전역 로깅 함수들
def log(text: str, printlogs: bool = False):
    """통합 로깅 함수"""
    if _dual_logger:
        try:
            _dual_logger.log(text, printlogs)
        except Exception as e:
            # 로깅 실패 시에도 최소한 콘솔에 출력
            print(f"로깅 실패: {e}")
            if printlogs:
                print(text)
    else:
        # 이중 로깅이 초기화되지 않은 경우 기본 출력
        if printlogs:
            print(text)

def init_dual_logging_system(primary_log_dir="logs", secondary_log_dir="/mnt/log_sd/logs"):
    """이중 로깅 시스템 초기화"""
    global _dual_logger
    try:
        _dual_logger = DualLogger(primary_log_dir, secondary_log_dir)
        print("이중 로깅 시스템 초기화 완료")
        return _dual_logger
    except Exception as e:
        print(f"이중 로깅 시스템 초기화 오류: {e}")
        return None

def close_dual_logging_system():
    """이중 로깅 시스템 종료"""
    global _dual_logger
    try:
        if _dual_logger:
            _dual_logger.close()
            _dual_logger = None
        print("이중 로깅 시스템 종료 완료")
    except Exception as e:
        print(f"이중 로깅 시스템 종료 오류: {e}")

def check_and_rotate_log_file(filepath: str, max_size_mb: int = 10):
    """로그 파일 크기를 체크하고 필요시 로테이션"""
    try:
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            max_size_bytes = max_size_mb * 1024 * 1024  # MB to bytes
            
            if file_size > max_size_bytes:
                # 백업 파일 생성
                backup_path = f"{filepath}.backup"
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                shutil.move(filepath, backup_path)
                
                # 새 파일 생성
                with open(filepath, 'w') as f:
                    f.write(f"# Log rotated at {datetime.now().isoformat()}\n")
                    
    except Exception as e:
        print(f"로그 회전 실패: {filepath} - {e}")

def safe_write_to_file(filepath: str, content: str, max_size_mb: int = 10):
    """안전한 파일 쓰기 (크기 체크 포함)"""
    try:
        # 로그 파일 크기 체크
        check_and_rotate_log_file(filepath, max_size_mb)
        
        # 파일에 쓰기
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(content)
            f.flush()  # 즉시 디스크에 쓰기
            
    except Exception as e:
        print(f"파일 쓰기 오류: {filepath} - {e}")

# 기존 호환성을 위한 함수 (deprecated)
def logdata(target: TextIO, text: str, printlogs=False):
    """데이터를 로깅할 때 사용 (기존 호환성 유지)"""
    log(text, printlogs)