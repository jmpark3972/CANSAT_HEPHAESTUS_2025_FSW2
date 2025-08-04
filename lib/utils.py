#!/usr/bin/env python3
"""
System Diagnostics and Utilities for CANSAT FSW
시스템 진단 및 유틸리티 함수들
"""

import os
import time
import threading
from typing import Dict, List, Optional, Tuple
from lib import events, appargs

def check_system_resources() -> Dict[str, float]:
    """
    시스템 리소스 상태 확인
    
    Returns:
        리소스 사용률 딕셔너리
    """
    resources = {}
    
    try:
        import psutil
        
        # CPU 사용률
        resources['cpu_percent'] = psutil.cpu_percent(interval=1)
        
        # 메모리 사용률
        memory = psutil.virtual_memory()
        resources['memory_percent'] = memory.percent
        resources['memory_available_mb'] = memory.available / (1024 * 1024)
        
        # 디스크 사용률
        disk = psutil.disk_usage('/')
        resources['disk_percent'] = disk.percent
        resources['disk_free_gb'] = disk.free / (1024 * 1024 * 1024)
        
        # 네트워크 상태 (간단한 체크)
        try:
            net_io = psutil.net_io_counters()
            resources['network_bytes_sent'] = net_io.bytes_sent
            resources['network_bytes_recv'] = net_io.bytes_recv
        except:
            resources['network_status'] = 'unknown'
            
    except ImportError:
        resources['error'] = 'psutil not available'
    except Exception as e:
        resources['error'] = str(e)
        
    return resources

def validate_message_structure(msg: str) -> bool:
    """
    메시지 구조 유효성 검사
    
    Args:
        msg: 검사할 메시지 문자열
        
    Returns:
        유효성 여부
    """
    try:
        if not isinstance(msg, str):
            return False
            
        parts = msg.split('|')
        if len(parts) != 4:
            return False
            
        # 숫자 필드 검증
        sender = int(parts[0])
        receiver = int(parts[1])
        msg_id = int(parts[2])
        
        if sender < 0 or receiver < 0 or msg_id < 0:
            return False
            
        return True
        
    except (ValueError, TypeError):
        return False

def monitor_process_health(process_dict: Dict, timeout: int = 30) -> Dict[str, str]:
    """
    프로세스 상태 모니터링
    
    Args:
        process_dict: 프로세스 딕셔너리
        timeout: 타임아웃 (초)
        
    Returns:
        프로세스 상태 딕셔너리
    """
    health_status = {}
    
    for app_id, app_elements in process_dict.items():
        try:
            if app_elements.process is None:
                health_status[app_id] = 'NO_PROCESS'
                continue
                
            if not app_elements.process.is_alive():
                health_status[app_id] = 'DEAD'
            else:
                health_status[app_id] = 'ALIVE'
                
        except Exception as e:
            health_status[app_id] = f'ERROR: {str(e)}'
            
    return health_status

def create_system_report() -> str:
    """
    시스템 상태 보고서 생성
    
    Returns:
        보고서 문자열
    """
    report = []
    report.append("=== CANSAT FSW System Report ===")
    report.append(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 시스템 리소스
    resources = check_system_resources()
    report.append("\n--- System Resources ---")
    for key, value in resources.items():
        if isinstance(value, float):
            report.append(f"{key}: {value:.2f}")
        else:
            report.append(f"{key}: {value}")
    
    # 파일 시스템 상태
    report.append("\n--- File System ---")
    try:
        log_dir = './logs'
        if os.path.exists(log_dir):
            log_size = sum(os.path.getsize(os.path.join(log_dir, f)) 
                          for f in os.listdir(log_dir) 
                          if os.path.isfile(os.path.join(log_dir, f)))
            report.append(f"Log directory size: {log_size / (1024*1024):.2f} MB")
        else:
            report.append("Log directory: Not found")
    except Exception as e:
        report.append(f"Log directory error: {e}")
    
    return "\n".join(report)

def emergency_shutdown(reason: str = "Unknown"):
    """
    긴급 종료 함수
    
    Args:
        reason: 종료 이유
    """
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"EMERGENCY SHUTDOWN: {reason}")
    
    # 시스템 보고서 생성
    try:
        report = create_system_report()
        with open(f'./logs/emergency_report_{int(time.time())}.txt', 'w') as f:
            f.write(report)
    except:
        pass
    
    # 강제 종료
    os._exit(1)

def validate_configuration() -> bool:
    """
    설정 파일 유효성 검사
    
    Returns:
        유효성 여부
    """
    try:
        from lib import config
        
        # 기본 설정 검사
        if config.FSW_CONF == config.CONF_NONE:
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, "Configuration is set to NONE")
            return False
            
        # 설정 파일 존재 확인
        if not os.path.exists(config.config_file_path):
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, "Configuration file not found")
            return False
            
        return True
        
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Configuration validation error: {e}")
        return False

def check_dependencies() -> Dict[str, bool]:
    """
    필요한 의존성 확인
    
    Returns:
        의존성 상태 딕셔너리
    """
    dependencies = {}
    
    # 핵심 라이브러리 확인
    required_modules = [
        'board', 'busio', 'adafruit_mlx90614', 'adafruit_mlx90640',
        'smbus2', 'serial', 'threading', 'multiprocessing'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
            dependencies[module] = True
        except ImportError:
            dependencies[module] = False
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Missing dependency: {module}")
    
    return dependencies

def create_backup_state():
    """
    현재 상태 백업 생성
    """
    try:
        from lib import prevstate
        
        backup_file = f'./logs/state_backup_{int(time.time())}.txt'
        with open(backup_file, 'w') as f:
            f.write(f"Backup created at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"FSW State: {prevstate.PREV_STATE}\n")
            f.write(f"Altitude Calibration: {prevstate.PREV_ALT_CAL}\n")
            f.write(f"Max Altitude: {prevstate.PREV_MAX_ALT}\n")
            
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"State backup created: {backup_file}")
        
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Backup creation failed: {e}")

def monitor_thread_health(thread_dict: Dict[str, threading.Thread]) -> Dict[str, str]:
    """
    스레드 상태 모니터링
    
    Args:
        thread_dict: 스레드 딕셔너리
        
    Returns:
        스레드 상태 딕셔너리
    """
    thread_status = {}
    
    for name, thread in thread_dict.items():
        try:
            if thread.is_alive():
                thread_status[name] = 'ALIVE'
            else:
                thread_status[name] = 'DEAD'
        except Exception as e:
            thread_status[name] = f'ERROR: {str(e)}'
            
    return thread_status

# 메인 실행 시 테스트
if __name__ == "__main__":
    print("=== CANSAT FSW Utilities Test ===")
    
    # 시스템 리소스 확인
    print("\n1. System Resources:")
    resources = check_system_resources()
    for key, value in resources.items():
        print(f"  {key}: {value}")
    
    # 의존성 확인
    print("\n2. Dependencies:")
    deps = check_dependencies()
    for dep, available in deps.items():
        status = "✓" if available else "✗"
        print(f"  {status} {dep}")
    
    # 설정 검증
    print("\n3. Configuration:")
    config_valid = validate_configuration()
    print(f"  Configuration valid: {config_valid}")
    
    # 시스템 보고서
    print("\n4. System Report:")
    report = create_system_report()
    print(report) 