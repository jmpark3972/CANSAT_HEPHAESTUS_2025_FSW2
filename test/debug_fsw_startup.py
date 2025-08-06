#!/usr/bin/env python3
"""
CANSAT FSW 시작 문제 진단 스크립트
main.py가 왜 시작되지 않는지 확인
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def log_event(message: str):
    """이벤트 로깅"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def check_environment():
    """환경 확인"""
    log_event("=== 환경 확인 ===")
    
    # 현재 디렉토리
    current_dir = os.getcwd()
    log_event(f"현재 디렉토리: {current_dir}")
    
    # 프로젝트 루트 찾기
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    log_event(f"프로젝트 루트: {project_root}")
    
    # main.py 존재 확인
    main_py_path = os.path.join(project_root, "main.py")
    if os.path.exists(main_py_path):
        log_event(f"✅ main.py 발견: {main_py_path}")
    else:
        log_event(f"❌ main.py 없음: {main_py_path}")
        return False
    
    # Python 경로 확인
    python_path = sys.executable
    log_event(f"Python 경로: {python_path}")
    
    # 가상환경 확인
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        log_event("✅ 가상환경 활성화됨")
    else:
        log_event("⚠️ 가상환경이 활성화되지 않음")
    
    return True

def check_dependencies():
    """의존성 확인"""
    log_event("=== 의존성 확인 ===")
    
    required_modules = [
        'multiprocessing',
        'threading',
        'time',
        'json',
        'signal',
        'psutil'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            log_event(f"✅ {module}")
        except ImportError:
            log_event(f"❌ {module} - 누락")
            missing_modules.append(module)
    
    if missing_modules:
        log_event(f"⚠️ 누락된 모듈: {missing_modules}")
        return False
    
    return True

def test_simple_import():
    """간단한 import 테스트"""
    log_event("=== Import 테스트 ===")
    
    try:
        # 프로젝트 루트를 Python 경로에 추가
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, project_root)
        
        # 주요 모듈 import 테스트
        modules_to_test = [
            'lib.config',
            'lib.appargs',
            'lib.msgstructure',
            'lib.logging'
        ]
        
        for module_name in modules_to_test:
            try:
                __import__(module_name)
                log_event(f"✅ {module_name}")
            except ImportError as e:
                log_event(f"❌ {module_name} - {e}")
                return False
        
        return True
        
    except Exception as e:
        log_event(f"❌ Import 테스트 실패: {e}")
        return False

def test_main_py_syntax():
    """main.py 문법 검사"""
    log_event("=== main.py 문법 검사 ===")
    
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_py_path = os.path.join(project_root, "main.py")
        
        # Python 문법 검사
        result = subprocess.run(
            [sys.executable, '-m', 'py_compile', main_py_path],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            log_event("✅ main.py 문법 검사 통과")
            return True
        else:
            log_event(f"❌ main.py 문법 오류: {result.stderr}")
            return False
            
    except Exception as e:
        log_event(f"❌ 문법 검사 실패: {e}")
        return False

def test_main_py_execution():
    """main.py 실행 테스트"""
    log_event("=== main.py 실행 테스트 ===")
    
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        main_py_path = os.path.join(project_root, "main.py")
        
        # 5초 타임아웃으로 실행
        process = subprocess.Popen(
            [sys.executable, main_py_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=project_root
        )
        
        # 5초 대기
        time.sleep(5)
        
        if process.poll() is None:
            log_event("✅ main.py 실행 성공 (프로세스 실행 중)")
            process.terminate()
            process.wait(timeout=3)
            return True
        else:
            stdout, stderr = process.communicate()
            log_event(f"❌ main.py 실행 실패 - 종료 코드: {process.returncode}")
            if stderr:
                log_event(f"오류: {stderr[:300]}...")
            if stdout:
                log_event(f"출력: {stdout[:300]}...")
            return False
            
    except Exception as e:
        log_event(f"❌ 실행 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🔍 CANSAT FSW 시작 문제 진단")
    print("=" * 50)
    
    tests = [
        ("환경 확인", check_environment),
        ("의존성 확인", check_dependencies),
        ("Import 테스트", test_simple_import),
        ("문법 검사", test_main_py_syntax),
        ("실행 테스트", test_main_py_execution)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{test_name} 중...")
        try:
            results[test_name] = test_func()
        except Exception as e:
            log_event(f"❌ {test_name} 테스트 중 오류: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("📊 진단 결과")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:15} | {status}")
        if result:
            passed += 1
    
    print("-" * 50)
    print(f"총 테스트: {len(results)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(results) - passed}개")
    
    if passed == len(results):
        print("\n🎉 모든 테스트 통과! FSW가 정상적으로 시작될 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트 실패. FSW 시작에 문제가 있습니다.")
        print("\n💡 해결 방법:")
        print("1. 가상환경이 활성화되어 있는지 확인")
        print("2. 필요한 패키지가 설치되어 있는지 확인")
        print("3. main.py 파일의 문법 오류 확인")
        print("4. 하드웨어 연결 상태 확인")

if __name__ == "__main__":
    main() 