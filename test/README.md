# CANSAT HEPHAESTUS 2025 FSW2 - 테스트 가이드

## 📋 테스트 파일 분류

### 🔧 진단 테스트 (Diagnostic Tests)
- `debug_fsw_startup.py` - FSW 시작 문제 진단
- `path_test.py` - Python 경로 및 import 테스트
- `import_test.py` - 모든 모듈 import 테스트
- `basic_main_test.py` - main.py 기본 실행 테스트
- `minimal_fsw_test.py` - 최소한의 FSW 테스트

### 🚀 안정성 테스트 (Stability Tests)
- `quick_stability_test.py` - 빠른 안정성 테스트
- `test_system_stability.py` - 시스템 안정성 시뮬레이션
- `test_main_termination.py` - main.py 종료 테스트

### 📦 단위 테스트 (Unit Tests)
- `test_config.py` - 설정 관리 테스트
- `test_appargs.py` - 앱 인수 및 메시지 ID 테스트
- `test_comm.py` - 통신 모듈 테스트
- `test_flight_states.py` - 비행 상태 관리 테스트

### 🔌 하드웨어 테스트 (Hardware Tests)
- `test_barometer.py` - 기압계 센서 테스트
- `test_imu.py` - IMU 센서 테스트
- `test_imu_sensor.py` - IMU 센서 직접 테스트
- `test_imu_temperature.py` - IMU 온도 센서 테스트
- `test_tmp007_direct.py` - TMP007 센서 직접 테스트
- `test_camera.py` - 카메라 모듈 테스트
- `test_camera_cam.py` - cam 명령어 테스트
- `test_thermal_camera.py` - 열화상 카메라 테스트
- `test_thermal_camera_advanced.py` - 열화상 카메라 고급 테스트
- `test_pitot.py` - Pitot 센서 테스트
- `test_fir1.py` - FIR1 센서 테스트
- `test_thermo.py` - 온도 센서 테스트
- `test_thermis.py` - Thermis 센서 테스트
- `test_gps.py` - GPS 모듈 테스트
- `test_xbee.py` - XBee 통신 테스트
- `test_motor_base.py` - 모터 기본 기능 테스트

### 🔄 통합 테스트 (Integration Tests)
- `test_all_sensors.py` - 모든 센서 통합 테스트
- `test_coverage.py` - 테스트 커버리지 분석

### 🛠️ 수정사항 테스트 (Fix Tests)
- `test_fixes.py` - 기본 수정사항 테스트
- `test_final_fixes.py` - 최종 수정사항 테스트
- `test_message_fixes.py` - 메시지 구조 수정사항 테스트
- `test_motor_logic_update.py` - 모터 로직 업데이트 테스트
- `test_motor_status_fixes.py` - 모터 상태 수정사항 테스트
- `test_pitot_calibration.py` - Pitot 캘리브레이션 테스트
- `test_pitot_final_fix.py` - Pitot 최종 수정사항 테스트

### 🚀 실행 도구 (Execution Tools)
- `run_all_tests.py` - 모든 테스트 실행
- `quick_test.py` - 핵심 테스트만 실행

## 🎯 사용법

### 1. 개별 테스트 실행
```bash
# 진단 테스트
python3 test/debug_fsw_startup.py
python3 test/path_test.py

# 하드웨어 테스트
python3 test/test_barometer.py
python3 test/test_imu.py

# 단위 테스트
python3 test/test_config.py
python3 test/test_appargs.py
```

### 2. 모든 테스트 실행
```bash
# 모든 테스트 실행
python3 test/run_all_tests.py

# 핵심 테스트만 실행
python3 test/quick_test.py
```

### 3. 안정성 테스트
```bash
# 빠른 안정성 테스트
python3 test/quick_stability_test.py

# 시스템 안정성 시뮬레이션
python3 test/test_system_stability.py
```

## 📊 테스트 결과 해석

### ✅ 성공 표시
- `✅` - 테스트 성공
- `🎉` - 모든 테스트 통과
- `📊` - 통계 정보

### ❌ 실패 표시
- `❌` - 테스트 실패
- `⚠️` - 경고
- `🚨` - 심각한 오류

### ⏰ 타임아웃
- `⏰` - 테스트 타임아웃 (60초 초과)

## 🔧 문제 해결

### Import 오류 해결
```bash
# 프로젝트 루트에서 실행
cd /path/to/CANSAT_HEPHAESTUS_2025_FSW2
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

### 의존성 설치
```bash
# 필요한 패키지 설치
pip3 install -r requirements.txt

# 시스템 패키지 설치
sudo apt update
sudo apt install -y python3-pigpio libcamera-tools
```

### 권한 문제 해결
```bash
# GPIO 권한 설정
sudo usermod -a -G gpio $USER
sudo usermod -a -G video $USER
```

## 📈 테스트 통계

### 현재 상태 (2025-08-06)
- **총 테스트 파일**: 36개
- **성공률**: 41.7% (15/36)
- **주요 문제**: Import 경로, 함수 시그니처, 설정 파일 생성

### 개선 목표
- **목표 성공률**: 85% 이상
- **테스트 실행 시간**: 단축
- **유지보수성**: 향상

## 🚀 향후 계획

### 단기 계획 (1-2주)
1. Import 경로 문제 해결
2. 함수 시그니처 수정
3. 불필요한 테스트 파일 정리

### 중기 계획 (1개월)
1. 테스트 자동화 개선
2. CI/CD 파이프라인 구축
3. 테스트 커버리지 확대

### 장기 계획 (3개월)
1. 성능 테스트 추가
2. 보안 테스트 구현
3. 문서화 개선

---

**팀**: HEPHAESTUS  
**최종 업데이트**: 2025-08-06  
**버전**: 2.0 