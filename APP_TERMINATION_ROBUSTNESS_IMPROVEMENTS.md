# 앱 종료 견고성 개선 사항

## 개요
사용자 요구사항: "하나의 앱이 선빠져서 강제 종료되어도 나머지 앱들은 정상작동 하고, 로그도 남아야해"

이 문서는 CANSAT FSW의 개별 앱이 강제 종료되어도 전체 시스템이 계속 작동하고 로그가 보존되도록 개선한 사항들을 정리합니다.

## 🔧 주요 개선 사항

### 1. 메인 프로세스 관리 개선 (`main.py`, `main_safe.py`)

#### 1.1 자동 재시작 시스템
- **중요도별 앱 분류**:
  - **Critical Apps**: HK, Comm, FlightLogic (시스템 핵심)
  - **Sensor Apps**: Barometer, GPS, IMU, Thermis, Thermo, Motor (중간 중요도)
  - **Non-Critical Apps**: FIR1, ThermalCamera, TMP007 (낮은 중요도)

#### 1.2 재시작 정책
```python
# 중요 앱: 즉시 재시작 시도
if appID in critical_apps:
    restart_app(appID)

# 센서 앱: 재시작 시도하되 실패해도 계속 진행
elif appID in sensor_apps:
    if restart_app(appID):
        # 성공
    else:
        # 실패해도 계속 진행

# 비중요 앱: 재시작하지 않고 계속 진행
elif appID in non_critical_apps:
    # 계속 진행
```

#### 1.3 재시작 제한
- 재시작 간격 제한: 30초 (무한 재시작 방지)
- 프로세스 정리: 기존 프로세스 종료 후 새 프로세스 생성
- 파이프 재생성: 연결이 끊어진 파이프 재생성

### 2. 개별 앱 견고성 개선

#### 2.1 파이프 통신 오류 처리
```python
try:
    message = Main_Pipe.recv()
except (EOFError, BrokenPipeError, ConnectionResetError) as e:
    safe_log(f"Pipe connection lost: {e}", "warning".upper(), True)
    # 연결이 끊어져도 로깅은 계속
    time.sleep(1)
    continue
```

#### 2.2 우아한 종료 처리
```python
except (KeyboardInterrupt, SystemExit):
    safe_log("App received termination signal", "info".upper(), True)
    APP_RUNSTATUS = False
except Exception as e:
    safe_log(f"Critical error: {e}", "error".upper(), True)
    APP_RUNSTATUS = False
    # 치명적 오류 발생 시에도 로깅은 계속
```

#### 2.3 종료 과정 보호
```python
try:
    app_terminate()
except Exception as e:
    # 종료 과정에서 오류가 발생해도 최소한의 로깅 시도
    try:
        print(f"[APP] Termination error: {e}")
    except:
        pass
```

### 3. 로깅 시스템 견고성 개선 (`lib/logging/unified_logging.py`)

#### 3.1 비동기 로깅 시스템
- **로그 워커 스레드**: 백그라운드에서 로그 처리
- **큐 기반 처리**: 메인 스레드 블로킹 방지
- **버퍼 시스템**: 로그 큐가 가득 찰 때 메모리 버퍼 사용

#### 3.2 파일 핸들러 관리
```python
def _get_file_handler(filepath: str):
    """파일 핸들러 가져오기 (프로세스 안전)"""
    if filepath not in _file_handlers:
        try:
            _ensure_log_directory()
            _file_handlers[filepath] = open(filepath, 'a', encoding='utf-8', buffering=1)
            _file_locks[filepath] = threading.Lock()
        except Exception as e:
            return None, None
    return _file_handlers[filepath], _file_locks[filepath]
```

#### 3.3 안전한 로그 쓰기
```python
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
    except Exception as e:
        # 파일 쓰기 실패 시에도 버퍼에 저장
        _log_buffer.append(f"[BUFFER-FAIL] {message}")
```

#### 3.4 긴급 로깅 함수
```python
def emergency_log(message: str, app_name: str = "EMERGENCY"):
    """긴급 로깅 함수 - 로깅 시스템이 실패해도 작동"""
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
```

### 4. 프로세스 종료 시 로그 보존

#### 4.1 시그널 핸들러
```python
def _signal_handler(signum, frame):
    """시그널 핸들러 (프로세스 종료 시 로그 보존)"""
    try:
        _cleanup_logging()
    except:
        pass
    sys.exit(0)
```

#### 4.2 종료 시 정리
```python
def _cleanup_logging():
    """로깅 시스템 정리"""
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
        
        # 버퍼 내용을 파일에 저장
        if _log_buffer:
            _write_log_safe(MAIN_LOG_PATH, f"[BUFFER_DUMP] {len(_log_buffer)} buffered messages")
            for buffered_msg in _log_buffer:
                _write_log_safe(MAIN_LOG_PATH, buffered_msg)
    except Exception as e:
        # 정리 과정에서 오류가 발생해도 무시
        pass
```

## 📊 개선된 앱 목록

### 메인 프로세스
- ✅ `main.py` - 자동 재시작 시스템 추가
- ✅ `main_safe.py` - 자동 재시작 시스템 추가

### 핵심 앱들
- ✅ `hk/hkapp.py` - 파이프 오류 처리, 우아한 종료
- ✅ `gps/gpsapp.py` - 파이프 오류 처리, 우아한 종료
- ✅ `imu/imuapp.py` - 파이프 오류 처리, 우아한 종료
- ✅ `comm/commapp.py` - 파이프 오류 처리, 우아한 종료

### 로깅 시스템
- ✅ `lib/logging/unified_logging.py` - 완전히 새로운 견고한 로깅 시스템

## 🎯 달성된 목표

### 1. 개별 앱 강제 종료 시나리오
- ✅ **메인 프로세스 계속 작동**: 개별 앱이 죽어도 메인 루프는 계속 실행
- ✅ **자동 재시작**: 중요 앱과 센서 앱은 자동으로 재시작 시도
- ✅ **우선순위 기반 처리**: 앱 중요도에 따른 차별화된 처리

### 2. 로그 보존
- ✅ **로그 시스템 견고성**: 로깅 시스템 자체가 실패해도 최소한의 로그 보존
- ✅ **버퍼 시스템**: 메모리 버퍼를 통한 로그 백업
- ✅ **파일 핸들러 관리**: 프로세스 안전한 파일 핸들링
- ✅ **종료 시 로그 보존**: 프로세스 종료 시에도 로그 보존

### 3. 시스템 안정성
- ✅ **파이프 오류 처리**: 연결 끊김 시에도 계속 진행
- ✅ **예외 처리 강화**: 모든 주요 함수에 예외 처리 추가
- ✅ **리소스 정리**: 프로세스 종료 시 적절한 리소스 정리

## 🔍 테스트 시나리오

### 시나리오 1: 개별 앱 강제 종료
1. 시스템 정상 실행
2. 개별 앱 프로세스 강제 종료 (`kill -9`)
3. 메인 프로세스가 앱 상태 감지
4. 중요도에 따른 재시작 시도
5. 로그 확인

### 시나리오 2: 파이프 연결 끊김
1. 개별 앱의 파이프 연결 강제 종료
2. 앱이 파이프 오류 감지
3. 오류 로깅 후 계속 진행
4. 메인 프로세스에서 재시작 시도

### 시나리오 3: 로깅 시스템 스트레스
1. 대량의 로그 메시지 생성
2. 로그 큐 가득 참 상황
3. 버퍼 시스템 작동 확인
4. 로그 손실 없음 확인

## 📈 성능 개선

### 메모리 사용량
- 로그 버퍼 크기: 1000개 메시지
- 큐 크기: 1000개 메시지
- 파일 핸들러 캐싱으로 I/O 최적화

### 응답성
- 비동기 로깅으로 메인 스레드 블로킹 방지
- 타임아웃 기반 파이프 폴링으로 응답성 향상
- 재시작 간격 제한으로 시스템 부하 방지

### 안정성
- 모든 주요 함수에 예외 처리 추가
- 파일 I/O 실패 시에도 계속 진행
- 프로세스 종료 시 적절한 정리 작업

## 🚀 사용법

### 일반적인 사용
```python
from lib.logging import safe_log

# 일반 로깅
safe_log("정상 작동 중", "INFO", True, "MyApp")

# 에러 로깅
safe_log("오류 발생", "ERROR", True, "MyApp")
```

### 긴급 상황
```python
from lib.logging import emergency_log

# 긴급 로깅 (로깅 시스템이 실패해도 작동)
emergency_log("치명적 오류 발생", "CriticalApp")
```

### 로그 버퍼 확인
```python
from lib.logging import get_log_buffer, flush_logs

# 버퍼 내용 확인
buffer = get_log_buffer()
print(f"버퍼에 {len(buffer)}개 메시지 저장됨")

# 버퍼를 파일에 강제 쓰기
flush_logs()
```

## 📝 주의사항

1. **재시작 제한**: 앱 재시작은 30초 간격으로 제한됩니다.
2. **로그 버퍼**: 메모리 기반이므로 시스템 재부팅 시 손실될 수 있습니다.
3. **파일 권한**: 로그 디렉토리에 쓰기 권한이 필요합니다.
4. **디스크 공간**: 로그 파일이 계속 증가하므로 주기적 정리가 필요합니다.

## 🔄 향후 개선 계획

1. **로그 로테이션**: 자동 로그 파일 로테이션 시스템
2. **원격 로깅**: 네트워크를 통한 원격 로그 전송
3. **로그 압축**: 로그 파일 압축으로 디스크 공간 절약
4. **모니터링 대시보드**: 실시간 시스템 상태 모니터링

---

**작성자**: Hyeon Lee (HEPHAESTUS)  
**작성일**: 2025년  
**버전**: 2.0 