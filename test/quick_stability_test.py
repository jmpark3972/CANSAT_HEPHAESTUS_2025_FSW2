#!/usr/bin/env python3
"""
CANSAT FSW 빠른 안정성 테스트
핵심 시나리오만 빠르게 테스트하여 시스템 안정성 확인
"""

import os
import sys
import time
import subprocess
import psutil
import signal
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def log_event(message: str):
    """이벤트 로깅"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def cleanup_processes():
    """기존 프로세스 정리"""
    log_event("기존 프로세스 정리 시작")
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    if 'main.py' in cmdline:
                        log_event(f"기존 main.py 프로세스 종료 (PID: {proc.info['pid']})")
                        proc.terminate()
                        proc.wait(timeout=5)
            except:
                pass
    except Exception as e:
        log_event(f"프로세스 정리 오류: {e}")

def start_fsw():
    """FSW 시작"""
    log_event("FSW 시작")
    
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 시작 대기
        time.sleep(5)
        
        if process.poll() is None:
            log_event(f"FSW 시작 성공 (PID: {process.pid})")
            return process
        else:
            log_event("FSW 시작 실패")
            return None
            
    except Exception as e:
        log_event(f"FSW 시작 오류: {e}")
        return None

def check_app_status():
    """앱 상태 확인"""
    app_status = {}
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    
                    # 주요 앱들 확인
                    apps = ["FlightLogicApp", "CommApp", "HKApp", "BarometerApp", "ImuApp"]
                    for app in apps:
                        if app.lower() in cmdline.lower():
                            app_status[app] = proc.is_running()
                            break
            except:
                pass
    except Exception as e:
        log_event(f"앱 상태 확인 오류: {e}")
    
    return app_status

def kill_random_app():
    """랜덤 앱 강제 종료"""
    log_event("랜덤 앱 강제 종료 시뮬레이션")
    
    try:
        non_critical_apps = ["BarometerApp", "ImuApp", "ThermoApp", "ThermisApp"]
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if proc.info['name'] == 'python' and proc.info['cmdline']:
                    cmdline = ' '.join(proc.info['cmdline'])
                    
                    for app in non_critical_apps:
                        if app.lower() in cmdline.lower():
                            log_event(f"{app} 강제 종료 (PID: {proc.info['pid']})")
                            proc.kill()
                            return True
            except:
                pass
    except Exception as e:
        log_event(f"앱 강제 종료 오류: {e}")
    
    return False

def test_scenario_1_normal_operation():
    """시나리오 1: 정상 작동"""
    log_event("=== 시나리오 1: 정상 작동 테스트 ===")
    
    # FSW 시작
    process = start_fsw()
    if not process:
        return False
    
    # 30초간 정상 작동 확인
    log_event("30초간 정상 작동 확인")
    start_time = time.time()
    
    while time.time() - start_time < 30:
        app_status = check_app_status()
        
        # 핵심 앱들 상태 확인
        critical_apps = ["FlightLogicApp", "CommApp", "HKApp"]
        for app in critical_apps:
            if app in app_status and not app_status[app]:
                log_event(f"❌ 핵심 앱 실패: {app}")
                return False
        
        time.sleep(2)
    
    log_event("✅ 정상 작동 테스트 통과")
    return True

def test_scenario_2_app_crash():
    """시나리오 2: 앱 크래시"""
    log_event("=== 시나리오 2: 앱 크래시 테스트 ===")
    
    # FSW 시작
    process = start_fsw()
    if not process:
        return False
    
    # 10초 대기
    time.sleep(10)
    
    # 랜덤 앱 강제 종료
    if kill_random_app():
        log_event("앱 강제 종료 완료")
        
        # 20초간 시스템 안정성 확인
        log_event("20초간 시스템 안정성 확인")
        start_time = time.time()
        
        while time.time() - start_time < 20:
            app_status = check_app_status()
            
            # 핵심 앱들 상태 확인
            critical_apps = ["FlightLogicApp", "CommApp", "HKApp"]
            for app in critical_apps:
                if app in app_status and not app_status[app]:
                    log_event(f"❌ 핵심 앱 실패: {app}")
                    return False
            
            time.sleep(2)
        
        log_event("✅ 앱 크래시 테스트 통과")
        return True
    else:
        log_event("❌ 앱 강제 종료 실패")
        return False

def test_scenario_3_forced_termination():
    """시나리오 3: 강제 종료"""
    log_event("=== 시나리오 3: 강제 종료 테스트 ===")
    
    # FSW 시작
    process = start_fsw()
    if not process:
        return False
    
    # 10초 대기
    time.sleep(10)
    
    # 강제 종료
    log_event("FSW 강제 종료")
    process.kill()
    
    # 종료 확인
    time.sleep(3)
    if process.poll() is not None:
        log_event("✅ 강제 종료 테스트 통과")
        return True
    else:
        log_event("❌ 강제 종료 실패")
        return False

def run_quick_test():
    """빠른 테스트 실행"""
    print("🚀 CANSAT FSW 빠른 안정성 테스트 시작")
    print("핵심 시나리오 3개를 빠르게 테스트합니다.")
    print()
    
    # 로그 디렉토리 생성
    os.makedirs("logs", exist_ok=True)
    
    # 기존 프로세스 정리
    cleanup_processes()
    
    test_results = {}
    
    try:
        # 시나리오 1: 정상 작동
        test_results["정상 작동"] = test_scenario_1_normal_operation()
        time.sleep(5)
        
        # 시나리오 2: 앱 크래시
        test_results["앱 크래시"] = test_scenario_2_app_crash()
        time.sleep(5)
        
        # 시나리오 3: 강제 종료
        test_results["강제 종료"] = test_scenario_3_forced_termination()
        
    except KeyboardInterrupt:
        log_event("⚠️ 사용자에 의해 중단됨")
        cleanup_processes()
        return
    
    # 결과 출력
    print("\n" + "="*50)
    print("📊 빠른 안정성 테스트 결과")
    print("="*50)
    
    passed = 0
    for scenario, result in test_results.items():
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{scenario:15} | {status}")
        if result:
            passed += 1
    
    print("-"*50)
    print(f"총 테스트: {len(test_results)}개")
    print(f"통과: {passed}개")
    print(f"실패: {len(test_results) - passed}개")
    print(f"성공률: {(passed/len(test_results))*100:.1f}%")
    
    if passed == len(test_results):
        print("\n🎉 모든 테스트 통과! 시스템이 안정적으로 작동합니다.")
    else:
        print("\n⚠️ 일부 테스트 실패. 시스템 안정성을 개선해야 합니다.")
    
    print("\n자세한 테스트는 test_system_stability.py를 실행하세요.")

if __name__ == "__main__":
    run_quick_test() 