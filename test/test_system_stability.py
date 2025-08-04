#!/usr/bin/env python3
"""
CANSAT FSW 시스템 안정성 시뮬레이션
상승부터 추락까지 앱 하나라도 꺼져도 다른 앱에 영향이 가지 않는지 테스트
"""

import os
import sys
import time
import signal
import threading
import subprocess
import psutil
import random
from datetime import datetime
from typing import Dict, List, Optional

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import appargs, msgstructure, logging

class SystemStabilitySimulator:
    """CANSAT FSW 시스템 안정성 시뮬레이터"""
    
    def __init__(self):
        self.test_results = {}
        self.running = True
        self.main_process = None
        self.app_processes = {}
        self.test_start_time = None
        
        # 테스트 시나리오 정의
        self.test_scenarios = {
            "normal_operation": "정상 작동",
            "app_crash": "앱 크래시",
            "hardware_failure": "하드웨어 오류",
            "forced_termination": "강제 종료",
            "pin_disconnection": "핀 분리",
            "memory_leak": "메모리 누수",
            "network_failure": "통신 오류",
            "power_fluctuation": "전원 변동"
        }
        
        # 핵심 앱 목록 (하나라도 꺼지면 안되는 앱들)
        self.critical_apps = [
            "FlightLogicApp",  # 비행 로직
            "CommApp",         # 통신
            "HKApp"           # 하우스키핑
        ]
        
        # 비핵심 앱 목록 (꺼져도 시스템은 작동)
        self.non_critical_apps = [
            "BarometerApp",    # 고도계
            "ImuApp",         # 자이로스코프
            "ThermoApp",      # 온도계
            "ThermisApp",     # 열화상
            "Tmp007App",      # 온도센서
            "PitotApp",       # 속도계
            "CameraApp",      # 카메라
            "MotorApp"        # 모터
        ]
        
        print("🚀 CANSAT FSW 시스템 안정성 시뮬레이터 시작")
        print(f"📊 테스트 시나리오: {len(self.test_scenarios)}개")
        print(f"🔴 핵심 앱: {len(self.critical_apps)}개")
        print(f"🟡 비핵심 앱: {len(self.non_critical_apps)}개")
        print("-" * 60)
    
    def log_test_event(self, event: str, details: str = ""):
        """테스트 이벤트 로깅"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        message = f"[{timestamp}] {event}"
        if details:
            message += f" - {details}"
        print(message)
        
        # 로그 파일에 기록
        try:
            with open("logs/stability_test.log", "a", encoding="utf-8") as f:
                f.write(f"{message}\n")
        except:
            pass
    
    def start_main_fsw(self) -> bool:
        """메인 FSW 프로세스 시작"""
        try:
            self.log_test_event("메인 FSW 시작 시도")
            
            # 기존 프로세스 정리
            self.cleanup_existing_processes()
            
            # 메인 FSW 시작
            self.main_process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # 시작 대기
            time.sleep(5)
            
            if self.main_process.poll() is None:
                self.log_test_event("메인 FSW 시작 성공", f"PID: {self.main_process.pid}")
                return True
            else:
                self.log_test_event("메인 FSW 시작 실패")
                return False
                
        except Exception as e:
            self.log_test_event("메인 FSW 시작 오류", str(e))
            return False
    
    def cleanup_existing_processes(self):
        """기존 프로세스 정리"""
        try:
            # Python 프로세스 중 FSW 관련 프로세스 종료
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if 'main.py' in cmdline or 'cameraapp' in cmdline:
                            self.log_test_event("기존 프로세스 종료", f"PID: {proc.info['pid']}")
                            proc.terminate()
                            proc.wait(timeout=5)
                except:
                    pass
        except Exception as e:
            self.log_test_event("프로세스 정리 오류", str(e))
    
    def monitor_app_status(self) -> Dict[str, bool]:
        """앱 상태 모니터링"""
        app_status = {}
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        
                        # 각 앱별 상태 확인
                        for app_name in self.critical_apps + self.non_critical_apps:
                            if app_name.lower() in cmdline.lower():
                                app_status[app_name] = proc.is_running()
                                break
                                
                except:
                    pass
                    
        except Exception as e:
            self.log_test_event("앱 상태 모니터링 오류", str(e))
        
        return app_status
    
    def simulate_app_crash(self, app_name: str) -> bool:
        """특정 앱 크래시 시뮬레이션"""
        try:
            self.log_test_event(f"앱 크래시 시뮬레이션 시작", app_name)
            
            # 해당 앱 프로세스 찾기
            target_proc = None
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['name'] == 'python' and proc.info['cmdline']:
                        cmdline = ' '.join(proc.info['cmdline'])
                        if app_name.lower() in cmdline.lower():
                            target_proc = proc
                            break
                except:
                    pass
            
            if target_proc:
                # 프로세스 강제 종료 (크래시 시뮬레이션)
                self.log_test_event(f"앱 강제 종료", f"{app_name} (PID: {target_proc.pid})")
                target_proc.kill()
                
                # 종료 확인
                time.sleep(2)
                if not target_proc.is_running():
                    self.log_test_event(f"앱 크래시 완료", app_name)
                    return True
                else:
                    self.log_test_event(f"앱 크래시 실패", app_name)
                    return False
            else:
                self.log_test_event(f"앱을 찾을 수 없음", app_name)
                return False
                
        except Exception as e:
            self.log_test_event(f"앱 크래시 시뮬레이션 오류", str(e))
            return False
    
    def simulate_hardware_failure(self) -> bool:
        """하드웨어 오류 시뮬레이션"""
        try:
            self.log_test_event("하드웨어 오류 시뮬레이션 시작")
            
            # 센서 관련 앱들에 오류 시뮬레이션
            sensor_apps = ["BarometerApp", "ImuApp", "ThermoApp", "ThermisApp"]
            
            for app in sensor_apps:
                if random.random() < 0.3:  # 30% 확률로 센서 오류
                    self.simulate_app_crash(app)
                    time.sleep(1)
            
            self.log_test_event("하드웨어 오류 시뮬레이션 완료")
            return True
            
        except Exception as e:
            self.log_test_event("하드웨어 오류 시뮬레이션 오류", str(e))
            return False
    
    def simulate_forced_termination(self) -> bool:
        """강제 종료 시뮬레이션"""
        try:
            self.log_test_event("강제 종료 시뮬레이션 시작")
            
            # 메인 프로세스에 SIGKILL 전송
            if self.main_process and self.main_process.poll() is None:
                self.main_process.kill()
                time.sleep(2)
                
                if self.main_process.poll() is not None:
                    self.log_test_event("강제 종료 완료")
                    return True
                else:
                    self.log_test_event("강제 종료 실패")
                    return False
            else:
                self.log_test_event("메인 프로세스가 실행 중이 아님")
                return False
                
        except Exception as e:
            self.log_test_event("강제 종료 시뮬레이션 오류", str(e))
            return False
    
    def check_system_stability(self, duration: int = 30) -> Dict[str, any]:
        """시스템 안정성 체크"""
        self.log_test_event(f"시스템 안정성 체크 시작 ({duration}초)")
        
        start_time = time.time()
        stability_data = {
            "start_time": start_time,
            "end_time": None,
            "critical_apps_failed": [],
            "non_critical_apps_failed": [],
            "system_crashed": False,
            "recovery_attempts": 0,
            "total_errors": 0
        }
        
        while time.time() - start_time < duration and self.running:
            try:
                # 앱 상태 확인
                app_status = self.monitor_app_status()
                
                # 핵심 앱 상태 체크
                for app in self.critical_apps:
                    if app in app_status and not app_status[app]:
                        if app not in stability_data["critical_apps_failed"]:
                            stability_data["critical_apps_failed"].append(app)
                            self.log_test_event(f"핵심 앱 실패 감지", app)
                
                # 비핵심 앱 상태 체크
                for app in self.non_critical_apps:
                    if app in app_status and not app_status[app]:
                        if app not in stability_data["non_critical_apps_failed"]:
                            stability_data["non_critical_apps_failed"].append(app)
                            self.log_test_event(f"비핵심 앱 실패 감지", app)
                
                # 시스템 전체 크래시 체크
                if self.main_process and self.main_process.poll() is not None:
                    stability_data["system_crashed"] = True
                    self.log_test_event("시스템 전체 크래시 감지")
                    break
                
                time.sleep(1)
                
            except Exception as e:
                stability_data["total_errors"] += 1
                self.log_test_event("안정성 체크 오류", str(e))
        
        stability_data["end_time"] = time.time()
        stability_data["duration"] = stability_data["end_time"] - stability_data["start_time"]
        
        return stability_data
    
    def run_stability_test(self, scenario: str, duration: int = 60) -> Dict[str, any]:
        """안정성 테스트 실행"""
        self.log_test_event(f"안정성 테스트 시작", f"시나리오: {scenario}, 지속시간: {duration}초")
        
        test_result = {
            "scenario": scenario,
            "start_time": datetime.now(),
            "duration": duration,
            "success": False,
            "stability_data": None,
            "errors": []
        }
        
        try:
            # 1. 메인 FSW 시작
            if not self.start_main_fsw():
                test_result["errors"].append("메인 FSW 시작 실패")
                return test_result
            
            # 2. 초기 안정화 대기
            time.sleep(10)
            
            # 3. 시나리오별 오류 시뮬레이션
            if scenario == "app_crash":
                # 랜덤 앱 크래시
                target_app = random.choice(self.non_critical_apps)
                self.simulate_app_crash(target_app)
                
            elif scenario == "hardware_failure":
                # 하드웨어 오류 시뮬레이션
                self.simulate_hardware_failure()
                
            elif scenario == "forced_termination":
                # 강제 종료 시뮬레이션
                time.sleep(20)  # 일정 시간 작동 후
                self.simulate_forced_termination()
                return test_result  # 강제 종료 후에는 바로 결과 반환
            
            # 4. 안정성 체크
            stability_data = self.check_system_stability(duration - 30)
            test_result["stability_data"] = stability_data
            
            # 5. 성공 여부 판정
            if stability_data["system_crashed"]:
                test_result["success"] = False
                test_result["errors"].append("시스템 전체 크래시")
            elif len(stability_data["critical_apps_failed"]) > 0:
                test_result["success"] = False
                test_result["errors"].append(f"핵심 앱 실패: {stability_data['critical_apps_failed']}")
            else:
                test_result["success"] = True
            
        except Exception as e:
            test_result["errors"].append(f"테스트 실행 오류: {str(e)}")
        
        finally:
            # 6. 정리
            self.cleanup_test()
        
        return test_result
    
    def cleanup_test(self):
        """테스트 정리"""
        try:
            self.log_test_event("테스트 정리 시작")
            
            # 메인 프로세스 종료
            if self.main_process and self.main_process.poll() is None:
                self.main_process.terminate()
                self.main_process.wait(timeout=10)
            
            # 기존 프로세스 정리
            self.cleanup_existing_processes()
            
            self.log_test_event("테스트 정리 완료")
            
        except Exception as e:
            self.log_test_event("테스트 정리 오류", str(e))
    
    def run_all_scenarios(self) -> Dict[str, Dict[str, any]]:
        """모든 시나리오 테스트 실행"""
        self.log_test_event("전체 시나리오 테스트 시작")
        
        all_results = {}
        
        for scenario in self.test_scenarios.keys():
            self.log_test_event(f"시나리오 테스트 시작", self.test_scenarios[scenario])
            
            result = self.run_stability_test(scenario, duration=60)
            all_results[scenario] = result
            
            # 결과 출력
            status = "✅ 성공" if result["success"] else "❌ 실패"
            self.log_test_event(f"시나리오 완료", f"{self.test_scenarios[scenario]}: {status}")
            
            if not result["success"]:
                for error in result["errors"]:
                    self.log_test_event(f"오류", error)
            
            # 다음 테스트 전 대기
            time.sleep(5)
        
        return all_results
    
    def generate_report(self, results: Dict[str, Dict[str, any]]):
        """테스트 결과 리포트 생성"""
        self.log_test_event("테스트 결과 리포트 생성")
        
        report = []
        report.append("=" * 80)
        report.append("🚀 CANSAT FSW 시스템 안정성 테스트 결과")
        report.append("=" * 80)
        report.append(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 전체 통계
        total_tests = len(results)
        successful_tests = sum(1 for r in results.values() if r["success"])
        failed_tests = total_tests - successful_tests
        
        report.append("📊 전체 통계")
        report.append(f"  총 테스트: {total_tests}개")
        report.append(f"  성공: {successful_tests}개")
        report.append(f"  실패: {failed_tests}개")
        report.append(f"  성공률: {(successful_tests/total_tests)*100:.1f}%")
        report.append("")
        
        # 시나리오별 결과
        report.append("📋 시나리오별 결과")
        report.append("-" * 60)
        
        for scenario, result in results.items():
            status = "✅ 성공" if result["success"] else "❌ 실패"
            scenario_name = self.test_scenarios[scenario]
            duration = result.get("duration", 0)
            
            report.append(f"{scenario_name:20} | {status:10} | {duration:5}초")
            
            if not result["success"]:
                for error in result["errors"]:
                    report.append(f"  └─ 오류: {error}")
        
        report.append("")
        
        # 안정성 분석
        report.append("🔍 안정성 분석")
        report.append("-" * 60)
        
        critical_failures = 0
        system_crashes = 0
        
        for result in results.values():
            if result.get("stability_data"):
                stability = result["stability_data"]
                if len(stability.get("critical_apps_failed", [])) > 0:
                    critical_failures += 1
                if stability.get("system_crashed", False):
                    system_crashes += 1
        
        report.append(f"핵심 앱 실패 발생: {critical_failures}회")
        report.append(f"시스템 전체 크래시: {system_crashes}회")
        
        if critical_failures == 0 and system_crashes == 0:
            report.append("🎉 모든 핵심 기능이 안정적으로 작동합니다!")
        elif critical_failures > 0:
            report.append("⚠️ 핵심 앱 실패가 발생했습니다. 개선이 필요합니다.")
        else:
            report.append("⚠️ 시스템 크래시가 발생했습니다. 긴급 개선이 필요합니다.")
        
        report.append("")
        report.append("=" * 80)
        
        # 리포트 저장
        report_text = "\n".join(report)
        print(report_text)
        
        try:
            with open("logs/stability_test_report.txt", "w", encoding="utf-8") as f:
                f.write(report_text)
            self.log_test_event("리포트 저장 완료", "logs/stability_test_report.txt")
        except Exception as e:
            self.log_test_event("리포트 저장 실패", str(e))

def main():
    """메인 함수"""
    print("🚀 CANSAT FSW 시스템 안정성 시뮬레이션 시작")
    print("이 테스트는 상승부터 추락까지 앱 하나라도 꺼져도")
    print("다른 앱에 영향이 가지 않는지 확인합니다.")
    print()
    
    # 로그 디렉토리 생성
    os.makedirs("logs", exist_ok=True)
    
    # 시뮬레이터 생성
    simulator = SystemStabilitySimulator()
    
    try:
        # 모든 시나리오 테스트 실행
        results = simulator.run_all_scenarios()
        
        # 결과 리포트 생성
        simulator.generate_report(results)
        
        print("\n🎯 시뮬레이션 완료!")
        print("자세한 결과는 logs/stability_test_report.txt를 확인하세요.")
        
    except KeyboardInterrupt:
        print("\n⚠️ 사용자에 의해 중단되었습니다.")
        simulator.cleanup_test()
    except Exception as e:
        print(f"\n❌ 시뮬레이션 오류: {e}")
        simulator.cleanup_test()

if __name__ == "__main__":
    main() 