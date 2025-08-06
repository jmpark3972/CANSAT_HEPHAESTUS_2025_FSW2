FLIGHT SOFTWARE FOR CANSAT AAS 2025

To make a new app, copy from sample app and replace 'sample' to app name (case sensitive)

# Prerequisities

## 0. Clone directory
Please clone this FSW in /home/pi for smooth automatic initialization! Set the raspberry pi name as pi!

    cd /home/pi
    git clone git@github.com:SPACE-Yonsei/CANSAT_AAS_2025_FSW.git

## 1. Install Adafruit Blinka
Before installing Adafruit modules, follow the steps provided in the link below to install adafruit-blinka
https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/installing-circuitpython-on-raspberry-pi

## 2. Install sensor libraries
The flight software uses Adafruit CircuitPython modules

    pip3 install adafruit-circuitpython-bmp3xx
    pip3 install adafruit-circuitpython-gps
    pip3 install adafruit-circuitpython-bno055
    pip3 install adafruit-circuitpython-ads1x15
    pip3 install adafruit-circuitpython-motor

## 3. Install Video Related modules (OPTIONAL - Camera Disabled)
**Note: Camera functionality is currently disabled as hardware is not installed.**

Opencv2 module is used in USB camera recording

    pip install opencv-python

Picamera2 module is used in Raspberry Pi Camera recording
It is pre-installed on Rapsberry Pi OS images

    sudo apt install python3-picamera2

### 3.1. Install Camera App Dependencies (DISABLED)
For Raspberry Pi Camera Module v3 Wide support (currently disabled):

    # sudo apt install ffmpeg v4l2-utils
    # chmod +x camera/install_camera.sh
    # ./camera/install_camera.sh

## 4. Install Basic modules
Other basic modules should be installed too

    pip3 install numpy
## 5. Install Pigpio

    pip3 install pigpio
    sudo systemctl enable pigpiod

# Run Flight software
## Update Submodules

    git submodule init
    git submodule update

## SELECT CONFIG
when initially running flight software, you will get the error

    #################################################################
    Config file does not exist: lib/config.txt, Configure the config file to run FSW!
    #################################################################

you should specify the operation mode of the FSW by editing the lib/config.txt file

# Optional Configuraton
## Granting permission to interface (Not Root)
When not running on root, permission to interfaces should be given

    sudo usermod -aG i2c {user_name}
    sudo usermod -aG gpio {user_name}
    sudo usermod -aG video {user_name}

## Optimizations
I2C clock stretching is recommended for stable use of sensors that use I2C
https://learn.adafruit.com/circuitpython-on-raspberrypi-linux/i2c-clock-stretching

## When running on Raspberry Pi 5 Family (Raspberry Pi 5, Raspberry Pi Compute Module 5)
There is a bug with adafruit board library (https://forums.raspberrypi.com/viewtopic.php?t=386485) on raspberry pi 5 family, so firmware downgrade is needed until the developers fix that bug

    sudo rpi-update 0ccee17

## When using USB camera using pads
we need to configure the pi.

on /boot/firmware/cmdline.txt, add the following after rootwait

    modules-load=dwc2,g_ether

on /boot/firmware/config.txt, add the following 

    dtoverlay=dwc2,dr_mode=host 
    
on /etc/modules, add

    dwc2

# 강화된 이중 로깅 시스템 (Robust Dual Logging System)

CANSAT 미션 중 낙하 시 라즈베리파이 파손으로 인한 데이터 손실을 방지하기 위해 추가 SD카드를 통한 이중 로깅 시스템을 구현했습니다. **플라이트 로직과 완전히 분리되어 있어 로직 오류나 앱 고장과 관계없이 항상 로그가 기록됩니다.**

# 시스템 진단 및 유틸리티

## lib/utils.py - 통합 진단 도구

시스템 진단과 센서 테스트를 위한 통합 유틸리티가 `lib/utils.py`에 포함되어 있습니다.

### 사용 방법

```bash
python3 -m lib.utils
```

### 주요 기능

1. **I2C 스캔** - 모든 I2C 장치 검색
2. **센서 초기화 테스트** - 주요 센서들의 연결 상태 확인
3. **Qwiic Mux 테스트** - 멀티플렉서 채널별 장치 확인
4. **시스템 보고서 생성** - 전체 시스템 상태 보고서 생성
5. **빠른 진단** - 주요 문제점만 빠르게 확인

### 프로그래밍 방식 사용

```python
from lib import utils

# I2C 장치 스캔
devices = utils.scan_i2c_devices()

# 특정 센서 연결 테스트
if utils.test_i2c_connection(0x28):
    print("IMU 연결 성공")

# 빠른 진단
if utils.quick_diagnostic():
    print("모든 센서 정상")
else:
    print("문제 발견")

# 시스템 보고서 생성
report = utils.create_system_report()
```

## 주요 특징

### 🔒 **플라이트 로직 독립성**
- 로직 오류나 앱 고장과 관계없이 로그 기록 보장
- 각 센서 앱의 상태와 무관하게 독립적 로깅
- 시스템 크래시 시에도 최소한의 로그 저장

### 🛡️ **견고한 오류 처리**
- 파일 손상 시 자동 복구 메커니즘
- SD카드 연결 문제 시 자동 재시도
- 메모리 버퍼링으로 성능 최적화

### ⚡ **실시간 이중 저장**
- 주 SD카드와 보조 SD카드에 동시 기록
- 30초마다 자동 백업
- 1분마다 SD카드 상태 모니터링 및 복구

### 🚨 **시그널 처리**
- 강제 종료 시에도 로그 저장
- SIGTERM, SIGINT 시그널 처리
- 프로그램 종료 시 자동 정리

## 사용법

### 기본 사용
```python
from lib import logging

# 로깅 시스템 초기화
logging.init_dual_logging_system()

# 로그 기록
logging.log("시스템 시작", printlogs=True)
logging.log("센서 데이터: GPS=37.123,45.678", printlogs=False)

# 시스템 종료 시
logging.close_dual_logging_system()
```

### 플라이트 로직에서 사용
```python
# 센서 데이터 로깅
log_sensor_data("GPS", {"lat": 37.123, "lon": 45.678, "alt": 1000})
log_sensor_data("IMU", {"roll": 1.5, "pitch": -0.8, "yaw": 90.2})

# 시스템 이벤트 로깅
log_system_event("STATE_CHANGE", "STANDBY -> ASCENT")
log_system_event("ERROR", "센서 연결 실패")
```

## 테스트

강화된 로깅 시스템을 테스트하려면:

```bash
python3 test_robust_logging.py
```

이 테스트는 다음을 확인합니다:
- 기본 로깅 기능
- 오류 처리 능력
- 동시 로깅 처리
- 시그널 처리
- 플라이트 로직 독립성
- 이중 SD카드 로깅

# Qwiic Mux 기반 FIR 센서 시스템

AS7263 센서를 제거하고 Qwiic Mux를 사용하여 두 개의 MLX90614 FIR 센서를 분리하여 사용하는 시스템으로 업그레이드했습니다.

## 하드웨어 구성

### Qwiic Mux 연결
- **I2C 주소**: 0x70 (기본값)
- **채널 0**: FIR1 (MLX90614)
- **채널 1**: FIR2 (MLX90614)
- **채널 2-7**: 향후 확장용

### 센서 연결
```
Qwiic Mux (0x70)
├── 채널 0 → FIR1 (MLX90614)
├── 채널 1 → FIR2 (MLX90614)
└── 채널 2-7 → 미사용
```

## 소프트웨어 구조

### 새로운 모듈
```
lib/qwiic_mux.py          # Qwiic Mux 제어 라이브러리
fir/fir1.py               # FIR1 센서 헬퍼 (채널 0)
fir/fir2.py               # FIR2 센서 헬퍼 (채널 1)
fir/firapp1.py            # FIR1 앱 (채널 0)
fir/firapp2.py            # FIR2 앱 (채널 1)
test_qwiic_mux.py         # 통합 테스트 스크립트
```

### 앱 구조 변경
- **기존**: `FirApp` (단일 FIR 센서)
- **변경**: `FirApp1` (채널 0) + `FirApp2` (채널 1)

## 사용법

### 1. 하드웨어 연결 확인
```bash
# Qwiic Mux 및 FIR 센서 테스트
python3 test_qwiic_mux.py
```

### 2. 개별 센서 테스트
```bash
# FIR1 센서 테스트 (채널 0)
python3 fir/fir1.py

# FIR2 센서 테스트 (채널 1)
python3 fir/fir2.py
```

### 3. 센서 로거 테스트
```bash
# 통합 센서 로거 테스트
python3 sensor_logger.py
```

### 4. 메인 시스템 실행
```bash
# 전체 시스템 실행 (이중 로깅 포함)
python3 main.py
```

## 데이터 형식

### FIR1 데이터 (채널 0)
- **앱 ID**: 20
- **메시지 ID**: 2002
- **데이터 형식**: `"ambient_temp,object_temp"`

### FIR2 데이터 (채널 1)
- **앱 ID**: 21
- **메시지 ID**: 2102
- **데이터 형식**: `"ambient_temp,object_temp"`

## 캘리브레이션

각 FIR 센서는 독립적으로 캘리브레이션할 수 있습니다:

```python
# FIR1 캘리브레이션
prevstate.update_fir1cal(ambient_offset, object_offset)

# FIR2 캘리브레이션
prevstate.update_fir2cal(ambient_offset, object_offset)
```

## 문제 해결

### Qwiic Mux가 인식되지 않는 경우
1. I2C 연결 확인: `i2cdetect -y 1`
2. Mux 주소 확인 (기본값: 0x70)
3. 전원 공급 확인

### FIR 센서가 인식되지 않는 경우
1. Mux 채널 선택 확인
2. 센서 I2C 주소 확인 (MLX90614: 0x5A)
3. 배선 연결 확인

### 센서 데이터 오류
1. 센서 초기화 대기 시간 확인
2. 채널 전환 시 안정화 시간 확인
3. I2C 클럭 속도 조정 (필요시)

## 이중 로깅 시스템 설정

### 1. 추가 SD카드 하드웨어 연결
- SPI 인터페이스를 통해 추가 SD카드를 연결
- GPIO 핀 연결:
  - MOSI (GPIO 10)
  - MISO (GPIO 9) 
  - SCLK (GPIO 11)
  - CS1 (GPIO 7)

### 2. 소프트웨어 설정

#### 2.1 초기 설정
```bash
# 설정 스크립트 실행
chmod +x setup_secondary_sd.sh
./setup_secondary_sd.sh
```

#### 2.2 재부팅 후 설정 완료
```bash
# 재부팅 후 설정 완료 스크립트 실행
chmod +x setup_sd_after_reboot.sh
./setup_sd_after_reboot.sh
```

### 3. 시스템 테스트
```bash
# 이중 로깅 시스템 테스트
python3 test_dual_logging.py
```

## 이중 로깅 시스템 특징

### 주요 기능
- **실시간 이중 저장**: 모든 로그를 메인 SD카드와 보조 SD카드에 동시 저장
- **자동 백업**: 30초마다 메인 로그를 보조 SD카드에 백업
- **오류 복구**: 보조 SD카드 오류 시 자동 재시도
- **호환성**: 기존 로깅 시스템과 완전 호환

### 로그 저장 위치
- **메인 로그**: `/home/pi/logs/` (기존 SD카드)
- **보조 로그**: `/mnt/log_sd/logs/` (추가 SD카드)
- **센서 로그**: `/home/pi/sensorlogs/` 및 `/mnt/log_sd/sensorlogs/`

### 시스템 구조
```
lib/logging.py               # 통합 로깅 시스템 (이중 로깅 포함)
lib/logging.py               # 기존 로깅 시스템 (이중 로깅 지원)
sensor_logger.py             # 센서 로거 (이중 저장 지원)
main.py                      # 메인 애플리케이션 (이중 로깅 초기화)
setup_secondary_sd.sh        # 초기 설정 스크립트
setup_sd_after_reboot.sh     # 재부팅 후 설정 스크립트
test_dual_logging.py         # 테스트 스크립트
```

## 사용법

### 일반적인 사용
기존 코드와 동일하게 사용하면 자동으로 이중 로깅이 적용됩니다:

```python
from lib import logging

# 기존 방식과 동일
logging.logdata(log_file, "테스트 메시지", printlogs=True)
```

### 직접 이중 로깅 사용
```python
from lib import logging

# 이중 로깅 시스템 초기화
logging.init_dual_logging_system()

# 로그 기록
logging.log("중요한 데이터", printlogs=True)

# 시스템 종료
logging.close_dual_logging_system()
```

## 문제 해결

### 보조 SD카드가 인식되지 않는 경우
1. SPI 연결 확인
2. Device Tree Overlay 설정 확인
3. `lsblk | grep mmcblk` 명령어로 디바이스 확인

### 로그 파일이 동기화되지 않는 경우
1. 보조 SD카드 마운트 상태 확인: `df -h | grep log_sd`
2. 권한 확인: `ls -la /mnt/log_sd/`
3. 시스템 재시작 후 재시도

### 성능 최적화
- 보조 SD카드 속도가 느린 경우 `spi-max-frequency`를 4000000으로 낮춤
- 백업 주기를 조정하려면 `lib/logging.py`의 `_backup_worker` 함수 수정

# Camera App - Raspberry Pi Camera Module v3 Wide

라즈베리파이 카메라 모듈 v3 wide를 사용하여 FSW 상승부터 낙하 후 30초까지 5초 주기로 영상을 녹화하는 앱입니다.

## 하드웨어 요구사항
- Raspberry Pi Zero 2W
- Raspberry Pi Camera Module v3 Wide
- CSI 케이블 연결

## 설치 및 설정

### 1. 의존성 설치
```bash
# 필수 패키지 설치
sudo apt install ffmpeg v4l2-utils

# 설치 스크립트 실행
chmod +x camera/install_camera.sh
./camera/install_camera.sh
```

### 2. 카메라 활성화
```bash
# raspi-config에서 카메라 활성화
sudo raspi-config
# Interface Options > Camera > Enable
```

### 3. 테스트
```bash
# 카메라 앱 테스트
python3 test_camera.py
```

## 기능

### 자동 녹화
- FSW 상승 시 자동 카메라 활성화
- 5초 주기로 5초 길이 비디오 파일 생성
- 착륙 후 30초까지 계속 녹화
- 타임스탬프 기반 파일명 자동 생성

### 안정성 기능
- 하드웨어 연결 상태 확인
- 프로세스 타임아웃 처리
- 임시 파일 자동 정리
- 디스크 사용량 모니터링
- 에러 복구 메커니즘

### 상태 모니터링
- 실시간 카메라 상태 확인
- 저장된 비디오 파일 수 추적
- 디스크 사용량 경고 (90% 초과 시)

## 설정

### 카메라 설정 (camera/camera_config.py)
```python
CAMERA_RESOLUTION = "1920x1080"  # 해상도
CAMERA_FPS = 30                   # 프레임레이트
RECORDING_INTERVAL = 5            # 녹화 주기 (초)
VIDEO_DURATION = 5                # 비디오 길이 (초)
VIDEO_QUALITY = "23"              # h264 품질
```

### 환경별 설정
```python
# 개발 환경 (낮은 해상도, 빠른 테스트)
from camera import camera_config
settings = camera_config.get_settings("dev")
camera_config.apply_settings(settings)

# 프로덕션 환경 (고해상도, 안정적)
settings = camera_config.get_settings("prod")
camera_config.apply_settings(settings)
```

## 메시지 구조

### 송신 메시지
- **HK**: 1Hz 하트비트
- **FlightLogic**: 5Hz 카메라 상태 (상태, 파일수, 디스크사용량)
- **Telemetry**: 1Hz 카메라 상태

### 수신 메시지
- **CameraActivate**: FlightLogic에서 카메라 활성화 명령
- **CameraDeactivate**: FlightLogic에서 카메라 비활성화 명령

## 파일 구조
```
camera/
├── camera.py              # 카메라 핵심 기능
├── cameraapp.py           # 앱 메인 로직
├── camera_config.py       # 설정 파일
├── install_camera.sh      # 설치 스크립트
└── README.md              # 상세 문서
```

## 문제 해결

### 카메라가 인식되지 않는 경우
```bash
# 하드웨어 확인
vcgencmd get_camera

# 드라이버 확인
ls /dev/video*

# 권한 설정
sudo chmod 666 /dev/video0
```

### ffmpeg 오류
```bash
# ffmpeg 재설치
sudo apt remove ffmpeg
sudo apt install ffmpeg
```

### 디스크 공간 부족
```bash
# 사용량 확인
df -h

# 오래된 파일 정리
find /home/pi/cansat_videos -name "*.h264" -mtime +7 -delete
```

## 성능 최적화

### 비디오 품질 조정
- `VIDEO_QUALITY` 값을 높이면 파일 크기 감소 (23-28 권장)
- 해상도를 낮추면 메모리 사용량 감소 (1280x720 권장)

### 녹화 주기 조정
- `RECORDING_INTERVAL` 값을 조정하여 녹화 빈도 변경 (5-10초 권장)

## 주의사항
1. **디스크 공간**: 비디오 파일은 크기가 클 수 있으므로 충분한 저장 공간 확보
2. **전력 소모**: 카메라 녹화는 전력을 많이 소모하므로 배터리 상태 확인
3. **온도 관리**: 장시간 녹화 시 라즈베리파이 온도 모니터링
4. **파일 관리**: 정기적으로 오래된 비디오 파일 정리 필요