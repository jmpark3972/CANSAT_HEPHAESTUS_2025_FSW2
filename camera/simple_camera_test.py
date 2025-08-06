#!/usr/bin/env python3
"""
Simple Pi Camera Test Script
기본적인 카메라 기능을 빠르게 테스트하기 위한 간단한 스크립트
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def check_camera_hardware():
    """카메라 하드웨어 확인"""
    print("🔍 카메라 하드웨어 확인 중...")
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'detected=1' in result.stdout:
            print("✅ 카메라 하드웨어 감지됨")
            return True
        else:
            print("❌ 카메라 하드웨어 감지되지 않음")
            print(f"출력: {result.stdout}")
            return False
    except Exception as e:
        print(f"❌ 카메라 하드웨어 확인 오류: {e}")
        return False

def check_camera_driver():
    """카메라 드라이버 확인"""
    print("🔍 카메라 드라이버 확인 중...")
    try:
        from pathlib import Path
        video_devices = list(Path('/dev').glob('video*'))
        if video_devices:
            print(f"✅ 비디오 디바이스 발견: {[str(d) for d in video_devices]}")
            return True
        else:
            print("❌ 비디오 디바이스 없음")
            return False
    except Exception as e:
        print(f"❌ 카메라 드라이버 확인 오류: {e}")
        return False

def check_ffmpeg():
    """FFmpeg 설치 확인"""
    print("🔍 FFmpeg 설치 확인 중...")
    try:
        result = subprocess.run(['ffmpeg', '-version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ FFmpeg 설치 확인됨")
            return True
        else:
            print("❌ FFmpeg 설치되지 않음")
            return False
    except Exception as e:
        print(f"❌ FFmpeg 확인 오류: {e}")
        return False

def test_single_photo():
    """단일 사진 촬영 테스트"""
    print("📸 단일 사진 촬영 테스트...")
    
    # 디렉토리 생성
    os.makedirs("logs/cansat_videos", exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"logs/cansat_videos/test_photo_{timestamp}.jpg"
    
    try:
        # raspistill 명령어로 사진 촬영
        cmd = [
            'raspistill',
            '-o', output_file,
            '-t', '1000',  # 1초 대기
            '-w', '1920',  # 너비
            '-h', '1080',  # 높이
            '-q', '80'     # 품질
        ]
        
        print(f"사진 촬영 중: {output_file}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ 사진 촬영 성공: {output_file}")
            return True
        else:
            print(f"❌ 사진 촬영 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 사진 촬영 타임아웃")
        return False
    except Exception as e:
        print(f"❌ 사진 촬영 오류: {e}")
        return False

def test_single_video():
    """단일 비디오 녹화 테스트"""
    print("🎥 단일 비디오 녹화 테스트...")
    
    # 디렉토리 생성
    os.makedirs("logs/cansat_videos", exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"logs/cansat_videos/test_video_{timestamp}.h264"
    
    try:
        # raspivid 명령어로 비디오 녹화
        cmd = [
            'raspivid',
            '-o', output_file,
            '-t', '5000',  # 5초
            '-w', '1920',  # 너비
            '-h', '1080',  # 높이
            '-fps', '30'   # 프레임레이트
        ]
        
        print(f"비디오 녹화 중: {output_file}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ 비디오 녹화 성공: {output_file}")
            return True
        else:
            print(f"❌ 비디오 녹화 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 비디오 녹화 타임아웃")
        return False
    except Exception as e:
        print(f"❌ 비디오 녹화 오류: {e}")
        return False

def test_ffmpeg_video():
    """FFmpeg를 사용한 비디오 녹화 테스트"""
    print("🎬 FFmpeg 비디오 녹화 테스트...")
    
    # 디렉토리 생성
    os.makedirs("logs/cansat_videos", exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"logs/cansat_videos/test_ffmpeg_{timestamp}.mp4"
    
    try:
        # FFmpeg 명령어로 비디오 녹화
        cmd = [
            'ffmpeg',
            '-f', 'v4l2',
            '-video_size', '1920x1080',
            '-framerate', '30',
            '-i', '/dev/video0',
            '-t', '3',  # 3초
            '-c:v', 'libx264',
            '-preset', 'ultrafast',
            '-crf', '23',
            '-y',
            output_file
        ]
        
        print(f"FFmpeg 비디오 녹화 중: {output_file}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print(f"✅ FFmpeg 비디오 녹화 성공: {output_file}")
            return True
        else:
            print(f"❌ FFmpeg 비디오 녹화 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ FFmpeg 비디오 녹화 타임아웃")
        return False
    except Exception as e:
        print(f"❌ FFmpeg 비디오 녹화 오류: {e}")
        return False

def check_disk_space():
    """디스크 공간 확인"""
    print("💾 디스크 공간 확인...")
    try:
        import shutil
        total, used, free = shutil.disk_usage("logs/cansat_videos")
        
        total_gb = total / (1024**3)
        used_gb = used / (1024**3)
        free_gb = free / (1024**3)
        usage_percent = (used / total) * 100
        
        print(f"총 용량: {total_gb:.1f} GB")
        print(f"사용 중: {used_gb:.1f} GB ({usage_percent:.1f}%)")
        print(f"여유 공간: {free_gb:.1f} GB")
        
        if free_gb < 1.0:
            print("⚠️  여유 공간이 1GB 미만입니다!")
            return False
        else:
            print("✅ 충분한 디스크 공간이 있습니다")
            return True
            
    except Exception as e:
        print(f"❌ 디스크 공간 확인 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("Pi Camera Simple Test")
    print("=" * 60)
    
    # 기본 확인
    print("\n1. 기본 시스템 확인")
    print("-" * 30)
    
    hw_ok = check_camera_hardware()
    driver_ok = check_camera_driver()
    ffmpeg_ok = check_ffmpeg()
    disk_ok = check_disk_space()
    
    if not all([hw_ok, driver_ok, ffmpeg_ok, disk_ok]):
        print("\n❌ 기본 시스템 확인 실패")
        print("다음 사항을 확인하세요:")
        if not hw_ok:
            print("- Pi Camera가 올바르게 연결되었는지 확인")
        if not driver_ok:
            print("- 카메라 드라이버가 설치되었는지 확인")
        if not ffmpeg_ok:
            print("- FFmpeg가 설치되었는지 확인: sudo apt install ffmpeg")
        if not disk_ok:
            print("- 충분한 디스크 공간이 있는지 확인")
        return
    
    print("\n✅ 기본 시스템 확인 완료")
    
    # 기능 테스트
    print("\n2. 카메라 기능 테스트")
    print("-" * 30)
    
    # 사용자 선택
    print("테스트할 기능을 선택하세요:")
    print("1. 단일 사진 촬영")
    print("2. 단일 비디오 녹화 (raspivid)")
    print("3. FFmpeg 비디오 녹화")
    print("4. 모든 테스트 실행")
    print("5. 종료")
    
    try:
        choice = input("\n선택 (1-5): ").strip()
        
        if choice == '1':
            test_single_photo()
        elif choice == '2':
            test_single_video()
        elif choice == '3':
            test_ffmpeg_video()
        elif choice == '4':
            print("\n모든 테스트 실행 중...")
            test_single_photo()
            time.sleep(2)
            test_single_video()
            time.sleep(2)
            test_ffmpeg_video()
        elif choice == '5':
            print("종료")
            return
        else:
            print("잘못된 선택입니다")
            return
            
    except KeyboardInterrupt:
        print("\n키보드 인터럽트 감지")
    
    print("\n테스트 완료!")
    print("생성된 파일은 logs/cansat_videos/ 디렉토리에서 확인할 수 있습니다.")

if __name__ == "__main__":
    main() 