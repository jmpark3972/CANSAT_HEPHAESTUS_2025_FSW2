#!/usr/bin/env python3
"""
CANSAT FSW 데이터 구조 최적화 모듈
메모리 효율적인 데이터 구조 및 캐시 관리
"""

import gc
import sys
from typing import Dict, List, Any, Optional, Tuple
from collections import deque
import weakref
import time

class DataOptimizer:
    """데이터 구조 최적화 클래스"""
    
    def __init__(self):
        self.cache = {}
        self.max_cache_size = 100
        self.cleanup_threshold = 80
        
    def optimize_sensor_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """센서 데이터 최적화"""
        optimized = {}
        
        for key, value in data.items():
            if isinstance(value, float):
                # 부동소수점 정밀도 줄이기
                optimized[key] = round(value, 2)
            elif isinstance(value, list) and len(value) > 50:
                # 큰 리스트는 최근 항목만 유지
                optimized[key] = value[-20:]  # 최근 20개만
            elif isinstance(value, dict) and len(value) > 30:
                # 큰 딕셔너리는 중요 키만 유지
                important_keys = ['value', 'status', 'error', 'timestamp']
                optimized[key] = {k: v for k, v in value.items() if k in important_keys}
            else:
                optimized[key] = value
        
        return optimized
    
    def create_ring_buffer(self, max_size: int = 100) -> deque:
        """링 버퍼 생성 (자동 크기 제한)"""
        return deque(maxlen=max_size)
    
    def optimize_list(self, data_list: List[Any], max_size: int = 50) -> List[Any]:
        """리스트 최적화 (크기 제한)"""
        if len(data_list) > max_size:
            return data_list[-max_size:]  # 최근 항목만 유지
        return data_list
    
    def cache_data(self, key: str, value: Any, max_age: int = 300):
        """데이터 캐싱 (메모리 효율적)"""
        if len(self.cache) >= self.max_cache_size:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'max_age': max_age
        }
    
    def get_cached_data(self, key: str) -> Optional[Any]:
        """캐시된 데이터 조회"""
        if key in self.cache:
            cache_entry = self.cache[key]
            if time.time() - cache_entry['timestamp'] < cache_entry['max_age']:
                return cache_entry['value']
            else:
                # 만료된 데이터 제거
                del self.cache[key]
        return None
    
    def cleanup_cache(self):
        """캐시 정리"""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self.cache.items():
            if current_time - entry['timestamp'] > entry['max_age']:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
        
        if expired_keys:
            print(f"[DataOptimizer] {len(expired_keys)}개 만료된 캐시 항목 제거")
    
    def optimize_string(self, text: str, max_length: int = 1000) -> str:
        """문자열 최적화"""
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text
    
    def create_weak_cache(self) -> Dict[str, Any]:
        """약한 참조 캐시 생성 (가비지 컬렉션 대상)"""
        return weakref.WeakValueDictionary()

# 전역 인스턴스
_data_optimizer = None

def get_data_optimizer() -> DataOptimizer:
    """데이터 최적화 인스턴스 반환"""
    global _data_optimizer
    if _data_optimizer is None:
        _data_optimizer = DataOptimizer()
    return _data_optimizer

def optimize_sensor_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """센서 데이터 최적화 (편의 함수)"""
    optimizer = get_data_optimizer()
    return optimizer.optimize_sensor_data(data)

def create_ring_buffer(max_size: int = 100) -> deque:
    """링 버퍼 생성 (편의 함수)"""
    optimizer = get_data_optimizer()
    return optimizer.create_ring_buffer(max_size)

def cleanup_data_cache():
    """데이터 캐시 정리 (편의 함수)"""
    optimizer = get_data_optimizer()
    optimizer.cleanup_cache()

def optimize_data_structure(data: Any) -> Any:
    """데이터 구조 최적화 (편의 함수)"""
    optimizer = get_data_optimizer()
    
    if isinstance(data, dict):
        return optimizer.optimize_sensor_data(data)
    elif isinstance(data, list):
        return optimizer.optimize_list(data)
    elif isinstance(data, str):
        return optimizer.optimize_string(data)
    else:
        return data 