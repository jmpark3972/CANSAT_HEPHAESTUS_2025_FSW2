# CANSAT FSW 메모리 최적화 가이드

## 개요
이 문서는 CANSAT FSW의 메모리 사용량을 줄이기 위한 최적화 방법들을 설명합니다.

## 현재 메모리 사용량 문제점

### 1. 로깅 시스템
- **문제**: 각 센서마다 로그 파일을 계속 열어두고 있음
- **해결**: 버퍼링 시스템 도입으로 메모리 사용량 감소

### 2. 데이터 구조
- **문제**: 큰 리스트와 딕셔너리가 메모리를 많이 사용
- **해결**: 크기 제한과 링 버퍼 사용

### 3. 가비지 컬렉션
- **문제**: 자동 가비지 컬렉션이 부족
- **해결**: 주기적인 메모리 정리 시스템

## 구현된 최적화 기능

### 1. 메모리 최적화 모듈 (`lib/memory_optimizer.py`)
```python
# 자동 메모리 정리
memory_optimizer.start_memory_optimization()

# 긴급 정리
memory_optimizer.emergency_cleanup_memory()
```

### 2. 로깅 시스템 최적화 (`lib/logging.py`)
- 버퍼링 시스템으로 메모리 사용량 감소
- 5초마다 자동 플러시
- 버퍼 크기 제한 (100개 항목)

### 3. 데이터 구조 최적화 (`lib/data_optimizer.py`)
```python
# 센서 데이터 최적화
optimized_data = optimize_sensor_data(raw_data)

# 링 버퍼 생성
ring_buffer = create_ring_buffer(max_size=100)
```

### 4. 센서 로깅 최적화
- 각 센서 모듈에서 버퍼링 시스템 사용
- 파일 핸들을 계속 열어두지 않음
- 주기적 플러시로 메모리 사용량 감소

## 추가 최적화 권장사항

### 1. 코드 최적화
```python
# 나쁜 예: 큰 리스트 유지
data_history = []

# 좋은 예: 크기 제한
from collections import deque
data_history = deque(maxlen=50)
```

### 2. 변수 관리
```python
# 나쁜 예: 전역 변수 남용
global_variable = []

# 좋은 예: 지역 변수 사용
def process_data():
    local_data = []
    # 처리 후 자동 정리
```

### 3. 메모리 모니터링
```python
# 메모리 사용량 확인
from lib.memory_optimizer import get_memory_optimizer
optimizer = get_memory_optimizer()
usage = optimizer.get_memory_usage()
print(f"메모리 사용량: {usage['percent']:.1f}%")
```

## 성능 모니터링

### 1. 메모리 사용량 추적
- 30초마다 자동 모니터링
- 75% 이상 시 긴급 정리
- 60% 이상 시 일반 정리

### 2. 가비지 컬렉션 통계
```python
stats = optimizer.get_optimization_stats()
print(f"수집된 객체: {stats['objects_collected']}")
```

## 설정 옵션

### 1. 메모리 임계값 조정
```python
# lib/memory_optimizer.py에서 조정 가능
self.cleanup_interval = 30  # 정리 간격 (초)
self.max_cache_size = 50    # 캐시 최대 크기
```

### 2. 로깅 버퍼 크기 조정
```python
# lib/logging.py에서 조정 가능
self.max_buffer_size = 100  # 로그 버퍼 크기
self.flush_interval = 5     # 플러시 간격 (초)
```

## 모니터링 명령어

### 1. 메모리 사용량 확인
```bash
# 실시간 메모리 사용량
python3 -c "from lib.memory_optimizer import get_memory_optimizer; print(get_memory_optimizer().get_memory_usage())"
```

### 2. 최적화 통계 확인
```bash
# 최적화 통계
python3 -c "from lib.memory_optimizer import get_memory_optimizer; print(get_memory_optimizer().get_optimization_stats())"
```

## 예상 효과

### 1. 메모리 사용량 감소
- 기존: 80-90% 메모리 사용
- 최적화 후: 50-70% 메모리 사용

### 2. 안정성 향상
- 메모리 부족으로 인한 크래시 방지
- 자동 복구 기능

### 3. 성능 향상
- 가비지 컬렉션 오버헤드 감소
- 더 빠른 데이터 처리

## 주의사항

### 1. 데이터 손실 방지
- 버퍼링 시스템으로 인한 데이터 손실 가능성
- 중요 데이터는 즉시 플러시

### 2. 성능 균형
- 과도한 최적화로 인한 성능 저하 방지
- 적절한 임계값 설정

### 3. 디버깅
- 최적화로 인한 문제 발생 시 로그 확인
- 메모리 사용량 모니터링 유지

## 결론

이 최적화 시스템을 통해 CANSAT FSW의 메모리 사용량을 크게 줄일 수 있습니다. 
정기적인 모니터링과 적절한 설정 조정으로 안정적인 운영이 가능합니다. 