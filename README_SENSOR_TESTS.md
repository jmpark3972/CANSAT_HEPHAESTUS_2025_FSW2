# HEPHAESTUS CANSAT 센서 테스트 가이드

이 디렉토리에는 HEPHAESTUS CANSAT의 모든 센서를 개별적으로 테스트할 수 있는 스크립트들이 포함되어 있습니다.

## 📋 테스트 가능한 센서 목록

1. **Barometer** - 대기압, 온도, 고도 측정
2. **IMU** - 자이로스코프, 가속도계, 자기계, 온도
3. **FIR1** - 적외선 온도 센서 (MLX90614)
4. **TMP007** - 비접촉 온도 센서
5. **Thermal Camera** - 열화상 카메라 (MLX90640)
6. **Pitot** - 공기속도 측정
7. **Thermo** - 온도 및 습도 센서
8. **Thermis** - 온도 센서
9. **GPS** - 위치 및 시간 정보

## 🚀 사용법

### 1. 개별 센서 테스트

각 센서를 개별적으로 테스트하려면:

```bash
# Barometer 테스트
python3 test_barometer.py

# IMU 테스트
python3 test_imu.py

# FIR1 테스트
python3 test_fir1.py

# TMP007 테스트
python3 test_tmp007.py

# Thermal Camera 테스트
python3 test_thermal_camera.py

# Thermal Camera 고급 테스트 (FPS, 통계 등)
python3 test_thermal_camera_advanced.py
python3 test_thermal_camera_advanced.py -r 4 -n 10  # 4Hz, 10프레임

# Pitot 테스트
python3 test_pitot.py

# Thermo 테스트
python3 test_thermo.py

# Thermis 테스트
python3 test_thermis.py

# GPS 테스트
python3 test_gps.py
```

### 2. 통합 테스트

모든 센서를 한 번에 테스트하려면:

```bash
# 대화형 모드 (센서 선택 가능)
python3 test_all_sensors.py

# 모든 센서 자동 테스트
python3 test_all_sensors.py --all
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
   ```

2. **권한 문제**
   ```bash
   # GPIO 권한 확인
   sudo usermod -a -G gpio $USER
   ```

3. **라이브러리 누락**
   ```bash
   # 필요한 라이브러리 설치
   pip3 install adafruit-circuitpython-bmp390
   pip3 install adafruit-circuitpython-mpu6050
   pip3 install adafruit-circuitpython-mlx90614
   pip3 install adafruit-circuitpython-mlx90640
   pip3 install pyserial
   ```

### 센서별 특이사항

- **GPS**: 실외에서 테스트 권장 (위성 신호 필요)
- **Thermal Camera**: 
  - 초기화 시간이 오래 걸릴 수 있음
  - 프레임 속도: 1-16 Hz 설정 가능
  - 첫 프레임은 EEPROM 읽기로 인해 1.3-2.0초 소요
- **TMP007**: 온도 값이 높게 나올 수 있음 (보정 필요)
- **Barometer**: 고도는 해수면 기준으로 계산됨

## 📝 로그 확인

테스트 중 발생하는 오류는 콘솔에 출력됩니다. 문제 해결을 위해 다음을 확인하세요:

1. 센서 연결 상태
2. 전원 공급 상태
3. I2C 주소 설정
4. 라이브러리 버전 호환성

## 🎯 권장 테스트 순서

1. **하드웨어 연결 확인**
2. **개별 센서 테스트** (문제 센서 식별)
3. **통합 테스트** (전체 시스템 확인)
4. **문제 센서 재테스트** (수정 후)

## 📞 지원

문제가 발생하면 다음 정보를 포함하여 문의하세요:

- 사용 중인 센서
- 발생한 오류 메시지
- 하드웨어 연결 상태
- 운영체제 및 Python 버전 