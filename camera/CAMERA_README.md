# Pi Camera 사용 가이드

## 개요

CANSAT 프로젝트를 위한 Pi Camera 모듈 설정 및 사용법을 설명합니다.

## 파일 구조

```
camera/
├── standalone_camera.py      # 독립 실행 카메라 스크립트
├── simple_camera_test.py     # 간단한 카메라 테스트 스크립트
├── install_camera.sh         # 카메라 설치 스크립트
├── camera.py                 # 메인 카메라 모듈
├── cameraapp.py              # 카메라 앱
├── camera_config.py          # 카메라 설정
└── CAMERA_README.md          # 이 파일
```

## 설치 및 설정

### 1. 자동 설치 (권장)

```bash
# 설치 스크립트 실행
chmod +x camera/install_camera.sh
./camera/install_camera.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- 시스템 패키지 업데이트
- 카메라 관련 패키지 설치 (FFmpeg, v4l-utils 등)
- Python 패키지 설치 (OpenCV, NumPy 등)
- 카메라 인터페이스 활성화
- I2C/SPI 인터페이스 활성화
- 로그 디렉토리 생성
- 권한 설정

### 2. 수동 설치

필요한 패키지들을 수동으로 설치할 수 있습니다:

```bash
# 시스템 패키지 설치
sudo apt update
sudo apt install -y python3-picamera2 ffmpeg v4l-utils libcamera-tools

# Python 패키지 설치
pip3 install opencv-python numpy pillow

# 카메라 인터페이스 활성화
echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
```

## 사용법

### 1. 간단한 카메라 테스트

기본적인 카메라 기능을 빠르게 테스트합니다:

```bash
python3 camera/simple_camera_test.py
```

**기능:**
- 카메라 하드웨어 확인
- 카메라 드라이버 확인
- FFmpeg 설치 확인
- 디스크 공간 확인
- 단일 사진 촬영
- 단일 비디오 녹화 (raspivid)
- FFmpeg 비디오 녹화

**사용법:**
1. 스크립트 실행
2. 기본 시스템 확인 완료 후 테스트 선택
3. 원하는 기능 선택 (1-5)

### 2. 독립 실행 카메라

전체 CANSAT 시스템과 독립적으로 카메라를 실행합니다:

```bash
python3 camera/standalone_camera.py
```

**기능:**
- 실시간 카메라 상태 모니터링
- 자동 비디오 녹화 (10초 간격)
- 디스크 사용량 모니터링
- 비디오 파일 관리
- 대화형 명령어 인터페이스

**사용법:**
- `r` - 녹화 시작/중지
- `s` - 현재 상태 확인
- `q` - 프로그램 종료

### 3. CANSAT 시스템 내 카메라

메인 CANSAT 시스템에서 카메라를 사용합니다:

```bash
python3 main.py
```

카메라는 자동으로 초기화되고 FlightLogic의 명령에 따라 동작합니다.

## 설정 옵션

### 카메라 설정 파일 (`camera_config.py`)

```python
# 비디오 설정
VIDEO_DURATION = 5          # 녹화 시간 (초)
RECORDING_INTERVAL = 10     # 녹화 간격 (초)
VIDEO_QUALITY = "medium"    # 품질 (low, medium, high)
FRAME_RATE = 30            # 프레임레이트
RESOLUTION = "1920x1080"   # 해상도

# 저장 경로
VIDEO_DIR = "logs/cansat_videos"  # 비디오 저장 경로
TEMP_DIR = "logs/cansat_camera_temp"  # 임시 파일 경로
LOG_DIR = "logs/cansat_camera_logs"   # 로그 파일 경로
```

### 시스템 설정 (`/boot/config.txt`)

```bash
# 카메라 자동 감지
camera_auto_detect=1

# I2C 인터페이스 (센서 통신용)
dtparam=i2c_arm=on

# SPI 인터페이스 (필요한 경우)
dtparam=spi=on
```

## 문제 해결

### 1. 카메라 하드웨어가 감지되지 않음

**증상:** `카메라 하드웨어 감지되지 않음` 오류

**해결 방법:**
1. Pi Camera가 올바르게 연결되었는지 확인
2. CSI 케이블이 제대로 연결되었는지 확인
3. 카메라 모듈이 손상되지 않았는지 확인
4. 시스템 재부팅 후 다시 시도

```bash
# 하드웨어 확인
vcgencmd get_camera

# 시스템 로그 확인
dmesg | grep camera
```

### 2. 비디오 디바이스가 없음

**증상:** `/dev/video0` 파일이 없음

**해결 방법:**
1. 카메라 인터페이스가 활성화되었는지 확인
2. 시스템 재부팅
3. raspi-config에서 카메라 활성화

```bash
# 카메라 인터페이스 활성화
sudo raspi-config
# Interface Options > Camera > Enable

# 또는 수동으로 설정
echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
sudo reboot
```

### 3. FFmpeg 오류

**증상:** `FFmpeg 설치되지 않음` 오류

**해결 방법:**
```bash
# FFmpeg 재설치
sudo apt remove ffmpeg
sudo apt install ffmpeg

# 또는 소스에서 설치
sudo apt install -y build-essential
# FFmpeg 소스 다운로드 및 컴파일
```

### 4. 권한 오류

**증상:** `Permission denied` 오류

**해결 방법:**
```bash
# 사용자를 video 그룹에 추가
sudo usermod -a -G video $USER

# 디렉토리 권한 설정
sudo chmod 755 logs/cansat_videos
sudo chmod 755 logs/cansat_camera_temp
sudo chmod 755 logs/cansat_camera_logs

# 재로그인 또는 재부팅
```

### 5. 디스크 공간 부족

**증상:** 녹화 중 오류 발생

**해결 방법:**
```bash
# 디스크 사용량 확인
df -h

# 불필요한 파일 정리
sudo apt autoremove
sudo apt autoclean

# 오래된 비디오 파일 삭제
find logs/cansat_videos -name "*.mp4" -mtime +7 -delete
```

## 성능 최적화

### 1. 비디오 품질 조정

낮은 품질로 설정하여 파일 크기와 CPU 사용량을 줄일 수 있습니다:

```python
# camera_config.py에서 설정
VIDEO_QUALITY = "low"  # low, medium, high
FRAME_RATE = 15       # 30에서 15로 감소
RESOLUTION = "1280x720"  # 1920x1080에서 1280x720으로 감소
```

### 2. 녹화 간격 조정

```python
RECORDING_INTERVAL = 30  # 10초에서 30초로 증가
VIDEO_DURATION = 3       # 5초에서 3초로 감소
```

### 3. 자동 정리 설정

오래된 파일을 자동으로 삭제하는 스크립트:

```bash
#!/bin/bash
# 7일 이상 된 비디오 파일 삭제
find logs/cansat_videos -name "*.mp4" -mtime +7 -delete
find logs/cansat_camera_temp -name "*" -mtime +1 -delete
```

## 로그 및 모니터링

### 로그 파일 위치

- **카메라 로그:** `logs/cansat_camera_logs/`
- **비디오 파일:** `logs/cansat_videos/`
- **임시 파일:** `logs/cansat_camera_temp/`

### 로그 확인

```bash
# 실시간 로그 확인
tail -f logs/cansat_camera_logs/cameraapp_$(date +%Y-%m-%d).log

# 오류 로그 확인
grep "ERROR" logs/cansat_camera_logs/*.log

# 디스크 사용량 확인
du -sh logs/cansat_videos/
```

## 고급 기능

### 1. 자동 백업

중요한 비디오 파일을 자동으로 백업:

```bash
#!/bin/bash
# USB 드라이브에 백업
rsync -av logs/cansat_videos/ /media/pi/USB_DRIVE/backup/
```

### 2. 네트워크 스트리밍

카메라 영상을 네트워크로 스트리밍:

```bash
# FFmpeg를 사용한 스트리밍
ffmpeg -f v4l2 -i /dev/video0 -c:v libx264 -preset ultrafast -f mpegts udp://192.168.1.100:1234
```

### 3. 이미지 처리

OpenCV를 사용한 이미지 처리:

```python
import cv2
import numpy as np

# 이미지 읽기
image = cv2.imread('logs/cansat_videos/test_photo.jpg')

# 이미지 처리 (예: 그레이스케일 변환)
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# 결과 저장
cv2.imwrite('processed_image.jpg', gray)
```

## 지원 및 문의

문제가 발생하거나 추가 도움이 필요한 경우:

1. 시스템 로그 확인: `dmesg | grep camera`
2. 카메라 상태 확인: `vcgencmd get_camera`
3. 비디오 디바이스 확인: `ls -la /dev/video*`
4. FFmpeg 테스트: `ffmpeg -f v4l2 -list_formats all -i /dev/video0`

## 참고 자료

- [Raspberry Pi Camera Documentation](https://www.raspberrypi.org/documentation/raspbian/applications/camera.md)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [OpenCV Python Tutorials](https://docs.opencv.org/master/d6/d00/tutorial_py_root.html) 