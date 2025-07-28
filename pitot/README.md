# Pitot 앱

Pitot tube 차압 센서를 위한 앱 모듈입니다.

## 기능

- **차압 측정**: ±500 Pa 범위의 차압 측정
- **온도 측정**: -40 ~ +85 °C 범위의 온도 측정
- **5Hz 샘플링**: 200ms 간격으로 데이터 수집
- **캘리브레이션**: 압력 및 온도 오프셋 지원
- **로그 저장**: `sensorlogs/pitot.txt`에 데이터 저장
- **메시지 버스**: 다른 앱들과 통신

## 파일 구조

```
pitot/
├── __init__.py          # 패키지 초기화
├── pitot.py             # Pitot 센서 헬퍼 모듈
├── pitotapp.py          # Pitot 앱 메인 모듈
├── pitot_test.py        # 단독 테스트 스크립트
└── README.md           # 이 파일
```

## 센서 사양

- **센서**: Pitot tube differential-pressure sensor
- **차압 범위**: ±500 Pa
- **온도 범위**: -40 ~ +85 °C
- **변환 시간**: 35ms
- **통신**: I2C (General Call Address 0x00)
- **샘플링**: 5Hz (200ms 간격)

## 연결

- **VCC**: 3.3V
- **GND**: Ground
- **SDA**: I2C SDA
- **SCL**: I2C SCL

## 사용법

### 단독 실행
```bash
cd pitot
python3 pitot_test.py
```

### 메인 앱에서 실행
```bash
python3 main.py
```

## 데이터 형식

### 로그 파일 (`sensorlogs/pitot.txt`)
```
2024-01-01 12:00:00.123,0.25,23.5
2024-01-01 12:00:00.323,0.30,23.6
```

### 메시지 버스 데이터
- **FlightLogic**: `"pressure,temperature"`
- **Telemetry**: `"pressure,temperature"`

## 캘리브레이션

캘리브레이션 명령어를 통해 압력과 온도 오프셋을 설정할 수 있습니다:

```
CAL:pressure_offset,temperature_offset
```

예: `CAL:0.5,1.2` 