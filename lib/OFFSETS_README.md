# CANSAT FSW 통합 오프셋 관리 시스템

## 개요

이 시스템은 CANSAT FSW의 모든 센서 오프셋과 보정값을 `lib/offsets.json` 파일에서 중앙 집중식으로 관리합니다.

## 주요 특징

- **통합 관리**: 모든 센서의 오프셋을 한 곳에서 관리
- **자동 마이그레이션**: 기존 개별 오프셋 파일들의 데이터를 자동으로 이전
- **스레드 안전**: 멀티스레드 환경에서 안전한 오프셋 접근
- **기존 호환성**: 기존 코드와의 호환성 유지
- **JSON 형식**: 읽기 쉬운 JSON 형식으로 저장

## 파일 구조

```
lib/
├── offsets.py          # 통합 오프셋 관리 시스템
├── offsets.json        # 오프셋 데이터 파일 (자동 생성)
├── migrate_offsets.py  # 마이그레이션 스크립트
└── OFFSETS_README.md   # 이 파일
```

## 지원하는 오프셋

### IMU (BNO055)
- `IMU.MAGNETOMETER`: 자기계 오프셋 [x, y, z]
- `IMU.GYROSCOPE`: 자이로스코프 오프셋 [x, y, z]
- `IMU.ACCELEROMETER`: 가속도계 오프셋 [x, y, z]
- `IMU.TEMPERATURE_OFFSET`: 온도 오프셋 (°C)

### Barometer (BMP390)
- `BAROMETER.ALTITUDE_OFFSET`: 고도 오프셋 (m)
- `BAROMETER.PRESSURE_OFFSET`: 압력 오프셋 (hPa)
- `BAROMETER.TEMPERATURE_OFFSET`: 온도 오프셋 (°C)

### Thermo (DHT11)
- `THERMO.TEMPERATURE_OFFSET`: 온도 오프셋 (°C)
- `THERMO.HUMIDITY_OFFSET`: 습도 오프셋 (%)

### Thermis
- `THERMIS.TEMPERATURE_OFFSET`: 온도 오프셋 (°C)

### TMP007
- `TMP007.TEMPERATURE_OFFSET`: 온도 오프셋 (°C)
- `TMP007.VOLTAGE_OFFSET`: 전압 오프셋 (μV)



### Thermal Camera (MLX90640)
- `THERMAL_CAMERA.TEMPERATURE_OFFSET`: 온도 오프셋 (K)
- `THERMAL_CAMERA.PIXEL_OFFSET`: 픽셀 오프셋 (°C)

### FIR1
- `FIR1.AMBIENT_OFFSET`: 앰비언트 온도 오프셋 (°C)
- `FIR1.OBJECT_OFFSET`: 오브젝트 온도 오프셋 (°C)

### NIR
- `NIR.OFFSET`: NIR 오프셋

### 통신
- `COMM.SIMP_OFFSET`: SIMP 오프셋

### 비행 로직
- `FLIGHT_LOGIC.DESCENT_ALT_OFFSET`: 하강 고도 오프셋 (m)
- `FLIGHT_LOGIC.ALTITUDE_THRESHOLD_OFFSET`: 고도 임계값 오프셋 (m)

## 사용법

### 기본 사용법

```python
from lib.offsets import get_offset, set_offset, get_offset_manager

# 오프셋 가져오기
barometer_offset = get_offset("BAROMETER.ALTITUDE_OFFSET", 0.0)
thermis_offset = get_offset("THERMIS.TEMPERATURE_OFFSET", 50.0)

# 오프셋 설정하기
set_offset("BAROMETER.ALTITUDE_OFFSET", 10.5)
set_offset("THERMIS.TEMPERATURE_OFFSET", 25.0)

# 관리자 인스턴스 직접 사용
manager = get_offset_manager()
manager.set_barometer_offset(15.2)
manager.set_thermis_offset(30.0)
```

### 센서별 편의 함수

```python
from lib.offsets import (
    get_imu_offsets, get_barometer_offset, get_thermis_offset,
    get_thermal_camera_offset
)

# IMU 오프셋
mag_offset, gyro_offset, accel_offset = get_imu_offsets()

# Barometer 오프셋
altitude_offset = get_barometer_offset()

# Thermis 오프셋
temp_offset = get_thermis_offset()



# Thermal Camera 오프셋
temp_offset = get_thermal_camera_offset()
```

### 모든 오프셋 출력

```python
from lib.offsets import get_offset_manager

manager = get_offset_manager()
manager.print_offsets()
```

## 마이그레이션

### 자동 마이그레이션

기존 오프셋 파일들을 새로운 시스템으로 자동 마이그레이션:

```bash
python3 lib/migrate_offsets.py
```

### 수동 마이그레이션

```python
from lib.offsets import get_offset_manager

manager = get_offset_manager()

# IMU 오프셋 설정
manager.set_imu_offsets(
    magnetometer=(409, 707, -443),
    gyroscope=(-1, -1, 2),
    accelerometer=(4, 20, -8)
)

# 다른 오프셋들 설정
manager.set_barometer_offset(0.0)
manager.set_thermis_offset(50.0)
```

## 오프셋 파일 형식

`lib/offsets.json` 파일 예시:

```json
{
  "IMU": {
    "MAGNETOMETER": [409, 707, -443],
    "GYROSCOPE": [-1, -1, 2],
    "ACCELEROMETER": [4, 20, -8],
    "TEMPERATURE_OFFSET": 0.0
  },
  "BAROMETER": {
    "ALTITUDE_OFFSET": 0.0,
    "PRESSURE_OFFSET": 0.0,
    "TEMPERATURE_OFFSET": 0.0
  },
  "THERMIS": {
    "TEMPERATURE_OFFSET": 50.0
  },

  "META": {
    "LAST_UPDATED": "2025-01-27T10:30:00",
    "VERSION": "1.0",
    "DESCRIPTION": "CANSAT FSW 통합 오프셋 관리 시스템"
  }
}
```

## 기존 코드와의 호환성

### 기존 방식 (여전히 작동)
```python
# IMU
from imu.offset import magneto_offset, gyro_offset, accel_offset

# Barometer
BAROMETER_OFFSET = 0.0

# Thermis
TEMP_OFFSET = 50.0
```

### 새로운 방식 (권장)
```python
from lib.offsets import get_imu_offsets, get_barometer_offset, get_thermis_offset

# IMU
magneto_offset, gyro_offset, accel_offset = get_imu_offsets()

# Barometer
BAROMETER_OFFSET = get_barometer_offset()

# Thermis
TEMP_OFFSET = get_thermis_offset()
```

## 명령어로 오프셋 설정

### Barometer 보정
```
CMD,3139,CAL
```

### Thermis 보정
```
CMD,3139,CAL,25.0
```



## 백업 및 복원

### 오프셋 내보내기
```python
from lib.offsets import get_offset_manager

manager = get_offset_manager()
manager.export_offsets("backup_offsets.json")
```

### 오프셋 가져오기
```python
from lib.offsets import get_offset_manager

manager = get_offset_manager()
manager.import_offsets("backup_offsets.json")
```

## 문제 해결

### 오프셋 파일이 없는 경우
시스템이 자동으로 기본값으로 `lib/offsets.json` 파일을 생성합니다.

### 마이그레이션 실패
1. `lib/migrate_offsets.py` 스크립트를 실행
2. 백업된 파일들을 확인
3. 수동으로 오프셋 설정

### 오프셋이 적용되지 않는 경우
1. 센서 앱이 새로운 오프셋 시스템을 사용하는지 확인
2. 오프셋 파일의 권한 확인
3. 로그에서 오프셋 로드 메시지 확인

## 개발자 정보

- **파일**: `lib/offsets.py`
- **버전**: 1.0
- **작성자**: CANSAT HEPHAESTUS Team
- **최종 업데이트**: 2025-01-27 