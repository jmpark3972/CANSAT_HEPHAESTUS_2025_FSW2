#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 진단 스크립트
CANSAT 시스템의 문제를 식별하고 수정하는 데 도움을 주는 스크립트
"""

import os
import sys
import time
import subprocess
import psutil
from pathlib import Path
from datetime import datetime

def log_diagnostic(message: str):
    """진단 메시지 로깅"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_system_resources():
    """시스템 리소스 확인"""
    print("=== 시스템 리소스 확인 ===")
    
    try:
        # 메모리 사용량
        memory = psutil.virtual_memory()
        log_diagnostic(f"메모리 사용량: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")
        
        # 디스크 사용량
        disk = psutil.disk_usage('/')
        log_diagnostic(f"디스크 사용량: {disk.percent}% ({disk.used // 1024 // 1024}MB / {disk.total // 1024 // 1024}MB)")
        
        # CPU 사용량
        cpu_percent = psutil.cpu_percent(interval=1)
        log_diagnostic(f"CPU 사용량: {cpu_percent}%")
        
        # 프로세스 수
        process_count = len(psutil.pids())
        log_diagnostic(f"활성 프로세스: {process_count}개")
        
        # 온도 확인 (라즈베리파이)
        try:
            result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
            if result.returncode == 0:
                temp = result.stdout.strip().split('=')[1]
                log_diagnostic(f"시스템 온도: {temp}")
        except Exception as e:
            log_diagnostic(f"시스템 온도 확인 오류: {e}")
        
        return memory.percent < 90 and disk.percent < 95
    except Exception as e:
        log_diagnostic(f"시스템 리소스 확인 오류: {e}")
        return False

def check_cansat_processes():
    """CANSAT 프로세스 확인"""
    print("\n=== CANSAT 프로세스 확인 ===")
    cansat_processes = []
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'python' in proc.info['name'].lower():
                    cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                    
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
                            cansat_processes.append(proc.info)
                            break
                            
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if cansat_processes:
            log_diagnostic(f"실행 중인 CANSAT 프로세스: {len(cansat_processes)}개")
            for proc in cansat_processes:
                cmdline = ' '.join(proc['cmdline']) if proc['cmdline'] else ''
                log_diagnostic(f"  PID {proc['pid']}: {cmdline[:80]}...")
        else:
            log_diagnostic("실행 중인 CANSAT 프로세스가 없습니다")
        
        return cansat_processes
    except Exception as e:
        log_diagnostic(f"CANSAT 프로세스 확인 오류: {e}")
        return []

def check_i2c_devices():
    """I2C 디바이스 확인"""
    print("\n=== I2C 디바이스 확인 ===")
    
    try:
        # i2cdetect 사용 가능 여부 확인
        result = subprocess.run(['which', 'i2cdetect'], capture_output=True, text=True)
        if result.returncode != 0:
            log_diagnostic("i2cdetect를 찾을 수 없습니다. i2c-tools 패키지를 설치하세요.")
            return False
        
        # I2C 버스 1 스캔
        log_diagnostic("I2C 버스 1 스캔 중...")
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        if result.returncode == 0:
            print("I2C 버스 1 디바이스:")
            print(result.stdout)
        else:
            log_diagnostic("I2C 버스 1 스캔 실패")
            
        # I2C 버스 0 스캔
        log_diagnostic("I2C 버스 0 스캔 중...")
        result = subprocess.run(['i2cdetect', '-y', '0'], capture_output=True, text=True)
        if result.returncode == 0:
            print("I2C 버스 0 디바이스:")
            print(result.stdout)
        else:
            log_diagnostic("I2C 버스 0 스캔 실패")
            
        return True
    except Exception as e:
        log_diagnostic(f"I2C 디바이스 확인 오류: {e}")
        return False

def check_serial_ports():
    """시리얼 포트 확인"""
    print("\n=== 시리얼 포트 확인 ===")
    
    try:
        # /dev/tty* 디바이스 확인
        serial_devices = []
        for device in Path('/dev').glob('tty*'):
            if device.is_char_device():
                serial_devices.append(str(device))
        
        if serial_devices:
            log_diagnostic(f"사용 가능한 시리얼 포트: {len(serial_devices)}개")
            for device in serial_devices[:10]:  # 처음 10개만 표시
                log_diagnostic(f"  {device}")
        else:
            log_diagnostic("사용 가능한 시리얼 포트가 없습니다")
            
        return len(serial_devices) > 0
    except Exception as e:
        log_diagnostic(f"시리얼 포트 확인 오류: {e}")
        return False

def check_gpio_access():
    """GPIO 접근 권한 확인"""
    print("\n=== GPIO 접근 권한 확인 ===")
    
    try:
        # GPIO 디렉토리 확인
        gpio_path = Path('/sys/class/gpio')
        if gpio_path.exists():
            log_diagnostic("GPIO 시스템 디렉토리 존재")
            
            # GPIO 그룹 확인
            result = subprocess.run(['groups'], capture_output=True, text=True)
            if result.returncode == 0:
                groups = result.stdout.strip().split()
                if 'gpio' in groups:
                    log_diagnostic("✅ GPIO 그룹에 속해 있습니다")
                else:
                    log_diagnostic("⚠️ GPIO 그룹에 속해 있지 않습니다")
                    
            # pigpiod 확인
            result = subprocess.run(['pgrep', 'pigpiod'], capture_output=True, text=True)
            if result.returncode == 0:
                log_diagnostic("✅ pigpiod가 실행 중입니다")
            else:
                log_diagnostic("⚠️ pigpiod가 실행 중이지 않습니다")
        else:
            log_diagnostic("❌ GPIO 시스템 디렉토리가 없습니다")
            
        return True
    except Exception as e:
        log_diagnostic(f"GPIO 접근 권한 확인 오류: {e}")
        return False

def check_python_dependencies():
    """Python 의존성 확인"""
    print("\n=== Python 의존성 확인 ===")
    
    required_packages = [
        'psutil',
        'pigpio',
        'numpy',
        'opencv-python',
        'pyserial',
        'adafruit-circuitpython-bno055',
        'adafruit-circuitpython-bmp3xx'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            if package == 'opencv-python':
                import cv2
            elif package == 'pyserial':
                import serial
            elif package == 'adafruit-circuitpython-bno055':
                import adafruit_bno055
            elif package == 'adafruit-circuitpython-bmp3xx':
                import adafruit_bmp3xx
            else:
                __import__(package.replace('-', '_'))
            log_diagnostic(f"✅ {package}")
        except ImportError:
            log_diagnostic(f"❌ {package} - 누락")
            missing_packages.append(package)
    
    return len(missing_packages) == 0

def check_file_permissions():
    """파일 권한 확인"""
    print("\n=== 파일 권한 확인 ===")
    
    try:
        # 로그 디렉토리 확인
        log_dirs = ['logs', 'eventlogs']
        for log_dir in log_dirs:
            if os.path.exists(log_dir):
                if os.access(log_dir, os.W_OK):
                    log_diagnostic(f"✅ {log_dir} 디렉토리 쓰기 권한 있음")
                else:
                    log_diagnostic(f"❌ {log_dir} 디렉토리 쓰기 권한 없음")
            else:
                log_diagnostic(f"⚠️ {log_dir} 디렉토리가 없습니다")
        
        # main.py 실행 권한 확인
        if os.path.exists('main.py'):
            if os.access('main.py', os.R_OK):
                log_diagnostic("✅ main.py 읽기 권한 있음")
            else:
                log_diagnostic("❌ main.py 읽기 권한 없음")
        else:
            log_diagnostic("❌ main.py 파일이 없습니다")
            
        return True
    except Exception as e:
        log_diagnostic(f"파일 권한 확인 오류: {e}")
        return False

def check_camera_hardware():
    """카메라 하드웨어 확인"""
    print("\n=== 카메라 하드웨어 확인 ===")
    
    try:
        # vcgencmd로 카메라 확인
        result = subprocess.run(['vcgencmd', 'get_camera'], capture_output=True, text=True)
        if result.returncode == 0:
            log_diagnostic(f"카메라 상태: {result.stdout.strip()}")
        
        # /dev/video* 디바이스 확인
        video_devices = list(Path('/dev').glob('video*'))
        if video_devices:
            log_diagnostic(f"비디오 디바이스: {len(video_devices)}개")
            for device in video_devices:
                log_diagnostic(f"  {device}")
        else:
            log_diagnostic("비디오 디바이스가 없습니다")
            
        return True
    except Exception as e:
        log_diagnostic(f"카메라 하드웨어 확인 오류: {e}")
        return False

def suggest_fixes():
    """수정 제안"""
    print("\n=== 수정 제안 ===")
    
    suggestions = [
        "1. 시스템 리소스 부족 시: 불필요한 프로세스 종료",
        "2. I2C 오류 시: sudo apt install i2c-tools",
        "3. GPIO 권한 문제 시: sudo usermod -a -G gpio $USER",
        "4. pigpiod 없음 시: sudo systemctl start pigpiod",
        "5. Python 패키지 누락 시: pip3 install -r requirements.txt",
        "6. 카메라 문제 시: sudo raspi-config에서 Camera 활성화",
        "7. 시리얼 포트 문제 시: sudo usermod -a -G dialout $USER"
    ]
    
    for suggestion in suggestions:
        log_diagnostic(suggestion)

def run_full_diagnostic():
    """전체 진단 실행"""
    print("🔍 CANSAT HEPHAESTUS 2025 FSW2 - 시스템 진단")
    print("=" * 60)
    
    # 1. 시스템 리소스 확인
    system_ok = check_system_resources()
    
    # 2. CANSAT 프로세스 확인
    processes = check_cansat_processes()
    
    # 3. I2C 디바이스 확인
    i2c_ok = check_i2c_devices()
    
    # 4. 시리얼 포트 확인
    serial_ok = check_serial_ports()
    
    # 5. GPIO 접근 권한 확인
    gpio_ok = check_gpio_access()
    
    # 6. Python 의존성 확인
    deps_ok = check_python_dependencies()
    
    # 7. 파일 권한 확인
    perms_ok = check_file_permissions()
    
    # 8. 카메라 하드웨어 확인
    camera_ok = check_camera_hardware()
    
    # 9. 수정 제안
    suggest_fixes()
    
    # 10. 결과 요약
    print("\n" + "=" * 60)
    print("📊 진단 결과 요약")
    print("=" * 60)
    
    results = [
        ("시스템 리소스", system_ok),
        ("I2C 디바이스", i2c_ok),
        ("시리얼 포트", serial_ok),
        ("GPIO 접근", gpio_ok),
        ("Python 의존성", deps_ok),
        ("파일 권한", perms_ok),
        ("카메라 하드웨어", camera_ok)
    ]
    
    passed = 0
    for name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{name:15} | {status}")
        if result:
            passed += 1
    
    print("-" * 60)
    print(f"총 검사: {len(results)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(results) - passed}개")
    
    if passed == len(results):
        print("\n🎉 모든 진단이 통과했습니다!")
        return True
    else:
        print(f"\n⚠️ {len(results) - passed}개 항목에 문제가 있습니다.")
        return False

def main():
    """메인 함수"""
    if len(sys.argv) > 1 and sys.argv[1] == '--quick':
        # 빠른 진단
        print("🔍 CANSAT HEPHAESTUS 2025 FSW2 - 빠른 진단")
        print("=" * 40)
        check_system_resources()
        check_cansat_processes()
        check_gpio_access()
    else:
        # 전체 진단
        run_full_diagnostic()

if __name__ == "__main__":
    main() 