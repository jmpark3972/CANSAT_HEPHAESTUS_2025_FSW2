#!/usr/bin/env python3
"""
CANSAT FSW 리소스 관리 시스템
메모리 누수 방지 및 리소스 모니터링
"""

import os
import sys
import time
import threading
import psutil
import gc
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path

from lib import logging, config

class ResourceManager:
    """리소스 관리자 클래스"""
    
    def __init__(self):
        self.monitoring = False
        self.monitor_thread = None
        self.resource_handlers: Dict[str, Callable] = {}
        self.memory_threshold = config.get_config("SYSTEM.MAX_MEMORY_USAGE", 80)
        self.disk_threshold = config.get_config("SYSTEM.MAX_DISK_USAGE", 90)
        self.check_interval = config.get_config("SYSTEM.PROCESS_CHECK_INTERVAL", 1.0)
        
        # 리소스 사용량 히스토리
        self.memory_history: List[float] = []
        self.disk_history: List[float] = []
        self.cpu_history: List[float] = []
        self.max_history_size = 100
        
        # 경고 카운터
        self.memory_warnings = 0
        self.disk_warnings = 0
        self.max_warnings = 5
        
        logging.log("리소스 관리자 초기화 완료")
    
    def start_monitoring(self):
        """리소스 모니터링 시작"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_resources, daemon=True)
        self.monitor_thread.start()
        logging.log("리소스 모니터링 시작")
    
    def stop_monitoring(self):
        """리소스 모니터링 중지"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        logging.log("리소스 모니터링 중지")
    
    def _monitor_resources(self):
        """리소스 모니터링 스레드"""
        while self.monitoring:
            try:
                # 메모리 사용량 체크
                memory_percent = psutil.virtual_memory().percent
                self.memory_history.append(memory_percent)
                if len(self.memory_history) > self.max_history_size:
                    self.memory_history.pop(0)
                
                # 디스크 사용량 체크
                disk_percent = psutil.disk_usage('/').percent
                self.disk_history.append(disk_percent)
                if len(self.disk_history) > self.max_history_size:
                    self.disk_history.pop(0)
                
                # CPU 사용량 체크
                cpu_percent = psutil.cpu_percent(interval=0.1)
                self.cpu_history.append(cpu_percent)
                if len(self.cpu_history) > self.max_history_size:
                    self.cpu_history.pop(0)
                
                # 임계값 체크
                self._check_thresholds(memory_percent, disk_percent, cpu_percent)
                
                # 메모리 정리 (주기적)
                if len(self.memory_history) % 10 == 0:
                    self._cleanup_memory()
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logging.log(f"리소스 모니터링 오류: {e}", "ERROR")
                time.sleep(self.check_interval)
    
    def _check_thresholds(self, memory_percent: float, disk_percent: float, cpu_percent: float):
        """임계값 체크 및 경고"""
        # 메모리 임계값 체크
        if memory_percent > self.memory_threshold:
            self.memory_warnings += 1
            logging.log(f"메모리 사용량 경고: {memory_percent:.1f}% (임계값: {self.memory_threshold}%)", "WARNING")
            
            if self.memory_warnings >= self.max_warnings:
                logging.log("메모리 사용량이 지속적으로 높습니다. 긴급 정리 실행", "ERROR")
                self._emergency_memory_cleanup()
                self.memory_warnings = 0
        
        # 디스크 임계값 체크
        if disk_percent > self.disk_threshold:
            self.disk_warnings += 1
            logging.log(f"디스크 사용량 경고: {disk_percent:.1f}% (임계값: {self.disk_threshold}%)", "WARNING")
            
            if self.disk_warnings >= self.max_warnings:
                logging.log("디스크 사용량이 지속적으로 높습니다. 로그 파일 정리 실행", "ERROR")
                self._cleanup_log_files()
                self.disk_warnings = 0
    
    def _cleanup_memory(self):
        """메모리 정리"""
        try:
            # 가비지 컬렉션 실행
            collected = gc.collect()
            
            # 메모리 히스토리 정리
            if len(self.memory_history) > self.max_history_size // 2:
                self.memory_history = self.memory_history[-self.max_history_size // 2:]
            
            if len(self.disk_history) > self.max_history_size // 2:
                self.disk_history = self.disk_history[-self.max_history_size // 2:]
            
            if len(self.cpu_history) > self.max_history_size // 2:
                self.cpu_history = self.cpu_history[-self.max_history_size // 2:]
            
            if collected > 0:
                logging.log(f"메모리 정리 완료: {collected}개 객체 수집")
                
        except Exception as e:
            logging.log(f"메모리 정리 오류: {e}", "ERROR")
    
    def _emergency_memory_cleanup(self):
        """긴급 메모리 정리"""
        try:
            # 강제 가비지 컬렉션
            gc.collect()
            
            # 히스토리 완전 정리
            self.memory_history.clear()
            self.disk_history.clear()
            self.cpu_history.clear()
            
            # 시스템 메모리 정리 시도
            if hasattr(psutil, 'pids'):
                # 불필요한 프로세스 정리 (시스템 프로세스는 제외)
                for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                    try:
                        if proc.info['memory_percent'] > 10:  # 10% 이상 메모리 사용
                            proc_name = proc.info['name']
                            if proc_name and 'python' not in proc_name.lower():
                                logging.log(f"높은 메모리 사용 프로세스 발견: {proc_name} ({proc.info['memory_percent']:.1f}%)", "WARNING")
                    except Exception as e:
                        logging.log(f"프로세스 정보 조회 오류: {e}", "WARNING")
            
            logging.log("긴급 메모리 정리 완료")
            
        except Exception as e:
            logging.log(f"긴급 메모리 정리 오류: {e}", "ERROR")
    
    def _cleanup_log_files(self):
        """로그 파일 정리"""
        try:
            log_dir = config.get_config("LOGGING.PRIMARY_LOG_DIR", "logs")
            retention_days = config.get_config("LOGGING.LOG_RETENTION_DAYS", 7)
            current_time = time.time()
            
            if os.path.exists(log_dir):
                for filename in os.listdir(log_dir):
                    filepath = os.path.join(log_dir, filename)
                    if os.path.isfile(filepath):
                        file_age = current_time - os.path.getmtime(filepath)
                        if file_age > retention_days * 24 * 3600:  # 일을 초로 변환
                            try:
                                os.remove(filepath)
                                logging.log(f"오래된 로그 파일 삭제: {filename}")
                            except Exception as e:
                                logging.log(f"로그 파일 삭제 실패: {filename} - {e}", "ERROR")
            
            logging.log("로그 파일 정리 완료")
            
        except Exception as e:
            logging.log(f"로그 파일 정리 오류: {e}", "ERROR")
    
    def get_resource_usage(self) -> Dict[str, float]:
        """현재 리소스 사용량 반환"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu = psutil.cpu_percent(interval=0.1)
            
            return {
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'cpu_percent': cpu
            }
        except Exception as e:
            logging.log(f"리소스 사용량 조회 오류: {e}", "ERROR")
            return {}
    
    def get_resource_history(self) -> Dict[str, List[float]]:
        """리소스 사용량 히스토리 반환"""
        return {
            'memory': self.memory_history.copy(),
            'disk': self.disk_history.copy(),
            'cpu': self.cpu_history.copy()
        }
    
    def register_resource_handler(self, resource_type: str, handler: Callable):
        """리소스 핸들러 등록"""
        self.resource_handlers[resource_type] = handler
        logging.log(f"리소스 핸들러 등록: {resource_type}")
    
    def generate_resource_report(self) -> str:
        """리소스 사용량 리포트 생성"""
        try:
            usage = self.get_resource_usage()
            history = self.get_resource_history()
            
            report = []
            report.append("=" * 60)
            report.append("📊 리소스 사용량 리포트")
            report.append("=" * 60)
            report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 현재 사용량
            report.append("🔍 현재 사용량")
            report.append(f"  메모리: {usage.get('memory_percent', 0):.1f}% ({usage.get('memory_available_mb', 0):.1f}MB 사용 가능)")
            report.append(f"  디스크: {usage.get('disk_percent', 0):.1f}% ({usage.get('disk_free_gb', 0):.1f}GB 사용 가능)")
            report.append(f"  CPU: {usage.get('cpu_percent', 0):.1f}%")
            report.append("")
            
            # 평균 사용량
            if history['memory']:
                avg_memory = sum(history['memory']) / len(history['memory'])
                report.append(f"📈 평균 메모리 사용량: {avg_memory:.1f}%")
            
            if history['disk']:
                avg_disk = sum(history['disk']) / len(history['disk'])
                report.append(f"📈 평균 디스크 사용량: {avg_disk:.1f}%")
            
            if history['cpu']:
                avg_cpu = sum(history['cpu']) / len(history['cpu'])
                report.append(f"📈 평균 CPU 사용량: {avg_cpu:.1f}%")
            
            report.append("")
            
            # 경고 정보
            report.append("⚠️ 경고 정보")
            report.append(f"  메모리 경고: {self.memory_warnings}회")
            report.append(f"  디스크 경고: {self.disk_warnings}회")
            report.append(f"  메모리 임계값: {self.memory_threshold}%")
            report.append(f"  디스크 임계값: {self.disk_threshold}%")
            report.append("")
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logging.log(f"리소스 리포트 생성 오류: {e}", "ERROR")
            return f"리소스 리포트 생성 실패: {e}"

# 전역 리소스 관리자 인스턴스
_resource_manager = None

def get_resource_manager() -> ResourceManager:
    """전역 리소스 관리자 인스턴스 가져오기"""
    global _resource_manager
    if _resource_manager is None:
        _resource_manager = ResourceManager()
    return _resource_manager

def start_resource_monitoring():
    """리소스 모니터링 시작 (편의 함수)"""
    get_resource_manager().start_monitoring()

def stop_resource_monitoring():
    """리소스 모니터링 중지 (편의 함수)"""
    get_resource_manager().stop_monitoring()

def get_current_resource_usage() -> Dict[str, float]:
    """현재 리소스 사용량 가져오기 (편의 함수)"""
    return get_resource_manager().get_resource_usage()

def cleanup_memory():
    """메모리 정리 (편의 함수)"""
    get_resource_manager()._cleanup_memory()

if __name__ == "__main__":
    # 리소스 관리자 테스트
    manager = get_resource_manager()
    manager.start_monitoring()
    
    try:
        print("리소스 모니터링 테스트 시작 (10초간)...")
        time.sleep(10)
        
        # 리소스 사용량 출력
        usage = manager.get_resource_usage()
        print(f"메모리 사용량: {usage.get('memory_percent', 0):.1f}%")
        print(f"디스크 사용량: {usage.get('disk_percent', 0):.1f}%")
        print(f"CPU 사용량: {usage.get('cpu_percent', 0):.1f}%")
        
        # 리포트 생성
        report = manager.generate_resource_report()
        print("\n" + report)
        
    finally:
        manager.stop_monitoring()
        print("리소스 모니터링 테스트 완료") 