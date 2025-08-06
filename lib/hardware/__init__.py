#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 하드웨어 패키지
하드웨어 관련 기능을 제공합니다.
"""

from .i2c_manager import I2CBusManager as I2CManager, get_i2c_manager
from .force_kill import force_kill_process, force_kill_all_processes
from .exception_handler import setup_exception_handler, handle_exception

__all__ = [
    'I2CManager',
    'get_i2c_manager',
    'force_kill_process',
    'force_kill_all_processes',
    'setup_exception_handler',
    'handle_exception'
] 