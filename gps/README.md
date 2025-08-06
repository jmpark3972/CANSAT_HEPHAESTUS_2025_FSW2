# GPS 모듈 가이드

이 폴더는 CANSAT HEPHAESTUS 2025 FSW2의 GPS (Global Positioning System) 기능을 담당하는 모듈들을 포함합니다.

## 📁 **파일 구조**

### 🔧 **핵심 GPS 모듈**
- `gps.py` - GPS 센서 핵심 인터페이스 (UART 통신)
- `gpsapp.py` - GPS 애플리케이션 (메인 GPS 앱)

### 🔍 **GPS 디버깅 및 테스트**
- `gps_debug.py` - GPS 디버깅 도구
- `gps_i2c.py` - I2C GPS 모듈 인터페이스 (대안)
- `gps_uart_improved.py` - 개선된 UART GPS 인터페이스
- `i2c_scan.py` - I2C 디바이스 스캔 도구

### 📋 **설정 파일**
- `.gitignore` - Git 무시 파일 설정

## 🛠️ **하드웨어 설정**

### **연결 정보**
- **RX 핀**: GPIO 22번 사용
- **통신 방식**: UART (Serial)
- **포트**: `/dev/serial0` (기본)
- **보드레이트**: 9600 bps
- **GPS 모듈**: MTK3339

### **시스템 설정**
```bash
# pigpio 데몬 활성화 (부팅 시 자동 시작)
sudo systemctl enable pigpiod

# 필요한 라이브러리 설치
pip3 install pigpio
pip3 install pyserial
```

## 🔧 **주요 기능**

### **GPS 데이터 수신**
- `init_gps()`: GPS pigpio 연결 초기화
- `read_gps()`: GPS의 NMEA 라인 모두 읽기
- `parse_gps_data()`: NMEA 라인에서 GGA, RMC 데이터 추출

### **GPS 데이터 파싱**
- `unit_convert_deg()`: 위도, 경도 상용 단위로 변환
- `gps_readdata()`: pi handle을 통해 필요한 데이터 파싱

### **시간 변환**
- UTC → KST (한국 표준시) 변환 (+9시간)
- GPS 시간 데이터 포맷팅

## 📊 **데이터 형식**

### **GPS 데이터 구조**
```python
GPS_LAT = 0.0      # 위도 (Latitude)
GPS_LON = 0.0      # 경도 (Longitude)
GPS_ALT = 0.0      # 고도 (Altitude)
GPS_TIME = "00:00:00"  # 시간 (KST)
GPS_SATS = 0       # 위성 수 (Satellites)
```

### **NMEA 메시지 형식**
- **GGA**: Global Positioning System Fix Data
- **RMC**: Recommended Minimum Navigation Information

## 🚀 **사용 방법**

### **1. 기본 GPS 사용**
```python
from gps import gps

# GPS 초기화
ser = gps.init_gps()

# GPS 데이터 읽기
data = gps.gps_readdata(ser)
if data:
    lat, lon, alt, time, sats = data
    print(f"위도: {lat}, 경도: {lon}, 고도: {alt}m")
```

### **2. GPS 앱 실행**
```python
from gps import gpsapp

# GPS 앱 초기화 및 실행
gpsapp.gpsapp_main(main_queue, main_pipe)
```

### **3. 디버깅**
```bash
# GPS 디버깅 실행
python3 gps/gps_debug.py

# I2C 디바이스 스캔
python3 gps/i2c_scan.py
```

## 🔍 **문제 해결**

### **일반적인 문제들**

1. **시리얼 포트 연결 실패**
   ```bash
   # 시리얼 포트 권한 확인
   sudo usermod -a -G dialout $USER
   
   # 시리얼 포트 활성화
   sudo raspi-config
   # Interface Options → Serial → Enable
   ```

2. **GPS 신호 없음**
   - GPS 모듈이 하늘을 향하는지 확인
   - 실외에서 테스트
   - 위성 수신 대기 (최대 5분)

3. **데이터 읽기 오류**
   ```bash
   # 시리얼 포트 상태 확인
   ls -la /dev/serial*
   
   # GPS 모듈 연결 확인
   dmesg | grep -i serial
   ```

### **디버깅 도구**

- `gps_debug.py`: 실시간 GPS 데이터 모니터링
- `i2c_scan.py`: I2C 디바이스 검색
- 로그 파일: `sensorlogs/gps.txt`

## 📝 **로그 파일**

GPS 관련 로그는 다음 위치에 저장됩니다:
- `sensorlogs/gps.txt` - GPS 상세 로그
- `logs/` - 메인 시스템 로그

## ⚠️ **주의사항**

- GPS 모듈은 실외에서만 정확한 신호를 받습니다
- 초기 위성 수신에는 시간이 걸릴 수 있습니다 (Cold Start)
- 시리얼 통신은 정확한 보드레이트 설정이 필요합니다
- GPS 시간은 UTC 기준이므로 KST로 변환해야 합니다

## 🔄 **대안 GPS 모듈**

- `gps_i2c.py`: I2C 통신을 사용하는 GPS 모듈
- `gps_uart_improved.py`: 개선된 UART 통신 방식

## 📚 **참고 자료**

- NMEA 0183 프로토콜
- MTK3339 GPS 모듈 데이터시트
- Raspberry Pi UART 설정 가이드
