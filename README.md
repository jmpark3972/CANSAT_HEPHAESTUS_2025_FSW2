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

## 3. Install Video Related modules
Opencv2 module is used in USB camera recording

    pip install opencv-python

Picamera2 module is used in Raspberry Pi Camera recording
It is pre-installed on Rapsberry Pi OS images

    sudo apt install python3-picamera2

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

# 이중 로깅 시스템 (Dual Logging System)

CANSAT 미션 중 낙하 시 라즈베리파이 파손으로 인한 데이터 손실을 방지하기 위해 추가 SD카드를 통한 이중 로깅 시스템을 구현했습니다.

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
lib/dual_logging.py          # 이중 로깅 시스템 핵심 모듈
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
from lib import dual_logging

# 이중 로깅 시스템 초기화
logger = dual_logging.init_dual_logging()

# 로그 기록
logger.log("중요한 데이터", print_logs=True)

# 시스템 종료
dual_logging.close_dual_logging()
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
- 백업 주기를 조정하려면 `dual_logging.py`의 `_backup_worker` 함수 수정