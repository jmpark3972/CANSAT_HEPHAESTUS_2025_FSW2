#!/usr/bin/env python3
# Camera App Test Script
# Author : Hyeon Lee  (HEPHAESTUS)

import sys
import os
import time
import subprocess
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from camera import camera as cam
from lib import events, appargs

def test_camera_hardware():
    """카메라 하드웨어 테스트."""
    print("=== 카메라 하드웨어 테스트 ===")
    
    # vcgencmd로 카메라 상태 확인
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print(f"카메라 상태: {result.stdout.strip()}")
            if "detected=1" in result.stdout:
                print("✓ 카메라 하드웨어 감지됨")
                return True
            else:
                print("✗ 카메라 하드웨어 감지되지 않음")
                return False
        else:
            print("✗ vcgencmd 실행 실패")
            return False
    except Exception as e:
        print(f"✗ 하드웨어 테스트 오류: {e}")
        return False

def test_camera_driver():
    """카메라 드라이버 테스트."""
    print("\n=== 카메라 드라이버 테스트 ===")
    
    # /dev/video0 존재 확인
    if os.path.exists('/dev/video0'):
        print("✓ /dev/video0 발견")
        
        # 권한 확인
        try:
            stat = os.stat('/dev/video0')
            print(f"권한: {oct(stat.st_mode)[-3:]}")
            return True
        except Exception as e:
            print(f"✗ 권한 확인 오류: {e}")
            return False
    else:
        print("✗ /dev/video0 없음")
        return False

def test_ffmpeg():
    """ffmpeg 설치 테스트."""
    print("\n=== ffmpeg 테스트 ===")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✓ ffmpeg 설치됨")
            # 버전 정보 출력
            version_line = result.stdout.split('\n')[0]
            print(f"버전: {version_line}")
            return True
        else:
            print("✗ ffmpeg 실행 실패")
            return False
    except FileNotFoundError:
        print("✗ ffmpeg 설치되지 않음")
        print("설치 명령: sudo apt install ffmpeg")
        return False
    except Exception as e:
        print(f"✗ ffmpeg 테스트 오류: {e}")
        return False

def test_camera_initialization():
    """카메라 초기화 테스트."""
    print("\n=== 카메라 초기화 테스트 ===")
    
    try:
        success = cam.init_camera()
        if success:
            print("✓ 카메라 초기화 성공")
            return True
        else:
            print("✗ 카메라 초기화 실패")
            return False
    except Exception as e:
        print(f"✗ 초기화 테스트 오류: {e}")
        return False

def test_recording():
    """녹화 기능 테스트."""
    print("\n=== 녹화 기능 테스트 ===")
    
    try:
        # 녹화 시작
        print("녹화 시작...")
        if cam.start_recording():
            print("✓ 녹화 시작 성공")
            
            # 10초 대기 (2개 비디오 파일 생성)
            print("10초간 녹화 중...")
            time.sleep(10)
            
            # 녹화 중지
            print("녹화 중지...")
            if cam.stop_recording():
                print("✓ 녹화 중지 성공")
                
                # 파일 생성 확인
                time.sleep(2)  # 파일 처리 대기
                video_count = cam.get_video_count()
                print(f"생성된 비디오 파일 수: {video_count}")
                
                if video_count > 0:
                    print("✓ 비디오 파일 생성 확인")
                    return True
                else:
                    print("✗ 비디오 파일 생성되지 않음")
                    return False
            else:
                print("✗ 녹화 중지 실패")
                return False
        else:
            print("✗ 녹화 시작 실패")
            return False
            
    except Exception as e:
        print(f"✗ 녹화 테스트 오류: {e}")
        return False

def test_status_monitoring():
    """상태 모니터링 테스트."""
    print("\n=== 상태 모니터링 테스트 ===")
    
    try:
        # 카메라 상태 확인
        status = cam.get_camera_status()
        print(f"카메라 상태: {status}")
        
        # 디스크 사용량 확인
        disk_info = cam.get_disk_usage()
        print(f"디스크 정보: {disk_info}")
        
        print("✓ 상태 모니터링 정상")
        return True
        
    except Exception as e:
        print(f"✗ 상태 모니터링 오류: {e}")
        return False

def cleanup_test():
    """테스트 정리."""
    print("\n=== 테스트 정리 ===")
    
    try:
        cam.terminate_camera()
        print("✓ 카메라 정리 완료")
        return True
    except Exception as e:
        print(f"✗ 정리 오류: {e}")
        return False

def main():
    """메인 테스트 함수."""
    print("카메라 앱 테스트 시작")
    print("=" * 50)
    
    # 테스트 결과 추적
    test_results = []
    
    # 1. 하드웨어 테스트
    test_results.append(("하드웨어", test_camera_hardware()))
    
    # 2. 드라이버 테스트
    test_results.append(("드라이버", test_camera_driver()))
    
    # 3. ffmpeg 테스트
    test_results.append(("ffmpeg", test_ffmpeg()))
    
    # 4. 초기화 테스트
    test_results.append(("초기화", test_camera_initialization()))
    
    # 5. 상태 모니터링 테스트
    test_results.append(("상태 모니터링", test_status_monitoring()))
    
    # 6. 녹화 테스트 (선택적)
    print("\n녹화 테스트를 실행하시겠습니까? (y/n): ", end="")
    response = input().lower().strip()
    
    if response == 'y':
        test_results.append(("녹화", test_recording()))
    else:
        print("녹화 테스트 건너뜀")
        test_results.append(("녹화", None))
    
    # 7. 정리
    test_results.append(("정리", cleanup_test()))
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    
    passed = 0
    total = 0
    
    for test_name, result in test_results:
        if result is None:
            print(f"{test_name:15} : 건너뜀")
        elif result:
            print(f"{test_name:15} : ✓ 통과")
            passed += 1
        else:
            print(f"{test_name:15} : ✗ 실패")
        total += 1
    
    print("-" * 50)
    print(f"통과: {passed}/{total}")
    
    if passed == total:
        print("🎉 모든 테스트 통과!")
        return 0
    else:
        print("⚠️  일부 테스트 실패")
        return 1

if __name__ == "__main__":
    exit(main()) 