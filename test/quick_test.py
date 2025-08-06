#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 빠른 테스트 스크립트
핵심 테스트만 빠르게 실행합니다.
"""

import os
import sys
import subprocess
import time
from datetime import datetime

def run_quick_test():
    """핵심 테스트만 빠르게 실행"""
    print("🚀 CANSAT HEPHAESTUS 2025 FSW2 - 빠른 테스트")
    print("=" * 50)
    
    # 핵심 테스트 목록
    core_tests = [
        "path_test.py",           # Python 경로 및 import 테스트
        "minimal_fsw_test.py",    # 최소한의 FSW 테스트
        "test_config.py",         # 설정 테스트
        "test_appargs.py",        # 앱 인수 테스트
        "test_tmp007_direct.py",  # TMP007 센서 테스트
    ]
    
    test_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(test_dir)
    
    print(f"📁 테스트 디렉토리: {test_dir}")
    print(f"📁 프로젝트 루트: {project_root}")
    print(f"📋 실행할 테스트: {len(core_tests)}개")
    
    results = {}
    start_time = time.time()
    
    for i, test_file in enumerate(core_tests, 1):
        test_path = os.path.join(test_dir, test_file)
        
        if not os.path.exists(test_path):
            print(f"⚠️ {test_file} - 파일이 없음")
            results[test_file] = {'success': False, 'error': 'File not found'}
            continue
        
        print(f"\n[{i}/{len(core_tests)}] 🚀 {test_file}")
        print("-" * 40)
        
        try:
            # 프로젝트 루트로 작업 디렉토리 변경
            original_dir = os.getcwd()
            os.chdir(project_root)
            
            # 테스트 실행
            test_start = time.time()
            result = subprocess.run(
                [sys.executable, test_path],
                capture_output=True,
                text=True,
                timeout=30  # 30초 타임아웃
            )
            test_duration = time.time() - test_start
            
            # 원래 디렉토리로 복귀
            os.chdir(original_dir)
            
            success = result.returncode == 0
            results[test_file] = {
                'success': success,
                'duration': test_duration,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
            
            if success:
                print(f"✅ 성공 ({test_duration:.2f}초)")
                if result.stdout.strip():
                    # 출력이 길면 요약만 표시
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 10:
                        print("출력 (요약):")
                        for line in lines[:5]:
                            print(f"  {line}")
                        print("  ...")
                        for line in lines[-5:]:
                            print(f"  {line}")
                    else:
                        print("출력:")
                        for line in lines:
                            print(f"  {line}")
            else:
                print(f"❌ 실패 (종료 코드: {result.returncode})")
                if result.stderr.strip():
                    print("오류:")
                    print(f"  {result.stderr.strip()}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ 타임아웃 (30초 초과)")
            results[test_file] = {'success': False, 'error': 'Timeout'}
        except Exception as e:
            print(f"💥 실행 오류: {e}")
            results[test_file] = {'success': False, 'error': str(e)}
    
    # 결과 요약
    total_time = time.time() - start_time
    successful = sum(1 for r in results.values() if r.get('success', False))
    failed = len(results) - successful
    
    print(f"\n{'='*50}")
    print("📊 빠른 테스트 결과 요약")
    print(f"{'='*50}")
    print(f"⏱️  총 실행 시간: {total_time:.2f}초")
    print(f"✅ 성공: {successful}개")
    print(f"❌ 실패: {failed}개")
    
    if len(results) > 0:
        success_rate = (successful / len(results)) * 100
        print(f"📈 성공률: {success_rate:.1f}%")
    
    # 상세 결과
    print(f"\n📋 상세 결과:")
    for test_file, result in results.items():
        status = "✅ 성공" if result.get('success', False) else "❌ 실패"
        duration = f"({result.get('duration', 0):.2f}초)" if 'duration' in result else ""
        error = result.get('error', '')
        
        print(f"  {status} {test_file} {duration}")
        if error:
            print(f"    오류: {error}")
    
    # 권장사항
    print(f"\n💡 권장사항:")
    if failed == 0:
        print("  🎉 모든 핵심 테스트가 성공했습니다!")
        print("  🚀 FSW를 실행해볼 준비가 되었습니다.")
    else:
        print("  🔧 실패한 테스트들을 확인하고 수정하세요.")
        print("  📝 전체 테스트를 실행하려면: python3 run_all_tests.py")
    
    print(f"\n{'='*50}")
    return failed == 0

if __name__ == "__main__":
    try:
        success = run_quick_test()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        exit(1)
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        exit(1) 