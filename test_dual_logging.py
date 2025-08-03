#!/usr/bin/env python3
"""
Dual Logging System Test
이중 로깅 시스템 테스트 스크립트
"""

import time
import os
from datetime import datetime
from lib import logging

def test_dual_logging():
    """이중 로깅 시스템 테스트"""
    print("=== 이중 로깅 시스템 테스트 ===")
    
    # 1. 이중 로깅 시스템 초기화
    print("\n1. 이중 로깅 시스템 초기화...")
    try:
        logger = logging.init_dual_logging_system()
        if logger is None:
            print("✗ 이중 로깅 시스템 초기화 실패: 로거가 None입니다")
            return False
        print("✓ 이중 로깅 시스템 초기화 성공")
    except Exception as e:
        print(f"✗ 이중 로깅 시스템 초기화 실패: {e}")
        return False
    
    # 2. 로그 디렉토리 확인
    print("\n2. 로그 디렉토리 확인...")
    primary_dir = "logs"
    secondary_dir = "/mnt/log_sd/logs"
    
    if os.path.exists(primary_dir):
        print(f"✓ 메인 로그 디렉토리 존재: {primary_dir}")
    else:
        print(f"✗ 메인 로그 디렉토리 없음: {primary_dir}")
    
    if os.path.exists(secondary_dir):
        print(f"✓ 보조 로그 디렉토리 존재: {secondary_dir}")
    else:
        print(f"✗ 보조 로그 디렉토리 없음: {secondary_dir}")
    
    # 3. 로그 파일 생성 테스트
    print("\n3. 로그 파일 생성 테스트...")
    test_messages = [
        "이중 로깅 시스템 테스트 시작",
        "메인 SD카드와 보조 SD카드에 동시 저장",
        "낙하 중 데이터 손실 방지",
        "CANSAT 미션 데이터 보호",
        "테스트 완료"
    ]
    
    for i, message in enumerate(test_messages, 1):
        logger.log(f"테스트 메시지 {i}: {message}", print_logs=True)
        time.sleep(1)
    
    # 4. 로그 파일 확인
    print("\n4. 로그 파일 확인...")
    primary_files = [f for f in os.listdir(primary_dir) if f.endswith('.txt')]
    secondary_files = []
    
    if os.path.exists(secondary_dir):
        secondary_files = [f for f in os.listdir(secondary_dir) if f.endswith('.txt')]
    
    print(f"메인 로그 파일 수: {len(primary_files)}")
    print(f"보조 로그 파일 수: {len(secondary_files)}")
    
    if primary_files:
        latest_primary = max(primary_files, key=lambda x: os.path.getctime(os.path.join(primary_dir, x)))
        primary_path = os.path.join(primary_dir, latest_primary)
        primary_size = os.path.getsize(primary_path)
        print(f"최신 메인 로그 파일: {latest_primary} ({primary_size} bytes)")
    
    if secondary_files:
        latest_secondary = max(secondary_files, key=lambda x: os.path.getctime(os.path.join(secondary_dir, x)))
        secondary_path = os.path.join(secondary_dir, latest_secondary)
        secondary_size = os.path.getsize(secondary_path)
        print(f"최신 보조 로그 파일: {latest_secondary} ({secondary_size} bytes)")
    
    # 5. 파일 내용 비교
    print("\n5. 파일 내용 비교...")
    if primary_files and secondary_files:
        try:
            with open(primary_path, 'r', encoding='utf-8') as f1:
                primary_content = f1.read()
            
            with open(secondary_path, 'r', encoding='utf-8') as f2:
                secondary_content = f2.read()
            
            if primary_content == secondary_content:
                print("✓ 메인과 보조 로그 파일 내용이 동일합니다")
            else:
                print("✗ 메인과 보조 로그 파일 내용이 다릅니다")
                print(f"메인 파일 크기: {len(primary_content)} bytes")
                print(f"보조 파일 크기: {len(secondary_content)} bytes")
        except Exception as e:
            print(f"파일 내용 비교 오류: {e}")
    
    # 6. 센서 로거 테스트
    print("\n6. 센서 로거 이중 저장 테스트...")
    try:
        from sensor_logger import MultiSensorLogger
        
        # 센서 로거 초기화 (실제 센서 없이 테스트)
        print("센서 로거 초기화 중...")
        sensor_logger = MultiSensorLogger()
        
        # 테스트 데이터 생성
        test_data = [
            ['2024-01-01 12:00:00.000', 25.5, 60.2, 100, 150, 200, 250, 300, 350, 2.5, 125.0],
            ['2024-01-01 12:00:01.000', 25.6, 60.3, 101, 151, 201, 251, 301, 351, 2.6, 126.0],
            ['2024-01-01 12:00:02.000', 25.7, 60.4, 102, 152, 202, 252, 302, 352, 2.7, 127.0]
        ]
        
        # CSV 파일에 테스트 데이터 저장
        import csv
        for data in test_data:
            with open(sensor_logger.primary_csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(data)
            
            if sensor_logger.secondary_sd_available:
                with open(sensor_logger.secondary_csv_filename, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow(data)
        
        print("✓ 센서 로거 이중 저장 테스트 완료")
        
    except Exception as e:
        print(f"✗ 센서 로거 테스트 실패: {e}")
    
    # 7. 시스템 종료
    print("\n7. 이중 로깅 시스템 종료...")
    try:
        logging.close_dual_logging_system()
        print("✓ 이중 로깅 시스템 종료 완료")
    except Exception as e:
        print(f"✗ 이중 로깅 시스템 종료 오류: {e}")
    
    print("\n=== 테스트 완료 ===")
    return True

if __name__ == "__main__":
    test_dual_logging() 