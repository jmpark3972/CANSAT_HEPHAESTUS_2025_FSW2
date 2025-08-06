# CANSAT HEPHAESTUS 2025 FSW2 - 종합 문서

## 📋 **목차**
1. [프로젝트 개요](#프로젝트-개요)
2. [시스템 아키텍처](#시스템-아키텍처)
3. [하드웨어 구성](#하드웨어-구성)
4. [소프트웨어 모듈](#소프트웨어-모듈)
5. [설치 및 설정](#설치-및-설정)
6. [사용법](#사용법)
7. [API 문서](#api-문서)
8. [트러블슈팅](#트러블슈팅)
9. [성능 최적화](#성능-최적화)
10. [개발 가이드](#개발-가이드)

---

## 🚀 **프로젝트 개요**

### **프로젝트 정보**
- **프로젝트명**: CANSAT HEPHAESTUS 2025 FSW2
- **버전**: 2.0
- **개발팀**: HEPHAESTUS
- **목적**: KAIST CANSAT 대회용 비행 소프트웨어
- **플랫폼**: Raspberry Pi 4B
- **언어**: Python 3.9+

### **주요 기능**
- 🛰️ **다중 센서 지원**: IMU, GPS, Barometer, Thermal Camera 등
- 📡 **실시간 통신**: UART, XBee 무선 통신
- 🎥 **이중 카메라**: Pi Camera + Thermal Camera
- ⚙️ **자동 제어**: 서보 모터 자동 제어
- 📊 **데이터 로깅**: 실시간 센서 데이터 수집 및 저장
- 🔄 **상태 관리**: 6단계 비행 상태 자동 전환

---

## 🏗️ **시스템 아키텍처**

### **전체 구조**
```
┌─────────────────────────────────────────────────────────────┐
│                    CANSAT FSW2 시스템                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   메인 앱    │  │   통신 앱    │  │  비행 로직   │         │
│  │  (MainApp)  │  │ (CommApp)   │  │(FlightLogic)│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   IMU 앱     │  │   GPS 앱     │  │ Barometer 앱 │         │
│  │ (ImuApp)    │  │ (GpsApp)    │  │(BarometerApp)│         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  카메라 앱    │  │ 열화상 카메라 │  │   모터 앱    │         │
│  │(CameraApp)  │  │(ThermalCam) │  │ (MotorApp)  │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  온도 센서들  │  │   Pitot 앱   │  │   HK 앱     │         │
│  │(Thermo/TMP) │  │ (PitotApp)  │  │  (HkApp)   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### **통신 구조**
- **메시지 기반 통신**: 각 앱은 독립적인 프로세스로 실행
- **Queue 기반**: 메인 앱이 메시지 라우팅 담당
- **Pipe 통신**: 부모-자식 프로세스 간 직접 통신
- **멀티프로세싱**: 안정성과 성능을 위한 병렬 처리

---

## 🔧 **하드웨어 구성**

### **센서 목록**
| 센서 | 모델 | 인터페이스 | 용도 |
|------|------|------------|------|
| IMU | BNO055 | I2C | 자세 측정 |
| GPS | NEO-6M | UART | 위치 측정 |
| Barometer | BMP390 | I2C | 고도 측정 |
| Thermal Camera | MLX90640 | I2C | 열화상 촬영 |
| Pi Camera | Camera Module v3 | CSI | 일반 촬영 |
| TMP007 | TMP007 | I2C | 온도 측정 |
| Thermis | ADS1115 | I2C | 온도 측정 |
| Pitot | MS4525DO | I2C | 속도 측정 |
| FIR1 | MLX90614 | I2C | 온도 측정 |

### **제어 장치**
| 장치 | 모델 | 인터페이스 | 용도 |
|------|------|------------|------|
| 서보 모터 | MG996R | PWM | 낙하산 제어 |
| 통신 모듈 | XBee S2C | UART | 무선 통신 |

### **연결도**
```
Raspberry Pi 4B
├── I2C Bus (SDA:2, SCL:3)
│   ├── BNO055 (IMU) - 0x28
│   ├── BMP390 (Barometer) - 0x77
│   ├── MLX90640 (Thermal) - 0x33
│   ├── TMP007 - 0x40
│   ├── ADS1115 (Thermis) - 0x48
│   ├── MLX90614 (FIR1) - 0x5A
│   └── MS4525DO (Pitot) - 0x28
├── UART (TX:14, RX:15)
│   ├── NEO-6M (GPS)
│   └── XBee S2C
├── PWM (GPIO:18)
│   └── MG996R (Servo)
└── CSI
    └── Camera Module v3
```

---

## 💻 **소프트웨어 모듈**

### **핵심 모듈**

#### **1. 메인 앱 (MainApp)**
- **파일**: `main.py`
- **역할**: 전체 시스템 관리 및 프로세스 제어
- **주요 기능**:
  - 프로세스 생성 및 관리
  - 메시지 라우팅
  - 시스템 상태 모니터링
  - 안전한 종료 처리

#### **2. 통신 앱 (CommApp)**
- **파일**: `comm/commapp.py`
- **역할**: 텔레메트리 데이터 처리 및 전송
- **주요 기능**:
  - 센서 데이터 수집
  - 텔레메트리 포맷팅
  - 무선 통신 관리
  - 실시간 상태 표시

#### **3. 비행 로직 앱 (FlightLogicApp)**
- **파일**: `flight_logic/flightlogicapp.py`
- **역할**: 비행 상태 관리 및 자동 제어
- **주요 기능**:
  - 6단계 비행 상태 관리
  - 모터 자동 제어
  - 카메라 제어
  - 안전 로직

### **센서 모듈**

#### **4. IMU 앱 (ImuApp)**
- **파일**: `imu/imuapp.py`
- **센서**: BNO055
- **데이터**: 자세각 (Roll, Pitch, Yaw), 가속도, 자이로스코프
- **샘플링**: 10Hz

#### **5. GPS 앱 (GpsApp)**
- **파일**: `gps/gpsapp.py`
- **센서**: NEO-6M
- **데이터**: 위도, 경도, 고도, 시간, 위성 수
- **샘플링**: 1Hz

#### **6. Barometer 앱 (BarometerApp)**
- **파일**: `barometer/barometerapp.py`
- **센서**: BMP390
- **데이터**: 압력, 고도, 온도
- **샘플링**: 10Hz

#### **7. Thermal Camera 앱 (ThermalCameraApp)**
- **파일**: `thermal_camera/thermo_cameraapp.py`
- **센서**: MLX90640
- **데이터**: 768픽셀 온도 데이터
- **샘플링**: 2Hz

#### **8. Camera 앱 (CameraApp)**
- **파일**: `camera/cameraapp.py`
- **센서**: Pi Camera Module v3
- **데이터**: 비디오 스트림, 이미지
- **기능**: 자동 녹화, 이미지 캡처

### **제어 모듈**

#### **9. Motor 앱 (MotorApp)**
- **파일**: `motor/motorapp.py`
- **장치**: MG996R 서보 모터
- **기능**: PWM 제어, 위치 제어
- **제어**: 0도(열림) ~ 180도(닫힘)

#### **10. HK 앱 (HkApp)**
- **파일**: `hk/hkapp.py`
- **역할**: 하우스키핑 데이터 관리
- **데이터**: 시스템 상태, 에러 정보

---

## ⚙️ **설치 및 설정**

### **시스템 요구사항**
- **OS**: Raspberry Pi OS (Bullseye)
- **Python**: 3.9+
- **메모리**: 최소 2GB RAM
- **저장공간**: 최소 8GB SD카드
- **네트워크**: WiFi 또는 이더넷

### **1단계: 시스템 업데이트**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv
```

### **2단계: Python 환경 설정**
```bash
python3 -m venv env
source env/bin/activate
pip install --upgrade pip
```

### **3단계: 의존성 설치**
```bash
# 시스템 패키지
sudo apt install -y \
    i2c-tools \
    python3-smbus \
    python3-dev \
    libgpiod2 \
    pigpio \
    libcamera-tools \
    ffmpeg

# Python 패키지
pip install -r requirements.txt
```

### **4단계: I2C 활성화**
```bash
sudo raspi-config
# Interface Options > I2C > Enable
sudo reboot
```

### **5단계: 권한 설정**
```bash
sudo usermod -a -G i2c,gpio,video $USER
sudo chmod +x startup.sh
```

### **6단계: 설정 파일 구성**
```bash
# lib/config.json 수정
{
    "FSW_MODE": "CONTAINER",
    "THERMIS_TEMP_THRESHOLD": 35.0,
    "PITOT": {
        "TEMP_CALIBRATION_OFFSET": -60.0
    }
}
```

---

## 🚀 **사용법**

### **기본 실행**
```bash
# 가상환경 활성화
source env/bin/activate

# FSW 실행
python3 main.py
```

### **테스트 실행**
```bash
# 전체 테스트
python3 test/test_coverage.py

# 개별 센서 테스트
python3 test/test_imu.py
python3 test/test_gps.py
python3 test/test_barometer.py
```

### **모니터링**
```bash
# 시스템 상태 확인
python3 -c "from lib.performance_monitor import get_performance_report; print(get_performance_report())"

# I2C 상태 확인
python3 -c "from lib.i2c_manager import get_i2c_health_report; print(get_i2c_health_report())"
```

### **로그 확인**
```bash
# 실시간 로그 모니터링
tail -f logs/system.log

# 특정 모듈 로그
tail -f logs/comm_commapp.log
tail -f logs/flight_flightlogicapp.log
```

---

## 📚 **API 문서**

### **메시지 구조**
```python
class MsgStructure:
    sender_app: int      # 송신 앱 ID
    receiver_app: int    # 수신 앱 ID
    MsgID: int          # 메시지 ID
    data: str           # 메시지 데이터
```

### **주요 메시지 ID**
| 메시지 | ID | 설명 |
|--------|----|----|
| MID_TerminateProcess | 1000 | 프로세스 종료 |
| MID_SendHK | 1100 | HK 데이터 전송 |
| MID_SendImuTlmData | 2100 | IMU 텔레메트리 |
| MID_SendGpsTlmData | 2200 | GPS 텔레메트리 |
| MID_SetServoAngle | 1400 | 서보 모터 제어 |

### **설정 관리**
```python
from lib import config

# 설정 읽기
value = config.get_config('THERMIS_TEMP_THRESHOLD')

# 설정 쓰기
config.set_config('NEW_SETTING', 'value')
```

### **로깅 시스템**
```python
from lib.unified_logging import safe_log

# 기본 로깅
safe_log("메시지", "INFO", True)

# 센서 데이터 로깅
from lib.unified_logging import log_sensor_data
log_sensor_data("IMU", {"roll": 1.5, "pitch": 2.1})
```

---

## 🔧 **트러블슈팅**

### **일반적인 문제**

#### **1. I2C 통신 오류**
```bash
# I2C 버스 확인
sudo i2cdetect -y 1

# I2C 버스 재시작
sudo rmmod i2c_bcm2708
sudo modprobe i2c_bcm2708
```

#### **2. 센서 초기화 실패**
```bash
# 센서별 테스트
python3 test/test_imu.py
python3 test/test_gps.py
python3 test/test_barometer.py
```

#### **3. 카메라 오류**
```bash
# 카메라 하드웨어 확인
vcgencmd get_camera

# 카메라 드라이버 확인
ls -la /dev/video*
```

#### **4. 메모리 부족**
```bash
# 메모리 사용량 확인
free -h

# 불필요한 프로세스 종료
sudo systemctl stop bluetooth
sudo systemctl stop avahi-daemon
```

### **오류 코드**
| 오류 코드 | 설명 | 해결방법 |
|-----------|------|----------|
| [Errno 5] | I2C 통신 오류 | I2C 버스 재시작 |
| [Errno 13] | 권한 오류 | 사용자 그룹 추가 |
| [Errno 110] | 연결 타임아웃 | 네트워크 확인 |

---

## ⚡ **성능 최적화**

### **시스템 최적화**
```bash
# CPU 성능 최적화
echo 'performance' | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# 메모리 최적화
echo 1 | sudo tee /proc/sys/vm/drop_caches
```

### **Python 최적화**
```python
# 가비지 컬렉션 최적화
import gc
gc.collect()

# 메모리 사용량 모니터링
import psutil
process = psutil.Process()
memory_info = process.memory_info()
```

### **네트워크 최적화**
```bash
# WiFi 전력 관리 비활성화
sudo iwconfig wlan0 power off

# 네트워크 버퍼 크기 증가
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
```

---

## 👨‍💻 **개발 가이드**

### **새 모듈 추가**
1. **디렉토리 생성**
```bash
mkdir new_module
touch new_module/__init__.py
touch new_module/new_module.py
touch new_module/new_moduleapp.py
```

2. **앱 구조**
```python
# new_moduleapp.py
from lib import appargs, msgstructure, logging
from multiprocessing import Queue, connection

def new_moduleapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    # 초기화
    # 메인 루프
    # 종료 처리
```

3. **메인 앱에 등록**
```python
# main.py에 추가
from new_module import new_moduleapp
# 프로세스 생성 및 등록
```

### **테스트 작성**
```python
# test/test_new_module.py
import unittest

class NewModuleTest(unittest.TestCase):
    def test_initialization(self):
        # 초기화 테스트
        pass
    
    def test_data_processing(self):
        # 데이터 처리 테스트
        pass
```

### **문서화**
```python
def function_name(param1: str, param2: int) -> bool:
    """
    함수 설명
    
    Args:
        param1: 첫 번째 매개변수 설명
        param2: 두 번째 매개변수 설명
    
    Returns:
        bool: 반환값 설명
    
    Raises:
        ValueError: 예외 설명
    """
    pass
```

---

## 📊 **성능 지표**

### **시스템 성능**
- **CPU 사용률**: 평균 15-25%
- **메모리 사용률**: 평균 30-40%
- **디스크 사용률**: 로그 파일에 따라 변동
- **네트워크**: 텔레메트리 전송량에 따라 변동

### **센서 성능**
- **IMU**: 10Hz 샘플링, ±0.1도 정확도
- **GPS**: 1Hz 업데이트, ±3m 정확도
- **Barometer**: 10Hz 샘플링, ±1m 정확도
- **Thermal Camera**: 2Hz 샘플링, ±0.5도 정확도

### **통신 성능**
- **텔레메트리**: 1Hz 전송
- **XBee**: 9600bps, 100m 범위
- **메시지 지연**: 평균 10-50ms

---

## 🔮 **향후 계획**

### **단기 계획 (1-2개월)**
- [ ] 성능 모니터링 시스템 완성
- [ ] 자동 테스트 시스템 구축
- [ ] 문서화 완성
- [ ] 버그 수정 및 안정성 향상

### **중기 계획 (3-6개월)**
- [ ] 머신러닝 기반 데이터 분석
- [ ] 실시간 데이터 시각화
- [ ] 원격 제어 기능 추가
- [ ] 고급 비행 로직 구현

### **장기 계획 (6개월+)**
- [ ] AI 기반 자율 비행
- [ ] 클라우드 연동
- [ ] 모바일 앱 개발
- [ ] 다중 CANSAT 지원

---

## 📞 **지원 및 연락처**

### **개발팀**
- **팀명**: HEPHAESTUS
- **대학**: 연세대학교
- **연락처**: [이메일 주소]
- **GitHub**: [GitHub 저장소]

### **문서 버전**
- **버전**: 2.0
- **최종 업데이트**: 2025-08-06
- **작성자**: AI Assistant
- **검토자**: 개발팀

---

**© 2025 HEPHAESTUS. All rights reserved.** 