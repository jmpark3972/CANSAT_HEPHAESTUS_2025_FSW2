#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - force_kill 모듈 테스트
"""

import os
import sys
import time
import subprocess

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_force_kill_module():
    """force_kill 모듈 테스트"""
    print("🔍 CANSAT HEPHAESTUS 2025 FSW2 - force_kill 모듈 테스트")
    print("=" * 60)
    
    try:
        # 1. 모듈 import 테스트
        print("\n1️⃣ 모듈 import 테스트")
        from lib.force_kill import (
            find_cansat_processes,
            kill_process_safely,
            kill_cansat_processes,
            kill_pigpiod,
            cleanup_files,
            check_system_status,
            force_kill_all
        )
        print("✅ force_kill 모듈 import 성공")
        
        # 2. 프로세스 검색 테스트
        print("\n2️⃣ 프로세스 검색 테스트")
        processes = find_cansat_processes()
        print(f"발견된 CANSAT 프로세스: {len(processes)}개")
        
        if processes:
            print("실행 중인 CANSAT 프로세스들:")
            for proc in processes:
                print(f"  - PID {proc['pid']}: {proc['cmdline']}")
        else:
            print("✅ 실행 중인 CANSAT 프로세스가 없습니다")
        
        # 3. 시스템 상태 확인 테스트
        print("\n3️⃣ 시스템 상태 확인 테스트")
        check_system_status()
        
        # 4. 파일 정리 테스트
        print("\n4️⃣ 파일 정리 테스트")
        cleanup_files()
        
        # 5. 사용법 안내
        print("\n5️⃣ 사용법 안내")
        print("강제 종료 실행:")
        print("  python3 lib/force_kill.py")
        print("  또는")
        print("  python3 -c \"from lib.force_kill import force_kill_all; force_kill_all()\"")
        print()
        print("시스템 상태 확인:")
        print("  python3 lib/force_kill.py --check")
        print("  또는")
        print("  python3 -c \"from lib.force_kill import check_system_status; check_system_status()\"")
        
        print("\n🎉 force_kill 모듈 테스트 완료!")
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    success = test_force_kill_module()
    
    if success:
        print("\n✅ 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n❌ 일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit(main()) 