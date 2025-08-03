#!/usr/bin/env python3
"""
Qwiic Mux Controller for CANSAT
Qwiic Mux를 통해 여러 I2C 센서를 제어하는 라이브러리
"""

import board
import busio
import time
from typing import Optional

class QwiicMux:
    """Qwiic Mux 제어 클래스"""
    
    def __init__(self, i2c_bus=None, mux_address=0x70):
        """
        Qwiic Mux 초기화
        
        Args:
            i2c_bus: I2C 버스 객체 (None이면 자동 생성)
            mux_address: Mux의 I2C 주소 (기본값: 0x70)
        """
        if i2c_bus is None:
            self.i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        else:
            self.i2c = i2c_bus
        
        self.mux_address = mux_address
        self.current_channel = None
        
        # Mux 초기화
        self._init_mux()
    
    def _init_mux(self):
        """Mux 초기화 - 모든 채널 비활성화"""
        try:
            # 모든 채널 비활성화 (0x00)
            self.i2c.writeto(self.mux_address, bytes([0x00]))
            self.current_channel = None
            print(f"Qwiic Mux 초기화 완료 (주소: 0x{self.mux_address:02X})")
        except Exception as e:
            print(f"Qwiic Mux 초기화 오류: {e}")
            raise
    
    def select_channel(self, channel: int) -> bool:
        """
        특정 채널 선택
        
        Args:
            channel: 선택할 채널 (0-7)
            
        Returns:
            성공 여부
        """
        if not 0 <= channel <= 7:
            print(f"잘못된 채널 번호: {channel} (0-7 범위여야 함)")
            return False
        
        try:
            # 채널 선택 (1 << channel)
            channel_byte = 1 << channel
            self.i2c.writeto(self.mux_address, bytes([channel_byte]))
            self.current_channel = channel
            
            # 안정화를 위한 짧은 대기
            time.sleep(0.01)
            
            print(f"Qwiic Mux 채널 {channel} 선택됨")
            return True
            
        except Exception as e:
            print(f"채널 {channel} 선택 오류: {e}")
            return False
    
    def disable_all_channels(self):
        """모든 채널 비활성화"""
        try:
            self.i2c.writeto(self.mux_address, bytes([0x00]))
            self.current_channel = None
            print("모든 Qwiic Mux 채널 비활성화")
        except Exception as e:
            print(f"채널 비활성화 오류: {e}")
    
    def get_current_channel(self) -> Optional[int]:
        """현재 선택된 채널 반환"""
        return self.current_channel
    
    def scan_channels(self) -> dict:
        """
        모든 채널에서 I2C 디바이스 스캔
        
        Returns:
            채널별 발견된 디바이스 주소 딕셔너리
        """
        devices = {}
        
        for channel in range(8):
            if self.select_channel(channel):
                time.sleep(0.1)  # 안정화 대기
                
                # I2C 스캔
                found_devices = []
                for address in range(0x08, 0x78):  # 일반적인 I2C 주소 범위
                    try:
                        self.i2c.writeto(address, bytes([]), stop=False)
                        found_devices.append(hex(address))
                    except:
                        pass
                
                if found_devices:
                    devices[channel] = found_devices
                    print(f"채널 {channel}: {found_devices}")
        
        return devices
    
    def close(self):
        """리소스 정리"""
        try:
            self.disable_all_channels()
            if hasattr(self.i2c, 'deinit'):
                self.i2c.deinit()
        except Exception as e:
            print(f"Qwiic Mux 종료 오류: {e}")

# 전역 Mux 인스턴스
_global_mux = None

def get_global_mux() -> QwiicMux:
    """전역 Mux 인스턴스 반환"""
    global _global_mux
    if _global_mux is None:
        _global_mux = QwiicMux()
    return _global_mux

def close_global_mux():
    """전역 Mux 인스턴스 종료"""
    global _global_mux
    if _global_mux:
        _global_mux.close()
        _global_mux = None 