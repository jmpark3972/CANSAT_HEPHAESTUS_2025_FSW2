#!/usr/bin/env python3
"""
강제 종료 스크립트
CANSAT 시스템을 강제로 종료합니다
"""

import os
import sys
import subprocess
import signal
import time

def kill_python_processes():
    """Python 프로세스들을 강제 종료"""
    print("Python 프로세스들을 찾아서 종료 중...")
    
    try:
        # main.py 관련 프로세스 찾기
        result = subprocess.run(['pgrep', '-f', 'main.py'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"프로세스 {pid} 종료 중...")
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except:
                        pass
        
        # 모든 Python 프로세스 종료 (필요시)
        result = subprocess.run(['pgrep', '-f', 'python.*main'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            for pid in pids:
                if pid:
                    print(f"Python 프로세스 {pid} 종료 중...")
                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except:
                        pass
                        
    except Exception as e:
        print(f"프로세스 종료 중 오류: {e}")

def kill_pigpiod():
    """pigpiod 프로세스 종료"""
    print("pigpiod 프로세스 종료 중...")
    try:
        subprocess.run(['sudo', 'pkill', 'pigpiod'], check=False)
        time.sleep(1)
    except:
        pass

def cleanup_files():
    """임시 파일들 정리"""
    print("임시 파일들 정리 중...")
    try:
        # Python 캐시 파일들 삭제
        subprocess.run(['find', '.', '-name', '*.pyc', '-delete'], check=False)
        subprocess.run(['find', '.', '-name', '__pycache__', '-type', 'd', '-exec', 'rm', '-rf', '{}', '+'], check=False)
    except:
        pass

def main():
    """메인 함수"""
    print("CANSAT 시스템 강제 종료 스크립트")
    print("=" * 40)
    
    # 1. Python 프로세스들 종료
    kill_python_processes()
    
    # 2. pigpiod 종료
    kill_pigpiod()
    
    # 3. 파일 정리
    cleanup_files()
    
    print("\n강제 종료 완료!")
    print("이제 main.py를 다시 실행할 수 있습니다.")

if __name__ == "__main__":
    main() 