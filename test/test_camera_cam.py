#!/usr/bin/env python3
"""
카메라 cam 명령어 테스트 스크립트
"""

import sys
import os
import subprocess
import time

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from camera.camera import camera

def test_camera_hardware():
    """카메라 하드웨어 테스트"""
    print("=== 카메라 하드웨어 테스트 ===")
    result = camera.check_camera_hardware()
    print(f"하드웨어 감지 결과: {result}")
    return result

def test_camera_driver():
    """카메라 드라이버 테스트"""
    print("\n=== 카메라 드라이버 테스트 ===")
    result = camera.check_camera_driver()
    print(f"드라이버 확인 결과: {result}")
    return result

def test_cam_command():
    """cam 명령어 직접 테스트"""
    print("\n=== cam 명령어 직접 테스트 ===")
    try:
        # 카메라 목록 확인
        result = subprocess.run(['cam', '-l'], capture_output=True, text=True, timeout=10)
        print(f"cam -l 결과:")
        print(f"Return code: {result.returncode}")
        print(f"Output: {result.stdout}")
        print(f"Error: {result.stderr}")
        
        if result.returncode == 0:
            print("cam 명령어가 정상적으로 작동합니다.")
            return True
        else:
            print("cam 명령어에 문제가 있습니다.")
            return False
            
    except Exception as e:
        print(f"cam 명령어 테스트 오류: {e}")
        return False

def test_camera_init():
    """카메라 초기화 테스트"""
    print("\n=== 카메라 초기화 테스트 ===")
    try:
        process = camera.init_camera()
        if process:
            print("카메라 초기화 성공")
            camera.terminate_camera()
            return True
        else:
            print("카메라 초기화 실패")
            return False
    except Exception as e:
        print(f"카메라 초기화 오류: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("카메라 cam 명령어 테스트 시작")
    print("=" * 50)
    
    # 디렉토리 생성
    print("디렉토리 생성...")
    camera.ensure_directories()
    
    # 각 테스트 실행
    hw_result = test_camera_hardware()
    driver_result = test_camera_driver()
    cam_result = test_cam_command()
    init_result = test_camera_init()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"하드웨어 감지: {'성공' if hw_result else '실패'}")
    print(f"드라이버 확인: {'성공' if driver_result else '실패'}")
    print(f"cam 명령어: {'성공' if cam_result else '실패'}")
    print(f"카메라 초기화: {'성공' if init_result else '실패'}")
    
    if all([hw_result, driver_result, cam_result, init_result]):
        print("\n모든 테스트가 성공했습니다!")
    else:
        print("\n일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    main() 