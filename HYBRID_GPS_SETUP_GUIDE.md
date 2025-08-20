# 🚀 하이브리드 GPS 시스템 설정 가이드

## 📋 개요

하이브리드 GPS 시스템은 GPS + WiFi + Cell Tower 정보를 조합하여 최대한 정확한 위치 정보를 제공합니다. 실내나 GPS 신호가 약한 환경에서도 안정적인 위치 추적이 가능합니다.

## 🔧 시스템 요구사항

### 하드웨어
- Raspberry Pi Zero 2 W (또는 호환 보드)
- MAX-M10S Qwiic GPS 모듈
- WiFi 연결 (내장 또는 USB WiFi 어댑터)
- GPS 안테나 (외장 권장)

### 소프트웨어
- Python 3.7+
- 필요한 Python 패키지들

## 📦 설치 단계

### 1단계: 필요한 패키지 설치

```bash
# 기본 패키지 설치
sudo apt update
sudo apt install -y python3-pip python3-dev i2c-tools

# I2C 활성화
sudo raspi-config
# Interface Options > I2C > Enable

# Python 패키지 설치
pip3 install adafruit-circuitpython-gps adafruit-blinka requests
```

### 2단계: I2C 설정 확인

```bash
# I2C 장치 스캔
i2cdetect -y 1

# 예상 출력:
#      0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
# 00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
# 70: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
```

### 3단계: WiFi 설정

```bash
# WiFi 인터페이스 확인
iwconfig

# WiFi 스캔 테스트
sudo iwlist wlan0 scan | grep ESSID
```

### 4단계: Google Maps API 키 설정 (선택사항)

WiFi 기반 위치 기능을 사용하려면 Google Maps API 키가 필요합니다.

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트 생성
2. Maps JavaScript API 활성화
3. API 키 생성
4. 환경변수로 설정:

```bash
export GOOGLE_MAPS_API_KEY='your_api_key_here'
```

영구 설정을 위해 `~/.bashrc`에 추가:

```bash
echo 'export GOOGLE_MAPS_API_KEY="your_api_key_here"' >> ~/.bashrc
source ~/.bashrc
```

## 🧪 테스트

### 기본 테스트

```bash
# 하이브리드 GPS 시스템 테스트
python3 test_hybrid_gps.py
```

### 개별 모듈 테스트

```bash
# I2C 장치 스캔
i2cdetect -y 1

# WiFi 스캔
sudo iwlist wlan0 scan

# GPS 모듈 테스트
python3 test_max_m10s_qwiic.py
```

## 📊 시스템 기능

### 위치 정보 소스

1. **GPS (우선순위: 높음)**
   - 정확도: 3-20m (위성 수에 따라)
   - 실외에서 최적 성능
   - 위성 수에 따른 정확도 자동 조정

2. **WiFi (우선순위: 중간)**
   - 정확도: 10-100m
   - 실내에서 유용
   - Google Geolocation API 사용

3. **Cell Tower (우선순위: 낮음)**
   - 정확도: 100-1000m
   - 긴급 상황에서 사용
   - 구현 예정

### 하이브리드 알고리즘

- **가중 평균**: 각 소스의 정확도에 따른 가중치 적용
- **폴백 시스템**: GPS 실패 시 WiFi, WiFi 실패 시 Cell Tower
- **캐싱**: WiFi 스캔 결과 30초간 캐시
- **재시도**: 최대 3회 자동 재시도

## 📈 성능 최적화

### GPS 최적화
- 안테나 위치: 하늘을 향하도록 설치
- 안테나 종류: 외장 GPS 안테나 권장
- 위치: 금속 장애물에서 멀리

### WiFi 최적화
- API 키 설정으로 정확도 향상
- 네트워크 스캔 주기 조정
- 캐시 시간 조정

### 시스템 최적화
- 로그 레벨 조정
- 데이터 수집 주기 조정
- 메모리 사용량 모니터링

## 🔍 문제 해결

### GPS 문제
```bash
# GPS 모듈 연결 확인
i2cdetect -y 1

# GPS 로그 확인
tail -f logs/hybrid_gps.log

# GPS 상태 확인
python3 -c "from gps import hybrid_gps; print(hybrid_gps.get_location_status())"
```

### WiFi 문제
```bash
# WiFi 인터페이스 확인
iwconfig

# WiFi 스캔 테스트
sudo iwlist wlan0 scan

# API 키 확인
echo $GOOGLE_MAPS_API_KEY
```

### 일반 문제
```bash
# 시스템 로그 확인
tail -f logs/hybrid_gps_high_freq.csv

# 프로세스 상태 확인
ps aux | grep hybrid

# 메모리 사용량 확인
free -h
```

## 📝 로그 파일

### 주요 로그 파일
- `logs/hybrid_gps.log`: 시스템 로그
- `logs/hybrid_gps_high_freq.csv`: 고빈도 위치 데이터
- `logs/hybrid_gps_hk.csv`: 하우스키핑 데이터
- `logs/hybrid_gps_status.csv`: 시스템 상태

### 로그 분석
```bash
# 최근 위치 데이터 확인
tail -20 logs/hybrid_gps_high_freq.csv

# 정확도 통계
awk -F',' 'NR>1 {sum+=$5; count++} END {print "평균 정확도:", sum/count, "m"}' logs/hybrid_gps_high_freq.csv

# 위치 소스 분포
awk -F',' 'NR>1 {sources[$6]++} END {for(s in sources) print s, sources[s]}' logs/hybrid_gps_high_freq.csv
```

## 🚀 고급 설정

### 커스텀 가중치 설정
`gps/hybrid_gps.py`에서 가중치 조정:

```python
self.accuracy_weights = {
    LocationSource.GPS: 0.7,    # GPS 가중치
    LocationSource.WIFI: 0.2,   # WiFi 가중치
    LocationSource.CELL: 0.1    # Cell 가중치
}
```

### 캐시 시간 조정
```python
self.wifi_cache_timeout = 30  # WiFi 캐시 시간 (초)
```

### 재시도 설정
```python
def get_location_with_fallback(self, max_attempts: int = 3):
    # 최대 재시도 횟수 조정
```

## 📞 지원

문제가 발생하면 다음을 확인하세요:

1. 하드웨어 연결 상태
2. 소프트웨어 의존성 설치
3. 로그 파일 분석
4. 네트워크 연결 상태
5. API 키 설정

## 🔄 업데이트

시스템 업데이트:

```bash
# 코드 업데이트
git pull origin main

# 의존성 업데이트
pip3 install --upgrade adafruit-circuitpython-gps adafruit-blinka requests

# 시스템 재시작
sudo reboot
```

---

**참고**: 이 시스템은 실험적 기능을 포함하고 있습니다. 실제 사용 전에 충분한 테스트를 진행하세요.
