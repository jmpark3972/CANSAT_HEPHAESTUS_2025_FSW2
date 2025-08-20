# HEPHAESTUS CANSAT 센서 테스트 가이드

이 폴더는 HEPHAESTUS CANSAT의 모든 센서와 시스템 구성 요소를 테스트하기 위한 스크립트들을 포함합니다.

## 📋 테스트 가능한 센서 목록

### 🔧 센서 테스트
- **test_barometer.py** - 대기압, 온도, 고도 측정 (BMP390)
- **test_imu.py** - 자이로스코프, 가속도계, 자기계, 온도 (BNO055)
- **test_imu_temperature.py** - BNO055 IMU 온도 센서 전용 테스트
- **test_fir1.py** - 적외선 온도 센서 (MLX90614)
- **test_tmp007_direct.py** - 비접촉 온도 센서 (TMP007) 직접 I2C 연결 테스트
- **test_thermal_camera.py** - 열화상 카메라 (MLX90640) 기본 테스트
- **test_thermal_camera_advanced.py** - 열화상 카메라 고급 테스트 (FPS, 통계 등)

- **test_thermo.py** - 온도 및 습도 센서 (DHT11)
- **test_thermis.py** - 온도 센서 (Thermis)
- **test_gps.py** - 위치 및 시간 정보 (GPS)

### 🎯 시스템 테스트
- **test_all_sensors.py** - 모든 센서 통합 테스트 (대화형 모드)
- **test_main_termination.py** - 메인 앱 종료 로직 테스트
- **test_motor_base.py** - 모터 기본 제어 테스트
- **test_flight_states.py** - 비행 상태 관리 시스템 테스트
- **test_camera.py** - 카메라 앱 테스트 (Raspberry Pi Camera Module v3 Wide)

## 🚀 사용법

### 1. 개별 센서 테스트

각 센서를 개별적으로 테스트하려면:

```bash
# Barometer 테스트
python3 test/test_barometer.py

# IMU 테스트
python3 test/test_imu.py

# FIR1 테스트
python3 test/test_fir1.py

# TMP007 직접 I2C 연결 테스트
python3 test/test_tmp007_direct.py

# Thermal Camera 기본 테스트
python3 test/test_thermal_camera.py

# Thermal Camera 고급 테스트 (FPS, 통계 등)
python3 test/test_thermal_camera_advanced.py
python3 test/test_thermal_camera_advanced.py -r 4 -n 10  # 4Hz, 10프레임



# Thermo 테스트
python3 test/test_thermo.py

# Thermis 테스트
python3 test/test_thermis.py

# GPS 테스트
python3 test/test_gps.py

# 카메라 테스트
python3 test/test_camera.py
```

### 2. 통합 테스트

모든 센서를 한 번에 테스트하려면:

```bash
# 대화형 모드 (센서 선택 가능)
python3 test/test_all_sensors.py

# 모든 센서 자동 테스트
python3 test/test_all_sensors.py --all
```

### 3. 시스템 테스트

```bash
# 메인 앱 종료 테스트
python3 test/test_main_termination.py

# 모터 기본 테스트
python3 test/test_motor_base.py

# 비행 상태 관리 테스트
python3 test/test_flight_states.py
```

## 📊 테스트 결과 해석

### ✅ 정상 작동
- 센서 초기화 성공
- 데이터 읽기 성공
- 예상 범위 내의 값 출력

### ❌ 문제 발생 시
1. **초기화 실패**: 하드웨어 연결 확인
2. **데이터 읽기 오류**: 센서 상태 확인
3. **비정상적인 값**: 센서 보정 필요

## 🔧 문제 해결

### 일반적인 문제들

1. **I2C 연결 오류**
   ```bash
   # I2C 디바이스 확인
   i2cdetect -y 1
   i2cdetect -y 0
   ```

2. **권한 문제**
   ```bash
   # GPIO 권한 확인
   sudo usermod -a -G gpio $USER
   
   # Serial 포트 권한 확인
   sudo usermod -a -G dialout $USER
   ```

3. **라이브러리 누락**
   ```bash
   # 필요한 라이브러리 설치
   pip3 install adafruit-circuitpython-bmp390
   pip3 install adafruit-circuitpython-bno055
   pip3 install adafruit-circuitpython-mlx90614
   pip3 install adafruit-circuitpython-gps
   ```

4. **카메라 관련 문제**
   ```bash
   # 카메라 하드웨어 확인
   vcgencmd get_camera
   
   # 카메라 드라이버 확인
   ls /dev/video*
   
   # ffmpeg 설치 확인
   ffmpeg -version
   ```

## ⚠️ 주의사항

- 테스트 실행 전 하드웨어 연결 상태를 확인하세요
- 일부 테스트는 실제 센서가 연결되어 있어야 정상 작동합니다
- 테스트 중 오류가 발생하면 로그를 확인하여 문제를 진단하세요
- 카메라 테스트는 실제 Raspberry Pi Camera Module v3 Wide가 연결되어 있어야 합니다
- 일부 테스트는 sudo 권한이 필요할 수 있습니다

## 📝 로그 확인

테스트 중 발생하는 오류는 다음 위치에서 확인할 수 있습니다:

```bash
# 이벤트 로그
tail -f eventlogs/error_event.txt
tail -f eventlogs/info_event.txt

# 센서별 로그
tail -f logs/*.log

# 카메라 로그
tail -f /home/pi/cansat_logs/camera_*.log
``` 