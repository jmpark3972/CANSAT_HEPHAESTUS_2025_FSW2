#!/usr/bin/env python3
"""
Qwiic Mux Controller for CANSAT
Qwiic Mux를 통해 여러 I2C 센서를 제어하는 라이브러리
"""

import time
import os
import fcntl
from contextlib import contextmanager
from typing import Optional

# 멀티플렉서 락 파일 경로
_LOCK_FILE = "/tmp/qwiic_mux.lock"

@contextmanager
def _mux_lock():
    """멀티플렉서 접근을 위한 간단한 락"""
    # 파일 락 대신 단순한 지연 사용
    time.sleep(0.01)  # 10ms 지연으로 충돌 방지
    yield
    time.sleep(0.01)  # 10ms 지연으로 안정화

def create_mux_instance(i2c_bus=None, mux_address=0x70):
    """독립적인 QwiicMux 인스턴스 생성"""
    if i2c_bus is None:
        import board
        import busio
        i2c_bus = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    return QwiicMux(i2c_bus=i2c_bus, mux_address=mux_address)

class QwiicMux:
    """Qwiic Mux (TCA9548A) 제어 클래스"""
    
    def __init__(self, i2c_bus, mux_address=0x70):
        self.i2c = i2c_bus
        self.mux_address = mux_address
        self.current_channel = None
        print(f"Qwiic Mux 초기화 완료 (주소: 0x{mux_address:02X})")
    
    def select_channel(self, channel: int) -> bool:
        """특정 채널 선택"""
        if not 0 <= channel <= 7:
            print(f"잘못된 채널 번호: {channel}")
            return False

        if self.current_channel == channel:
            return True
    
        try:
            # 먼저 모든 채널 비활성화
            self.i2c.writeto(self.mux_address, bytes([0x00]))
            time.sleep(0.05)  # 안정화 대기
            
            # 채널 선택 (1 << channel)
            channel_byte = 1 << channel
            self.i2c.writeto(self.mux_address, bytes([channel_byte]))
            self.current_channel = channel
            
            # 안정화를 위한 충분한 대기
            time.sleep(0.1)
            
            print(f"Qwiic Mux 채널 {channel} 선택됨")
            return True
            
        except Exception as e:
            print(f"채널 {channel} 선택 오류: {e}")
            # 오류 발생 시 채널 상태 초기화
            self.current_channel = None
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
    
    @contextmanager
    def channel_guard(self, channel: int):
        """채널 선택과 I2C 작업을 안전하게 보호하는 컨텍스트 매니저"""
        with _mux_lock():  # 🔒 멀티플렉서 락 획득
            ok = self.select_channel(channel)  # 채널 전환
            if not ok:
                raise RuntimeError(f"채널 {channel} 선택 실패")
            try:
                yield  # 여기서 I2C 작업 수행
            finally:
                pass  # 필요하면 모든 채널 끄기

    def close(self):
        """리소스 정리"""
        try:
            self.disable_all_channels()
            if hasattr(self.i2c, 'deinit'):
                try:
                    self.i2c.deinit()
                except Exception as e:
                    print(f"I2C deinit 오류: {e}")
        except Exception as e:
            print(f"Qwiic Mux 종료 오류: {e}")
        finally:
            self.i2c = None
            self.current_channel = None

# 전역 Mux 인스턴스 (사용하지 않음 - 각 센서가 독립적인 인스턴스 사용)
_global_mux = None

def get_global_mux() -> QwiicMux:
    """전역 Mux 인스턴스 반환 (권장하지 않음)"""
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