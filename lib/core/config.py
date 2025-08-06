#!/usr/bin/env python3
"""
CANSAT FSW 설정 관리 시스템
하드코딩된 값들을 중앙 집중식으로 관리
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# 기본 설정값들
DEFAULT_CONFIG = {
    # FSW 운영 모드
    "FSW_MODE": "PAYLOAD",  # PAYLOAD, CONTAINER, ROCKET, NONE
    
    # 팀 ID 매핑
    "TEAM_IDS": {
        "PAYLOAD": "SpaceY",
        "CONTAINER": "SpaceY",
        "ROCKET": "SpaceY",
        "NONE": "SpaceY"
    },
    
    # 통신 설정
    "COMM": {
        "SERIAL_BAUDRATE": 9600,
        "SERIAL_TIMEOUT": 1.0,
        "XBEE_RESET_GPIO": 18,
        "TELEMETRY_INTERVAL": 1.0,  # 초
        "COMMAND_TIMEOUT": 5.0,     # 초
        "MAX_RETRY_COUNT": 3
    },
    
    # GPS 설정
    "GPS": {
        "SERIAL_PORT": "/dev/serial0",
        "BAUDRATE": 9600,
        "TIMEOUT": 1.0,
        "UPDATE_INTERVAL": 0.1,     # 초
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.2  # 초 (5Hz)
    },
    
    # 센서 설정
    "SENSORS": {
        "I2C_FREQUENCY": 400000,
        "SENSOR_TIMEOUT": 2.0,
        "CALIBRATION_SAMPLES": 100,
        "READ_INTERVAL": 0.1        # 초
    },
    
    # IMU 설정
    "IMU": {
        "I2C_ADDRESS": 0x28,
        "CALIBRATION_TIMEOUT": 30,   # 초
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.1  # 초 (10Hz)
    },
    
    # Barometer 설정
    "BAROMETER": {
        "I2C_ADDRESS": 0x77,
        "SEA_LEVEL_PRESSURE": 1013.25,  # hPa
        "ALTITUDE_OFFSET": 0.0,
        "TELMETRY_INTERVAL": 1.0,       # 초
        "FLIGHTLOGIC_INTERVAL": 0.2     # 초 (5Hz)
    },
    
    # 온도 센서 설정
    "THERMO": {
        "DHT_PIN": 4,
        "READ_INTERVAL": 2.0,       # 초
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.1  # 초 (10Hz)
    },
    
    "THERMIS": {
        "I2C_ADDRESS": 0x48,
        "ADC_CHANNEL": 0,
        "VOLTAGE_REFERENCE": 3.3,
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.1  # 초 (10Hz)
    },
    
    "TMP007": {
        "I2C_ADDRESS": 0x40,
        "READ_INTERVAL": 1.0,       # 초
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.1  # 초 (10Hz)
    },
    

    
    # 열화상 카메라 설정
    "THERMAL_CAMERA": {
        "I2C_ADDRESS": 0x33,
        "READ_INTERVAL": 0.5,       # 초
        "TELMETRY_INTERVAL": 1.0,   # 초
        "FLIGHTLOGIC_INTERVAL": 0.2  # 초 (5Hz)
    },
    
    # 모터 설정
    "MOTOR": {
        "SERVO_PIN": 12,
        "MOTOR_OPEN_PULSE": 500,      # 0도 (열림)
        "MOTOR_CLOSE_PULSE": 2500,    # 180도 (닫힘)
        "MOVE_DURATION": 2.0,         # 초
        "COMMAND_TIMEOUT": 5.0        # 초
    },
    
    # 카메라 설정
    "CAMERA": {
        "VIDEO_DURATION": 5,          # 초
        "RECORDING_INTERVAL": 5,      # 초
        "POST_LANDING_DELAY": 30,     # 초
        "VIDEO_QUALITY": "medium",    # low, medium, high
        "FRAME_RATE": 30,
        "RESOLUTION": "1920x1080",
        "TELMETRY_INTERVAL": 1.0,     # 초
        "FLIGHTLOGIC_INTERVAL": 0.2   # 초 (5Hz)
    },
    
    # 비행 로직 설정
    "FLIGHT_LOGIC": {
        "THERMIS_TEMP_THRESHOLD": 35.0,      # °C
        "MOTOR_CLOSE_ALT_THRESHOLD": 70.0,   # m
        "ASCENT_ALT_THRESHOLD": 75.0,        # m
        "DESCENT_ALT_OFFSET": 20.0,          # m
        "LANDED_ALT_THRESHOLD": 15.0,        # m
        "STATE_TRANSITION_COUNT": 5,         # 회
        "RECENT_ALT_CHECK_LEN": 10,          # 개
        "MOTOR_COMMAND_RETRY": 3,            # 회
        "UPDATE_INTERVAL": 0.1               # 초 (10Hz)
    },
    
    # 로깅 설정
    "LOGGING": {
        "PRIMARY_LOG_DIR": "logs",
        "SECONDARY_LOG_DIR": "/mnt/log_sd/logs",
        "LOG_LEVEL": "INFO",         # DEBUG, INFO, WARNING, ERROR
        "LOG_ROTATION_SIZE": 10,     # MB
        "LOG_RETENTION_DAYS": 7,
        "BACKUP_INTERVAL": 300,      # 초 (5분)
        "RECOVERY_INTERVAL": 60      # 초 (1분)
    },
    
    # 시스템 설정
    "SYSTEM": {
        "MAIN_LOOP_TIMEOUT": 0.5,    # 초
        "PROCESS_CHECK_INTERVAL": 1.0,  # 초
        "HK_INTERVAL": 1.0,          # 초
        "MAX_MEMORY_USAGE": 80,      # %
        "MAX_DISK_USAGE": 90,        # %
        "EMERGENCY_SHUTDOWN_DELAY": 5.0  # 초
    },
    
    # 테스트 설정
    "TEST": {
        "SENSOR_TEST_DURATION": 10,  # 초
        "STABILITY_TEST_DURATION": 60,  # 초
        "QUICK_TEST_DURATION": 30,   # 초
        "TEST_RETRY_COUNT": 3
    }
}

class ConfigManager:
    """설정 관리자 클래스"""
    
    def __init__(self, config_file: str = "lib/config.json"):
        self.config_file = Path(config_file)
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """설정 파일 로드"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # 기본값과 병합
                    return self._merge_configs(DEFAULT_CONFIG, config)
            else:
                # 기본 설정으로 파일 생성
                self._save_config(DEFAULT_CONFIG)
                return DEFAULT_CONFIG
        except Exception as e:
            print(f"설정 파일 로드 오류: {e}")
            return DEFAULT_CONFIG
    
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """기본 설정과 사용자 설정 병합"""
        merged = default.copy()
        
        def merge_dict(base: Dict[str, Any], update: Dict[str, Any]):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(merged, user)
        return merged
    
    def _save_config(self, config: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 파일 저장 오류: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """설정값 가져오기 (점 표기법 지원)"""
        try:
            keys = key.split('.')
            value = self.config
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """설정값 설정 (점 표기법 지원)"""
        try:
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            config[keys[-1]] = value
            self._save_config(self.config)
        except Exception as e:
            print(f"설정값 설정 오류: {e}")
    
    def get_fsw_mode(self) -> str:
        """FSW 모드 가져오기"""
        return self.get("FSW_MODE", "PAYLOAD")
    
    def get_team_id(self) -> str:
        """팀 ID 가져오기"""
        mode = self.get_fsw_mode()
        return self.get(f"TEAM_IDS.{mode}", "SpaceY")
    
    def reload(self):
        """설정 파일 다시 로드"""
        self.config = self._load_config()
    
    def reset_to_default(self):
        """기본 설정으로 초기화"""
        self.config = DEFAULT_CONFIG.copy()
        self._save_config(self.config)
    
    def export_config(self, filepath: str):
        """설정 내보내기"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"설정 내보내기 오류: {e}")
    
    def import_config(self, filepath: str):
        """설정 가져오기"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.config = self._merge_configs(DEFAULT_CONFIG, config)
                self._save_config(self.config)
        except Exception as e:
            print(f"설정 가져오기 오류: {e}")

# 전역 설정 관리자 인스턴스
_config_manager = None

def get_config_manager() -> ConfigManager:
    """전역 설정 관리자 인스턴스 가져오기"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager

def get_config(key: str, default: Any = None) -> Any:
    """설정값 가져오기 (편의 함수)"""
    return get_config_manager().get(key, default)

def set_config(key: str, value: Any):
    """설정값 설정 (편의 함수)"""
    get_config_manager().set(key, value)

# 기존 호환성을 위한 상수들
FSW_MODE = get_config("FSW_MODE", "PAYLOAD")
TEAM_IDS = get_config("TEAM_IDS", {
    "PAYLOAD": "SpaceY",
    "CONTAINER": "SpaceY", 
    "ROCKET": "SpaceY",
    "NONE": "SpaceY"
})

# FSW 설정 상수들 (기존 호환성)
CONF_NONE = 0
CONF_PAYLOAD = 1
CONF_CONTAINER = 2
CONF_ROCKET = 3

# FSW_CONF 매핑
FSW_CONF_MAPPING = {
    "NONE": CONF_NONE,
    "PAYLOAD": CONF_PAYLOAD,
    "CONTAINER": CONF_CONTAINER,
    "ROCKET": CONF_ROCKET
}

# 현재 FSW 설정
FSW_CONF = FSW_CONF_MAPPING.get(FSW_MODE, CONF_PAYLOAD)

def get_team_id(mode: str = None) -> str:
    """팀 ID 가져오기 (기존 호환성)"""
    if mode is None:
        mode = FSW_MODE
    return TEAM_IDS.get(mode, "SpaceY")

# 설정 파일이 없으면 생성
config_txt_path = os.path.join(os.path.dirname(__file__), "config.txt")
if not os.path.exists(config_txt_path):
    try:
        with open(config_txt_path, "w", encoding="utf-8") as f:
            f.write(f"FSW_MODE={FSW_MODE}\n")
            f.write(f"TEAM_ID={get_team_id()}\n")
    except Exception as e:
        print(f"기본 설정 파일 생성 오류: {e}")

if __name__ == "__main__":
    # 설정 테스트
    config = get_config_manager()
    print(f"FSW 모드: {config.get_fsw_mode()}")
    print(f"팀 ID: {config.get_team_id()}")
    print(f"IMU 주소: {config.get('IMU.I2C_ADDRESS')}")
    print(f"모터 열림 펄스: {config.get('MOTOR.MOTOR_OPEN_PULSE')}")
    print(f"온도 임계값: {config.get('FLIGHT_LOGIC.THERMIS_TEMP_THRESHOLD')}°C")

