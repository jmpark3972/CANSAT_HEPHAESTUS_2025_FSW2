#!/usr/bin/env python3
"""
간단한 main.py 시작 테스트
"""

import os
import sys
import subprocess

def main():
    print("🔍 main.py 시작 테스트")
    print("=" * 40)
    
    # 1. 현재 위치 확인
    current_dir = os.getcwd()
    print(f"현재 디렉토리: {current_dir}")
    
    # 2. main.py 찾기
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    main_py_path = os.path.join(project_root, "main.py")
    print(f"main.py 경로: {main_py_path}")
    
    if not os.path.exists(main_py_path):
        print("❌ main.py 파일이 없습니다!")
        return
    
    print("✅ main.py 파일 발견")
    
    # 3. 직접 실행 시도
    print("\n🚀 main.py 직접 실행 시도...")
    try:
        # 프로젝트 루트로 이동
        os.chdir(project_root)
        print(f"작업 디렉토리 변경: {os.getcwd()}")
        
        # main.py 실행 (3초 후 종료)
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("main.py 프로세스 시작됨...")
        
        # 3초 대기
        import time
        time.sleep(3)
        
        if process.poll() is None:
            print("✅ main.py가 정상적으로 실행 중입니다!")
            process.terminate()
            process.wait(timeout=2)
        else:
            stdout, stderr = process.communicate()
            print(f"❌ main.py 실행 실패 (종료 코드: {process.returncode})")
            if stderr:
                print(f"오류 메시지:\n{stderr}")
            if stdout:
                print(f"출력 메시지:\n{stdout}")
                
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
    
    # 4. Python 경로 확인
    print(f"\n🐍 Python 경로: {sys.executable}")
    
    # 5. 가상환경 확인
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 가상환경 활성화됨")
    else:
        print("⚠️ 가상환경이 활성화되지 않음")

if __name__ == "__main__":
    main() 