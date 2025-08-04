# 고주파수 데이터 수집 시스템

## 개요
센서 데이터를 최대한 많이 수집하기 위해 각 센서 앱의 데이터 수집 주파수를 높이고, 고주파수 로깅 시스템을 구축했습니다.

## 변경된 센서 앱들

### 1. IMU 앱 (`imu/imuapp.py`)
- **데이터 수집 주파수**: 100Hz → **200Hz** (5ms 간격)
- **Telemetry 전송 주파수**: 1Hz → **10Hz** (0.1초 간격)
- **새로운 로그 파일**:
  - `logs/imu/high_freq_imu_log.csv`: 200Hz 고주파수 IMU 데이터
  - `logs/imu/hk_log.csv`: HK 데이터 로그
  - `logs/imu/error_log.csv`: 오류 로그

### 2. Barometer 앱 (`barometer/barometerapp.py`)
- **데이터 수집 주파수**: 5Hz → **50Hz** (20ms 간격)
- **새로운 로그 파일**:
  - `logs/barometer/high_freq_barometer_log.csv`: 50Hz 고주파수 기압계 데이터
  - `logs/barometer/hk_log.csv`: HK 데이터 로그
  - `logs/barometer/error_log.csv`: 오류 로그

### 3. TMP007 앱 (`tmp007/tmp007app.py`)
- **데이터 수집 주파수**: 4Hz → **10Hz** (0.1초 간격)
- **새로운 로그 파일**:
  - `logs/tmp007/high_freq_tmp007_log.csv`: 10Hz 고주파수 TMP007 데이터
  - `logs/tmp007/hk_log.csv`: HK 데이터 로그
  - `logs/tmp007/error_log.csv`: 오류 로그

### 4. Pitot 앱 (`pitot/pitotapp.py`)
- **데이터 수집 주파수**: 5Hz → **20Hz** (50ms 간격)
- **새로운 로그 파일**:
  - `logs/pitot/high_freq_pitot_log.csv`: 20Hz 고주파수 Pitot 데이터
  - `logs/pitot/hk_log.csv`: HK 데이터 로그
  - `logs/pitot/error_log.csv`: 오류 로그

## 로깅 시스템 특징

### 1. 고주파수 CSV 로깅
- 각 센서마다 별도의 고주파수 로그 파일 생성
- 밀리초 단위 타임스탬프 포함
- CSV 형식으로 구조화된 데이터 저장

### 2. 강제 종료 시 로그 보존
- `emergency_log_to_file()` 함수로 강제 종료 시에도 로그 저장
- 각 센서 앱에서 독립적인 로그 디렉토리 관리

### 3. HK 데이터 로깅
- 모든 센서 앱에서 HK 데이터를 CSV로 로깅
- 센서별 상세 정보 포함

## 데이터 수집 주파수 요약

| 센서 | 이전 주파수 | 새로운 주파수 | 로그 파일 |
|------|-------------|---------------|-----------|
| IMU | 100Hz | **200Hz** | `high_freq_imu_log.csv` |
| Barometer | 5Hz | **50Hz** | `high_freq_barometer_log.csv` |
| TMP007 | 4Hz | **10Hz** | `high_freq_tmp007_log.csv` |
| Pitot | 5Hz | **20Hz** | `high_freq_pitot_log.csv` |

## CommApp Telemetry
- CommApp은 여전히 1Hz로 XBee를 통해 지상국에 데이터 전송
- 하지만 각 센서는 더 높은 주파수로 로그에 데이터 저장
- 따라서 지상국 통신과 무관하게 최대한 많은 센서 데이터 수집 가능

## 로그 파일 구조

### IMU 고주파수 로그
```csv
timestamp,roll,pitch,yaw,accx,accy,accz,magx,magy,magz,gyrx,gyry,gyrz,temp
2024-01-01 12:00:00.123,1.23,2.34,3.45,0.1,0.2,9.8,...
```

### Barometer 고주파수 로그
```csv
timestamp,pressure,temperature,altitude
2024-01-01 12:00:00.123,1013.25,25.6,100.5
```

### TMP007 고주파수 로그
```csv
timestamp,object_temp,die_temp,voltage
2024-01-01 12:00:00.123,25.6,26.1,3.3
```

### Pitot 고주파수 로그
```csv
timestamp,pressure,temperature
2024-01-01 12:00:00.123,1013.25,25.6
```

## 주의사항

1. **디스크 공간**: 고주파수 로깅으로 인해 로그 파일 크기가 크게 증가할 수 있습니다.
2. **시스템 부하**: 높은 주파수로 데이터를 수집하므로 CPU 사용량이 증가할 수 있습니다.
3. **로그 로테이션**: 장시간 운영 시 로그 파일 크기 모니터링이 필요합니다.

## 성능 최적화

- 각 센서 앱에서 독립적인 로깅 시스템 운영
- 비동기 로깅으로 메인 데이터 수집에 영향 최소화
- 강제 종료 시에도 로그 보존을 위한 안전장치 구현 