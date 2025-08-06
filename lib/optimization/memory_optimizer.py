#!/usr/bin/env python3
"""
CANSAT FSW 메모리 최적화 모듈
메모리 사용량을 줄이기 위한 다양한 최적화 기법 제공
"""

import gc
import sys
import psutil
import threading
import time
from typing import Dict, List, Any, Optional
from collections import deque
import weakref

class MemoryOptimizer:
    """메모리 최적화 클래스"""
    
    def __init__(self):
        self.optimization_enabled = True
        self.cleanup_interval = 30  # 30초마다 정리
        self.max_cache_size = 50  # 캐시 최대 크기
        self.cleanup_thread = None
        self.running = False
        
        # 메모리 사용량 히스토리 (최근 20개만 유지)
        self.memory_history = deque(maxlen=20)
        
        # 가비지 컬렉션 통계
        self.gc_stats = {
            'collections': 0,
            'objects_collected': 0,
            'last_cleanup': time.time()
        }
    
    def start_optimization(self):
        """메모리 최적화 시작"""
        if self.running:
            return
        
        self.running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print("[MemoryOptimizer] 메모리 최적화 시작")
    
    def stop_optimization(self):
        """메모리 최적화 중지"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        print("[MemoryOptimizer] 메모리 최적화 중지")
    
    def _cleanup_loop(self):
        """정기적인 메모리 정리 루프"""
        while self.running:
            try:
                # 메모리 사용량 기록
                memory_percent = psutil.virtual_memory().percent
                self.memory_history.append(memory_percent)
                
                # 메모리 사용량이 높으면 즉시 정리
                if memory_percent > 75:
                    self.emergency_cleanup()
                elif memory_percent > 60:
                    self.normal_cleanup()
                
                time.sleep(self.cleanup_interval)
                
            except Exception as e:
                print(f"[MemoryOptimizer] 정리 루프 오류: {e}")
                time.sleep(self.cleanup_interval)
    
    def normal_cleanup(self):
        """일반적인 메모리 정리"""
        try:
            # 가비지 컬렉션 실행
            collected = gc.collect()
            self.gc_stats['collections'] += 1
            self.gc_stats['objects_collected'] += collected
            
            if collected > 0:
                print(f"[MemoryOptimizer] 일반 정리: {collected}개 객체 수집")
                
        except Exception as e:
            print(f"[MemoryOptimizer] 일반 정리 오류: {e}")
    
    def emergency_cleanup(self):
        """긴급 메모리 정리"""
        try:
            # 강제 가비지 컬렉션
            collected = gc.collect()
            self.gc_stats['collections'] += 1
            self.gc_stats['objects_collected'] += collected
            
            # 메모리 히스토리 정리
            if len(self.memory_history) > 10:
                # 최근 10개만 유지
                temp_list = list(self.memory_history)[-10:]
                self.memory_history.clear()
                self.memory_history.extend(temp_list)
            
            print(f"[MemoryOptimizer] 긴급 정리: {collected}개 객체 수집, 메모리 히스토리 정리")
            
        except Exception as e:
            print(f"[MemoryOptimizer] 긴급 정리 오류: {e}")
    
    def optimize_data_structures(self, data_dict: Dict[str, Any]) -> Dict[str, Any]:
        """데이터 구조 최적화"""
        optimized = {}
        
        for key, value in data_dict.items():
            if isinstance(value, list) and len(value) > 100:
                # 큰 리스트는 최근 항목만 유지
                optimized[key] = value[-50:]  # 최근 50개만
            elif isinstance(value, dict) and len(value) > 50:
                # 큰 딕셔너리는 중요 키만 유지
                important_keys = ['status', 'error', 'last_update', 'value']
                optimized[key] = {k: v for k, v in value.items() if k in important_keys}
            else:
                optimized[key] = value
        
        return optimized
    
    def get_memory_usage(self) -> Dict[str, float]:
        """현재 메모리 사용량 정보"""
        try:
            memory = psutil.virtual_memory()
            return {
                'percent': memory.percent,
                'available_mb': memory.available / (1024 * 1024),
                'used_mb': memory.used / (1024 * 1024),
                'total_mb': memory.total / (1024 * 1024)
            }
        except Exception as e:
            print(f"[MemoryOptimizer] 메모리 사용량 조회 오류: {e}")
            return {}
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """최적화 통계"""
        return {
            'gc_collections': self.gc_stats['collections'],
            'objects_collected': self.gc_stats['objects_collected'],
            'memory_history': list(self.memory_history),
            'last_cleanup': self.gc_stats['last_cleanup']
        }

# 전역 인스턴스
_memory_optimizer = None

def get_memory_optimizer() -> MemoryOptimizer:
    """메모리 최적화 인스턴스 반환"""
    global _memory_optimizer
    if _memory_optimizer is None:
        _memory_optimizer = MemoryOptimizer()
    return _memory_optimizer

def start_memory_optimization():
    """메모리 최적화 시작"""
    optimizer = get_memory_optimizer()
    optimizer.start_optimization()

def stop_memory_optimization():
    """메모리 최적화 중지"""
    optimizer = get_memory_optimizer()
    optimizer.stop_optimization()

def cleanup_memory():
    """즉시 메모리 정리"""
    optimizer = get_memory_optimizer()
    optimizer.normal_cleanup()

def emergency_cleanup_memory():
    """긴급 메모리 정리"""
    optimizer = get_memory_optimizer()
    optimizer.emergency_cleanup() 