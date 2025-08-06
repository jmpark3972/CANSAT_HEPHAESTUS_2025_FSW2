# CANSAT HEPHAESTUS 2025 FSW2 - 이중 로깅 시스템 설정 가이드

## 📋 개요

이중 로깅 시스템은 메인 SD 카드와 서브 SD 카드(SPI 인터페이스)에 동시에 로그를 저장하여 데이터 손실을 방지하는 시스템입니다. 강제 종료 시에도 데이터가 보호됩니다.

## 🎯 주요 기능

- **이중 저장**: 메인 SD + 서브 SD 카드에 동시 저장
- **강제 종료 보호**: Ctrl+C, SIGTERM 시에도 데이터 보호
- **실시간 동기화**: 버퍼링과 즉시 플러시로 데이터 안전성 확보
- **자동 복구**: 서브 SD 카드 오류 시 메인 SD만으로 계속 작동

## 🔧 하드웨어 요구사항

### 필수 하드웨어
- 라즈베리파이 (메인 SD 카드)
- 추가 SD 카드 (서브 SD 카드)
- SPI 연결 케이블

### SPI 핀 연결
```
라즈베리파이    SD 카드 모듈
GPIO 10 (MOSI) → MOSI
GPIO 9  (MISO) → MISO  
GPIO 11 (SCLK) → SCK
GPIO 7  (CS1)  → CS
3.3V           → VCC
GND            → GND
```

## 🚀 설치 및 설정

### 1단계: SPI SD 카드 설정

```bash
# 1. 설정 스크립트 실행
chmod +x setup_spi_sd.sh
./setup_spi_sd.sh

# 2. 재부팅
sudo reboot
```

### 2단계: 재부팅 후 설정

```bash
# 1. 재부팅 후 설정 스크립트 실행
chmod +x setup_spi_sd_post_reboot.sh
./setup_spi_sd_post_reboot.sh
```

### 3단계: 이중 로깅 시스템 테스트

```bash
# 이중 로깅 시스템 테스트
python3 test/test_dual_logging.py
```

## 📁 디렉토리 구조

### 메인 SD 카드
```
logs/
├── cansat_videos/          # 비디오 파일
├── cansat_camera_temp/     # 카메라 임시 파일
├── cansat_camera_logs/     # 카메라 로그
├── thermal_videos/         # 열화상 비디오
└── YYYY-MM-DD_dual_log.txt # 이중 로그 파일
```

### 서브 SD 카드 (SPI)
```
/mnt/log_sd/
├── cansat_logs/            # 메인 로그
├── cansat_videos/          # 비디오 파일 (복사본)
├── cansat_camera_temp/     # 카메라 임시 파일
├── cansat_camera_logs/     # 카메라 로그
├── thermal_videos/         # 열화상 비디오
└── YYYY-MM-DD_dual_log.txt # 이중 로그 파일
```

## 💻 사용법

### 기본 로깅

```python
from lib.dual_logging import info, warning, error, debug

# 기본 로깅
info("시스템 시작", "SYSTEM")
warning("경고 메시지", "SENSOR")
error("오류 발생", "CAMERA")
debug("디버그 정보", "DEBUG")
```

### 센서 데이터 로깅

```python
from lib.dual_logging import sensor_data

# 센서 데이터 로깅
sensor_data("BAROMETER", {
    "altitude": 100.5,
    "temperature": 25.3,
    "pressure": 1013.25
})
```

### 시스템 이벤트 로깅

```python
from lib.dual_logging import system_event

# 시스템 이벤트 로깅
system_event("FLIGHT_STATE_CHANGE", {
    "old_state": "ASCENT",
    "new_state": "DESCENT",
    "altitude": 150.0
})
```

### 긴급 데이터 저장

```python
from lib.dual_logging import emergency_save

# 긴급 데이터 저장 (강제 종료 시)
emergency_data = {
    "timestamp": "2025-08-06T14:30:00",
    "flight_data": {...},
    "sensor_data": {...}
}
emergency_save(emergency_data, "emergency_flight_data.json")
```

## 🔍 모니터링 및 확인

### 로그 파일 확인

```bash
# 메인 로그 확인
tail -f logs/$(date +%Y-%m-%d)_dual_log.txt

# 서브 로그 확인
tail -f /mnt/log_sd/cansat_logs/$(date +%Y-%m-%d)_dual_log.txt
```

### 디스크 사용량 확인

```bash
# 메인 SD 사용량
df -h /home/pi

# 서브 SD 사용량
df -h /mnt/log_sd
```

### 동기화 상태 확인

```bash
# 로그 파일 비교
diff logs/$(date +%Y-%m-%d)_dual_log.txt /mnt/log_sd/cansat_logs/$(date +%Y-%m-%d)_dual_log.txt
```

## ⚠️ 문제 해결

### 서브 SD 카드가 마운트되지 않는 경우

```bash
# 1. SPI 설정 확인
sudo vcgencmd get_config str | grep spi

# 2. 오버레이 확인
ls -la /boot/firmware/overlays/spi_sd1.dtbo

# 3. config.txt 확인
grep -i spi /boot/firmware/config.txt

# 4. 재부팅
sudo reboot
```

### 로그 동기화 실패

```bash
# 1. 서브 SD 카드 상태 확인
lsblk | grep mmcblk

# 2. 마운트 상태 확인
mount | grep log_sd

# 3. 권한 확인
ls -la /mnt/log_sd/

# 4. 수동 마운트
sudo mount -a
```

### 디스크 공간 부족

```bash
# 1. 사용량 확인
df -h

# 2. 오래된 로그 파일 정리
find logs/ -name "*.txt" -mtime +7 -delete
find /mnt/log_sd/cansat_logs/ -name "*.txt" -mtime +7 -delete

# 3. 비디오 파일 정리
find logs/cansat_videos/ -name "*.mp4" -mtime +3 -delete
find /mnt/log_sd/cansat_videos/ -name "*.mp4" -mtime +3 -delete
```

## 🔧 고급 설정

### 로그 레벨 변경

```python
from lib.dual_logging import dual_logger

# 로그 레벨 설정 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
dual_logger.current_level = 'DEBUG'
```

### 버퍼 크기 조정

```python
from lib.dual_logging import dual_logger

# 버퍼 크기 조정 (기본값: 100)
dual_logger.buffer_size = 50

# 플러시 간격 조정 (기본값: 5초)
dual_logger.flush_interval = 3
```

### 커스텀 로그 포맷

```python
from lib.dual_logging import dual_logger
from datetime import datetime

# 커스텀 로그 함수
def custom_log(message, data=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    log_entry = f"[{timestamp}] [CUSTOM] {message}"
    if data:
        log_entry += f" | DATA: {data}"
    dual_logger.log_queue.put(log_entry)
```

## 📊 성능 최적화

### 권장 설정

1. **버퍼 크기**: 50-100 (메모리 사용량과 성능의 균형)
2. **플러시 간격**: 3-5초 (데이터 안전성과 성능의 균형)
3. **로그 레벨**: INFO (프로덕션), DEBUG (개발)

### 모니터링 지표

- 로그 파일 크기
- 동기화 지연 시간
- 디스크 사용량
- 메모리 사용량

## 🚨 주의사항

1. **서브 SD 카드 품질**: 고품질 SD 카드 사용 권장
2. **정기 백업**: 중요한 데이터는 별도 백업
3. **디스크 공간**: 충분한 여유 공간 확보
4. **전원 안정성**: 안정적인 전원 공급 필요

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. 로그 파일 확인
2. 하드웨어 연결 상태
3. SPI 설정 상태
4. 디스크 사용량

---

**팀**: HEPHAESTUS  
**버전**: 1.0  
**최종 업데이트**: 2025-08-06 