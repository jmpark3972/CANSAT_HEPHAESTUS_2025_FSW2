#!/usr/bin/env python3
"""
CANSAT FSW 통합 오프셋 관리 시스템
모든 센서의 보정값과 오프셋을 중앙 집중식으로 관리
"""

import os
import json
import threading
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from lib import logging

class OffsetManager:
    """통합 오프셋 관리자 클래스"""
    
    def __init__(self, offset_file: str = "lib/offsets.json"):
        self.offset_file = Path(offset_file)
        self.lock = threading.Lock()
        
        # 기본 오프셋값들
        self.default_offsets = {
            # IMU 오프셋 (자기계, 자이로스코프, 가속도계)
            "IMU": {
                "MAGNETOMETER": [0, 0, 0],      # [x, y, z]
                "GYROSCOPE": [0, 0, 0],         # [x, y, z]
                "ACCELEROMETER": [0, 0, 0],     # [x, y, z]
                "TEMPERATURE_OFFSET": 0.0       # °C
            },
            
            # Barometer 오프셋
            "BAROMETER": {
                "ALTITUDE_OFFSET": 0.0,         # m
                "PRESSURE_OFFSET": 0.0,         # hPa
                "TEMPERATURE_OFFSET": 0.0       # °C
            },
            
            # Thermo (DHT11) 오프셋
            "THERMO": {
                "TEMPERATURE_OFFSET": 0.0,      # °C
                "HUMIDITY_OFFSET": 0.0          # %
            },
            
            # Thermis 오프셋
            "THERMIS": {
                "TEMPERATURE_OFFSET": 70.0      # °C (기본값)
            },
            
            # TMP007 오프셋
            "TMP007": {
                "TEMPERATURE_OFFSET": -80,      # °C
                "VOLTAGE_OFFSET": 0.0           # μV
            },
            
            # Pitot Tube 오프셋
            "PITOT": {
                "PRESSURE_OFFSET": 0.0,         # Pa
                "TEMPERATURE_OFFSET": 60.0,    # °C (기본값)
                "AIRSPEED_OFFSET": 0.0          # m/s
            },
            
            # Thermal Camera 오프셋
            "THERMAL_CAMERA": {
                "TEMPERATURE_OFFSET": 273.15,   # K (섭씨를 켈빈으로 변환)
                "PIXEL_OFFSET": 0.0             # °C
            },
            
            # FIR1 오프셋
            "FIR1": {
                "AMBIENT_OFFSET": 0.0,          # °C
                "OBJECT_OFFSET": 0.0            # °C
            },
            
            # NIR 오프셋
            "NIR": {
                "OFFSET": 40.0                  # 기본값
            },
            
            # 통신 오프셋
            "COMM": {
                "SIMP_OFFSET": 0.0              # 단순화된 고도 오프셋
            },
            
            # 비행 로직 오프셋
            "FLIGHT_LOGIC": {
                "DESCENT_ALT_OFFSET": 20.0,     # m
                "ALTITUDE_THRESHOLD_OFFSET": 0.0 # m
            },
            
            # 메타데이터
            "META": {
                "LAST_UPDATED": "",
                "VERSION": "1.0",
                "DESCRIPTION": "CANSAT FSW 통합 오프셋 관리 시스템"
            }
        }
        
        # 오프셋 로드
        self.offsets = self._load_offsets()
    
    def _load_offsets(self) -> Dict[str, Any]:
        """오프셋 파일 로드"""
        try:
            if self.offset_file.exists():
                with open(self.offset_file, 'r', encoding='utf-8') as f:
                    offsets = json.load(f)
                    # 기본값과 병합
                    return self._merge_offsets(self.default_offsets, offsets)
            else:
                # 기본 오프셋으로 시작
                current_offsets = self.default_offsets.copy()
                
                # 기존 IMU 오프셋 파일에서 데이터 마이그레이션
                current_offsets = self._migrate_legacy_imu_offsets(current_offsets)
                current_offsets = self._migrate_legacy_prevstate_offsets(current_offsets)
                
                # 파일 저장
                self._save_offsets(current_offsets)
                return current_offsets
        except Exception as e:
            logging.log(f"오프셋 파일 로드 오류: {e}", True)
            return self.default_offsets.copy()
    
    def _merge_offsets(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """기본 오프셋과 사용자 오프셋 병합"""
        merged = default.copy()
        
        def merge_dict(base: Dict[str, Any], update: Dict[str, Any]):
            for key, value in update.items():
                if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                    merge_dict(base[key], value)
                else:
                    base[key] = value
        
        merge_dict(merged, user)
        return merged
    
    def _save_offsets(self, offsets: Dict[str, Any]):
        """오프셋 파일 저장"""
        try:
            self.offset_file.parent.mkdir(parents=True, exist_ok=True)
            
            # 메타데이터 업데이트
            offsets["META"]["LAST_UPDATED"] = datetime.now().isoformat()
            
            with open(self.offset_file, 'w', encoding='utf-8') as f:
                json.dump(offsets, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logging.log(f"오프셋 파일 저장 오류: {e}", True)
    
    def _migrate_legacy_imu_offsets(self, current_offsets: Dict[str, Any]) -> Dict[str, Any]:
        """기존 IMU 오프셋 파일에서 데이터 마이그레이션"""
        try:
            legacy_offset_file = Path("imu/offset.py")
            if legacy_offset_file.exists():
                with open(legacy_offset_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if len(lines) >= 3:
                        # 자기계 오프셋 (첫 번째 줄)
                        mag_line = lines[0].strip()
                        mag_values = [int(x.strip()) for x in mag_line.split(',')]
                        
                        # 자이로스코프 오프셋 (두 번째 줄)
                        gyro_line = lines[1].strip()
                        gyro_values = [int(x.strip()) for x in gyro_line.split(',')]
                        
                        # 가속도계 오프셋 (세 번째 줄)
                        accel_line = lines[2].strip()
                        accel_values = [int(x.strip()) for x in accel_line.split(',')]
                        
                        # 새로운 시스템에 설정
                        current_offsets["IMU"]["MAGNETOMETER"] = mag_values
                        current_offsets["IMU"]["GYROSCOPE"] = gyro_values
                        current_offsets["IMU"]["ACCELEROMETER"] = accel_values
                        
                        logging.log("기존 IMU 오프셋 데이터를 마이그레이션했습니다", True)
                        logging.log(f"자기계: {mag_values}", True)
                        logging.log(f"자이로스코프: {gyro_values}", True)
                        logging.log(f"가속도계: {accel_values}", True)
        except Exception as e:
            logging.log(f"기존 IMU 오프셋 마이그레이션 오류: {e}", True)
        
        return current_offsets
    
    def _migrate_legacy_prevstate_offsets(self, current_offsets: Dict[str, Any]) -> Dict[str, Any]:
        """기존 prevstate.txt 파일에서 오프셋 데이터 마이그레이션"""
        try:
            prevstate_file = Path("lib/prevstate.txt")
            if prevstate_file.exists():
                with open(prevstate_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('THERMO_TOFF='):
                            value = float(line.split('=')[1])
                            current_offsets["THERMO"]["TEMPERATURE_OFFSET"] = value
                        elif line.startswith('THERMO_HOFF='):
                            value = float(line.split('=')[1])
                            current_offsets["THERMO"]["HUMIDITY_OFFSET"] = value
                        elif line.startswith('FIR_AOFF='):
                            value = float(line.split('=')[1])
                            current_offsets["FIR1"]["AMBIENT_OFFSET"] = value
                        elif line.startswith('FIR_OOFF='):
                            value = float(line.split('=')[1])
                            current_offsets["FIR1"]["OBJECT_OFFSET"] = value
                        elif line.startswith('THERMIS_OFF='):
                            value = float(line.split('=')[1])
                            current_offsets["THERMIS"]["TEMPERATURE_OFFSET"] = value
                        elif line.startswith('NIR_OFFSET='):
                            value = float(line.split('=')[1])
                            current_offsets["NIR"]["OFFSET"] = value
                        elif line.startswith('PITOT_POFF='):
                            value = float(line.split('=')[1])
                            current_offsets["PITOT"]["PRESSURE_OFFSET"] = value
                        elif line.startswith('PITOT_TOFF='):
                            value = float(line.split('=')[1])
                            current_offsets["PITOT"]["TEMPERATURE_OFFSET"] = value
                
                logging.log("기존 prevstate.txt 오프셋 데이터를 마이그레이션했습니다", True)
        except Exception as e:
            logging.log(f"기존 prevstate.txt 오프셋 마이그레이션 오류: {e}", True)
        
        return current_offsets
    
    def get(self, key: str, default: Any = None) -> Any:
        """오프셋값 가져오기 (점 표기법 지원)"""
        with self.lock:
            try:
                keys = key.split('.')
                value = self.offsets
                for k in keys:
                    value = value[k]
                return value
            except (KeyError, TypeError):
                return default
    
    def set(self, key: str, value: Any):
        """오프셋값 설정 (점 표기법 지원)"""
        with self.lock:
            try:
                keys = key.split('.')
                offsets = self.offsets
                for k in keys[:-1]:
                    if k not in offsets:
                        offsets[k] = {}
                    offsets = offsets[k]
                offsets[keys[-1]] = value
                self._save_offsets(self.offsets)
                logging.log(f"오프셋 업데이트: {key} = {value}", True)
            except Exception as e:
                logging.log(f"오프셋 설정 오류: {e}", True)
    
    def get_imu_offsets(self) -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
        """IMU 오프셋 가져오기"""
        mag = tuple(self.get("IMU.MAGNETOMETER", [0, 0, 0]))
        gyro = tuple(self.get("IMU.GYROSCOPE", [0, 0, 0]))
        accel = tuple(self.get("IMU.ACCELEROMETER", [0, 0, 0]))
        return mag, gyro, accel
    
    def set_imu_offsets(self, magnetometer: Tuple[int, int, int], 
                       gyroscope: Tuple[int, int, int], 
                       accelerometer: Tuple[int, int, int]):
        """IMU 오프셋 설정"""
        self.set("IMU.MAGNETOMETER", list(magnetometer))
        self.set("IMU.GYROSCOPE", list(gyroscope))
        self.set("IMU.ACCELEROMETER", list(accelerometer))
    
    def get_barometer_offset(self) -> float:
        """Barometer 고도 오프셋 가져오기"""
        return self.get("BAROMETER.ALTITUDE_OFFSET", 0.0)
    
    def set_barometer_offset(self, offset: float):
        """Barometer 고도 오프셋 설정"""
        self.set("BAROMETER.ALTITUDE_OFFSET", offset)
    
    def get_thermis_offset(self) -> float:
        """Thermis 온도 오프셋 가져오기"""
        return self.get("THERMIS.TEMPERATURE_OFFSET", 50.0)
    
    def set_thermis_offset(self, offset: float):
        """Thermis 온도 오프셋 설정"""
        self.set("THERMIS.TEMPERATURE_OFFSET", offset)
    
    def get_pitot_offsets(self) -> Tuple[float, float]:
        """Pitot 압력/온도 오프셋 가져오기"""
        pressure = self.get("PITOT.PRESSURE_OFFSET", 0.0)
        temperature = self.get("PITOT.TEMPERATURE_OFFSET", -60.0)
        return pressure, temperature
    
    def set_pitot_offsets(self, pressure_offset: float, temperature_offset: float):
        """Pitot 압력/온도 오프셋 설정"""
        self.set("PITOT.PRESSURE_OFFSET", pressure_offset)
        self.set("PITOT.TEMPERATURE_OFFSET", temperature_offset)
    
    def get_thermal_camera_offset(self) -> float:
        """Thermal Camera 온도 오프셋 가져오기"""
        return self.get("THERMAL_CAMERA.TEMPERATURE_OFFSET", 273.15)
    
    def set_thermal_camera_offset(self, offset: float):
        """Thermal Camera 온도 오프셋 설정"""
        self.set("THERMAL_CAMERA.TEMPERATURE_OFFSET", offset)
    
    def get_fir1_offsets(self) -> Tuple[float, float]:
        """FIR1 앰비언트/오브젝트 오프셋 가져오기"""
        ambient = self.get("FIR1.AMBIENT_OFFSET", 0.0)
        object_temp = self.get("FIR1.OBJECT_OFFSET", 0.0)
        return ambient, object_temp
    
    def set_fir1_offsets(self, ambient_offset: float, object_offset: float):
        """FIR1 앰비언트/오브젝트 오프셋 설정"""
        self.set("FIR1.AMBIENT_OFFSET", ambient_offset)
        self.set("FIR1.OBJECT_OFFSET", object_offset)
    
    def get_nir_offset(self) -> float:
        """NIR 오프셋 가져오기"""
        return self.get("NIR.OFFSET", 40.0)
    
    def set_nir_offset(self, offset: float):
        """NIR 오프셋 설정"""
        self.set("NIR.OFFSET", offset)
    
    def get_comm_offset(self) -> float:
        """통신 SIMP 오프셋 가져오기"""
        return self.get("COMM.SIMP_OFFSET", 0.0)
    
    def set_comm_offset(self, offset: float):
        """통신 SIMP 오프셋 설정"""
        self.set("COMM.SIMP_OFFSET", offset)
    
    def reset_to_default(self):
        """기본 오프셋으로 초기화"""
        with self.lock:
            self.offsets = self.default_offsets.copy()
            self._save_offsets(self.offsets)
            logging.log("오프셋을 기본값으로 초기화했습니다", True)
    
    def export_offsets(self, filepath: str):
        """오프셋 내보내기"""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.offsets, f, indent=2, ensure_ascii=False)
            logging.log(f"오프셋을 {filepath}에 내보냈습니다", True)
        except Exception as e:
            logging.log(f"오프셋 내보내기 오류: {e}", True)
    
    def import_offsets(self, filepath: str):
        """오프셋 가져오기"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                offsets = json.load(f)
                self.offsets = self._merge_offsets(self.default_offsets, offsets)
                self._save_offsets(self.offsets)
            logging.log(f"오프셋을 {filepath}에서 가져왔습니다", True)
        except Exception as e:
            logging.log(f"오프셋 가져오기 오류: {e}", True)
    
    def get_all_offsets(self) -> Dict[str, Any]:
        """모든 오프셋 가져오기"""
        with self.lock:
            return self.offsets.copy()
    
    def print_offsets(self):
        """모든 오프셋 출력"""
        with self.lock:
            print("\n=== CANSAT FSW 통합 오프셋 현황 ===")
            for category, values in self.offsets.items():
                if category != "META":
                    print(f"\n[{category}]")
                    if isinstance(values, dict):
                        for key, value in values.items():
                            print(f"  {key}: {value}")
                    else:
                        print(f"  {values}")
            print(f"\n마지막 업데이트: {self.offsets.get('META', {}).get('LAST_UPDATED', 'N/A')}")

# 전역 오프셋 관리자 인스턴스
_offset_manager = None

def get_offset_manager() -> OffsetManager:
    """전역 오프셋 관리자 인스턴스 가져오기"""
    global _offset_manager
    if _offset_manager is None:
        _offset_manager = OffsetManager()
    return _offset_manager

def get_offset(key: str, default: Any = None) -> Any:
    """오프셋값 가져오기 (편의 함수)"""
    return get_offset_manager().get(key, default)

def set_offset(key: str, value: Any):
    """오프셋값 설정 (편의 함수)"""
    get_offset_manager().set(key, value)

# 기존 호환성을 위한 함수들
def get_imu_offsets() -> Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]:
    """IMU 오프셋 가져오기 (기존 호환성)"""
    return get_offset_manager().get_imu_offsets()

def get_barometer_offset() -> float:
    """Barometer 오프셋 가져오기 (기존 호환성)"""
    return get_offset_manager().get_barometer_offset()

def get_thermis_offset() -> float:
    """Thermis 오프셋 가져오기 (기존 호환성)"""
    return get_offset_manager().get_thermis_offset()

def get_pitot_offsets() -> Tuple[float, float]:
    """Pitot 오프셋 가져오기 (기존 호환성)"""
    return get_offset_manager().get_pitot_offsets()

def get_comm_offset() -> float:
    """통신 SIMP 오프셋 가져오기 (기존 호환성)"""
    return get_offset_manager().get_comm_offset()

if __name__ == "__main__":
    # 오프셋 관리자 테스트
    manager = get_offset_manager()
    manager.print_offsets()
    
    # 테스트: 일부 오프셋 설정
    print("\n=== 오프셋 테스트 ===")
    manager.set_barometer_offset(10.5)
    manager.set_thermis_offset(25.0)
    manager.set_pitot_offsets(5.2, -55.0)
    
    print(f"Barometer 오프셋: {manager.get_barometer_offset()}m")
    print(f"Thermis 오프셋: {manager.get_thermis_offset()}°C")
    print(f"Pitot 오프셋: {manager.get_pitot_offsets()}") 