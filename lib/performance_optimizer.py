#!/usr/bin/env python3
"""
CANSAT FSW 성능 최적화 시스템
메모리 사용량, CPU 사용량, I/O 성능 최적화
"""

import os
import sys
import time
import threading
import gc
import psutil
import cProfile
import pstats
import io
from typing import Dict, List, Optional, Callable, Any
from functools import wraps, lru_cache
from collections import deque
import weakref

from lib import logging, config

class PerformanceOptimizer:
    """성능 최적화 관리자"""
    
    def __init__(self):
        self.profiling = False
        self.profiler = None
        self.optimization_enabled = True
        self.cache_enabled = True
        self.memory_pool_enabled = True
        
        # 성능 메트릭
        self.metrics = {
            'function_calls': {},
            'execution_times': {},
            'memory_usage': deque(maxlen=100),
            'cpu_usage': deque(maxlen=100),
            'cache_hits': 0,
            'cache_misses': 0
        }
        
        # 메모리 풀
        self.memory_pool = {}
        self.pool_lock = threading.Lock()
        
        # 캐시
        self.cache = {}
        self.cache_lock = threading.Lock()
        self.cache_ttl = 300  # 5분
        
        logging.log("성능 최적화 시스템 초기화 완료")
    
    def start_profiling(self, output_file: str = "performance_profile.prof"):
        """프로파일링 시작"""
        if self.profiling:
            return
        
        self.profiling = True
        self.profiler = cProfile.Profile()
        self.profiler.enable()
        logging.log(f"프로파일링 시작: {output_file}")
    
    def stop_profiling(self, output_file: str = "performance_profile.prof"):
        """프로파일링 중지 및 결과 저장"""
        if not self.profiling or not self.profiler:
            return
        
        self.profiler.disable()
        self.profiling = False
        
        # 프로파일 결과 저장
        try:
            self.profiler.dump_stats(output_file)
            
            # 통계 출력
            s = io.StringIO()
            stats = pstats.Stats(self.profiler, stream=s).sort_stats('cumulative')
            stats.print_stats(20)  # 상위 20개 함수
            
            logging.log("프로파일링 결과:")
            logging.log(s.getvalue())
            
        except Exception as e:
            logging.log(f"프로파일링 결과 저장 오류: {e}", "ERROR")
        
        self.profiler = None
    
    def monitor_performance(self, func: Callable) -> Callable:
        """함수 성능 모니터링 데코레이터"""
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            start_memory = psutil.Process().memory_info().rss
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                end_memory = psutil.Process().memory_info().rss
                
                execution_time = end_time - start_time
                memory_delta = end_memory - start_memory
                
                # 메트릭 업데이트
                func_name = func.__name__
                if func_name not in self.metrics['execution_times']:
                    self.metrics['execution_times'][func_name] = []
                
                self.metrics['execution_times'][func_name].append(execution_time)
                if len(self.metrics['execution_times'][func_name]) > 100:
                    self.metrics['execution_times'][func_name].pop(0)
                
                # 성능 경고
                if execution_time > 1.0:  # 1초 이상
                    logging.log(f"성능 경고: {func_name} 실행 시간 {execution_time:.3f}초", "WARNING")
                
                if memory_delta > 1024 * 1024:  # 1MB 이상
                    logging.log(f"메모리 경고: {func_name} 메모리 사용량 {memory_delta / 1024 / 1024:.2f}MB", "WARNING")
        
        return wrapper
    
    def cache_result(self, ttl: int = None) -> Callable:
        """함수 결과 캐싱 데코레이터"""
        if not self.cache_enabled:
            return lambda func: func
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 캐시 키 생성
                cache_key = f"{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                with self.cache_lock:
                    # 캐시에서 검색
                    if cache_key in self.cache:
                        cache_entry = self.cache[cache_key]
                        if time.time() - cache_entry['timestamp'] < (ttl or self.cache_ttl):
                            self.metrics['cache_hits'] += 1
                            return cache_entry['result']
                        else:
                            # 만료된 캐시 삭제
                            del self.cache[cache_key]
                    
                    self.metrics['cache_misses'] += 1
                
                # 함수 실행
                result = func(*args, **kwargs)
                
                # 결과 캐싱
                with self.cache_lock:
                    self.cache[cache_key] = {
                        'result': result,
                        'timestamp': time.time()
                    }
                    
                    # 캐시 크기 제한
                    if len(self.cache) > 1000:
                        # 가장 오래된 항목 삭제
                        oldest_key = min(self.cache.keys(), 
                                       key=lambda k: self.cache[k]['timestamp'])
                        del self.cache[oldest_key]
                
                return result
            
            return wrapper
        return decorator
    
    def memory_pool(self, pool_name: str):
        """메모리 풀 데코레이터"""
        if not self.memory_pool_enabled:
            return lambda func: func
        
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.pool_lock:
                    if pool_name not in self.memory_pool:
                        self.memory_pool[pool_name] = []
                    
                    # 풀에서 객체 재사용
                    if self.memory_pool[pool_name]:
                        obj = self.memory_pool[pool_name].pop()
                        try:
                            return func(*args, **kwargs, _pooled_obj=obj)
                        except Exception:
                            # 재사용 실패 시 새로 생성
                            return func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def return_to_pool(self, pool_name: str, obj: Any):
        """객체를 메모리 풀로 반환"""
        if not self.memory_pool_enabled:
            return
        
        with self.pool_lock:
            if pool_name not in self.memory_pool:
                self.memory_pool[pool_name] = []
            
            # 풀 크기 제한
            if len(self.memory_pool[pool_name]) < 10:
                self.memory_pool[pool_name].append(obj)
    
    def optimize_memory(self):
        """메모리 최적화"""
        try:
            # 가비지 컬렉션 실행
            collected = gc.collect()
            
            # 캐시 정리
            with self.cache_lock:
                current_time = time.time()
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if current_time - entry['timestamp'] > self.cache_ttl
                ]
                for key in expired_keys:
                    del self.cache[key]
            
            # 메모리 풀 정리
            with self.pool_lock:
                for pool_name in list(self.memory_pool.keys()):
                    if len(self.memory_pool[pool_name]) > 5:
                        # 풀 크기 제한
                        self.memory_pool[pool_name] = self.memory_pool[pool_name][:5]
            
            if collected > 0:
                logging.log(f"메모리 최적화 완료: {collected}개 객체 수집")
            
        except Exception as e:
            logging.log(f"메모리 최적화 오류: {e}", "ERROR")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 반환"""
        metrics = self.metrics.copy()
        
        # 평균 실행 시간 계산
        for func_name, times in metrics['execution_times'].items():
            if times:
                metrics['execution_times'][func_name] = {
                    'avg': sum(times) / len(times),
                    'min': min(times),
                    'max': max(times),
                    'count': len(times)
                }
        
        # 캐시 히트율 계산
        total_cache_access = metrics['cache_hits'] + metrics['cache_misses']
        if total_cache_access > 0:
            metrics['cache_hit_rate'] = metrics['cache_hits'] / total_cache_access
        else:
            metrics['cache_hit_rate'] = 0.0
        
        return metrics
    
    def generate_performance_report(self) -> str:
        """성능 리포트 생성"""
        try:
            metrics = self.get_performance_metrics()
            
            report = []
            report.append("=" * 60)
            report.append("🚀 성능 최적화 리포트")
            report.append("=" * 60)
            report.append(f"생성 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            report.append("")
            
            # 캐시 통계
            report.append("📊 캐시 통계")
            report.append(f"  캐시 히트: {metrics['cache_hits']}회")
            report.append(f"  캐시 미스: {metrics['cache_misses']}회")
            report.append(f"  히트율: {metrics['cache_hit_rate']:.2%}")
            report.append(f"  활성 캐시: {len(self.cache)}개")
            report.append("")
            
            # 함수 성능
            report.append("⚡ 함수 성능 (상위 10개)")
            sorted_functions = sorted(
                metrics['execution_times'].items(),
                key=lambda x: x[1]['avg'] if isinstance(x[1], dict) else 0,
                reverse=True
            )[:10]
            
            for func_name, perf_data in sorted_functions:
                if isinstance(perf_data, dict):
                    report.append(f"  {func_name}:")
                    report.append(f"    평균: {perf_data['avg']:.3f}초")
                    report.append(f"    최소: {perf_data['min']:.3f}초")
                    report.append(f"    최대: {perf_data['max']:.3f}초")
                    report.append(f"    호출: {perf_data['count']}회")
            
            report.append("")
            
            # 메모리 풀 상태
            report.append("💾 메모리 풀 상태")
            for pool_name, pool_objects in self.memory_pool.items():
                report.append(f"  {pool_name}: {len(pool_objects)}개 객체")
            
            report.append("")
            report.append("=" * 60)
            
            return "\n".join(report)
            
        except Exception as e:
            logging.log(f"성능 리포트 생성 오류: {e}", "ERROR")
            return f"성능 리포트 생성 실패: {e}"
    
    def clear_cache(self):
        """캐시 정리"""
        with self.cache_lock:
            self.cache.clear()
        logging.log("캐시 정리 완료")
    
    def clear_memory_pool(self):
        """메모리 풀 정리"""
        with self.pool_lock:
            self.memory_pool.clear()
        logging.log("메모리 풀 정리 완료")

# 전역 성능 최적화 인스턴스
_performance_optimizer = None

def get_performance_optimizer() -> PerformanceOptimizer:
    """전역 성능 최적화 인스턴스 가져오기"""
    global _performance_optimizer
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
    return _performance_optimizer

def monitor_performance(func: Callable) -> Callable:
    """함수 성능 모니터링 (편의 함수)"""
    return get_performance_optimizer().monitor_performance(func)

def cache_result(ttl: int = None) -> Callable:
    """함수 결과 캐싱 (편의 함수)"""
    return get_performance_optimizer().cache_result(ttl)

def memory_pool(pool_name: str) -> Callable:
    """메모리 풀 (편의 함수)"""
    return get_performance_optimizer().memory_pool(pool_name)

def optimize_memory():
    """메모리 최적화 (편의 함수)"""
    get_performance_optimizer().optimize_memory()

def get_performance_metrics() -> Dict[str, Any]:
    """성능 메트릭 가져오기 (편의 함수)"""
    return get_performance_optimizer().get_performance_metrics()

# 성능 최적화 유틸리티 함수들
@lru_cache(maxsize=128)
def cached_calculation(value: float) -> float:
    """캐시된 계산 예시"""
    time.sleep(0.1)  # 시뮬레이션된 계산 시간
    return value * 2

@monitor_performance
def monitored_function(data: List[int]) -> int:
    """모니터링된 함수 예시"""
    time.sleep(0.05)  # 시뮬레이션된 처리 시간
    return sum(data)

@cache_result(ttl=60)
def cached_api_call(endpoint: str) -> Dict[str, Any]:
    """캐시된 API 호출 예시"""
    time.sleep(0.1)  # 시뮬레이션된 네트워크 지연
    return {"endpoint": endpoint, "data": "cached_result"}

if __name__ == "__main__":
    # 성능 최적화 테스트
    optimizer = get_performance_optimizer()
    
    print("성능 최적화 시스템 테스트 시작")
    
    # 캐시 테스트
    print("\n1. 캐시 테스트")
    start_time = time.time()
    result1 = cached_calculation(10.0)
    result2 = cached_calculation(10.0)  # 캐시된 결과
    end_time = time.time()
    print(f"결과: {result1}, {result2}")
    print(f"실행 시간: {end_time - start_time:.3f}초")
    
    # 모니터링 테스트
    print("\n2. 모니터링 테스트")
    monitored_function([1, 2, 3, 4, 5])
    
    # 메트릭 출력
    print("\n3. 성능 메트릭")
    metrics = get_performance_metrics()
    print(f"캐시 히트율: {metrics['cache_hit_rate']:.2%}")
    
    # 리포트 생성
    print("\n4. 성능 리포트")
    report = optimizer.generate_performance_report()
    print(report)
    
    print("\n성능 최적화 시스템 테스트 완료") 