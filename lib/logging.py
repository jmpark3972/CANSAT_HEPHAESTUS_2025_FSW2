from typing import Type, TextIO
from datetime import datetime
from multiprocessing import Lock
import os
import threading
import time
import shutil
import signal
import sys
import atexit

mutex = Lock()

# 전역 이중 로거 인스턴스
_dual_logger = None

class DualLogger:
    """이중 로깅 시스템을 관리하는 클래스 - 플라이트 로직과 완전히 분리"""
    
    def __init__(self, primary_log_dir="logs", secondary_log_dir="/mnt/log_sd/logs"):
        self.primary_log_dir = primary_log_dir
        self.secondary_log_dir = secondary_log_dir
        self.primary_log_file = None
        self.secondary_log_file = None
        self.backup_thread = None
        self.backup_running = False
        self.recovery_thread = None
        self.recovery_running = False
        self.log_buffer = []
        self.buffer_lock = threading.Lock()
        
        # 시그널 핸들러 등록
        self._setup_signal_handlers()
        
        # 종료 시 정리 함수 등록
        atexit.register(self._cleanup_on_exit)
        
        self._create_log_directories()
        self._check_secondary_sd()
        self._init_log_files()
        self.start_backup_thread()
        self.start_recovery_thread()
    
    def _setup_signal_handlers(self):
        """시스템 시그널 핸들러 설정"""
        try:
            signal.signal(signal.SIGTERM, self._signal_handler)
            signal.signal(signal.SIGINT, self._signal_handler)
        except Exception as e:
            print(f"시그널 핸들러 설정 오류: {e}")
    
    def _signal_handler(self, signum, frame):
        """시그널 핸들러 - 강제 종료 시에도 로그 저장"""
        print(f"시그널 {signum} 수신, 로그 시스템 정리 중...")
        self._emergency_save()
        self.close()
        sys.exit(0)
    
    def _emergency_save(self):
        """비상 시 로그 저장"""
        try:
            with self.buffer_lock:
                if self.log_buffer:
                    # 버퍼의 모든 로그를 즉시 저장
                    for log_entry in self.log_buffer:
                        self._write_to_files(log_entry)
                    self.log_buffer.clear()
        except Exception as e:
            print(f"비상 로그 저장 오류: {e}")
    
    def _cleanup_on_exit(self):
        """프로그램 종료 시 정리"""
        try:
            self._emergency_save()
            self.close()
        except Exception as e:
            print(f"종료 시 정리 오류: {e}")
    
    def _create_log_directories(self):
        """로그 디렉토리 생성 - 여러 번 시도"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # 현재 작업 디렉토리 기준으로 상대 경로 사용
                primary_path = os.path.abspath(self.primary_log_dir)
                os.makedirs(primary_path, exist_ok=True)
                print(f"주 로그 디렉토리 생성/확인: {primary_path}")
                
                if self.secondary_log_dir:
                    try:
                        os.makedirs(self.secondary_log_dir, exist_ok=True)
                        print(f"보조 로그 디렉토리 생성/확인: {self.secondary_log_dir}")
                    except Exception as e:
                        print(f"보조 로그 디렉토리 생성 실패: {e}")
                        self.secondary_log_dir = None
                break
            except Exception as e:
                print(f"로그 디렉토리 생성 시도 {attempt + 1} 실패: {e}")
                if attempt == max_retries - 1:
                    print("로그 디렉토리 생성 최종 실패")
                    raise e
                time.sleep(1)
    
    def _check_secondary_sd(self):
        """보조 SD 카드 사용 가능 여부 확인 - 지속적 모니터링"""
        try:
            if not os.path.exists(self.secondary_log_dir):
                print(f"보조 SD 카드 마운트 포인트가 존재하지 않음: {self.secondary_log_dir}")
                # 디렉토리 생성 시도
                try:
                    os.makedirs(self.secondary_log_dir, exist_ok=True)
                    print(f"보조 로그 디렉토리 생성 성공: {self.secondary_log_dir}")
                except PermissionError:
                    print(f"보조 로그 디렉토리 생성 권한 없음: {self.secondary_log_dir}")
                    print("sudo mkdir -p /mnt/log_sd/logs && sudo chown -R SpaceY:SpaceY /mnt/log_sd/logs 명령을 실행하세요")
                    self.secondary_log_dir = None
                    return
                except Exception as e:
                    print(f"보조 로그 디렉토리 생성 실패: {e}")
                    self.secondary_log_dir = None
                    return
            
            # 쓰기 권한 확인
            test_file = os.path.join(self.secondary_log_dir, "test_write.tmp")
            try:
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
                print(f"보조 SD 카드 쓰기 권한 확인 완료: {self.secondary_log_dir}")
            except PermissionError:
                print(f"보조 SD 카드 쓰기 권한 없음: {self.secondary_log_dir}")
                print("sudo chown -R SpaceY:SpaceY /mnt/log_sd/logs && sudo chmod -R 755 /mnt/log_sd/logs 명령을 실행하세요")
                self.secondary_log_dir = None
            except Exception as e:
                print(f"보조 SD 카드 쓰기 테스트 실패: {e}")
                self.secondary_log_dir = None
        except Exception as e:
            print(f"보조 SD 카드 확인 오류: {e}")
            self.secondary_log_dir = None
    
    def _init_log_files(self):
        """로그 파일 초기화 - 자동 복구 포함"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 주 로그 파일
        primary_filename = f"system_log_{timestamp}.txt"
        primary_path = os.path.join(self.primary_log_dir, primary_filename)
        
        try:
            self.primary_log_file = open(primary_path, 'w', encoding='utf-8', buffering=8192)
            print(f"주 로그 파일 생성: {primary_path}")
        except Exception as e:
            print(f"주 로그 파일 생성 오류: {e}")
            self.primary_log_file = None
        
        # 보조 로그 파일
        if self.secondary_log_dir:
            secondary_filename = f"system_log_{timestamp}.txt"
            secondary_path = os.path.join(self.secondary_log_dir, secondary_filename)
            
            try:
                self.secondary_log_file = open(secondary_path, 'w', encoding='utf-8', buffering=8192)
                print(f"보조 로그 파일 생성: {secondary_path}")
            except Exception as e:
                print(f"보조 로그 파일 생성 오류: {e}")
                self.secondary_log_file = None
    
    def _write_to_files(self, log_entry):
        """파일에 로그 쓰기 - 개별 오류 처리"""
        # 주 로그 파일에 기록
        if self.primary_log_file:
            try:
                self.primary_log_file.write(log_entry)
                self.primary_log_file.flush()
            except Exception as e:
                print(f"주 로그 파일 기록 오류: {e}")
                # 파일 재생성 시도
                self._recreate_primary_file()
        
        # 보조 로그 파일에 기록
        if self.secondary_log_file:
            try:
                self.secondary_log_file.write(log_entry)
                self.secondary_log_file.flush()
            except Exception as e:
                print(f"보조 로그 파일 기록 오류: {e}")
                # 파일 재생성 시도
                self._recreate_secondary_file()
    
    def _recreate_primary_file(self):
        """주 로그 파일 재생성"""
        try:
            if self.primary_log_file:
                self.primary_log_file.close()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            primary_filename = f"system_log_{timestamp}_recovered.txt"
            primary_path = os.path.join(self.primary_log_dir, primary_filename)
            
            self.primary_log_file = open(primary_path, 'w', encoding='utf-8', buffering=8192)
            print(f"주 로그 파일 재생성: {primary_path}")
        except Exception as e:
            print(f"주 로그 파일 재생성 실패: {e}")
            self.primary_log_file = None
    
    def _recreate_secondary_file(self):
        """보조 로그 파일 재생성"""
        try:
            if self.secondary_log_file:
                self.secondary_log_file.close()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            secondary_filename = f"system_log_{timestamp}_recovered.txt"
            secondary_path = os.path.join(self.secondary_log_dir, secondary_filename)
            
            self.secondary_log_file = open(secondary_path, 'w', encoding='utf-8', buffering=8192)
            print(f"보조 로그 파일 재생성: {secondary_path}")
        except Exception as e:
            print(f"보조 로그 파일 재생성 실패: {e}")
            self.secondary_log_file = None
    
    def log(self, text: str, printlogs: bool = False):
        """로그 메시지를 두 위치에 동시에 기록 - 버퍼링 포함"""
        timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
        log_entry = f'[{timestamp}] {text}\n'
        
        # 버퍼에 추가
        with self.buffer_lock:
            self.log_buffer.append(log_entry)
            
            # 버퍼가 10개 이상이면 즉시 파일에 쓰기
            if len(self.log_buffer) >= 10:
                for entry in self.log_buffer:
                    self._write_to_files(entry)
                self.log_buffer.clear()
        
        # 콘솔 출력
        if printlogs:
            try:
                print(log_entry.rstrip())
            except Exception:
                pass  # 콘솔 출력 실패는 무시
    
    def start_backup_thread(self):
        """백업 스레드 시작"""
        if not self.backup_thread:
            self.backup_running = True
            self.backup_thread = threading.Thread(target=self._backup_worker, daemon=True)
            self.backup_thread.start()
    
    def start_recovery_thread(self):
        """복구 스레드 시작"""
        if not self.recovery_thread:
            self.recovery_running = True
            self.recovery_thread = threading.Thread(target=self._recovery_worker, daemon=True)
            self.recovery_thread.start()
    
    def _backup_worker(self):
        """백업 작업자 스레드"""
        while self.backup_running:
            try:
                time.sleep(30)  # 30초마다 백업
                self._backup_logs()
            except Exception as e:
                print(f"백업 스레드 오류: {e}")
                time.sleep(5)  # 오류 시 잠시 대기
    
    def _recovery_worker(self):
        """복구 작업자 스레드 - SD카드 상태 모니터링"""
        while self.recovery_running:
            try:
                time.sleep(60)  # 1분마다 체크
                self._check_and_recover()
            except Exception as e:
                print(f"복구 스레드 오류: {e}")
                time.sleep(10)
    
    def _check_and_recover(self):
        """SD카드 상태 확인 및 복구"""
        # 보조 SD카드 재확인
        if not self.secondary_log_dir:
            self._check_secondary_sd()
            if self.secondary_log_dir and not self.secondary_log_file:
                self._init_log_files()
        
        # 파일 상태 확인
        if self.primary_log_file and self.primary_log_file.closed:
            self._recreate_primary_file()
        
        if self.secondary_log_file and self.secondary_log_file.closed:
            self._recreate_secondary_file()
    
    def _backup_logs(self):
        """로그 파일 백업"""
        if not self.primary_log_dir or not self.secondary_log_dir:
            return
        
        try:
            # 주 로그 디렉토리의 모든 파일을 보조 로그 디렉토리로 복사
            for filename in os.listdir(self.primary_log_dir):
                if filename.endswith('.txt'):
                    primary_path = os.path.join(self.primary_log_dir, filename)
                    secondary_path = os.path.join(self.secondary_log_dir, filename)
                    
                    # 파일이 존재하지 않거나 크기가 다르면 복사
                    if not os.path.exists(secondary_path) or \
                       os.path.getsize(primary_path) != os.path.getsize(secondary_path):
                        shutil.copy2(primary_path, secondary_path)
        except Exception as e:
            print(f"로그 백업 오류: {e}")
    
    def close(self):
        """로그 파일들 닫기 - 모든 버퍼 저장"""
        # 버퍼의 모든 로그 저장
        self._emergency_save()
        
        self.backup_running = False
        self.recovery_running = False
        
        if self.backup_thread:
            self.backup_thread.join(timeout=5)
        
        if self.recovery_thread:
            self.recovery_thread.join(timeout=5)
        
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

def logdata(target: Type[TextIO], text: str, printlogs=False):
    """데이터를 로깅할 때 사용 (기존 호환성 유지)"""
    try:
        with mutex:
            t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            string_to_write = f'[{t}] {text}'
            if printlogs:
                print(string_to_write)
            target.write(string_to_write + '\n')
            target.flush()
    except Exception as e:
        print(f"Error while Logging : {e}")
        return
    
    # 이중 로깅 시스템에도 로깅
    if _dual_logger:
        try:
            _dual_logger.log(text, printlogs)
        except Exception as e:
            print(f"이중 로깅 오류: {e}")

def log(text: str, printlogs: bool = False):
    """새로운 통합 로깅 함수 - 플라이트 로직과 독립적"""
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
    """이중 로깅 시스템 초기화 - 강화된 오류 처리"""
    global _dual_logger
    try:
        _dual_logger = DualLogger(primary_log_dir, secondary_log_dir)
        print("이중 로깅 시스템 초기화 완료")
        return _dual_logger
    except Exception as e:
        print(f"이중 로깅 시스템 초기화 오류: {e}")
        # 초기화 실패 시에도 기본 로깅은 가능하도록
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
                    
                # events.LogEvent("Logging", events.EventType.info, f"Log file rotated: {filepath}") # events 모듈이 없으므로 주석 처리
    except Exception as e:
        # events.LogEvent("Logging", events.EventType.error, f"Log rotation failed for {filepath}: {e}") # events 모듈이 없으므로 주석 처리
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
        print(f"[로그 기록 오류] {filepath}: {e}")
        # 필요시, 별도 에러 로그 파일에 기록
        try:
            with open("logs/log_error.txt", "a") as errlog:
                from datetime import datetime
                errlog.write(f"{datetime.now().isoformat()} {filepath} {e}\n")
        except Exception as e2:
            print(f"[로그 기록 오류-2] log_error.txt: {e2}")