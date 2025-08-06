#!/usr/bin/env python3
"""
I2C Bus Manager for CANSAT HEPHAESTUS 2025 FSW2
I2C 버스 안정성 및 재시작 메커니즘 제공
"""

import subprocess
import time
import threading
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class I2CBusStatus(Enum):
    NORMAL = "normal"
    DEGRADED = "degraded"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class I2CDevice:
    address: int
    name: str
    last_seen: float
    error_count: int = 0
    status: I2CBusStatus = I2CBusStatus.NORMAL

class I2CBusManager:
    """I2C 버스 관리자"""
    
    def __init__(self):
        self.bus_status = I2CBusStatus.NORMAL
        self.devices: Dict[int, I2CDevice] = {}
        self.error_threshold = 5
        self.restart_threshold = 10
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        
        # 알려진 I2C 디바이스 목록
        self.known_devices = {
            0x33: "MLX90640 (Thermal Camera)",
            0x5A: "MLX90614 (FIR1)",
            0x68: "BNO055 (IMU)",
            0x77: "BMP390 (Barometer)",
            0x40: "TMP007",
            0x48: "ADS1115 (Thermis)",
            0x3C: "OLED Display",
            0x76: "BME280",
        }
    
    def scan_i2c_bus(self, bus_number: int = 1) -> List[int]:
        """I2C 버스 스캔"""
        try:
            result = subprocess.run(
                ['i2cdetect', '-y', str(bus_number)],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                addresses = []
                lines = result.stdout.strip().split('\n')
                
                for line in lines[1:]:  # 헤더 제외
                    if line.strip():
                        parts = line.split(':')
                        if len(parts) > 1:
                            hex_values = parts[1].strip().split()
                            for hex_val in hex_values:
                                if hex_val != '--' and hex_val:
                                    try:
                                        addr = int(hex_val, 16)
                                        addresses.append(addr)
                                    except ValueError:
                                        continue
                
                return addresses
            else:
                logging.error(f"I2C bus scan failed: {result.stderr}")
                return []
                
        except subprocess.TimeoutExpired:
            logging.error("I2C bus scan timeout")
            return []
        except Exception as e:
            logging.error(f"I2C bus scan error: {e}")
            return []
    
    def check_device_health(self, address: int, bus_number: int = 1) -> bool:
        """특정 I2C 디바이스 상태 확인"""
        try:
            # 간단한 읽기 테스트
            result = subprocess.run(
                ['i2cget', '-y', str(bus_number), str(address), '0x00'],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except:
            return False
    
    def restart_i2c_bus(self, bus_number: int = 1) -> bool:
        """I2C 버스 재시작"""
        try:
            logging.warning(f"Restarting I2C bus {bus_number}")
            
            # I2C 모듈 언로드
            subprocess.run(['sudo', 'rmmod', 'i2c_bcm2708'], 
                         capture_output=True, timeout=5)
            time.sleep(1)
            
            # I2C 모듈 다시 로드
            subprocess.run(['sudo', 'modprobe', 'i2c_bcm2708'], 
                         capture_output=True, timeout=5)
            time.sleep(2)
            
            # 버스 상태 확인
            addresses = self.scan_i2c_bus(bus_number)
            if addresses:
                logging.info(f"I2C bus {bus_number} restarted successfully. Found {len(addresses)} devices")
                return True
            else:
                logging.error(f"I2C bus {bus_number} restart failed")
                return False
                
        except Exception as e:
            logging.error(f"I2C bus restart error: {e}")
            return False
    
    def monitor_i2c_health(self, bus_number: int = 1, interval: int = 30):
        """I2C 버스 상태 모니터링"""
        while self.monitoring_active:
            try:
                with self.lock:
                    # 현재 연결된 디바이스 스캔
                    current_addresses = self.scan_i2c_bus(bus_number)
                    
                    # 기존 디바이스 상태 업데이트
                    for addr in self.devices:
                        if addr in current_addresses:
                            # 디바이스가 정상적으로 감지됨
                            if self.check_device_health(addr, bus_number):
                                self.devices[addr].status = I2CBusStatus.NORMAL
                                self.devices[addr].error_count = 0
                                self.devices[addr].last_seen = time.time()
                            else:
                                # 디바이스는 있지만 응답 없음
                                self.devices[addr].error_count += 1
                                if self.devices[addr].error_count >= self.error_threshold:
                                    self.devices[addr].status = I2CBusStatus.ERROR
                        else:
                            # 디바이스가 감지되지 않음
                            self.devices[addr].error_count += 1
                            if self.devices[addr].error_count >= self.restart_threshold:
                                self.devices[addr].status = I2CBusStatus.OFFLINE
                    
                    # 새로운 디바이스 추가
                    for addr in current_addresses:
                        if addr not in self.devices:
                            device_name = self.known_devices.get(addr, f"Unknown Device")
                            self.devices[addr] = I2CDevice(
                                address=addr,
                                name=device_name,
                                last_seen=time.time()
                            )
                    
                    # 전체 버스 상태 평가
                    error_count = sum(1 for dev in self.devices.values() 
                                    if dev.status in [I2CBusStatus.ERROR, I2CBusStatus.OFFLINE])
                    
                    if error_count == 0:
                        self.bus_status = I2CBusStatus.NORMAL
                    elif error_count < len(self.devices) // 2:
                        self.bus_status = I2CBusStatus.DEGRADED
                    else:
                        self.bus_status = I2CBusStatus.ERROR
                        
                        # 심각한 오류 시 자동 재시작
                        if error_count >= len(self.devices) // 2:
                            logging.critical("Critical I2C bus errors detected. Attempting restart...")
                            if self.restart_i2c_bus(bus_number):
                                # 재시작 후 디바이스 재등록
                                self.devices.clear()
                                time.sleep(5)  # 재시작 후 안정화 대기
                
                time.sleep(interval)
                
            except Exception as e:
                logging.error(f"I2C monitoring error: {e}")
                time.sleep(interval)
    
    def start_monitoring(self, bus_number: int = 1, interval: int = 30):
        """I2C 모니터링 시작"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self.monitor_i2c_health,
                args=(bus_number, interval),
                daemon=True
            )
            self.monitor_thread.start()
            logging.info("I2C bus monitoring started")
    
    def stop_monitoring(self):
        """I2C 모니터링 중지"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logging.info("I2C bus monitoring stopped")
    
    def get_bus_status(self) -> I2CBusStatus:
        """현재 버스 상태 반환"""
        return self.bus_status
    
    def get_device_status(self, address: int) -> Optional[I2CDevice]:
        """특정 디바이스 상태 반환"""
        return self.devices.get(address)
    
    def get_health_report(self) -> Dict:
        """전체 상태 보고서"""
        with self.lock:
            return {
                'bus_status': self.bus_status.value,
                'total_devices': len(self.devices),
                'normal_devices': sum(1 for dev in self.devices.values() 
                                    if dev.status == I2CBusStatus.NORMAL),
                'error_devices': sum(1 for dev in self.devices.values() 
                                   if dev.status == I2CBusStatus.ERROR),
                'offline_devices': sum(1 for dev in self.devices.values() 
                                     if dev.status == I2CBusStatus.OFFLINE),
                'devices': {
                    addr: {
                        'name': dev.name,
                        'status': dev.status.value,
                        'error_count': dev.error_count,
                        'last_seen': dev.last_seen
                    }
                    for addr, dev in self.devices.items()
                }
            }

# 전역 I2C 관리자 인스턴스
i2c_manager = I2CBusManager()

def get_i2c_manager() -> I2CBusManager:
    """전역 I2C 관리자 반환"""
    return i2c_manager

def init_i2c_monitoring(bus_number: int = 1, interval: int = 30):
    """I2C 모니터링 초기화"""
    i2c_manager.start_monitoring(bus_number, interval)

def stop_i2c_monitoring():
    """I2C 모니터링 중지"""
    i2c_manager.stop_monitoring()

def restart_i2c_bus(bus_number: int = 1) -> bool:
    """I2C 버스 재시작 (편의 함수)"""
    return i2c_manager.restart_i2c_bus(bus_number)

def get_i2c_health_report() -> Dict:
    """I2C 상태 보고서 (편의 함수)"""
    return i2c_manager.get_health_report() 