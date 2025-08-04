# Camera App - Raspberry Pi Camera Module v3 Wide

## 개요
Raspberry Pi Camera Module v3 Wide를 사용하여 비디오 녹화를 수행하는 FSW 애플리케이션입니다. 상승 단계부터 착륙 후 30초까지 5초 주기로 비디오를 녹화하며, 안정성과 상세한 로깅을 우선시합니다.

## 하드웨어 요구사항
- Raspberry Pi Zero 2W
- Raspberry Pi Camera Module v3 Wide
- CSI 케이블 연결
- 충분한 저장 공간 (SD 카드 또는 외부 저장소)

## 소프트웨어 요구사항
- Python 3.7+
- ffmpeg
- v4l2-utils
- 필요한 Python 패키지: multiprocessing, threading, subprocess, pathlib

## 설치
```bash
# 의존성 설치
sudo apt update
sudo apt install ffmpeg v4l2-utils

# 또는 설치 스크립트 사용
chmod +x install_camera.sh
./install_camera.sh
```

## 설정
`camera_config.py`에서 다음 설정을 조정할 수 있습니다:
- 해상도: 1920x1080 (기본값)
- FPS: 30 (기본값)
- 녹화 간격: 5초 (기본값)
- 비디오 품질: h264 CRF 23 (기본값)
- 저장 경로: /home/pi/cansat_videos

## 기능
- **자동 녹화**: 상승 단계에서 자동 시작, 착륙 후 30초에 자동 종료
- **5초 주기 녹화**: 연속적인 비디오 파일 생성
- **상태 모니터링**: 실시간 카메라 상태, 파일 수, 디스크 사용량 추적
- **오류 처리**: 하드웨어/드라이버 확인, 프로세스 타임아웃, 디스크 공간 모니터링
- **상세한 로깅**: 모든 이벤트와 상태 변화를 로그 파일에 기록

## 로깅 시스템

### 로그 파일 구조
카메라 앱은 두 가지 유형의 로그를 생성합니다:

1. **카메라 모듈 로그** (`/home/pi/cansat_logs/camera_YYYY-MM-DD.log`)
   - 하드웨어 초기화 및 드라이버 상태
   - 녹화 시작/종료 이벤트
   - 비디오 파일 생성 정보
   - 디스크 공간 모니터링
   - FFmpeg 프로세스 상태

2. **카메라 앱 로그** (`/home/pi/cansat_logs/cameraapp_YYYY-MM-DD.log`)
   - 앱 초기화 및 종료
   - 메시지 송수신 기록
   - 상태 변화 추적
   - 스레드 시작/종료
   - 오류 및 경고 메시지

### 로그 레벨
- **INFO**: 일반적인 정보 메시지
- **WARNING**: 주의가 필요한 상황 (디스크 공간 부족 등)
- **ERROR**: 오류 상황
- **RECORDING_START/STOP**: 녹화 시작/종료
- **FILE_CREATED**: 비디오 파일 생성
- **MSG_RECEIVED/SENT**: 메시지 송수신

### 로그 예시
```
[2025-01-15 10:30:15.123] [INFO] Starting camera initialization
[2025-01-15 10:30:15.456] [INFO] Camera hardware status: supported=1 detected=1
[2025-01-15 10:30:15.789] [INFO] Camera driver available (/dev/video0)
[2025-01-15 10:30:16.012] [INFO] Disk space available: 85.2% free
[2025-01-15 10:30:16.345] [INFO] Camera initialization complete
[2025-01-15 10:30:20.567] [RECORDING_START] Video recording started
[2025-01-15 10:30:25.890] [FILE_CREATED] Video file created: video_20250115_103025.h264 (2048576 bytes)
[2025-01-15 10:30:30.123] [WARNING] Low disk space: 87.5% used
[2025-01-15 10:35:45.678] [RECORDING_STOP] Video recording stopped
```

## 메시지 구조

### 수신 메시지
- `MID_TerminateProcess`: 앱 종료 명령
- `MID_CameraActivate`: 녹화 시작 명령
- `MID_CameraDeactivate`: 녹화 중지 명령

### 송신 메시지
- `MID_SendHK`: HK 데이터 (1Hz)
- `MID_SendCameraTlmData`: 텔레메트리 데이터 (1Hz)
- `MID_SendCameraFlightLogicData`: FlightLogic 데이터 (5Hz)

## 파일 구조
```
camera/
├── camera.py              # 핵심 카메라 기능
├── cameraapp.py           # FSW 앱 로직
├── camera_config.py       # 설정 파일
├── install_camera.sh      # 설치 스크립트
├── test_camera.py         # 테스트 스크립트
└── README.md             # 이 파일
```

## 사용법
1. 하드웨어 연결 확인
2. 의존성 설치
3. FSW 실행 시 자동으로 시작됨
4. FlightLogic에서 상승 단계 진입 시 자동 녹화 시작
5. 착륙 후 30초에 자동 녹화 종료

## 문제 해결

### 일반적인 문제
1. **카메라 하드웨어 감지 실패**
   - CSI 케이블 연결 확인
   - `vcgencmd get_camera` 명령어로 상태 확인

2. **드라이버 문제**
   - `/dev/video0` 존재 확인
   - `v4l2-ctl --list-devices`로 장치 확인

3. **FFmpeg 오류**
   - FFmpeg 설치 확인
   - 권한 문제 확인

4. **디스크 공간 부족**
   - 로그에서 경고 메시지 확인
   - 오래된 비디오 파일 정리

### 로그 확인 방법
```bash
# 실시간 로그 모니터링
tail -f /home/pi/cansat_logs/camera_$(date +%Y-%m-%d).log
tail -f /home/pi/cansat_logs/cameraapp_$(date +%Y-%m-%d).log

# 특정 이벤트 검색
grep "ERROR" /home/pi/cansat_logs/camera_*.log
grep "RECORDING_START" /home/pi/cansat_logs/camera_*.log
```

## 성능 최적화
- **메모리 사용량**: 5초 주기 녹화로 메모리 부하 최소화
- **CPU 사용량**: FFmpeg ultrafast 프리셋 사용
- **디스크 I/O**: 직접 파일 저장으로 임시 파일 오버헤드 제거
- **네트워크**: 압축된 상태 정보만 전송

## 주의사항
- 카메라 하드웨어가 연결되지 않은 상태에서 실행 시 오류 발생
- 디스크 공간이 95% 이상 사용되면 경고 로그 생성
- 녹화 중 FFmpeg 프로세스 타임아웃 시 자동 재시도
- 모든 로그는 UTF-8 인코딩으로 저장

## 테스트
```bash
# 테스트 스크립트 실행
cd test/
python test_camera.py
```

## 라이센스
HEPHAESTUS CANSAT Team 