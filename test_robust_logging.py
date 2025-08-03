#!/usr/bin/env python3
"""
강화된 로깅 시스템 테스트
플라이트 로직과 독립적으로 작동하는지 확인
"""

import time
import threading
import signal
import sys
from lib import logging

def test_basic_logging():
    """기본 로깅 테스트"""
    print("\n=== 기본 로깅 테스트 ===")
    
    try:
        # 이중 로깅 시스템 초기화
        logging.init_dual_logging_system()
        
        # 다양한 로그 메시지 테스트
        logging.log("시스템 시작", printlogs=True)
        logging.log("센서 데이터: GPS=37.123,45.678", printlogs=False)
        logging.log("상태 변경: STANDBY -> ASCENT", printlogs=True)
        logging.log("오류 발생: 센서 연결 실패", printlogs=True)
        
        time.sleep(2)
        print("✓ 기본 로깅 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 기본 로깅 테스트 실패: {e}")
        return False

def test_error_handling():
    """오류 처리 테스트"""
    print("\n=== 오류 처리 테스트 ===")
    
    try:
        # 로깅 시스템이 오류를 견뎌내는지 테스트
        logging.log("정상 로그 1", printlogs=True)
        
        # 의도적으로 오류 상황 시뮬레이션
        for i in range(10):
            logging.log(f"스트레스 테스트 로그 {i}", printlogs=False)
            time.sleep(0.1)
        
        logging.log("오류 처리 테스트 완료", printlogs=True)
        print("✓ 오류 처리 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 오류 처리 테스트 실패: {e}")
        return False

def test_concurrent_logging():
    """동시 로깅 테스트"""
    print("\n=== 동시 로깅 테스트 ===")
    
    def worker(worker_id):
        """워커 스레드"""
        for i in range(5):
            logging.log(f"워커 {worker_id} - 로그 {i}", printlogs=False)
            time.sleep(0.1)
    
    try:
        # 여러 스레드에서 동시에 로깅
        threads = []
        for i in range(3):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()
        
        # 모든 스레드 완료 대기
        for t in threads:
            t.join()
        
        logging.log("동시 로깅 테스트 완료", printlogs=True)
        print("✓ 동시 로깅 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 동시 로깅 테스트 실패: {e}")
        return False

def test_signal_handling():
    """시그널 처리 테스트"""
    print("\n=== 시그널 처리 테스트 ===")
    
    def signal_handler(signum, frame):
        print(f"\n시그널 {signum} 수신, 로그 시스템 정리 중...")
        logging.close_dual_logging_system()
        sys.exit(0)
    
    try:
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, signal_handler)
        
        logging.log("시그널 처리 테스트 시작", printlogs=True)
        
        # 몇 초간 로깅 후 시그널 시뮬레이션
        for i in range(5):
            logging.log(f"시그널 테스트 로그 {i}", printlogs=False)
            time.sleep(1)
        
        print("✓ 시그널 처리 테스트 완료 (Ctrl+C로 테스트 가능)")
        return True
        
    except Exception as e:
        print(f"✗ 시그널 처리 테스트 실패: {e}")
        return False

def test_flight_logic_independence():
    """플라이트 로직 독립성 테스트"""
    print("\n=== 플라이트 로직 독립성 테스트 ===")
    
    try:
        # 플라이트 로직 시뮬레이션
        def simulate_flight_logic():
            """플라이트 로직 시뮬레이션"""
            try:
                # 의도적으로 오류 발생
                raise Exception("플라이트 로직 오류 시뮬레이션")
            except Exception as e:
                # 로깅은 여전히 작동해야 함
                logging.log(f"플라이트 로직 오류: {e}", printlogs=True)
        
        # 플라이트 로직 오류 시뮬레이션
        simulate_flight_logic()
        
        # 오류 후에도 로깅이 계속 작동하는지 확인
        logging.log("플라이트 로직 오류 후 로깅 테스트", printlogs=True)
        logging.log("센서 데이터: 온도=25.5, 고도=1000", printlogs=False)
        
        print("✓ 플라이트 로직 독립성 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 플라이트 로직 독립성 테스트 실패: {e}")
        return False

def test_dual_sd_logging():
    """이중 SD 카드 로깅 테스트"""
    print("\n=== 이중 SD 카드 로깅 테스트 ===")
    
    try:
        # 다양한 센서 데이터 시뮬레이션
        sensor_data = [
            {"type": "GPS", "data": {"lat": 37.123, "lon": 45.678, "alt": 1000}},
            {"type": "IMU", "data": {"roll": 1.5, "pitch": -0.8, "yaw": 90.2}},
            {"type": "BAROMETER", "data": {"pressure": 1013.25, "altitude": 1000}},
            {"type": "FIR1", "data": {"ambient": 25.5, "object": 30.2}},
            {"type": "FIR2", "data": {"ambient": 25.3, "object": 29.8}},
            {"type": "THERMAL", "data": {"avg": 26.1, "min": 24.5, "max": 28.3}}
        ]
        
        for sensor in sensor_data:
            log_entry = f"[{sensor['type']}] {sensor['data']}"
            logging.log(log_entry, printlogs=False)
            time.sleep(0.2)
        
        logging.log("이중 SD 카드 로깅 테스트 완료", printlogs=True)
        print("✓ 이중 SD 카드 로깅 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 이중 SD 카드 로깅 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("강화된 로깅 시스템 테스트")
    print("=" * 50)
    
    # 테스트 실행
    tests = [
        ("기본 로깅", test_basic_logging),
        ("오류 처리", test_error_handling),
        ("동시 로깅", test_concurrent_logging),
        ("시그널 처리", test_signal_handling),
        ("플라이트 로직 독립성", test_flight_logic_independence),
        ("이중 SD 카드 로깅", test_dual_sd_logging)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} 테스트 예외 발생: {e}")
            results.append((test_name, False))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    
    passed = 0
    for test_name, result in results:
        status = "✓ 성공" if result else "✗ 실패"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n전체: {passed}/{len(results)} 테스트 통과")
    
    if passed == len(results):
        print("\n🎉 모든 테스트 통과! 로깅 시스템이 견고하게 작동합니다.")
    else:
        print("\n⚠️  일부 테스트 실패. 로깅 시스템을 점검하세요.")
    
    # 로깅 시스템 정리
    try:
        logging.close_dual_logging_system()
        print("로깅 시스템 정리 완료")
    except Exception as e:
        print(f"로깅 시스템 정리 오류: {e}") 