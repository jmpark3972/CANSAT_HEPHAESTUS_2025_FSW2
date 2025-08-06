#!/usr/bin/env python3
"""
Pi Camera v2 Test Script
Pi Camera v2 전용 테스트 스크립트
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def check_camera_v2_hardware():
    """Pi Camera v2 하드웨어 확인"""
    print("🔍 Pi Camera v2 하드웨어 확인 중...")
    
    # 방법 1: vcgencmd
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and 'detected=1' in result.stdout:
            print("✅ vcgencmd로 카메라 감지됨")
            return True
        else:
            print(f"❌ vcgencmd 결과: {result.stdout}")
    except Exception as e:
        print(f"❌ vcgencmd 오류: {e}")
    
    # 방법 2: device-tree 확인
    try:
        from pathlib import Path
        csi0 = Path('/proc/device-tree/soc/csi0')
        csi1 = Path('/proc/device-tree/soc/csi1')
        
        if csi0.exists():
            print("✅ CSI0 노드 발견 (Pi Camera v2)")
            return True
        elif csi1.exists():
            print("✅ CSI1 노드 발견 (Pi Camera v1)")
            return True
        else:
            print("❌ CSI 노드 없음")
    except Exception as e:
        print(f"❌ device-tree 확인 오류: {e}")
    
    # 방법 3: dmesg 확인
    try:
        result = subprocess.run(['dmesg'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            if 'camera' in result.stdout.lower() or 'csi' in result.stdout.lower():
                print("✅ dmesg에서 카메라 관련 메시지 발견")
                return True
            else:
                print("❌ dmesg에서 카메라 관련 메시지 없음")
    except Exception as e:
        print(f"❌ dmesg 확인 오류: {e}")
    
    return False

def check_camera_v2_driver():
    """Pi Camera v2 드라이버 확인"""
    print("🔍 Pi Camera v2 드라이버 확인 중...")
    
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
        print(f"❌ 드라이버 확인 오류: {e}")
        return False

def test_raspistill_v2():
    """raspistill로 Pi Camera v2 테스트"""
    print("📸 raspistill로 Pi Camera v2 테스트...")
    
    try:
        # 테스트 사진 촬영
        test_file = f"test_picamera_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        cmd = [
            'raspistill',
            '-o', test_file,
            '-t', '1000',  # 1초 대기
            '-w', '1920',  # 너비
            '-h', '1080',  # 높이
            '-q', '80'     # 품질
        ]
        
        print(f"사진 촬영 중: {test_file}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(test_file):
            print(f"✅ 사진 촬영 성공: {test_file}")
            # 테스트 파일 삭제
            os.remove(test_file)
            return True
        else:
            print(f"❌ 사진 촬영 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 사진 촬영 타임아웃")
        return False
    except Exception as e:
        print(f"❌ raspistill 테스트 오류: {e}")
        return False

def test_raspivid_v2():
    """raspivid로 Pi Camera v2 테스트"""
    print("🎥 raspivid로 Pi Camera v2 테스트...")
    
    try:
        # 테스트 비디오 녹화
        test_file = f"test_picamera_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.h264"
        
        cmd = [
            'raspivid',
            '-o', test_file,
            '-t', '3000',  # 3초
            '-w', '1920',  # 너비
            '-h', '1080',  # 높이
            '-fps', '30'   # 프레임레이트
        ]
        
        print(f"비디오 녹화 중: {test_file}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0 and os.path.exists(test_file):
            print(f"✅ 비디오 녹화 성공: {test_file}")
            # 테스트 파일 삭제
            os.remove(test_file)
            return True
        else:
            print(f"❌ 비디오 녹화 실패: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ 비디오 녹화 타임아웃")
        return False
    except Exception as e:
        print(f"❌ raspivid 테스트 오류: {e}")
        return False

def test_libcamera_v2():
    """libcamera로 Pi Camera v2 테스트"""
    print("📹 libcamera로 Pi Camera v2 테스트...")
    
    try:
        # 카메라 목록 확인
        result = subprocess.run(['libcamera-hello', '--list-cameras'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ libcamera 카메라 목록:")
            print(result.stdout)
            return True
        else:
            print(f"❌ libcamera 카메라 목록 실패: {result.stderr}")
            return False
            
    except FileNotFoundError:
        print("⚠️ libcamera-hello가 설치되지 않음")
        return False
    except Exception as e:
        print(f"❌ libcamera 테스트 오류: {e}")
        return False

def check_config_v2():
    """Pi Camera v2 설정 확인"""
    print("⚙️ Pi Camera v2 설정 확인 중...")
    
    try:
        with open('/boot/config.txt', 'r') as f:
            config_content = f.read()
        
        checks = [
            ('camera_auto_detect=1', '카메라 자동 감지'),
            ('dtoverlay=ov5647', 'OV5647 센서 오버레이'),
            ('dtparam=i2c_arm=on', 'I2C 활성화')
        ]
        
        all_good = True
        for setting, description in checks:
            if setting in config_content:
                print(f"✅ {description}: {setting}")
            else:
                print(f"❌ {description}: {setting} (누락)")
                all_good = False
        
        return all_good
        
    except Exception as e:
        print(f"❌ 설정 파일 읽기 오류: {e}")
        return False

def main():
    """메인 함수"""
    print("=" * 60)
    print("Pi Camera v2 Test")
    print("=" * 60)
    
    # 설정 확인
    print("\n1. 설정 확인")
    print("-" * 30)
    config_ok = check_config_v2()
    
    # 하드웨어 확인
    print("\n2. 하드웨어 확인")
    print("-" * 30)
    hw_ok = check_camera_v2_hardware()
    
    # 드라이버 확인
    print("\n3. 드라이버 확인")
    print("-" * 30)
    driver_ok = check_camera_v2_driver()
    
    # 기능 테스트
    print("\n4. 기능 테스트")
    print("-" * 30)
    
    raspistill_ok = test_raspistill_v2()
    time.sleep(1)
    raspivid_ok = test_raspivid_v2()
    time.sleep(1)
    libcamera_ok = test_libcamera_v2()
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    
    results = [
        ("설정", config_ok),
        ("하드웨어", hw_ok),
        ("드라이버", driver_ok),
        ("raspistill", raspistill_ok),
        ("raspivid", raspivid_ok),
        ("libcamera", libcamera_ok)
    ]
    
    all_passed = True
    for test_name, result in results:
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{test_name:12}: {status}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    if all_passed:
        print("🎉 모든 테스트 통과! Pi Camera v2가 정상 작동합니다.")
    else:
        print("⚠️ 일부 테스트 실패. 다음을 확인하세요:")
        print("1. Pi Camera v2가 올바르게 연결되었는지")
        print("2. CSI 케이블이 제대로 연결되었는지")
        print("3. /boot/config.txt 설정이 올바른지")
        print("4. 시스템을 재부팅했는지")
        print("5. 필요한 패키지가 설치되었는지")

if __name__ == "__main__":
    main() 