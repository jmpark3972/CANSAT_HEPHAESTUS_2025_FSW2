#!/usr/bin/env python3
"""
Test script to verify main.py termination logic
"""
import subprocess
import time
import signal
import os

def test_termination():
    print("main.py 종료 테스트 시작...")
    print("프로그램을 시작하고 Ctrl+C로 종료를 테스트합니다.")
    
    try:
        # Start main.py
        process = subprocess.Popen(['python3', 'main.py'], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        print(f"main.py 프로세스 시작됨 (PID: {process.pid})")
        print("5초 후 Ctrl+C 시뮬레이션...")
        
        time.sleep(5)
        
        # Simulate Ctrl+C
        print("SIGINT 시그널 전송...")
        process.send_signal(signal.SIGINT)
        
        # Wait for termination
        try:
            process.wait(timeout=10)
            print("프로그램이 정상적으로 종료되었습니다.")
        except subprocess.TimeoutExpired:
            print("10초 타임아웃. 강제 종료...")
            process.kill()
            process.wait()
            print("강제 종료 완료.")
            
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_termination() 