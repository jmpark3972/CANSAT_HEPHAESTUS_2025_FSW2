#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 라이브러리 패키지
모든 공통 기능들을 제공하는 메인 라이브러리 패키지입니다.
"""

# 핵심 기능들
from .core import *

# 로깅 시스템
from .logging import safe_log, get_unified_logger, LogLevel, LogCategory

# 최적화 기능들
from .optimization import (
    start_memory_optimization, stop_memory_optimization,
    start_performance_optimization, stop_performance_optimization,
    start_performance_monitoring, stop_performance_monitoring,
    optimize_data_structure
)

# 하드웨어 관련 기능들
from .hardware import (
    I2CManager, get_i2c_manager,
    force_kill_process, force_kill_all_processes,
    setup_exception_handler, handle_exception
)

# 기본 앱 클래스
from .base_app import BaseApp, SensorApp, CommunicationApp, create_app_instance, run_app

# 기타 유틸리티들
from .type_hints import *
from .offsets import *
from .resource_manager import start_resource_monitoring, stop_resource_monitoring
from .logging import LogRotator

__all__ = [
    # 핵심 기능들 (core에서)
    'MainAppArg', 'HkAppArg', 'BarometerAppArg', 'GpsAppArg', 'ImuAppArg',
    'FlightlogicAppArg', 'CommAppArg', 'MotorAppArg', 'FirApp1Arg',
    'ThermisAppArg', 'Tmp007AppArg', 'ThermalcameraAppArg', 'ThermoAppArg',
    'MsgStructure', 'fill_msg', 'pack_msg', 'unpack_msg', 'send_msg',
    'AppID', 'MsgID', 'get_config', 'set_config', 'load_config',
    'reset_prevstate', 'update_prevstate', 'get_prevstate',
    'safe_write_to_file', 'check_and_rotate_log_file',
    
    # 로깅 시스템
    'safe_log', 'get_unified_logger', 'LogLevel', 'LogCategory',
    
    # 최적화 기능들
    'start_memory_optimization', 'stop_memory_optimization',
    'start_performance_optimization', 'stop_performance_optimization',
    'start_performance_monitoring', 'stop_performance_monitoring',
    'optimize_data_structure',
    
    # 하드웨어 관련 기능들
    'I2CManager', 'get_i2c_manager',
    'force_kill_process', 'force_kill_all_processes',
    'setup_exception_handler', 'handle_exception',
    
    # 기본 앱 클래스
    'BaseApp', 'SensorApp', 'CommunicationApp', 'create_app_instance', 'run_app',
    
    # 기타 유틸리티들
    'start_resource_monitoring', 'stop_resource_monitoring',
    'LogRotator'
] 