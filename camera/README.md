# Camera App - Raspberry Pi Camera Module v3 Wide

## 개요
라즈베리파이 카메라 모듈 v3 wide를 사용하여 FSW 상승부터 낙하 후 30초까지 5초 주기로 영상을 녹화하는 앱입니다.

## 하드웨어 요구사항
- Raspberry Pi Zero 2W
- Raspberry Pi Camera Module v3 Wide
- CSI 케이블 연결

## 소프트웨어 요구사항
- ffmpeg (비디오 녹화용)
- v4l2-utils (카메라 드라이버 확인용)

## 설치
```bash
# ffmpeg 설치
sudo apt update
sudo apt install ffmpeg v4l2-utils

# 카메라 활성화 (raspi-config에서)
sudo raspi-config
# Interface Options > Camera > Enable
```

## 설정
### 카메라 설정 (camera.py)
```python
# 해상도 및 프레임레이트
CAMERA_RESOLUTION = "1920x1080"  # Full HD
CAMERA_FPS = 30

# 녹화 설정
RECORDING_INTERVAL = 5  # 5초 주기
VIDEO_DURATION = 5      # 5초 녹화
VIDEO_FORMAT = "h264"   # 비디오 포맷
VIDEO_QUALITY = "23"    # h264 품질 (낮을수록 좋은 품질)

# 저장 경로
VIDEO_DIR = "/home/pi/cansat_videos"
TEMP_DIR = "/tmp/camera_temp"
```

## 기능
### 1. 자동 녹화
- FSW 상승 시부터 낙하 후 30초까지 자동 녹화
- 5초 주기로 5초 길이의 비디오 파일 생성
- 타임스탬프 기반 파일명 자동 생성

### 2. 안정성 기능
- 하드웨어 연결 상태 확인
- 드라이버 가용성 확인
- 프로세스 타임아웃 처리
- 임시 파일 자동 정리
- 에러 복구 메커니즘

### 3. 상태 모니터링
- 실시간 카메라 상태 확인
- 저장된 비디오 파일 수 추적
- 디스크 사용량 모니터링

## 메시지 구조
### 송신 메시지
- **HK**: 1Hz 하트비트
- **FlightLogic**: 5Hz 카메라 상태 (상태, 파일수, 디스크사용량)
- **Telemetry**: 1Hz 카메라 상태

### 수신 메시지
- **CameraActivate**: FlightLogic에서 카메라 활성화 명령
- **CameraDeactivate**: FlightLogic에서 카메라 비활성화 명령
- **TerminateProcess**: 메인 앱에서 프로세스 종료 명령

## 파일 구조
```
camera/
├── camera.py          # 카메라 핵심 기능
├── cameraapp.py       # 앱 메인 로직
└── README.md          # 이 파일
```

## 사용법
### 1. 독립 실행
```bash
cd camera
python3 cameraapp.py
```

### 2. 메인 앱 통합
메인 앱에서 카메라 앱을 프로세스로 실행:
```python
# main.py에서
camera_process = Process(target=cameraapp_main, args=(Main_Queue, Main_Pipe))
camera_process.start()
```

## 문제 해결
### 1. 카메라가 인식되지 않는 경우
```bash
# 하드웨어 확인
vcgencmd get_camera

# 드라이버 확인
ls /dev/video*

# 카메라 활성화
sudo raspi-config
```

### 2. ffmpeg 오류
```bash
# ffmpeg 재설치
sudo apt remove ffmpeg
sudo apt install ffmpeg

# 권한 확인
sudo chmod 666 /dev/video0
```

### 3. 디스크 공간 부족
```bash
# 사용량 확인
df -h

# 오래된 파일 정리
find /home/pi/cansat_videos -name "*.h264" -mtime +7 -delete
```

## 성능 최적화
### 1. 비디오 품질 조정
- `VIDEO_QUALITY` 값을 높이면 파일 크기 감소
- 권장값: 23-28 (품질과 크기 균형)

### 2. 해상도 조정
- 메모리 사용량 감소를 위해 해상도 낮출 수 있음
- 권장값: 1280x720 (HD)

### 3. 녹화 주기 조정
- `RECORDING_INTERVAL` 값을 조정하여 녹화 빈도 변경
- 권장값: 5-10초

## 로그
카메라 앱의 모든 이벤트는 `eventlogs/` 디렉토리에 기록됩니다:
- `info_event.txt`: 일반 정보
- `error_event.txt`: 오류 메시지
- `debug_event.txt`: 디버그 정보

## 주의사항
1. **디스크 공간**: 비디오 파일은 크기가 클 수 있으므로 충분한 저장 공간 확보
2. **전력 소모**: 카메라 녹화는 전력을 많이 소모하므로 배터리 상태 확인
3. **온도 관리**: 장시간 녹화 시 라즈베리파이 온도 모니터링
4. **파일 관리**: 정기적으로 오래된 비디오 파일 정리 필요 