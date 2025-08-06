#!/usr/bin/env python3
"""
Performance Monitor for CANSAT HEPHAESTUS 2025 FSW2
시스템 성능 모니터링 및 최적화
"""

import psutil
import time
import threading
import json
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from collections import deque

@dataclass
class SystemMetrics:
    """시스템 메트릭 데이터 클래스"""
    timestamp: float
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    disk_used_gb: float
    disk_free_gb: float
    network_sent_mb: float
    network_recv_mb: float
    temperature: Optional[float] = None
    process_count: int = 0
    thread_count: int = 0

@dataclass
class ProcessMetrics:
    """프로세스 메트릭 데이터 클래스"""
    pid: int
    name: str
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    status: str
    create_time: float
    num_threads: int

class PerformanceMonitor:
    """성능 모니터링 시스템"""
    
    def __init__(self, history_size: int = 1000, monitoring_interval: float = 5.0):
        self.history_size = history_size
        self.monitoring_interval = monitoring_interval
        self.monitoring_active = False
        self.monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 메트릭 히스토리
        self.system_metrics_history = deque(maxlen=history_size)
        self.process_metrics_history = deque(maxlen=history_size)
        
        # 임계값 설정
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 90.0,
            'disk_critical': 98.0,
            'temperature_warning': 70.0,
            'temperature_critical': 85.0
        }
        
        # 알림 콜백
        self.alert_callbacks: List[callable] = []
        
        # 성능 통계
        self.performance_stats = {
            'start_time': time.time(),
            'total_samples': 0,
            'alerts_triggered': 0,
            'peak_cpu': 0.0,
            'peak_memory': 0.0,
            'peak_temperature': 0.0
        }
    
    def start_monitoring(self):
        """모니터링 시작"""
        if not self.monitoring_active:
            self.monitoring_active = True
            self.monitor_thread = threading.Thread(
                target=self._monitoring_loop,
                daemon=True
            )
            self.monitor_thread.start()
            print("Performance monitoring started")
    
    def stop_monitoring(self):
        """모니터링 중지"""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        print("Performance monitoring stopped")
    
    def _monitoring_loop(self):
        """모니터링 루프"""
        while self.monitoring_active:
            try:
                # 시스템 메트릭 수집
                system_metrics = self._collect_system_metrics()
                self.system_metrics_history.append(system_metrics)
                
                # 프로세스 메트릭 수집
                process_metrics = self._collect_process_metrics()
                self.process_metrics_history.append(process_metrics)
                
                # 임계값 체크 및 알림
                self._check_thresholds(system_metrics)
                
                # 통계 업데이트
                self._update_stats(system_metrics)
                
                self.performance_stats['total_samples'] += 1
                
            except Exception as e:
                print(f"Performance monitoring error: {e}")
            
            time.sleep(self.monitoring_interval)
    
    def _collect_system_metrics(self) -> SystemMetrics:
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 메모리 정보
            memory = psutil.virtual_memory()
            
            # 디스크 정보
            disk = psutil.disk_usage('/')
            
            # 네트워크 정보
            network = psutil.net_io_counters()
            
            # 온도 정보 (Raspberry Pi)
            temperature = self._get_temperature()
            
            # 프로세스 및 스레드 수
            process_count = len(psutil.pids())
            thread_count = psutil.cpu_count() * 2  # 대략적인 추정
            
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used_mb=memory.used / (1024 * 1024),
                memory_available_mb=memory.available / (1024 * 1024),
                disk_percent=disk.percent,
                disk_used_gb=disk.used / (1024 * 1024 * 1024),
                disk_free_gb=disk.free / (1024 * 1024 * 1024),
                network_sent_mb=network.bytes_sent / (1024 * 1024),
                network_recv_mb=network.bytes_recv / (1024 * 1024),
                temperature=temperature,
                process_count=process_count,
                thread_count=thread_count
            )
        except Exception as e:
            print(f"System metrics collection error: {e}")
            return SystemMetrics(
                timestamp=time.time(),
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_available_mb=0.0,
                disk_percent=0.0,
                disk_used_gb=0.0,
                disk_free_gb=0.0,
                network_sent_mb=0.0,
                network_recv_mb=0.0
            )
    
    def _collect_process_metrics(self) -> List[ProcessMetrics]:
        """프로세스 메트릭 수집"""
        process_metrics = []
        
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 
                                           'memory_info', 'status', 'create_time', 'num_threads']):
                try:
                    info = proc.info
                    process_metrics.append(ProcessMetrics(
                        pid=info['pid'],
                        name=info['name'],
                        cpu_percent=info['cpu_percent'],
                        memory_percent=info['memory_percent'],
                        memory_mb=info['memory_info'].rss / (1024 * 1024),
                        status=info['status'],
                        create_time=info['create_time'],
                        num_threads=info['num_threads']
                    ))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Process metrics collection error: {e}")
        
        return process_metrics
    
    def _get_temperature(self) -> Optional[float]:
        """Raspberry Pi 온도 읽기"""
        try:
            with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                temp = float(f.read().strip()) / 1000.0
                return temp
        except Exception as e:
            print(f"Temperature reading error: {e}")
            return None
    
    def _check_thresholds(self, metrics: SystemMetrics):
        """임계값 체크 및 알림"""
        alerts = []
        
        # CPU 체크
        if metrics.cpu_percent >= self.thresholds['cpu_critical']:
            alerts.append(f"CRITICAL: CPU usage {metrics.cpu_percent:.1f}%")
        elif metrics.cpu_percent >= self.thresholds['cpu_warning']:
            alerts.append(f"WARNING: CPU usage {metrics.cpu_percent:.1f}%")
        
        # 메모리 체크
        if metrics.memory_percent >= self.thresholds['memory_critical']:
            alerts.append(f"CRITICAL: Memory usage {metrics.memory_percent:.1f}%")
        elif metrics.memory_percent >= self.thresholds['memory_warning']:
            alerts.append(f"WARNING: Memory usage {metrics.memory_percent:.1f}%")
        
        # 디스크 체크
        if metrics.disk_percent >= self.thresholds['disk_critical']:
            alerts.append(f"CRITICAL: Disk usage {metrics.disk_percent:.1f}%")
        elif metrics.disk_percent >= self.thresholds['disk_warning']:
            alerts.append(f"WARNING: Disk usage {metrics.disk_percent:.1f}%")
        
        # 온도 체크
        if metrics.temperature:
            if metrics.temperature >= self.thresholds['temperature_critical']:
                alerts.append(f"CRITICAL: Temperature {metrics.temperature:.1f}°C")
            elif metrics.temperature >= self.thresholds['temperature_warning']:
                alerts.append(f"WARNING: Temperature {metrics.temperature:.1f}°C")
        
        # 알림 전송
        if alerts:
            self.performance_stats['alerts_triggered'] += 1
            for alert in alerts:
                self._send_alert(alert, metrics)
    
    def _send_alert(self, alert: str, metrics: SystemMetrics):
        """알림 전송"""
        alert_data = {
            'timestamp': datetime.fromtimestamp(metrics.timestamp).isoformat(),
            'alert': alert,
            'metrics': asdict(metrics)
        }
        
        # 콜백 함수들 호출
        for callback in self.alert_callbacks:
            try:
                callback(alert_data)
            except Exception as e:
                print(f"Alert callback error: {e}")
        
        # 콘솔 출력
        print(f"🚨 {alert}")
    
    def _update_stats(self, metrics: SystemMetrics):
        """통계 업데이트"""
        self.performance_stats['peak_cpu'] = max(self.performance_stats['peak_cpu'], metrics.cpu_percent)
        self.performance_stats['peak_memory'] = max(self.performance_stats['peak_memory'], metrics.memory_percent)
        if metrics.temperature:
            self.performance_stats['peak_temperature'] = max(self.performance_stats['peak_temperature'], metrics.temperature)
    
    def add_alert_callback(self, callback: callable):
        """알림 콜백 추가"""
        self.alert_callbacks.append(callback)
    
    def get_current_metrics(self) -> Optional[SystemMetrics]:
        """현재 시스템 메트릭 반환"""
        with self._lock:
            if self.system_metrics_history:
                return self.system_metrics_history[-1]
            return None
    
    def get_metrics_history(self, count: int = 100) -> List[SystemMetrics]:
        """메트릭 히스토리 반환"""
        with self._lock:
            return list(self.system_metrics_history)[-count:]
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 보고서 생성"""
        with self._lock:
            current_metrics = self.get_current_metrics()
            
            if not current_metrics:
                return {
                    'status': 'No data available',
                    'monitoring_active': self.monitoring_active
                }
            
            # 평균값 계산
            recent_metrics = self.get_metrics_history(20)  # 최근 20개 샘플
            avg_cpu = sum(m.cpu_percent for m in recent_metrics) / len(recent_metrics)
            avg_memory = sum(m.memory_percent for m in recent_metrics) / len(recent_metrics)
            avg_temperature = sum(m.temperature or 0 for m in recent_metrics) / len(recent_metrics)
            
            return {
                'monitoring_active': self.monitoring_active,
                'current_metrics': asdict(current_metrics),
                'average_metrics': {
                    'cpu_percent': round(avg_cpu, 1),
                    'memory_percent': round(avg_memory, 1),
                    'temperature': round(avg_temperature, 1) if avg_temperature > 0 else None
                },
                'performance_stats': self.performance_stats,
                'thresholds': self.thresholds,
                'uptime_hours': (time.time() - self.performance_stats['start_time']) / 3600
            }
    
    def save_metrics_to_file(self, filename: str = None):
        """메트릭을 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"logs/performance_metrics_{timestamp}.json"
        
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        with self._lock:
            data = {
                'export_time': datetime.now().isoformat(),
                'performance_stats': self.performance_stats,
                'thresholds': self.thresholds,
                'system_metrics': [asdict(m) for m in self.system_metrics_history],
                'process_metrics': [
                    [asdict(p) for p in metrics] 
                    for metrics in self.process_metrics_history
                ]
            }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Performance metrics saved to {filename}")
        except Exception as e:
            print(f"Failed to save performance metrics: {e}")
    
    def set_thresholds(self, **kwargs):
        """임계값 설정"""
        for key, value in kwargs.items():
            if key in self.thresholds:
                self.thresholds[key] = value
    
    def get_memory_usage_by_process(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """메모리 사용량 상위 프로세스"""
        current_processes = self.process_metrics_history[-1] if self.process_metrics_history else []
        
        # 메모리 사용량으로 정렬
        sorted_processes = sorted(current_processes, key=lambda p: p.memory_mb, reverse=True)
        
        return [
            {
                'name': p.name,
                'pid': p.pid,
                'memory_mb': round(p.memory_mb, 2),
                'memory_percent': round(p.memory_percent, 1),
                'cpu_percent': round(p.cpu_percent, 1)
            }
            for p in sorted_processes[:top_n]
        ]

# 전역 성능 모니터
performance_monitor = PerformanceMonitor()

def get_performance_monitor() -> PerformanceMonitor:
    """전역 성능 모니터 반환"""
    return performance_monitor

def start_performance_monitoring():
    """성능 모니터링 시작 (편의 함수)"""
    performance_monitor.start_monitoring()

def stop_performance_monitoring():
    """성능 모니터링 중지 (편의 함수)"""
    performance_monitor.stop_monitoring()

def get_system_metrics() -> Optional[SystemMetrics]:
    """현재 시스템 메트릭 반환 (편의 함수)"""
    return performance_monitor.get_current_metrics()

def get_performance_report() -> Dict[str, Any]:
    """성능 보고서 반환 (편의 함수)"""
    return performance_monitor.get_performance_report() 