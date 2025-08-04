#!/usr/bin/env python3
"""
Camera App Test Script
Raspberry Pi Camera Module v3 Wide 테스트
"""

import sys
import os
import time
import subprocess
import threading
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging, appargs

def test_camera_hardware():
    """카메라 하드웨어 확인"""
    print("1. 카메라 하드웨어 확인...")
    
    try:
        # vcgencmd로 카메라 상태 확인
        result = subprocess.run(['vcgencmd', 'get_camera'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   카메라 상태: {result.stdout.strip()}")
            if 'detected=1' in result.stdout:
                print("   ✓ 카메라 하드웨어 감지됨")
                return True
            else:
                print("   ✗ 카메라 하드웨어 감지되지 않음")
                return False
        else:
            print("   ✗ vcgencmd 명령어 실패")
            return False
    except Exception as e:
        print(f"   ✗ 카메라 하드웨어 확인 오류: {e}")
        return False

def test_camera_driver():
    """카메라 드라이버 확인"""
    print("2. 카메라 드라이버 확인...")
    
    try:
        # /dev/video* 디바이스 확인
        video_devices = list(Path('/dev').glob('video*'))
        if video_devices:
            print(f"   발견된 비디오 디바이스: {[str(d) for d in video_devices]}")
            print("   ✓ 카메라 드라이버 로드됨")
            return True
        else:
            print("   ✗ 비디오 디바이스 없음")
            return False
    except Exception as e:
        print(f"   ✗ 카메라 드라이버 확인 오류: {e}")
        return False

def test_ffmpeg():
    """FFmpeg 설치 확인"""
    print("3. FFmpeg 설치 확인...")
    
    try:
        result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"   {version_line}")
            print("   ✓ FFmpeg 설치됨")
            return True
        else:
            print("   ✗ FFmpeg 설치되지 않음")
            return False
    except Exception as e:
        print(f"   ✗ FFmpeg 확인 오류: {e}")
        return False

def test_camera_initialization():
    """카메라 초기화 테스트"""
    print("4. 카메라 초기화 테스트...")
    
    try:
        from camera import camera
        
        # 카메라 초기화
        camera_process = camera.init_camera()
        if camera_process:
            print("   ✓ 카메라 초기화 성공")
            
            # 카메라 종료
            camera.terminate_camera()
            print("   ✓ 카메라 종료 성공")
            return True
        else:
            print("   ✗ 카메라 초기화 실패")
            return False
    except Exception as e:
        print(f"   ✗ 카메라 초기화 테스트 오류: {e}")
        return False

def test_recording():
    """녹화 테스트"""
    print("5. 녹화 테스트...")
    
    try:
        from camera import camera
        
        # 카메라 초기화
        camera_process = camera.init_camera()
        if not camera_process:
            print("   ✗ 카메라 초기화 실패로 녹화 테스트 건너뜀")
            return False
        
        # 5초 녹화 테스트
        print("   5초간 녹화 테스트 시작...")
        success = camera.record_single_video(camera_process, 5)
        
        # 카메라 종료
        camera.terminate_camera()
        
        if success:
            print("   ✓ 녹화 테스트 성공")
            return True
        else:
            print("   ✗ 녹화 테스트 실패")
            return False
    except Exception as e:
        print(f"   ✗ 녹화 테스트 오류: {e}")
        return False

def test_status_monitoring():
    """상태 모니터링 테스트"""
    print("6. 상태 모니터링 테스트...")
    
    try:
        from camera import camera
        
        # 카메라 초기화
        camera_process = camera.init_camera()
        if not camera_process:
            print("   ✗ 카메라 초기화 실패로 상태 모니터링 테스트 건너뜀")
            return False
        
        # 상태 확인
        status = camera.get_camera_status(camera_process)
        print(f"   카메라 상태: {status}")
        
        # 디스크 사용량 확인
        disk_usage = camera.get_disk_usage()
        print(f"   디스크 사용량: {disk_usage:.1f}%")
        
        # 카메라 종료
        camera.terminate_camera()
        
        print("   ✓ 상태 모니터링 테스트 성공")
        return True
    except Exception as e:
        print(f"   ✗ 상태 모니터링 테스트 오류: {e}")
        return False

def cleanup_test():
    """테스트 정리"""
    print("7. 테스트 정리...")
    
    try:
        # 임시 파일 정리
        temp_files = list(Path('.').glob('temp_*.mp4'))
        for temp_file in temp_files:
            temp_file.unlink()
            print(f"   임시 파일 삭제: {temp_file}")
        
        print("   ✓ 테스트 정리 완료")
        return True
    except Exception as e:
        print(f"   ✗ 테스트 정리 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== Camera App 테스트 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    test_results['hardware'] = test_camera_hardware()
    test_results['driver'] = test_camera_driver()
    test_results['ffmpeg'] = test_ffmpeg()
    test_results['initialization'] = test_camera_initialization()
    test_results['recording'] = test_recording()
    test_results['monitoring'] = test_status_monitoring()
    test_results['cleanup'] = cleanup_test()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:15}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! 카메라 앱이 정상적으로 작동합니다.")
        return True
    else:
        print("⚠️  일부 테스트 실패. 카메라 설정을 확인하세요.")
        return False

if __name__ == "__main__":
    main() 