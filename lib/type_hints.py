#!/usr/bin/env python3
"""
CANSAT FSW 타입 힌팅 정의
모든 앱에서 공통으로 사용할 타입 정의
"""

from typing import (
    Dict, List, Optional, Union, Tuple, Callable, Any,
    TypeVar, Generic, Protocol, runtime_checkable
)
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import threading

# 기본 타입 별칭
AppID = int
MID = int
ProcessID = int
ThreadID = int

# 센서 데이터 타입
Temperature = float  # °C
Pressure = float     # hPa
Altitude = float     # m
Humidity = float     # %
Voltage = float      # V
Current = float      # A
Power = float        # W
Frequency = float    # Hz
Angle = float        # degrees
Acceleration = float # m/s²
AngularVelocity = float  # rad/s
MagneticField = float    # μT

# 시간 관련 타입
Timestamp = float    # Unix timestamp
Duration = float     # seconds
Interval = float     # seconds

# 파일 관련 타입
FilePath = Union[str, Path]
FileSize = int       # bytes

# 통신 관련 타입
SerialPort = str
BaudRate = int
IPAddress = str
Port = int

# 설정 관련 타입
ConfigKey = str
ConfigValue = Union[str, int, float, bool, List, Dict]

# 로깅 관련 타입
LogLevel = str  # "DEBUG", "INFO", "WARNING", "ERROR"
LogMessage = str

# 상태 관련 타입
AppStatus = str  # "RUNNING", "STOPPED", "ERROR", "INITIALIZING"
FlightState = str  # "LAUNCHPAD", "ASCENT", "APOGEE", "DESCENT", "LANDED"

# 제네릭 타입 변수
T = TypeVar('T')
K = TypeVar('K')
V = TypeVar('V')

# 데이터 클래스들
@dataclass
class SensorData:
    """센서 데이터 기본 클래스"""
    timestamp: Timestamp
    temperature: Optional[Temperature] = None
    pressure: Optional[Pressure] = None
    altitude: Optional[Altitude] = None
    humidity: Optional[Humidity] = None
    voltage: Optional[Voltage] = None
    current: Optional[Current] = None
    power: Optional[Power] = None

@dataclass
class IMUData(SensorData):
    """IMU 센서 데이터"""
    roll: Optional[Angle] = None
    pitch: Optional[Angle] = None
    yaw: Optional[Angle] = None
    acceleration_x: Optional[Acceleration] = None
    acceleration_y: Optional[Acceleration] = None
    acceleration_z: Optional[Acceleration] = None
    gyro_x: Optional[AngularVelocity] = None
    gyro_y: Optional[AngularVelocity] = None
    gyro_z: Optional[AngularVelocity] = None
    magnetic_x: Optional[MagneticField] = None
    magnetic_y: Optional[MagneticField] = None
    magnetic_z: Optional[MagneticField] = None

@dataclass
class GPSData(SensorData):
    """GPS 데이터"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[Altitude] = None
    satellites: Optional[int] = None
    gps_time: Optional[str] = None
    fix_quality: Optional[int] = None

@dataclass
class BarometerData(SensorData):
    """기압계 데이터"""
    pressure: Optional[Pressure] = None
    altitude: Optional[Altitude] = None
    sea_level_pressure: Optional[Pressure] = None

@dataclass
class TemperatureData(SensorData):
    """온도 센서 데이터"""
    temperature: Optional[Temperature] = None
    humidity: Optional[Humidity] = None

@dataclass
class MotorData:
    """모터 데이터"""
    timestamp: Timestamp
    angle: Optional[Angle] = None
    pulse: Optional[int] = None
    status: Optional[str] = None
    target_angle: Optional[Angle] = None
    target_pulse: Optional[int] = None

@dataclass
class CameraData:
    """카메라 데이터"""
    timestamp: Timestamp
    recording: bool = False
    file_count: int = 0
    current_file: Optional[str] = None
    disk_usage: Optional[FileSize] = None
    status: Optional[str] = None

@dataclass
class SystemStatus:
    """시스템 상태"""
    timestamp: Timestamp
    memory_usage: float  # %
    disk_usage: float    # %
    cpu_usage: float     # %
    temperature: Optional[Temperature] = None
    uptime: Optional[Duration] = None
    app_count: int = 0
    running_apps: List[str] = None

@dataclass
class AppInfo:
    """앱 정보"""
    app_id: AppID
    app_name: str
    process_id: Optional[ProcessID] = None
    thread_count: int = 0
    status: AppStatus = "STOPPED"
    start_time: Optional[Timestamp] = None
    last_heartbeat: Optional[Timestamp] = None
    error_count: int = 0
    memory_usage: Optional[float] = None

@dataclass
class MessageData:
    """메시지 데이터"""
    sender_app: AppID
    receiver_app: AppID
    message_id: MID
    data: str
    timestamp: Timestamp
    sequence: Optional[int] = None

@dataclass
class ConfigData:
    """설정 데이터"""
    key: ConfigKey
    value: ConfigValue
    description: Optional[str] = None
    category: Optional[str] = None
    default_value: Optional[ConfigValue] = None
    min_value: Optional[Union[int, float]] = None
    max_value: Optional[Union[int, float]] = None
    unit: Optional[str] = None

@dataclass
class LogEntry:
    """로그 엔트리"""
    timestamp: Timestamp
    level: LogLevel
    message: LogMessage
    app_name: Optional[str] = None
    thread_id: Optional[ThreadID] = None
    process_id: Optional[ProcessID] = None

# 프로토콜 정의
@runtime_checkable
class SensorProtocol(Protocol):
    """센서 프로토콜"""
    def read_data(self) -> Optional[SensorData]:
        """센서 데이터 읽기"""
        ...
    
    def initialize(self) -> bool:
        """센서 초기화"""
        ...
    
    def terminate(self) -> None:
        """센서 종료"""
        ...

@runtime_checkable
class AppProtocol(Protocol):
    """앱 프로토콜"""
    def initialize(self) -> bool:
        """앱 초기화"""
        ...
    
    def run(self) -> None:
        """앱 실행"""
        ...
    
    def terminate(self) -> None:
        """앱 종료"""
        ...
    
    def get_status(self) -> AppStatus:
        """앱 상태 반환"""
        ...

@runtime_checkable
class ConfigProtocol(Protocol):
    """설정 프로토콜"""
    def get(self, key: ConfigKey, default: Optional[ConfigValue] = None) -> ConfigValue:
        """설정값 가져오기"""
        ...
    
    def set(self, key: ConfigKey, value: ConfigValue) -> None:
        """설정값 설정"""
        ...
    
    def save(self) -> bool:
        """설정 저장"""
        ...
    
    def load(self) -> bool:
        """설정 로드"""
        ...

# 타입 검증 함수들
def is_valid_temperature(temp: Any) -> bool:
    """온도값 유효성 검사"""
    if not isinstance(temp, (int, float)):
        return False
    return -273.15 <= temp <= 1000  # 절대영도 ~ 1000°C

def is_valid_pressure(pressure: Any) -> bool:
    """압력값 유효성 검사"""
    if not isinstance(pressure, (int, float)):
        return False
    return 0 <= pressure <= 2000  # 0 ~ 2000 hPa

def is_valid_altitude(altitude: Any) -> bool:
    """고도값 유효성 검사"""
    if not isinstance(altitude, (int, float)):
        return False
    return -1000 <= altitude <= 50000  # -1000m ~ 50km

def is_valid_humidity(humidity: Any) -> bool:
    """습도값 유효성 검사"""
    if not isinstance(humidity, (int, float)):
        return False
    return 0 <= humidity <= 100  # 0 ~ 100%

def is_valid_angle(angle: Any) -> bool:
    """각도값 유효성 검사"""
    if not isinstance(angle, (int, float)):
        return False
    return -180 <= angle <= 180  # -180° ~ 180°

def is_valid_app_id(app_id: Any) -> bool:
    """앱 ID 유효성 검사"""
    if not isinstance(app_id, int):
        return False
    return 1 <= app_id <= 100  # 1 ~ 100

def is_valid_mid(mid: Any) -> bool:
    """MID 유효성 검사"""
    if not isinstance(mid, int):
        return False
    return 1000 <= mid <= 9999  # 1000 ~ 9999

# 타입 변환 함수들
def to_temperature(value: Any) -> Optional[Temperature]:
    """온도로 변환"""
    try:
        temp = float(value)
        return temp if is_valid_temperature(temp) else None
    except (ValueError, TypeError):
        return None

def to_pressure(value: Any) -> Optional[Pressure]:
    """압력으로 변환"""
    try:
        pressure = float(value)
        return pressure if is_valid_pressure(pressure) else None
    except (ValueError, TypeError):
        return None

def to_altitude(value: Any) -> Optional[Altitude]:
    """고도로 변환"""
    try:
        altitude = float(value)
        return altitude if is_valid_altitude(altitude) else None
    except (ValueError, TypeError):
        return None

def to_humidity(value: Any) -> Optional[Humidity]:
    """습도로 변환"""
    try:
        humidity = float(value)
        return humidity if is_valid_humidity(humidity) else None
    except (ValueError, TypeError):
        return None

def to_angle(value: Any) -> Optional[Angle]:
    """각도로 변환"""
    try:
        angle = float(value)
        return angle if is_valid_angle(angle) else None
    except (ValueError, TypeError):
        return None

# 유틸리티 함수들
def create_sensor_data(
    temperature: Optional[Temperature] = None,
    pressure: Optional[Pressure] = None,
    altitude: Optional[Altitude] = None,
    humidity: Optional[Humidity] = None,
    **kwargs
) -> SensorData:
    """센서 데이터 생성"""
    return SensorData(
        timestamp=datetime.now().timestamp(),
        temperature=temperature,
        pressure=pressure,
        altitude=altitude,
        humidity=humidity,
        **kwargs
    )

def validate_sensor_data(data: SensorData) -> bool:
    """센서 데이터 유효성 검사"""
    if data.temperature is not None and not is_valid_temperature(data.temperature):
        return False
    if data.pressure is not None and not is_valid_pressure(data.pressure):
        return False
    if data.altitude is not None and not is_valid_altitude(data.altitude):
        return False
    if data.humidity is not None and not is_valid_humidity(data.humidity):
        return False
    return True

def format_sensor_data(data: SensorData) -> str:
    """센서 데이터 포맷팅"""
    parts = []
    if data.temperature is not None:
        parts.append(f"T:{data.temperature:.2f}°C")
    if data.pressure is not None:
        parts.append(f"P:{data.pressure:.2f}hPa")
    if data.altitude is not None:
        parts.append(f"A:{data.altitude:.2f}m")
    if data.humidity is not None:
        parts.append(f"H:{data.humidity:.1f}%")
    return ", ".join(parts) if parts else "No data"

# 타입 힌팅을 위한 별칭들
SensorDataDict = Dict[str, Union[float, int, str, None]]
AppStatusDict = Dict[AppID, AppStatus]
ConfigDict = Dict[ConfigKey, ConfigValue]
LogEntryList = List[LogEntry]
MessageDataList = List[MessageData]

# 제네릭 컨테이너들
class TypedDict:
    """타입이 지정된 딕셔너리"""
    def __init__(self, key_type: type, value_type: type):
        self.key_type = key_type
        self.value_type = value_type
        self._data: Dict[K, V] = {}
    
    def __setitem__(self, key: K, value: V) -> None:
        if not isinstance(key, self.key_type):
            raise TypeError(f"Key must be {self.key_type}")
        if not isinstance(value, self.value_type):
            raise TypeError(f"Value must be {self.value_type}")
        self._data[key] = value
    
    def __getitem__(self, key: K) -> V:
        return self._data[key]
    
    def __contains__(self, key: K) -> bool:
        return key in self._data
    
    def get(self, key: K, default: Optional[V] = None) -> Optional[V]:
        return self._data.get(key, default)

# 타입 힌팅을 위한 상수들
VALID_LOG_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
VALID_APP_STATUSES = ("RUNNING", "STOPPED", "ERROR", "INITIALIZING", "TERMINATING")
VALID_FLIGHT_STATES = ("LAUNCHPAD", "ASCENT", "APOGEE", "DESCENT", "LANDED", "MOTOR_CLOSE")

if __name__ == "__main__":
    # 타입 힌팅 테스트
    print("타입 힌팅 모듈 테스트")
    
    # 센서 데이터 생성 테스트
    sensor_data = create_sensor_data(
        temperature=25.5,
        pressure=1013.25,
        altitude=100.0,
        humidity=60.0
    )
    print(f"센서 데이터: {format_sensor_data(sensor_data)}")
    print(f"유효성 검사: {validate_sensor_data(sensor_data)}")
    
    # 타입 변환 테스트
    print(f"온도 변환: {to_temperature('25.5')}")
    print(f"압력 변환: {to_pressure('1013.25')}")
    print(f"고도 변환: {to_altitude('100.0')}")
    
    print("타입 힌팅 모듈 테스트 완료") 