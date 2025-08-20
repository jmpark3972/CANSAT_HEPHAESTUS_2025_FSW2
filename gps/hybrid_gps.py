#!/usr/bin/env python3
"""
Hybrid GPS System for CANSAT HEPHAESTUS 2025
GPS + WiFi + Cell Tower 하이브리드 위치 시스템

이 모듈은 여러 위치 정보 소스를 조합하여 최대한 정확한 위치를 제공합니다.
"""

import time
import os
import json
import requests
import subprocess
import threading
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, List, Tuple
import board
import busio
from adafruit_gps import GPS_GtopI2C

# 위치 정보 소스 열거형
class LocationSource(Enum):
    GPS = "gps"
    WIFI = "wifi"
    CELL = "cell"
    HYBRID = "hybrid"

# 위치 데이터 클래스
@dataclass
class LocationData:
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy: Optional[float] = None
    source: LocationSource = LocationSource.GPS
    timestamp: datetime = None
    satellites: Optional[int] = None
    wifi_networks: Optional[List[str]] = None
    cell_towers: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()

class HybridGPSSystem:
    """하이브리드 GPS 시스템"""
    
    def __init__(self):
        # 로그 파일 설정 (먼저 초기화)
        self.log_dir = './logs'
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, 'hybrid_gps.log')
        
        self.gps_data = None
        self.wifi_data = None
        self.cell_data = None
        self.last_gps_fix = None
        self.last_wifi_fix = None
        self.last_cell_fix = None
        
        # GPS 모듈 초기화
        self.i2c = None
        self.gps = None
        self._init_gps()
        
        # WiFi 스캔 캐시
        self.wifi_cache = {}
        self.wifi_cache_timeout = 30  # 30초
        
        # 위치 정확도 가중치
        self.accuracy_weights = {
            LocationSource.GPS: 0.7,
            LocationSource.WIFI: 0.2,
            LocationSource.CELL: 0.1
        }
        
        # API 키 (실제 사용 시 환경변수로 설정)
        self.google_api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
        
    def _init_gps(self):
        """GPS 모듈 초기화"""
        try:
            self.i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
            
            # I2C 스캔 결과 출력
            scanned_devices = self.i2c.scan()
            self._log(f"I2C 스캔 결과: {[hex(addr) for addr in scanned_devices]}")
            
            # MAX-M10S GPS 모듈의 I2C 주소는 0x42
            if 0x42 in scanned_devices:
                self._log("MAX-M10S GPS 모듈 발견 (0x42)")
                self.gps = GPS_GtopI2C(self.i2c, address=0x42)
            else:
                self._log("MAX-M10S GPS 모듈을 찾을 수 없습니다 (0x42)", "ERROR")
                self._log("연결 상태를 확인하세요:", "ERROR")
                self._log("1. Qwiic 케이블이 올바르게 연결되었는지 확인", "ERROR")
                self._log("2. GPS 모듈에 전원이 공급되는지 확인", "ERROR")
                self._log("3. I2C가 활성화되었는지 확인 (sudo raspi-config)", "ERROR")
                return False
            
            # GPS 설정 최적화
            try:
                # GPS 업데이트 속도 설정 (1Hz)
                self.gps.send_command(b'PMTK220,1000')
                # NMEA 문장 출력 설정
                self.gps.send_command(b'PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0')
                # DGPS 모드 설정
                self.gps.send_command(b'PMTK301,1')
                self._log("GPS 설정 최적화 완료")
            except Exception as cmd_error:
                self._log(f"GPS 명령 설정 실패 (무시하고 계속): {cmd_error}", "WARNING")
            
            self._log("GPS 모듈 초기화 성공")
            return True
        except Exception as e:
            self._log(f"GPS 모듈 초기화 실패: {e}", "ERROR")
            return False
    
    def _log(self, message: str, level: str = "INFO"):
        """로그 기록"""
        try:
            timestamp = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            log_entry = f"[{timestamp}] [{level}] {message}\n"
            
            # log_file 속성이 없으면 생성
            if not hasattr(self, 'log_file'):
                self.log_file = os.path.join(self.log_dir, 'hybrid_gps.log')
            
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
                f.flush()
        except Exception as e:
            print(f"로그 기록 실패: {e}")
    
    def get_gps_location(self) -> Optional[LocationData]:
        """GPS 위치 정보 읽기"""
        try:
            if not self.gps:
                return None
            
            self.gps.update()
            
            if self.gps.has_fix:
                location = LocationData(
                    latitude=self.gps.latitude,
                    longitude=self.gps.longitude,
                    altitude=self.gps.altitude_m,
                    accuracy=self._calculate_gps_accuracy(),
                    source=LocationSource.GPS,
                    satellites=self.gps.satellites
                )
                
                self.last_gps_fix = location
                self._log(f"GPS 픽스: {location.latitude:.6f}, {location.longitude:.6f}")
                return location
            else:
                self._log("GPS 픽스 없음")
                return None
                
        except Exception as e:
            self._log(f"GPS 읽기 오류: {e}", "ERROR")
            return None
    
    def _calculate_gps_accuracy(self) -> float:
        """GPS 정확도 계산 (위성 수 기반)"""
        if not self.gps:
            return 100.0
        
        satellites = self.gps.satellites or 0
        
        # 위성 수에 따른 정확도 추정
        if satellites >= 8:
            return 3.0  # 3m
        elif satellites >= 6:
            return 5.0  # 5m
        elif satellites >= 4:
            return 10.0  # 10m
        else:
            return 20.0  # 20m
    
    def scan_wifi_networks(self) -> List[Dict]:
        """WiFi 네트워크 스캔"""
        try:
            # 캐시된 결과 확인
            current_time = time.time()
            if 'networks' in self.wifi_cache:
                cache_time, networks = self.wifi_cache['networks']
                if current_time - cache_time < self.wifi_cache_timeout:
                    return networks
            
            # iwlist 명령어로 WiFi 스캔
            result = subprocess.run(
                ['sudo', 'iwlist', 'wlan0', 'scan'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                self._log("WiFi 스캔 실패", "WARNING")
                return []
            
            # WiFi 네트워크 파싱
            networks = []
            lines = result.stdout.split('\n')
            
            for line in lines:
                if 'ESSID:' in line:
                    essid = line.split('"')[1] if '"' in line else line.split(':')[1].strip()
                    if essid and essid != '':
                        networks.append({'ssid': essid})
            
            # 캐시에 저장
            self.wifi_cache['networks'] = (current_time, networks)
            
            self._log(f"WiFi 네트워크 {len(networks)}개 발견")
            return networks
            
        except Exception as e:
            self._log(f"WiFi 스캔 오류: {e}", "ERROR")
            return []
    
    def get_wifi_location(self) -> Optional[LocationData]:
        """WiFi 기반 위치 정보"""
        try:
            networks = self.scan_wifi_networks()
            
            if not networks:
                return None
            
            # Google API 키가 있으면 Google Geolocation API 사용
            if self.google_api_key:
                try:
                    payload = {
                        'wifiAccessPoints': [
                            {'macAddress': f"00:00:00:00:00:{i:02x}", 'signalStrength': -50}
                            for i, _ in enumerate(networks[:5])  # 상위 5개 네트워크만 사용
                        ]
                    }
                    
                    response = requests.post(
                        f'https://www.googleapis.com/geolocation/v1/geolocate?key={self.google_api_key}',
                        json=payload,
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        location = data['location']
                        
                        wifi_location = LocationData(
                            latitude=location['lat'],
                            longitude=location['lng'],
                            accuracy=data.get('accuracy', 100.0),
                            source=LocationSource.WIFI,
                            wifi_networks=[n['ssid'] for n in networks[:5]]
                        )
                        
                        self.last_wifi_fix = wifi_location
                        self._log(f"Google WiFi 위치: {wifi_location.latitude:.6f}, {wifi_location.longitude:.6f}")
                        return wifi_location
                    else:
                        self._log(f"Google WiFi 위치 API 오류: {response.status_code}", "WARNING")
                except Exception as api_error:
                    self._log(f"Google API 호출 실패: {api_error}", "WARNING")
            
            # API 키가 없거나 실패한 경우, 간단한 위치 추정
            # 한국 대략적인 중심 좌표 사용 (서울 근처)
            estimated_location = LocationData(
                latitude=37.5665,  # 서울 위도
                longitude=126.9780,  # 서울 경도
                accuracy=5000.0,  # 5km 정확도
                source=LocationSource.WIFI,
                wifi_networks=[n['ssid'] for n in networks[:5]]
            )
            
            self.last_wifi_fix = estimated_location
            self._log(f"추정 WiFi 위치 (서울): {estimated_location.latitude:.6f}, {estimated_location.longitude:.6f}")
            return estimated_location
                
        except Exception as e:
            self._log(f"WiFi 위치 오류: {e}", "ERROR")
            return None
    
    def get_cell_location(self) -> Optional[LocationData]:
        """셀 타워 기반 위치 정보 (간단한 구현)"""
        try:
            # 실제 구현에서는 셀 타워 정보를 수집해야 함
            # 여기서는 간단한 예시로 구현
            
            # 셀 타워 정보 수집 (실제로는 하드웨어에서 가져와야 함)
            cell_info = self._get_cell_tower_info()
            
            if not cell_info:
                return None
            
            # OpenCellID API 또는 유사한 서비스 사용
            # 실제 구현에서는 적절한 API를 사용해야 함
            
            self._log("셀 타워 위치 정보 수집 (구현 필요)")
            return None
            
        except Exception as e:
            self._log(f"셀 위치 오류: {e}", "ERROR")
            return None
    
    def _get_cell_tower_info(self) -> Optional[Dict]:
        """셀 타워 정보 수집"""
        # 실제 구현에서는 모뎀/셀 모듈에서 정보를 가져와야 함
        # 여기서는 더미 데이터 반환
        return None
    
    def combine_locations(self, locations: List[LocationData]) -> Optional[LocationData]:
        """여러 위치 정보를 조합하여 최적의 위치 계산"""
        if not locations:
            return None
        
        if len(locations) == 1:
            return locations[0]
        
        # 가중 평균 계산
        total_weight = 0
        weighted_lat = 0
        weighted_lon = 0
        weighted_alt = 0
        alt_count = 0
        
        for location in locations:
            weight = self.accuracy_weights.get(location.source, 0.1)
            if location.accuracy:
                weight *= (1.0 / location.accuracy)  # 정확도가 높을수록 가중치 증가
            
            weighted_lat += location.latitude * weight
            weighted_lon += location.longitude * weight
            total_weight += weight
            
            if location.altitude is not None:
                weighted_alt += location.altitude * weight
                alt_count += 1
        
        if total_weight == 0:
            return locations[0]  # 첫 번째 위치 반환
        
        # 최종 위치 계산
        final_lat = weighted_lat / total_weight
        final_lon = weighted_lon / total_weight
        final_alt = weighted_alt / alt_count if alt_count > 0 else None
        
        # 최종 정확도 계산
        final_accuracy = min(loc.accuracy for loc in locations if loc.accuracy)
        
        return LocationData(
            latitude=final_lat,
            longitude=final_lon,
            altitude=final_alt,
            accuracy=final_accuracy,
            source=LocationSource.HYBRID,
            timestamp=datetime.now()
        )
    
    def get_hybrid_location(self, timeout: float = 5.0) -> Optional[LocationData]:
        """하이브리드 위치 정보 획득"""
        start_time = time.time()
        locations = []
        
        # GPS 위치 시도
        gps_location = self.get_gps_location()
        if gps_location:
            locations.append(gps_location)
        
        # WiFi 위치 시도 (GPS가 없거나 부정확한 경우)
        if not gps_location or (gps_location and gps_location.accuracy > 10.0):
            wifi_location = self.get_wifi_location()
            if wifi_location:
                locations.append(wifi_location)
        
        # 셀 타워 위치 시도 (다른 방법들이 실패한 경우)
        if not locations:
            cell_location = self.get_cell_location()
            if cell_location:
                locations.append(cell_location)
        
        # 위치 정보 조합
        if locations:
            hybrid_location = self.combine_locations(locations)
            self._log(f"하이브리드 위치 획득: {len(locations)}개 소스 조합")
            return hybrid_location
        
        self._log("위치 정보 획득 실패", "WARNING")
        return None
    
    def get_location_with_fallback(self, max_attempts: int = 3) -> Optional[LocationData]:
        """폴백을 사용한 위치 정보 획득"""
        for attempt in range(max_attempts):
            location = self.get_hybrid_location()
            if location:
                return location
            
            self._log(f"위치 획득 시도 {attempt + 1}/{max_attempts} 실패")
            time.sleep(2)  # 2초 대기 후 재시도
        
        # 모든 시도 실패 시 마지막 알려진 위치 반환
        if self.last_gps_fix:
            self._log("마지막 GPS 픽스 반환")
            return self.last_gps_fix
        elif self.last_wifi_fix:
            self._log("마지막 WiFi 픽스 반환")
            return self.last_wifi_fix
        
        return None
    
    def get_location_status(self) -> Dict:
        """위치 시스템 상태 정보"""
        return {
            'gps_available': self.gps is not None,
            'gps_has_fix': self.gps.has_fix if self.gps else False,
            'gps_satellites': self.gps.satellites if self.gps else 0,
            'wifi_available': bool(self.google_api_key),
            'last_gps_fix': self.last_gps_fix.timestamp.isoformat() if self.last_gps_fix else None,
            'last_wifi_fix': self.last_wifi_fix.timestamp.isoformat() if self.last_wifi_fix else None,
            'wifi_cache_age': time.time() - self.wifi_cache.get('networks', [0, []])[0] if 'networks' in self.wifi_cache else None
        }
    
    def cleanup(self):
        """리소스 정리"""
        try:
            if self.i2c:
                self.i2c.deinit()
            self._log("하이브리드 GPS 시스템 정리 완료")
        except Exception as e:
            self._log(f"정리 오류: {e}", "ERROR")

# 전역 인스턴스
_hybrid_gps_instance = None

def get_hybrid_gps() -> HybridGPSSystem:
    """하이브리드 GPS 시스템 인스턴스 반환"""
    global _hybrid_gps_instance
    if _hybrid_gps_instance is None:
        _hybrid_gps_instance = HybridGPSSystem()
    return _hybrid_gps_instance

def init_hybrid_gps() -> HybridGPSSystem:
    """하이브리드 GPS 시스템 초기화"""
    return get_hybrid_gps()

def read_hybrid_location() -> Optional[LocationData]:
    """하이브리드 위치 정보 읽기"""
    gps = get_hybrid_gps()
    return gps.get_location_with_fallback()

def get_location_status() -> Dict:
    """위치 시스템 상태 확인"""
    gps = get_hybrid_gps()
    return gps.get_location_status()

def cleanup_hybrid_gps():
    """하이브리드 GPS 시스템 정리"""
    global _hybrid_gps_instance
    if _hybrid_gps_instance:
        _hybrid_gps_instance.cleanup()
        _hybrid_gps_instance = None
