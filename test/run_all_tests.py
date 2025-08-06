#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 통합 테스트 스크립트
모든 테스트 파일을 한 번에 실행하고 결과를 요약합니다.
"""

import os
import sys
import subprocess
import time
import glob
from datetime import datetime

class TestRunner:
    def __init__(self):
        self.test_dir = os.path.dirname(os.path.abspath(__file__))
        self.project_root = os.path.dirname(self.test_dir)
        self.results = {}
        self.start_time = None
        self.end_time = None
        
    def get_test_files(self):
        """테스트 파일 목록 가져오기"""
        test_files = []
        
        # test_*.py 파일들 찾기
        pattern = os.path.join(self.test_dir, "test_*.py")
        for file_path in glob.glob(pattern):
            filename = os.path.basename(file_path)
            if filename != "run_all_tests.py":  # 자기 자신 제외
                test_files.append(filename)
        
        # 특별한 테스트 파일들 추가
        special_tests = [
            "quick_stability_test.py",
            "test_system_stability.py",
            "path_test.py",
            "minimal_fsw_test.py",
            "basic_main_test.py",
            "import_test.py"
        ]
        
        for test in special_tests:
            test_path = os.path.join(self.test_dir, test)
            if os.path.exists(test_path) and test not in test_files:
                test_files.append(test)
        
        return sorted(test_files)
    
    def run_single_test(self, test_file):
        """단일 테스트 실행"""
        test_path = os.path.join(self.test_dir, test_file)
        
        print(f"\n{'='*60}")
        print(f"🚀 테스트 실행: {test_file}")
        print(f"{'='*60}")
        
        try:
            # 프로젝트 루트로 작업 디렉토리 변경
            original_dir = os.getcwd()
            os.chdir(self.project_root)
            
            # 테스트 실행
            start_time = time.time()
            result = subprocess.run(
                [sys.executable, test_path],
                capture_output=True,
                text=True,
                timeout=60  # 60초 타임아웃
            )
            end_time = time.time()
            
            # 원래 디렉토리로 복귀
            os.chdir(original_dir)
            
            # 결과 저장
            self.results[test_file] = {
                'success': result.returncode == 0,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'duration': end_time - start_time,
                'timeout': False
            }
            
            # 결과 출력
            if result.returncode == 0:
                print(f"✅ {test_file} - 성공 ({self.results[test_file]['duration']:.2f}초)")
                if result.stdout.strip():
                    print("출력:")
                    print(result.stdout.strip())
            else:
                print(f"❌ {test_file} - 실패 (종료 코드: {result.returncode})")
                if result.stderr.strip():
                    print("오류:")
                    print(result.stderr.strip())
                if result.stdout.strip():
                    print("출력:")
                    print(result.stdout.strip())
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {test_file} - 타임아웃 (60초 초과)")
            self.results[test_file] = {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': 'Timeout after 60 seconds',
                'duration': 60,
                'timeout': True
            }
            
        except Exception as e:
            print(f"💥 {test_file} - 실행 오류: {e}")
            self.results[test_file] = {
                'success': False,
                'returncode': -1,
                'stdout': '',
                'stderr': str(e),
                'duration': 0,
                'timeout': False
            }
    
    def run_all_tests(self):
        """모든 테스트 실행"""
        print("🚀 CANSAT HEPHAESTUS 2025 FSW2 - 통합 테스트 시작")
        print(f"📅 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 테스트 디렉토리: {self.test_dir}")
        print(f"📁 프로젝트 루트: {self.project_root}")
        
        self.start_time = time.time()
        
        # 테스트 파일 목록 가져오기
        test_files = self.get_test_files()
        
        print(f"\n📋 발견된 테스트 파일: {len(test_files)}개")
        for i, test_file in enumerate(test_files, 1):
            print(f"  {i:2d}. {test_file}")
        
        print(f"\n🎯 테스트 실행 시작...")
        
        # 각 테스트 실행
        for test_file in test_files:
            self.run_single_test(test_file)
        
        self.end_time = time.time()
        self.print_summary()
    
    def print_summary(self):
        """테스트 결과 요약 출력"""
        total_time = self.end_time - self.start_time
        total_tests = len(self.results)
        successful_tests = sum(1 for result in self.results.values() if result['success'])
        failed_tests = total_tests - successful_tests
        timeout_tests = sum(1 for result in self.results.values() if result['timeout'])
        
        print(f"\n{'='*80}")
        print("📊 통합 테스트 결과 요약")
        print(f"{'='*80}")
        print(f"📅 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"⏱️  총 실행 시간: {total_time:.2f}초")
        print(f"📋 총 테스트: {total_tests}개")
        print(f"✅ 성공: {successful_tests}개")
        print(f"❌ 실패: {failed_tests}개")
        print(f"⏰ 타임아웃: {timeout_tests}개")
        
        if total_tests > 0:
            success_rate = (successful_tests / total_tests) * 100
            print(f"📈 성공률: {success_rate:.1f}%")
        
        # 성공한 테스트 목록
        if successful_tests > 0:
            print(f"\n✅ 성공한 테스트 ({successful_tests}개):")
            for test_file, result in self.results.items():
                if result['success']:
                    print(f"  ✓ {test_file} ({result['duration']:.2f}초)")
        
        # 실패한 테스트 목록
        if failed_tests > 0:
            print(f"\n❌ 실패한 테스트 ({failed_tests}개):")
            for test_file, result in self.results.items():
                if not result['success']:
                    status = "타임아웃" if result['timeout'] else f"종료코드: {result['returncode']}"
                    print(f"  ✗ {test_file} - {status}")
                    if result['stderr'].strip():
                        print(f"    오류: {result['stderr'].strip()}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        if failed_tests == 0:
            print("  🎉 모든 테스트가 성공했습니다!")
        else:
            print("  🔧 실패한 테스트들을 개별적으로 확인해보세요.")
            print("  📝 자세한 오류 내용은 위의 오류 메시지를 참고하세요.")
        
        if timeout_tests > 0:
            print("  ⏰ 타임아웃된 테스트는 더 긴 시간이 필요할 수 있습니다.")
        
        print(f"\n{'='*80}")
    
    def save_results(self, filename="test_results.txt"):
        """테스트 결과를 파일로 저장"""
        results_path = os.path.join(self.test_dir, filename)
        
        with open(results_path, 'w', encoding='utf-8') as f:
            f.write("CANSAT HEPHAESTUS 2025 FSW2 - 테스트 결과\n")
            f.write("=" * 50 + "\n")
            f.write(f"실행 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"총 실행 시간: {self.end_time - self.start_time:.2f}초\n\n")
            
            for test_file, result in self.results.items():
                f.write(f"테스트: {test_file}\n")
                f.write(f"결과: {'성공' if result['success'] else '실패'}\n")
                f.write(f"실행 시간: {result['duration']:.2f}초\n")
                if result['stderr']:
                    f.write(f"오류: {result['stderr']}\n")
                if result['stdout']:
                    f.write(f"출력: {result['stdout']}\n")
                f.write("-" * 30 + "\n")
        
        print(f"📄 테스트 결과가 {results_path}에 저장되었습니다.")

def main():
    """메인 함수"""
    runner = TestRunner()
    
    try:
        runner.run_all_tests()
        runner.save_results()
        
        # 전체 성공 여부에 따른 종료 코드
        failed_count = sum(1 for result in runner.results.values() if not result['success'])
        return 0 if failed_count == 0 else 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️ 사용자에 의해 중단되었습니다.")
        return 1
    except Exception as e:
        print(f"\n💥 예상치 못한 오류: {e}")
        return 1

if __name__ == "__main__":
    exit(main()) 