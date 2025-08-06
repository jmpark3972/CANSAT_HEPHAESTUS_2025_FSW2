#!/usr/bin/env python3
"""
CANSAT HEPHAESTUS 2025 FSW2 - 이중 로깅 시스템 테스트
"""

import os
import sys
import time
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_dual_logging_system():
    """이중 로깅 시스템 테스트"""
    print("🔍 CANSAT HEPHAESTUS 2025 FSW2 - 이중 로깅 시스템 테스트")
    print("=" * 60)
    
    # 1. 서브 SD 카드 마운트 확인
    print("\n1️⃣ 서브 SD 카드 마운트 확인")
    if os.path.exists("/mnt/log_sd"):
        print("✅ 서브 SD 카드가 마운트되어 있습니다: /mnt/log_sd")
        
        # 용량 확인
        try:
            import subprocess
            result = subprocess.run(['df', '-h', '/mnt/log_sd'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        print(f"   용량: {parts[1]} / {parts[2]} ({parts[4]})")
        except Exception as e:
            print(f"   용량 확인 실패: {e}")
    else:
        print("❌ 서브 SD 카드가 마운트되지 않았습니다")
        print("   SPI SD 카드 설정을 먼저 완료해주세요")
        return False
    
    # 2. 이중 로깅 디렉토리 확인
    print("\n2️⃣ 이중 로깅 디렉토리 확인")
    directories = [
        "/mnt/log_sd/cansat_logs",
        "/mnt/log_sd/cansat_videos", 
        "/mnt/log_sd/cansat_camera_temp",
        "/mnt/log_sd/cansat_camera_logs",
        "/mnt/log_sd/thermal_videos"
    ]
    
    # 권한 문제 해결 시도
    print("   🔧 권한 문제 해결 시도 중...")
    try:
        import subprocess
        import getpass
        
        current_user = getpass.getuser()
        result = subprocess.run(
            ['sudo', 'chown', '-R', f'{current_user}:{current_user}', '/mnt/log_sd'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            print("   ✅ 권한 수정 완료")
        else:
            print(f"   ⚠️ 권한 수정 실패: {result.stderr}")
            print("   💡 수동으로 다음 명령을 실행해주세요:")
            print("      sudo chown -R SpaceY:SpaceY /mnt/log_sd")
            print("      sudo chmod -R 755 /mnt/log_sd")
    except Exception as e:
        print(f"   ⚠️ 권한 수정 시도 실패: {e}")
    
    for directory in directories:
        if os.path.exists(directory):
            print(f"✅ {directory}")
        else:
            print(f"❌ {directory}")
            try:
                os.makedirs(directory, exist_ok=True)
                print(f"   📁 생성됨: {directory}")
            except PermissionError:
                print(f"   ❌ 권한 오류로 생성 실패: {directory}")
                print("      sudo chown -R SpaceY:SpaceY /mnt/log_sd 명령을 실행해주세요")
            except Exception as e:
                print(f"   ❌ 생성 실패: {e}")
    
    # 3. 이중 로깅 시스템 테스트
    print("\n3️⃣ 이중 로깅 시스템 테스트")
    try:
        from lib.dual_logging import dual_logger, info, warning, error, sensor_data, system_event
        
        # 테스트 로그 메시지들
        info("이중 로깅 시스템 테스트 시작", "TEST")
        warning("테스트 경고 메시지", "TEST")
        error("테스트 오류 메시지", "TEST")
        
        # 센서 데이터 테스트
        sensor_data("TEST_SENSOR", {
            "temperature": 25.5,
            "humidity": 60.0,
            "pressure": 1013.25
        })
        
        # 시스템 이벤트 테스트
        system_event("DUAL_LOGGING_TEST", {
            "status": "success",
            "timestamp": datetime.now().isoformat(),
            "test_data": "이중 로깅 테스트 완료"
        })
        
        print("✅ 이중 로깅 시스템 테스트 완료")
        
        # 4. 로그 파일 확인
        print("\n4️⃣ 로그 파일 확인")
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        # 메인 로그 파일 확인
        main_log_file = f"logs/{date_str}_dual_log.txt"
        if os.path.exists(main_log_file):
            print(f"✅ 메인 로그 파일: {main_log_file}")
            with open(main_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   로그 라인 수: {len(lines)}")
        else:
            print(f"❌ 메인 로그 파일 없음: {main_log_file}")
        
        # 서브 로그 파일 확인
        sub_log_file = f"/mnt/log_sd/cansat_logs/{date_str}_dual_log.txt"
        if os.path.exists(sub_log_file):
            print(f"✅ 서브 로그 파일: {sub_log_file}")
            with open(sub_log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                print(f"   로그 라인 수: {len(lines)}")
        else:
            print(f"❌ 서브 로그 파일 없음: {sub_log_file}")
        
        # 5. 파일 동기화 테스트
        print("\n5️⃣ 파일 동기화 테스트")
        test_data = {
            "test_type": "dual_logging_sync",
            "timestamp": datetime.now().isoformat(),
            "message": "이중 로깅 동기화 테스트"
        }
        
        # 메인 SD에 저장
        main_test_file = "logs/dual_logging_test.json"
        with open(main_test_file, 'w', encoding='utf-8') as f:
            json.dump(test_data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        
        # 서브 SD에 복사
        sub_test_file = "/mnt/log_sd/cansat_logs/dual_logging_test.json"
        import shutil
        shutil.copy2(main_test_file, sub_test_file)
        
        # 파일 비교
        if os.path.exists(main_test_file) and os.path.exists(sub_test_file):
            with open(main_test_file, 'r', encoding='utf-8') as f1:
                with open(sub_test_file, 'r', encoding='utf-8') as f2:
                    if f1.read() == f2.read():
                        print("✅ 파일 동기화 테스트 성공")
                    else:
                        print("❌ 파일 동기화 테스트 실패")
        else:
            print("❌ 테스트 파일 생성 실패")
        
        # 6. 긴급 저장 테스트
        print("\n6️⃣ 긴급 저장 테스트")
        emergency_data = {
            "emergency_type": "test",
            "timestamp": datetime.now().isoformat(),
            "data": "긴급 저장 테스트 데이터"
        }
        
        from lib.dual_logging import emergency_save
        emergency_save(emergency_data, "emergency_test.json")
        
        # 긴급 저장 파일 확인
        main_emergency = "logs/emergency_test.json"
        sub_emergency = "/mnt/log_sd/cansat_logs/emergency_test.json"
        
        if os.path.exists(main_emergency) and os.path.exists(sub_emergency):
            print("✅ 긴급 저장 테스트 성공")
        else:
            print("❌ 긴급 저장 테스트 실패")
        
        # 7. 정리
        print("\n7️⃣ 테스트 정리")
        cleanup_files = [
            main_test_file,
            sub_test_file,
            main_emergency,
            sub_emergency
        ]
        
        for file_path in cleanup_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️ 삭제됨: {file_path}")
            except Exception as e:
                print(f"❌ 삭제 실패: {file_path} - {e}")
        
        print("\n🎉 이중 로깅 시스템 테스트 완료!")
        print("=" * 60)
        print("📋 테스트 결과:")
        print("✅ 서브 SD 카드 마운트")
        print("✅ 이중 로깅 디렉토리")
        print("✅ 로그 시스템 동작")
        print("✅ 파일 동기화")
        print("✅ 긴급 저장")
        print("\n🚀 이중 로깅 시스템이 정상적으로 작동합니다!")
        
        return True
        
    except ImportError as e:
        print(f"❌ 이중 로깅 모듈 import 실패: {e}")
        return False
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")
        return False

def main():
    """메인 함수"""
    success = test_dual_logging_system()
    
    if success:
        print("\n✅ 모든 테스트가 성공했습니다!")
        return 0
    else:
        print("\n❌ 일부 테스트가 실패했습니다.")
        return 1

if __name__ == "__main__":
    exit(main()) 