#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - lib 모듈들 테스트
"""

import os
import sys
import subprocess

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_force_kill_module():
    """force_kill 모듈 테스트"""
    print("🔍 force_kill 모듈 테스트")
    print("-" * 40)
    
    try:
        from lib.force_kill import (
            find_cansat_processes,
            check_system_status
        )
        
        # 프로세스 검색 테스트
        processes = find_cansat_processes()
        print(f"발견된 CANSAT 프로세스: {len(processes)}개")
        
        # 시스템 상태 확인 테스트
        check_system_status()
        
        print("✅ force_kill 모듈 테스트 성공")
        return True
        
    except Exception as e:
        print(f"❌ force_kill 모듈 테스트 실패: {e}")
        return False

def test_diagnostic_module():
    """diagnostic_script 모듈 테스트"""
    print("\n🔍 diagnostic_script 모듈 테스트")
    print("-" * 40)
    
    try:
        from lib.diagnostic_script import (
            check_system_resources,
            check_cansat_processes,
            check_gpio_access
        )
        
        # 시스템 리소스 확인
        system_ok = check_system_resources()
        print(f"시스템 리소스 상태: {'✅ 정상' if system_ok else '❌ 문제'}")
        
        # CANSAT 프로세스 확인
        processes = check_cansat_processes()
        print(f"CANSAT 프로세스: {len(processes)}개")
        
        # GPIO 접근 확인
        gpio_ok = check_gpio_access()
        print(f"GPIO 접근 상태: {'✅ 정상' if gpio_ok else '❌ 문제'}")
        
        print("✅ diagnostic_script 모듈 테스트 성공")
        return True
        
    except Exception as e:
        print(f"❌ diagnostic_script 모듈 테스트 실패: {e}")
        return False

def test_lib_convenience_functions():
    """lib 편의 함수들 테스트"""
    print("\n🔍 lib 편의 함수들 테스트")
    print("-" * 40)
    
    try:
        from lib import (
            force_kill_cansat,
            check_cansat_status,
            run_diagnostic,
            quick_diagnostic
        )
        
        print("✅ 편의 함수들 import 성공")
        
        # 빠른 진단만 실행 (전체 진단은 시간이 오래 걸림)
        print("빠른 진단 실행 중...")
        quick_diagnostic()
        
        print("✅ lib 편의 함수들 테스트 성공")
        return True
        
    except Exception as e:
        print(f"❌ lib 편의 함수들 테스트 실패: {e}")
        return False

def test_shell_scripts():
    """셸 스크립트 테스트"""
    print("\n🔍 셸 스크립트 테스트")
    print("-" * 40)
    
    scripts = [
        ('lib/initial_install.sh', '초기 설치 스크립트'),
        ('lib/update_all_modules.sh', '모듈 업데이트 스크립트'),
        ('lib/force_kill.py', '강제 종료 스크립트'),
        ('lib/diagnostic_script.py', '진단 스크립트')
    ]
    
    success_count = 0
    for script_path, description in scripts:
        if os.path.exists(script_path):
            print(f"✅ {description}: {script_path}")
            success_count += 1
        else:
            print(f"❌ {description}: {script_path} - 파일 없음")
    
    print(f"셸 스크립트 테스트: {success_count}/{len(scripts)} 성공")
    return success_count == len(scripts)

def show_usage_guide():
    """사용법 안내"""
    print("\n📚 사용법 안내")
    print("=" * 60)
    
    print("🔧 강제 종료:")
    print("  python3 lib/force_kill.py")
    print("  python3 -c \"from lib import force_kill_cansat; force_kill_cansat()\"")
    print()
    
    print("🔍 시스템 진단:")
    print("  python3 lib/diagnostic_script.py")
    print("  python3 lib/diagnostic_script.py --quick")
    print("  python3 -c \"from lib import run_diagnostic; run_diagnostic()\"")
    print()
    
    print("🚀 초기 설치:")
    print("  chmod +x lib/initial_install.sh")
    print("  ./lib/initial_install.sh")
    print()
    
    print("🔄 모듈 업데이트:")
    print("  chmod +x lib/update_all_modules.sh")
    print("  ./lib/update_all_modules.sh")
    print()
    
    print("📊 시스템 상태 확인:")
    print("  python3 lib/force_kill.py --check")
    print("  python3 -c \"from lib import check_cansat_status; check_cansat_status()\"")

def main():
    """메인 함수"""
    print("🔍 CANSAT HEPHAESTUS 2025 FSW2 - lib 모듈들 테스트")
    print("=" * 60)
    
    # 테스트 실행
    tests = [
        ("force_kill 모듈", test_force_kill_module),
        ("diagnostic_script 모듈", test_diagnostic_module),
        ("lib 편의 함수들", test_lib_convenience_functions),
        ("셸 스크립트", test_shell_scripts)
    ]
    
    passed = 0
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} 테스트 중 오류: {e}")
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("📊 테스트 결과 요약")
    print("=" * 60)
    print(f"총 테스트: {len(tests)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(tests) - passed}개")
    
    if passed == len(tests):
        print("\n🎉 모든 테스트가 성공했습니다!")
    else:
        print(f"\n⚠️ {len(tests) - passed}개 테스트가 실패했습니다.")
    
    # 사용법 안내
    show_usage_guide()
    
    return 0 if passed == len(tests) else 1

if __name__ == "__main__":
    exit(main()) 