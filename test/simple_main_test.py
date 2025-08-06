#!/usr/bin/env python3
"""
main.py 기본 실행 테스트
"""

import os
import sys
import subprocess
import time

def main():
    print("🔍 main.py 기본 실행 테스트")
    print("=" * 40)
    
    # 현재 디렉토리 확인
    current_dir = os.getcwd()
    print(f"현재 디렉토리: {current_dir}")
    
    # main.py 경로 확인
    main_py_path = os.path.join(current_dir, "main.py")
    if os.path.exists(main_py_path):
        print(f"✅ main.py 발견: {main_py_path}")
    else:
        print(f"❌ main.py 없음: {main_py_path}")
        return
    
    # Python 경로 확인
    python_path = sys.executable
    print(f"Python 경로: {python_path}")
    
    # 가상환경 확인
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ 가상환경 활성화됨")
    else:
        print("⚠️ 가상환경이 활성화되지 않음")
    
    # main.py 직접 실행 시도
    print("\n🚀 main.py 실행 시도...")
    try:
        process = subprocess.Popen(
            [python_path, main_py_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=current_dir
        )
        
        # 2초 대기
        time.sleep(2)
        
        if process.poll() is None:
            print("✅ main.py 실행 성공 (프로세스 실행 중)")
            process.terminate()
            process.wait(timeout=3)
        else:
            stdout, stderr = process.communicate()
            print(f"❌ main.py 실행 실패 - 종료 코드: {process.returncode}")
            if stderr:
                print(f"오류: {stderr}")
            if stdout:
                print(f"출력: {stdout}")
                
    except Exception as e:
        print(f"❌ 실행 오류: {e}")

if __name__ == "__main__":
    main() 