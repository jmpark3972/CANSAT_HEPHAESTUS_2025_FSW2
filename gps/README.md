# GPS Modules for CANSAT HEPHAESTUS 2025

이 디렉토리는 CANSAT HEPHAESTUS 2025 프로젝트의 GPS 모듈들을 포함합니다.

## 모듈 목록

### 1. MAX-M10S GPS Module (`gps_max_m10s.py`)
- **하드웨어**: MAX-M10S Qwiic GPS 모듈
- **연결**: I2C (주소: 0x42)
- **특징**: 고정밀 GPS 위치 정보, I2C 통신

### 2. Hybrid GPS System (`hybrid_gps.py`)
- **기능**: GPS + WiFi + Cell Tower 하이브리드 위치 시스템
- **특징**: 여러 위치 정보 소스를 조합하여 최적의 위치 제공
- **폴백**: GPS 실패 시 WiFi, WiFi 실패 시 Cell Tower 사용

### 3. GPS Applications
- `gpsapp.py`: MAX-M10S GPS 애플리케이션
- `hybrid_gpsapp.py`: 하이브리드 GPS 애플리케이션

## 설치 및 설정

### 1. 필요한 패키지 설치
```bash
pip install adafruit-circuitpython-gps
pip install requests
```

### 2. I2C 활성화 (Raspberry Pi)
```bash
sudo raspi-config
# Interface Options > I2C > Enable
```

### 3. 하드웨어 연결
- MAX-M10S GPS 모듈을 Qwiic 케이블로 연결
- GPS 안테나 연결 확인
- 전원 공급 확인

## 사용법

### 1. 초기 설정
```bash
# prevstate.txt 파일 초기화 (gpsapp.py 실행 전 필요)
python3 init_prevstate.py
```

### 2. GPS 모듈 테스트
```bash
# 종합 GPS 테스트
python3 test_gps_simple.py

# 개별 모듈 테스트
python3 gps_max_m10s.py
python3 hybrid_gps.py
```

### 3. GPS 애플리케이션 실행
```bash
# MAX-M10S GPS 애플리케이션
python3 gpsapp.py

# 하이브리드 GPS 애플리케이션
python3 hybrid_gpsapp.py
```

## 문제 해결

### 1. "No I2C device at address: 0x10" 오류
**원인**: 잘못된 I2C 주소 사용
**해결**: MAX-M10S는 0x42 주소를 사용합니다. 코드가 수정되었습니다.

### 2. "Failed to load prevstate" 오류
**원인**: `lib/prevstate.txt` 파일이 없음
**해결**: 
```bash
python3 init_prevstate.py
```

### 3. GPS 픽스가 안됨
**확인사항**:
- GPS 안테나가 연결되어 있는지 확인
- 맑은 하늘을 향하고 있는지 확인
- 실외에서 테스트 (실내에서는 신호가 약함)
- 처음 실행 시 30초-2분 정도 기다림

### 4. I2C 장치가 감지되지 않음
**확인사항**:
```bash
# I2C 활성화 확인
sudo i2cdetect -y 1

# I2C 장치 스캔
python3 i2c_scan.py
```

### 5. 하이브리드 GPS에서 WiFi 위치만 작동
**확인사항**:
- Google Maps API 키 설정 (선택사항)
- WiFi 네트워크 스캔 권한 확인
- 인터넷 연결 확인

## 로그 파일

GPS 모듈들은 다음 위치에 로그를 생성합니다:
- `logs/gps_high_freq.csv`: 고주파 GPS 데이터
- `logs/hk_log.csv`: 하우스키핑 데이터
- `sensorlogs/gps_max_m10s.txt`: MAX-M10S GPS 로그
- `logs/hybrid_gps.log`: 하이브리드 GPS 로그

## API 키 설정 (선택사항)

하이브리드 GPS에서 Google Maps API를 사용하려면:
```bash
export GOOGLE_MAPS_API_KEY="your_api_key_here"
```

## 성능 최적화

### 1. GPS 업데이트 주기
- 기본: 1Hz (1초마다 업데이트)
- 변경: `gps.send_command(b'PMTK220,500')` (0.5초마다)

### 2. 데이터 필터링
- GPS 정확도 임계값 설정
- 위성 수 최소 요구사항 설정
- 신호 강도 필터링

## 개발자 정보

### 모듈 구조
```
gps/
├── gps_max_m10s.py      # MAX-M10S GPS 모듈
├── hybrid_gps.py        # 하이브리드 GPS 시스템
├── gpsapp.py           # MAX-M10S GPS 애플리케이션
├── hybrid_gpsapp.py    # 하이브리드 GPS 애플리케이션
├── test_gps_simple.py  # 종합 테스트 스크립트
├── init_prevstate.py   # prevstate 초기화 스크립트
└── README.md           # 이 파일
```

### 주요 클래스
- `GPS_GtopI2C`: MAX-M10S GPS 모듈 클래스
- `HybridGPSSystem`: 하이브리드 GPS 시스템 클래스
- `LocationData`: 위치 데이터 클래스
- `LocationSource`: 위치 정보 소스 열거형

## 라이선스

이 프로젝트는 CANSAT HEPHAESTUS 2025 팀의 일부입니다.
