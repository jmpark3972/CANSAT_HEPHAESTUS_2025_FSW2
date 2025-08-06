#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 강제 종료 유틸리티
CANSAT 시스템을 강제로 종료하고 정리합니다
"""

import os
import sys
import subprocess
import signal
import time
import psutil
from datetime import datetime

def log_action(message: str):
    """액션 로깅"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def find_cansat_processes():
    """CANSAT 관련 프로세스 찾기"""
    cansat_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    
                    # CANSAT 관련 프로세스들
                    cansat_keywords = [
                        'main.py',
                        'FlightLogicApp',
                        'CommApp', 
                        'HKApp',
                        'BarometerApp',
                        'ImuApp',
                        'GpsApp',
                        'MotorApp',
                        'CameraApp',
                        'ThermalCameraApp'
                    ]
                    
                    for keyword in cansat_keywords:
                        if keyword in cmdline:
                            cansat_processes.append({
                                'pid': proc.info['pid'],
                                'cmdline': cmdline[:100] + '...' if len(cmdline) > 100 else cmdline
                            })
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    except Exception as e:
        log_action(f"프로세스 검색 오류: {e}")
    
    return cansat_processes

def kill_process_safely(pid: int, process_name: str = "Unknown"):
    """프로세스를 안전하게 종료"""
    try:
        proc = psutil.Process(pid)
        
        # 1단계: 정상 종료 시도
        log_action(f"{process_name} (PID: {pid}) 정상 종료 시도...")
        proc.terminate()
        
        # 2초 대기
        try:
            proc.wait(timeout=2)
            log_action(f"✅ {process_name} (PID: {pid}) 정상 종료됨")
            return True
        except psutil.TimeoutExpired:
            pass
        
        # 2단계: 강제 종료
        log_action(f"{process_name} (PID: {pid}) 강제 종료 시도...")
        proc.kill()
        
        # 1초 대기
        try:
            proc.wait(timeout=1)
            log_action(f"✅ {process_name} (PID: {pid}) 강제 종료됨")
            return True
        except psutil.TimeoutExpired:
            pass
        
        # 3단계: 최후의 수단
        log_action(f"{process_name} (PID: {pid}) 최후 강제 종료...")
        os.kill(pid, signal.SIGKILL)
        time.sleep(0.5)
        
        if not proc.is_running():
            log_action(f"✅ {process_name} (PID: {pid}) 최종 종료됨")
            return True
        else:
            log_action(f"❌ {process_name} (PID: {pid}) 종료 실패")
            return False
            
    except psutil.NoSuchProcess:
        log_action(f"✅ {process_name} (PID: {pid}) 이미 종료됨")
        return True
    except Exception as e:
        log_action(f"❌ {process_name} (PID: {pid}) 종료 오류: {e}")
        return False

def kill_cansat_processes():
    """CANSAT 관련 프로세스들을 종료"""
    log_action("CANSAT 관련 프로세스 검색 중...")
    
    cansat_processes = find_cansat_processes()
    
    if not cansat_processes:
        log_action("✅ 실행 중인 CANSAT 프로세스가 없습니다")
        return True
    
    log_action(f"발견된 CANSAT 프로세스: {len(cansat_processes)}개")
    
    success_count = 0
    for proc_info in cansat_processes:
        pid = proc_info['pid']
        cmdline = proc_info['cmdline']
        
        # 프로세스 이름 추출
        if 'main.py' in cmdline:
            process_name = "Main FSW"
        elif 'FlightLogicApp' in cmdline:
            process_name = "FlightLogic"
        elif 'CommApp' in cmdline:
            process_name = "Communication"
        elif 'HKApp' in cmdline:
            process_name = "Housekeeping"
        elif 'BarometerApp' in cmdline:
            process_name = "Barometer"
        elif 'ImuApp' in cmdline:
            process_name = "IMU"
        elif 'GpsApp' in cmdline:
            process_name = "GPS"
        elif 'MotorApp' in cmdline:
            process_name = "Motor"
        elif 'CameraApp' in cmdline:
            process_name = "Camera"
        elif 'ThermalCameraApp' in cmdline:
            process_name = "Thermal Camera"
        else:
            process_name = "Unknown CANSAT Process"
        
        if kill_process_safely(pid, process_name):
            success_count += 1
    
    log_action(f"프로세스 종료 완료: {success_count}/{len(cansat_processes)} 성공")
    return success_count == len(cansat_processes)

def kill_pigpiod():
    """pigpiod 프로세스 종료"""
    log_action("pigpiod 프로세스 종료 중...")
    
    try:
        # pigpiod 프로세스 찾기
        result = subprocess.run(['pgrep', 'pigpiod'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    kill_process_safely(int(pid), "pigpiod")
        else:
            log_action("✅ pigpiod 프로세스가 실행 중이지 않습니다")
            
    except Exception as e:
        log_action(f"pigpiod 종료 오류: {e}")

def cleanup_files():
    """임시 파일들 정리"""
    log_action("임시 파일들 정리 중...")
    
    try:
        # Python 캐시 파일들 삭제
        log_action("Python 캐시 파일 삭제 중...")
        subprocess.run(['find', '.', '-name', '*.pyc', '-delete'], check=False)
        subprocess.run(['find', '.', '-name', '__pycache__', '-type', 'd', '-exec', 'rm', '-rf', '{}', '+'], check=False)
        
        # 로그 파일 정리 (선택적)
        log_action("임시 로그 파일 정리 중...")
        temp_logs = [
            'logs/temp_*.txt',
            'logs/debug_*.txt',
            'logs/error_*.txt'
        ]
        
        for pattern in temp_logs:
            subprocess.run(['find', '.', '-name', pattern.split('/')[-1], '-delete'], check=False)
            
        log_action("✅ 파일 정리 완료")
        
    except Exception as e:
        log_action(f"파일 정리 오류: {e}")

def check_system_status():
    """시스템 상태 확인"""
    log_action("시스템 상태 확인 중...")
    
    # 남은 CANSAT 프로세스 확인
    remaining_processes = find_cansat_processes()
    if remaining_processes:
        log_action(f"⚠️ 남은 CANSAT 프로세스: {len(remaining_processes)}개")
        for proc in remaining_processes:
            log_action(f"  - PID {proc['pid']}: {proc['cmdline']}")
    else:
        log_action("✅ 모든 CANSAT 프로세스가 종료되었습니다")
    
    # pigpiod 상태 확인
    try:
        result = subprocess.run(['pgrep', 'pigpiod'], capture_output=True, text=True)
        if result.returncode == 0:
            log_action("⚠️ pigpiod가 여전히 실행 중입니다")
        else:
            log_action("✅ pigpiod가 종료되었습니다")
    except Exception as e:
        log_action(f"pigpiod 상태 확인 오류: {e}")

def force_kill_all():
    """모든 CANSAT 관련 프로세스 강제 종료"""
    print("🚨 CANSAT HEPHAESTUS 2025 FSW2 - 강제 종료 시스템")
    print("=" * 60)
    
    # 1. CANSAT 프로세스들 종료
    kill_cansat_processes()
    
    # 2. pigpiod 종료
    kill_pigpiod()
    
    # 3. 파일 정리
    cleanup_files()
    
    # 4. 시스템 상태 확인
    print("\n" + "=" * 60)
    check_system_status()
    
    print("\n🎉 강제 종료 완료!")
    print("이제 main.py를 다시 실행할 수 있습니다.")

def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        check_system_status()
    else:
        force_kill_all()

# 편의 함수들
def force_kill_process(pid: int, process_name: str = "Unknown"):
    """특정 프로세스 강제 종료 (편의 함수)"""
    return kill_process_safely(pid, process_name)

def force_kill_all_processes():
    """모든 CANSAT 프로세스 강제 종료 (편의 함수)"""
    return force_kill_all()

if __name__ == "__main__":
    main() 