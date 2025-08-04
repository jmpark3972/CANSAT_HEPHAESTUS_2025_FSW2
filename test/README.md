# CANSAT 테스트 파일들

이 폴더는 CANSAT 시스템의 각 구성 요소를 테스트하기 위한 스크립트들을 포함합니다.

## 테스트 파일 목록

### 센서 테스트
- **test_imu.py** - IMU (BNO055) 센서 테스트
- **test_barometer.py** - 기압계 센서 테스트  
- **test_gps.py** - GPS 모듈 테스트
- **test_thermo.py** - 온도 센서 테스트
- **test_thermis.py** - THERMIS 센서 테스트
- **test_tmp007.py** - TMP007 온도 센서 테스트
- **test_imu_temperature.py** - BNO055 IMU 온도 센서 테스트

### FIR 센서 테스트
- **test_fir.py** - FIR (MLX90614) 센서 기본 테스트
- **test_fir_channels.py** - FIR 센서 채널별 테스트

### 시스템 테스트
- **test_main_termination.py** - 메인 앱 종료 로직 테스트
- **test_sensor_issues.py** - 센서 문제 진단 및 해결 테스트
- **test_motor_base.py** - 모터 기본 제어 테스트

## 사용법

각 테스트 파일은 독립적으로 실행할 수 있습니다:

```bash
# IMU 센서 테스트
python3 test/test_imu.py

# 기압계 센서 테스트
python3 test/test_barometer.py

# GPS 테스트
python3 test/test_gps.py

# TMP007 센서 테스트
python3 test/test_tmp007.py

# BNO055 IMU 온도 센서 테스트
python3 test/test_imu_temperature.py

# FIR 센서 테스트
python3 test/test_fir.py

# 메인 앱 종료 테스트
python3 test/test_main_termination.py

# 모터 기본 테스트
python3 test/test_motor_base.py
```

## 주의사항

- 테스트 실행 전 하드웨어 연결 상태를 확인하세요
- 일부 테스트는 실제 센서가 연결되어 있어야 정상 작동합니다
- 테스트 중 오류가 발생하면 로그를 확인하여 문제를 진단하세요 