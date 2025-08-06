# CANSAT FSW 테스트 스크립트 모음

이 폴더는 CANSAT FSW (Flight Software)의 다양한 기능을 테스트하기 위한 스크립트들을 포함합니다.

## 📁 테스트 파일 분류

### 🔧 **핵심 시스템 테스트**
- `test_system_stability.py` - 전체 시스템 안정성 테스트
- `test_all_sensors.py` - 모든 센서 통합 테스트
- `test_config.py` - 설정 시스템 테스트
- `test_appargs.py` - 애플리케이션 인수 테스트
- `test_comm.py` - 통신 시스템 테스트
- `test_main_termination.py` - 메인 프로세스 종료 테스트

### 📡 **통신 및 네트워크 테스트**
- `test_xbee.py` - XBee 무선 통신 테스트
- `test_gps.py` - GPS 센서 테스트

### 📷 **카메라 시스템 테스트**
- `test_camera.py` - 기본 카메라 기능 테스트
- `test_camera_cam.py` - libcamera cam 명령어 테스트
- `test_thermal_camera.py` - 열화상 카메라 기본 테스트
- `test_thermal_camera_advanced.py` - 열화상 카메라 고급 테스트

### 🌡️ **온도 센서 테스트**
- `test_thermo.py` - DHT11 온도/습도 센서 테스트
- `test_thermis.py` - Thermis 온도 센서 테스트
- `test_tmp007_direct.py` - TMP007 비접촉 온도 센서 테스트
- `test_imu_temperature.py` - IMU 온도 센서 테스트

### 🧭 **IMU 및 자세 센서 테스트**
- `test_imu.py` - IMU (BNO055) 기본 테스트
- `test_imu_sensor.py` - IMU 센서 상세 테스트

### 🌪️ **공기역학 센서 테스트**
- `test_barometer.py` - 기압계 센서 테스트
- `test_pitot.py` - Pitot 관 기본 테스트
- `test_pitot_calibration.py` - Pitot 관 캘리브레이션 테스트
- `test_pitot_final_fix.py` - Pitot 최종 수정사항 테스트

### 🔥 **적외선 센서 테스트**
- `test_fir1.py` - FIR1 적외선 센서 테스트

### ⚙️ **모터 및 제어 테스트**
- `test_motor_base.py` - 모터 기본 기능 테스트
- `test_motor_logic_update.py` - 모터 로직 업데이트 테스트
- `test_motor_status_fixes.py` - 모터 상태 표시 수정 테스트

### 🚀 **비행 로직 테스트**
- `test_flight_states.py` - 비행 상태 전환 테스트

### 🔧 **수정사항 테스트**
- `test_fixes.py` - 기본 수정사항 테스트
- `test_message_fixes.py` - 메시지 구조 수정 테스트
- `test_final_fixes.py` - 최종 수정사항 통합 테스트

### ⚡ **성능 및 안정성 테스트**
- `quick_stability_test.py` - 빠른 안정성 테스트

## 🚀 **사용 방법**

### 1. 개별 센서 테스트
```bash
# IMU 센서 테스트
python3 test/test_imu.py

# 카메라 테스트
python3 test/test_camera.py

# GPS 테스트
python3 test/test_gps.py
```

### 2. 통합 시스템 테스트
```bash
# 전체 시스템 안정성 테스트
python3 test/test_system_stability.py

# 모든 센서 통합 테스트
python3 test/test_all_sensors.py
```

### 3. 수정사항 검증 테스트
```bash
# 최종 수정사항 테스트
python3 test/test_final_fixes.py

# Pitot 캘리브레이션 테스트
python3 test/test_pitot_final_fix.py
```

## 📋 **테스트 실행 순서 권장사항**

1. **기본 센서 테스트**
   ```bash
   python3 test/test_imu.py
   python3 test/test_barometer.py
   python3 test/test_gps.py
   ```

2. **카메라 시스템 테스트**
   ```bash
   python3 test/test_camera.py
   python3 test/test_thermal_camera.py
   ```

3. **통신 시스템 테스트**
   ```bash
   python3 test/test_comm.py
   python3 test/test_xbee.py
   ```

4. **통합 시스템 테스트**
   ```bash
   python3 test/test_all_sensors.py
   python3 test/test_system_stability.py
   ```

## ⚠️ **주의사항**

- 모든 테스트는 Raspberry Pi 환경에서 실행되어야 합니다
- 하드웨어 센서가 연결되어 있어야 정확한 테스트가 가능합니다
- 일부 테스트는 관리자 권한이 필요할 수 있습니다
- 테스트 실행 전 가상환경 활성화를 권장합니다

## 🔍 **문제 해결**

테스트 실행 중 오류가 발생하면:
1. 센서 하드웨어 연결 상태 확인
2. 필요한 라이브러리 설치 확인
3. 권한 설정 확인
4. 로그 파일 확인

## 📝 **로그 파일 위치**

테스트 실행 시 생성되는 로그 파일들:
- `logs/` - 메인 로그 파일들
- `sensorlogs/` - 센서별 상세 로그
- `eventlogs/` - 이벤트 로그 