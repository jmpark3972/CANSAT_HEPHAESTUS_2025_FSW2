# CANSAT HEPHAESTUS 2025 Motor Control

## 파일 구조

### 메인 파일
- **motorapp.py** - 메인 모터 제어 앱 (현재 사용 중)
  - 페이로드, 컨테이너, 로켓 모터 제어
  - IMU Yaw 데이터 기반 짐벌 제어
  - MEC 명령 처리
  - 설정별 모터 동작 (CONF_PAYLOAD, CONF_CONTAINER, CONF_ROCKET)

### 헬퍼 파일
- **motor.py** - 모터 제어 헬퍼 함수들
  - `angle_to_pulse()` - 각도를 펄스로 변환
  - 각종 모터 제어 유틸리티 함수들

### 테스트 파일
- **test_motor_base.py** - 모터 기본 제어 테스트 (test 폴더로 이동됨)

## 사용법

```bash
# 메인 모터 앱 실행 (main.py에서 자동 실행)
python3 main.py

# 독립 실행 테스트
python3 motor/motorapp.py
```

## 기능

### 페이로드 모드 (CONF_PAYLOAD)
- IMU Yaw 데이터를 받아서 짐벌 모터 제어
- 90도를 중심으로 ±90도 회전
- MEC 명령으로 ON/OFF 제어 가능

### 컨테이너 모드 (CONF_CONTAINER)
- 페이로드 해제 모터 제어
- MEC 명령으로 ON/OFF 제어

### 로켓 모드 (CONF_ROCKET)
- 로켓 모터 활성화/대기 제어
- MEC 명령으로 활성화