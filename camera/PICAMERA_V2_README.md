# Pi Camera v2 사용 가이드

## 개요

CANSAT 프로젝트를 위한 Pi Camera v2 모듈 설정 및 사용법을 설명합니다.

## Pi Camera v2 특징

- **센서**: OV5647 (8MP)
- **해상도**: 최대 3280x2464
- **프레임레이트**: 최대 30fps (1080p)
- **연결**: CSI 인터페이스
- **호환성**: Raspberry Pi 1, 2, 3, 4, Zero

## 파일 구조

```
camera/
├── test_picamera_v2.py        # Pi Camera v2 전용 테스트 스크립트
├── setup_picamera_v2.sh       # Pi Camera v2 빠른 설정 스크립트
├── standalone_camera.py       # 독립 실행 카메라 스크립트
├── simple_camera_test.py      # 간단한 카메라 테스트 스크립트
├── install_camera.sh          # 카메라 설치 스크립트
├── camera.py                  # 메인 카메라 모듈
├── cameraapp.py               # 카메라 앱
├── camera_config.py           # 카메라 설정
└── PICAMERA_V2_README.md      # 이 파일
```

## 설치 및 설정

### 1. 빠른 설정 (권장)

```bash
# Pi Camera v2 전용 설정 스크립트 실행
chmod +x camera/setup_picamera_v2.sh
sudo ./camera/setup_picamera_v2.sh
```

이 스크립트는 다음을 자동으로 수행합니다:
- `/boot/config.txt` 백업 생성
- 카메라 자동 감지 설정 추가
- OV5647 센서 오버레이 설정 추가
- I2C 인터페이스 활성화
- 하드웨어 및 패키지 확인

### 2. 수동 설정

필요한 경우 수동으로 설정할 수 있습니다:

```bash
# /boot/config.txt 편집
sudo nano /boot/config.txt

# 다음 설정 추가:
camera_auto_detect=1
dtoverlay=ov5647
dtparam=i2c_arm=on

# 저장 후 재부팅
sudo reboot
```

### 3. 패키지 설치

```bash
# 시스템 패키지 업데이트
sudo apt update

# 카메라 관련 패키지 설치
sudo apt install -y \
    python3-picamera2 \
    python3-picamera2-doc \
    ffmpeg \
    v4l-utils \
    libcamera-tools \
    libcamera-apps

# Python 패키지 설치
pip3 install opencv-python numpy pillow
```

## 사용법

### 1. Pi Camera v2 전용 테스트

Pi Camera v2에 특화된 테스트를 실행합니다:

```bash
python3 camera/test_picamera_v2.py
```

**기능:**
- Pi Camera v2 하드웨어 확인
- OV5647 센서 설정 확인
- raspistill/raspivid 테스트
- libcamera 호환성 확인
- 설정 파일 검증

### 2. 간단한 카메라 테스트

기본적인 카메라 기능을 테스트합니다:

```bash
python3 camera/simple_camera_test.py
```

### 3. 독립 실행 카메라

전체 CANSAT 시스템과 독립적으로 카메라를 실행합니다:

```bash
python3 camera/standalone_camera.py
```

### 4. CANSAT 시스템 내 카메라

메인 CANSAT 시스템에서 카메라를 사용합니다:

```bash
python3 main.py
```

## 설정 옵션

### /boot/config.txt 설정

```bash
# 카메라 자동 감지
camera_auto_detect=1

# Pi Camera v2 전용 오버레이 (OV5647 센서)
dtoverlay=ov5647

# I2C 인터페이스 (센서 통신용)
dtparam=i2c_arm=on

# SPI 인터페이스 (필요한 경우)
dtparam=spi=on
```

### 카메라 설정 파일 (`camera_config.py`)

```python
# Pi Camera v2 최적화 설정
VIDEO_DURATION = 5          # 녹화 시간 (초)
RECORDING_INTERVAL = 10     # 녹화 간격 (초)
VIDEO_QUALITY = "medium"    # 품질 (low, medium, high)
FRAME_RATE = 30            # 프레임레이트
RESOLUTION = "1920x1080"   # 해상도 (v2 최적)

# 저장 경로
VIDEO_DIR = "logs/cansat_videos"
TEMP_DIR = "logs/cansat_camera_temp"
LOG_DIR = "logs/cansat_camera_logs"
```

## 문제 해결

### 1. 카메라 하드웨어가 감지되지 않음

**증상:** `카메라 하드웨어 감지되지 않음` 오류

**해결 방법:**
1. Pi Camera v2가 올바르게 연결되었는지 확인
2. CSI 케이블이 제대로 연결되었는지 확인
3. `/boot/config.txt`에 다음 설정 확인:
   ```bash
   camera_auto_detect=1
   dtoverlay=ov5647
   ```
4. 시스템 재부팅 후 다시 시도

```bash
# 하드웨어 확인
vcgencmd get_camera

# 시스템 로그 확인
dmesg | grep camera
```

### 2. OV5647 센서 오류

**증상:** `OV5647` 관련 오류

**해결 방법:**
```bash
# /boot/config.txt에 오버레이 추가
echo "dtoverlay=ov5647" | sudo tee -a /boot/config.txt

# 재부팅
sudo reboot
```

### 3. 비디오 디바이스가 없음

**증상:** `/dev/video0` 파일이 없음

**해결 방법:**
1. 카메라 인터페이스가 활성화되었는지 확인
2. 시스템 재부팅
3. raspi-config에서 카메라 활성화

```bash
# 카메라 인터페이스 활성화
sudo raspi-config
# Interface Options > Camera > Enable
```

### 4. raspistill/raspivid 오류

**증상:** `raspistill` 또는 `raspivid` 명령어 오류

**해결 방법:**
```bash
# 패키지 재설치
sudo apt remove raspberrypi-kernel
sudo apt install raspberrypi-kernel

# 또는 libcamera 사용
libcamera-still -o test.jpg
libcamera-vid -o test.h264
```

## 성능 최적화

### 1. Pi Camera v2 최적화 설정

```python
# camera_config.py에서 설정
VIDEO_QUALITY = "medium"  # v2에 최적화된 품질
FRAME_RATE = 30          # v2 최대 프레임레이트
RESOLUTION = "1920x1080" # v2 최적 해상도
```

### 2. 메모리 및 CPU 최적화

```bash
# GPU 메모리 할당 증가
echo "gpu_mem=128" | sudo tee -a /boot/config.txt

# CPU 성능 모드
echo "arm_freq=1400" | sudo tee -a /boot/config.txt
```

### 3. 저장 공간 최적화

```bash
# 오래된 파일 자동 정리
find logs/cansat_videos -name "*.mp4" -mtime +7 -delete
find logs/cansat_camera_temp -name "*" -mtime +1 -delete
```

## 고급 기능

### 1. libcamera 사용

Pi Camera v2는 libcamera와 호환됩니다:

```bash
# 사진 촬영
libcamera-still -o photo.jpg

# 비디오 녹화
libcamera-vid -o video.h264

# 카메라 목록 확인
libcamera-hello --list-cameras
```

### 2. Python picamera2 사용

```python
from picamera2 import Picamera2

# 카메라 초기화
picam2 = Picamera2()
config = picam2.create_preview_configuration()
picam2.configure(config)
picam2.start()

# 사진 촬영
picam2.capture_file("test.jpg")
```

### 3. OpenCV 연동

```python
import cv2

# 카메라 캡처
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

ret, frame = cap.read()
if ret:
    cv2.imwrite("opencv_test.jpg", frame)

cap.release()
```

## 지원 및 문의

문제가 발생하거나 추가 도움이 필요한 경우:

1. **하드웨어 확인:**
   ```bash
   vcgencmd get_camera
   ls -la /dev/video*
   ```

2. **설정 확인:**
   ```bash
   grep -E "(camera|ov5647)" /boot/config.txt
   ```

3. **로그 확인:**
   ```bash
   dmesg | grep camera
   journalctl -u camera-app
   ```

4. **테스트 실행:**
   ```bash
   python3 camera/test_picamera_v2.py
   ```

## 참고 자료

- [Raspberry Pi Camera Module v2 Documentation](https://www.raspberrypi.org/documentation/hardware/camera/)
- [PiCamera2 Documentation](https://picamera2.readthedocs.io/)
- [libcamera Documentation](https://libcamera.org/)
- [OV5647 Sensor Datasheet](https://www.ovt.com/products/sensor.php?id=79)

## Pi Camera v2 vs v3 비교

| 특징 | Pi Camera v2 | Pi Camera v3 |
|------|-------------|-------------|
| 센서 | OV5647 | IMX708 |
| 해상도 | 8MP | 12MP |
| 최대 해상도 | 3280x2464 | 4056x3040 |
| 프레임레이트 | 30fps (1080p) | 60fps (1080p) |
| 자동초점 | 없음 | 있음 |
| HDR | 없음 | 있음 |
| 호환성 | Pi 1,2,3,4,Zero | Pi 3,4,Zero 2W |
| 설정 | dtoverlay=ov5647 | camera_auto_detect=1 | 