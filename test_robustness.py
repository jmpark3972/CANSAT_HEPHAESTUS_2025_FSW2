#!/usr/bin/env python3
"""
테스트 스크립트: 앱 실패 시에도 로깅이 계속되는지 확인
"""

import time
import subprocess
import signal
import sys
import os

def test_system_robustness():
    """시스템 견고성 테스트"""
    print("=== 시스템 견고성 테스트 시작 ===")
    
    # 메인 프로세스 시작
    try:
        print("메인 프로세스 시작 중...")
        process = subprocess.Popen(
            ["python3", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 시스템 안정화 대기
        print("시스템 안정화 대기 중... (10초)")
        time.sleep(10)
        
        # 로그 파일 확인
        log_files = [
            "logs/imu/high_freq_imu_log.csv",
            "logs/imu/hk_log.csv", 
            "logs/imu/error_log.csv"
        ]
        
        print("로그 파일 상태 확인:")
        for log_file in log_files:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                print(f"  ✓ {log_file}: {size} bytes")
            else:
                print(f"  ✗ {log_file}: 파일 없음")
        
        # 시스템 상태 모니터링 (30초)
        print("시스템 상태 모니터링 중... (30초)")
        start_time = time.time()
        
        while time.time() - start_time < 30:
            # 프로세스 상태 확인
            if process.poll() is not None:
                print("메인 프로세스가 예기치 않게 종료됨")
                break
            
            # 로그 파일 크기 변화 확인
            for log_file in log_files:
                if os.path.exists(log_file):
                    current_size = os.path.getsize(log_file)
                    print(f"  {log_file}: {current_size} bytes")
            
            time.sleep(5)
        
        # 프로세스 종료
        print("테스트 완료, 프로세스 종료 중...")
        process.terminate()
        
        try:
            process.wait(timeout=10)
            print("프로세스 정상 종료")
        except subprocess.TimeoutExpired:
            print("프로세스 강제 종료")
            process.kill()
            process.wait()
        
        # 최종 로그 파일 상태 확인
        print("\n최종 로그 파일 상태:")
        for log_file in log_files:
            if os.path.exists(log_file):
                size = os.path.getsize(log_file)
                print(f"  {log_file}: {size} bytes")
                
                # 로그 내용 일부 출력
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"    마지막 로그: {lines[-1].strip()}")
                except Exception as e:
                    print(f"    로그 읽기 오류: {e}")
            else:
                print(f"  {log_file}: 파일 없음")
        
        print("\n=== 테스트 완료 ===")
        
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")
        if 'process' in locals():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                process.kill()

def test_imu_failure_recovery():
    """IMU 실패 복구 테스트"""
    print("\n=== IMU 실패 복구 테스트 ===")
    
    # IMU 로그 파일 초기화
    imu_log_dir = "logs/imu"
    os.makedirs(imu_log_dir, exist_ok=True)
    
    # 테스트용 로그 파일 생성
    test_log_file = os.path.join(imu_log_dir, "test_recovery.csv")
    
    try:
        with open(test_log_file, 'w', encoding='utf-8') as f:
            f.write("timestamp,test_type,status\n")
            f.write(f"{time.time()},test_start,ok\n")
        
        print("IMU 복구 테스트 로그 생성됨")
        
        # 실제 테스트는 main.py 실행 중에 IMU 센서를 물리적으로 분리/연결하여 수행
        print("IMU 센서 물리적 분리/연결 테스트를 수동으로 수행하세요")
        print("센서 분리 시 더미 데이터로 전환되는지 확인")
        print("센서 재연결 시 정상 데이터로 복구되는지 확인")
        
    except Exception as e:
        print(f"IMU 복구 테스트 오류: {e}")

if __name__ == "__main__":
    try:
        test_system_robustness()
        test_imu_failure_recovery()
    except KeyboardInterrupt:
        print("\n테스트 중단됨")
    except Exception as e:
        print(f"테스트 실패: {e}")
        sys.exit(1) 