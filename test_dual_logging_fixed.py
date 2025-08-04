#!/usr/bin/env python3
"""
이중 로깅 시스템 테스트 - 보조 SD 카드 권한 설정 후
"""

import os
import sys
import time
from datetime import datetime

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lib.logging import init_dual_logging_system, close_dual_logging_system

def test_dual_logging():
    """이중 로깅 시스템 테스트"""
    print("=" * 60)
    print("이중 로깅 시스템 테스트 시작")
    print("=" * 60)
    
    # 보조 SD 카드 권한 확인
    print("\n1. 보조 SD 카드 권한 확인...")
    secondary_log_dir = "/mnt/log_sd/logs"
    
    if not os.path.exists(secondary_log_dir):
        print(f"❌ 보조 로그 디렉토리가 존재하지 않음: {secondary_log_dir}")
        print("다음 명령을 실행하세요:")
        print("sudo mkdir -p /mnt/log_sd/logs")
        print("sudo chown -R SpaceY:SpaceY /mnt/log_sd/logs")
        print("sudo chmod -R 755 /mnt/log_sd/logs")
        return False
    
    # 쓰기 권한 테스트
    test_file = os.path.join(secondary_log_dir, "test_write.tmp")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        print(f"✅ 보조 SD 카드 쓰기 권한 확인 완료: {secondary_log_dir}")
    except Exception as e:
        print(f"❌ 보조 SD 카드 쓰기 권한 없음: {e}")
        print("다음 명령을 실행하세요:")
        print("sudo chown -R SpaceY:SpaceY /mnt/log_sd/logs")
        print("sudo chmod -R 755 /mnt/log_sd/logs")
        return False
    
    # 이중 로깅 시스템 초기화
    print("\n2. 이중 로깅 시스템 초기화...")
    try:
        dual_logger = init_dual_logging_system()
        if dual_logger is None:
            print("❌ 이중 로깅 시스템 초기화 실패")
            return False
        print("✅ 이중 로깅 시스템 초기화 성공")
    except Exception as e:
        print(f"❌ 이중 로깅 시스템 초기화 오류: {e}")
        return False
    
    # 로그 테스트
    print("\n3. 로그 기록 테스트...")
    test_messages = [
        "이중 로깅 시스템 테스트 시작",
        "주 로그와 보조 로그에 동시 기록",
        "센서 데이터 시뮬레이션: 온도=25.5°C, 압력=1013.25hPa",
        "GPS 데이터 시뮬레이션: 위도=37.5665, 경도=126.9780",
        "IMU 데이터 시뮬레이션: 가속도=(0.1, 0.2, 9.8), 자이로=(0.01, 0.02, 0.03)",
        "이중 로깅 시스템 테스트 완료"
    ]
    
    for i, message in enumerate(test_messages, 1):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] INFO | Test | {message}\n"
        
        try:
            dual_logger.log(log_entry)
            print(f"✅ 로그 기록 {i}/{len(test_messages)}: {message[:30]}...")
        except Exception as e:
            print(f"❌ 로그 기록 실패 {i}: {e}")
        
        time.sleep(0.1)  # 100ms 대기
    
    # 로그 파일 확인
    print("\n4. 로그 파일 확인...")
    
    # 주 로그 파일 확인
    primary_log_dir = "logs"
    primary_files = [f for f in os.listdir(primary_log_dir) if f.startswith("system_log_") and f.endswith(".txt")]
    if primary_files:
        latest_primary = max(primary_files, key=lambda x: os.path.getctime(os.path.join(primary_log_dir, x)))
        primary_path = os.path.join(primary_log_dir, latest_primary)
        primary_size = os.path.getsize(primary_path)
        print(f"✅ 주 로그 파일: {latest_primary} ({primary_size} bytes)")
    else:
        print("❌ 주 로그 파일을 찾을 수 없음")
    
    # 보조 로그 파일 확인
    secondary_files = [f for f in os.listdir(secondary_log_dir) if f.startswith("system_log_") and f.endswith(".txt")]
    if secondary_files:
        latest_secondary = max(secondary_files, key=lambda x: os.path.getctime(os.path.join(secondary_log_dir, x)))
        secondary_path = os.path.join(secondary_log_dir, latest_secondary)
        secondary_size = os.path.getsize(secondary_path)
        print(f"✅ 보조 로그 파일: {latest_secondary} ({secondary_size} bytes)")
    else:
        print("❌ 보조 로그 파일을 찾을 수 없음")
    
    # 로그 내용 비교
    if primary_files and secondary_files:
        print("\n5. 로그 내용 비교...")
        try:
            with open(primary_path, 'r', encoding='utf-8') as f1, \
                 open(secondary_path, 'r', encoding='utf-8') as f2:
                primary_content = f1.read()
                secondary_content = f2.read()
                
                if primary_content == secondary_content:
                    print("✅ 주 로그와 보조 로그 내용이 동일함")
                else:
                    print("❌ 주 로그와 보조 로그 내용이 다름")
                    print(f"주 로그 크기: {len(primary_content)} bytes")
                    print(f"보조 로그 크기: {len(secondary_content)} bytes")
        except Exception as e:
            print(f"❌ 로그 내용 비교 실패: {e}")
    
    # 이중 로깅 시스템 종료
    print("\n6. 이중 로깅 시스템 종료...")
    try:
        close_dual_logging_system()
        print("✅ 이중 로깅 시스템 종료 완료")
    except Exception as e:
        print(f"❌ 이중 로깅 시스템 종료 오류: {e}")
    
    print("\n" + "=" * 60)
    print("이중 로깅 시스템 테스트 완료")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    success = test_dual_logging()
    sys.exit(0 if success else 1) 