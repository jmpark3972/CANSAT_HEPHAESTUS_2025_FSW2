#!/usr/bin/env python3
"""
기본 main.py 시작 테스트
"""

import os
import sys
import subprocess
import time

def main():
    print("🔍 기본 main.py 시작 테스트")
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
    
    # 3. Python 문법 검사
    print("\n🔧 Python 문법 검사...")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', main_py_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✅ main.py 문법 검사 통과")
        else:
            print(f"❌ main.py 문법 오류: {result.stderr}")
            return
    except Exception as e:
        print(f"❌ 문법 검사 실패: {e}")
        return
    
    # 4. 기본 import 테스트
    print("\n📦 기본 import 테스트...")
    try:
        # 프로젝트 루트를 Python 경로에 추가
        sys.path.insert(0, project_root)
        
        # 기본 모듈들 import 테스트
        basic_modules = [
            'lib.config',
            'lib.appargs',
            'lib.msgstructure',
            'lib.logging'
        ]
        
        for module_name in basic_modules:
            try:
                __import__(module_name)
                print(f"✅ {module_name}")
            except ImportError as e:
                print(f"❌ {module_name} - {e}")
                return
            except Exception as e:
                print(f"❌ {module_name} - {e}")
                return
                
    except Exception as e:
        print(f"❌ Import 테스트 실패: {e}")
        return
    
    # 5. config 테스트
    print("\n⚙️ Config 테스트...")
    try:
        from lib import config
        
        fsw_mode = config.get_config("FSW_MODE")
        print(f"FSW_MODE: {fsw_mode}")
        
        if fsw_mode == "NONE":
            print("❌ FSW_MODE가 NONE으로 설정되어 있습니다!")
            return
        else:
            print("✅ FSW_MODE 정상")
            
    except Exception as e:
        print(f"❌ Config 테스트 실패: {e}")
        return
    
    # 6. 직접 실행 시도 (2초만)
    print("\n🚀 main.py 직접 실행 시도 (2초)...")
    try:
        # 프로젝트 루트로 이동
        original_dir = os.getcwd()
        os.chdir(project_root)
        
        # main.py 실행
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print("main.py 프로세스 시작됨...")
        
        # 2초 대기
        time.sleep(2)
        
        if process.poll() is None:
            print("✅ main.py가 정상적으로 실행 중입니다!")
            process.terminate()
            process.wait(timeout=1)
        else:
            stdout, stderr = process.communicate()
            print(f"❌ main.py 실행 실패 (종료 코드: {process.returncode})")
            if stderr:
                print(f"오류 메시지:\n{stderr[:500]}...")
            if stdout:
                print(f"출력 메시지:\n{stdout[:500]}...")
        
        # 원래 디렉토리로 복귀
        os.chdir(original_dir)
                
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
    
    print("\n" + "=" * 40)
    print("🎉 기본 테스트 완료!")

if __name__ == "__main__":
    main() 