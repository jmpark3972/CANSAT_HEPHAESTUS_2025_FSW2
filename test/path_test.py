#!/usr/bin/env python3
"""
Python 경로 및 import 테스트
"""

import os
import sys

def main():
    print("🔍 Python 경로 및 import 테스트")
    print("=" * 40)
    
    # 1. 현재 위치 확인
    current_dir = os.getcwd()
    print(f"현재 디렉토리: {current_dir}")
    
    # 2. Python 경로 확인
    print(f"\n🐍 Python 실행 파일: {sys.executable}")
    print(f"Python 버전: {sys.version}")
    
    # 3. sys.path 확인
    print(f"\n📁 Python 경로 (sys.path):")
    for i, path in enumerate(sys.path):
        print(f"  {i}: {path}")
    
    # 4. 프로젝트 루트 찾기
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    print(f"\n📂 프로젝트 루트: {project_root}")
    
    # 5. 프로젝트 루트를 Python 경로에 추가
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
        print(f"✅ 프로젝트 루트를 Python 경로에 추가: {project_root}")
    else:
        print(f"✅ 프로젝트 루트가 이미 Python 경로에 있음: {project_root}")
    
    # 6. 기본 모듈 import 테스트
    print(f"\n📦 기본 모듈 import 테스트:")
    
    basic_modules = [
        'os',
        'sys',
        'time',
        'json',
        'multiprocessing',
        'threading'
    ]
    
    for module_name in basic_modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name} - {e}")
    
    # 7. lib 모듈 import 테스트
    print(f"\n📦 lib 모듈 import 테스트:")
    
    lib_modules = [
        'lib.config',
        'lib.appargs',
        'lib.msgstructure',
        'lib.logging',
        'lib.types'
    ]
    
    for module_name in lib_modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name} - {e}")
        except Exception as e:
            print(f"  ❌ {module_name} - {e}")
    
    # 8. 앱 모듈 import 테스트
    print(f"\n📦 앱 모듈 import 테스트:")
    
    app_modules = [
        'comm.commapp',
        'flight_logic.flightlogicapp',
        'hk.hkapp',
        'barometer.barometerapp',
        'imu.imuapp'
    ]
    
    for module_name in app_modules:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name}")
        except ImportError as e:
            print(f"  ❌ {module_name} - {e}")
        except Exception as e:
            print(f"  ❌ {module_name} - {e}")
    
    # 9. 파일 존재 확인
    print(f"\n📁 중요 파일 존재 확인:")
    
    important_files = [
        'main.py',
        'lib/config.py',
        'lib/appargs.py',
        'lib/msgstructure.py',
        'lib/logging.py',
        'comm/commapp.py',
        'flight_logic/flightlogicapp.py'
    ]
    
    for file_path in important_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - 파일이 없음")
    
    print(f"\n" + "=" * 40)
    print("🎉 경로 테스트 완료!")

if __name__ == "__main__":
    main() 