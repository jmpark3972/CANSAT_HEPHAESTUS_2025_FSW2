#!/usr/bin/env python3
"""
MAX-M10S GPS Integration Test for CANSAT HEPHAESTUS 2025
기존 CANSAT 프로젝트와 MAX-M10S GPS 통합 테스트
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def test_i2c_devices():
    """I2C 장치 스캔 테스트"""
    print("=== I2C 장치 스캔 ===")
    try:
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("I2C 장치 목록:")
            print(result.stdout)
            return True
        else:
            print("I2C 스캔 실패")
            return False
    except Exception as e:
        print(f"I2C 스캔 오류: {e}")
        return False

def test_gps_module():
    """MAX-M10S GPS 모듈 테스트"""
    print("\n=== MAX-M10S GPS 모듈 테스트 ===")
    try:
        # GPS 모듈 직접 테스트
        from gps import gps_max_m10s
        
        print("GPS 모듈 초기화 중...")
        i2c, gps = gps_max_m10s.init_gps()
        
        if gps is None:
            print("✗ GPS 모듈 초기화 실패")
            return False
        
        print("✓ GPS 모듈 초기화 성공")
        
        # GPS 데이터 읽기 테스트
        print("GPS 데이터 읽기 테스트 (30초)...")
        start_time = time.time()
        fix_count = 0
        
        while time.time() - start_time < 30:
            data = gps_max_m10s.read_gps(gps)
            
            if data and data.get('has_fix'):
                fix_count += 1
                print(f"Fix #{fix_count}: Lat={data['latitude']:.6f}, Lon={data['longitude']:.6f}")
                
                if fix_count >= 3:
                    print("✓ GPS 데이터 읽기 성공!")
                    break
            else:
                print(".", end="", flush=True)
            
            time.sleep(1)
        
        if fix_count == 0:
            print("\n⚠️ GPS 픽스를 얻지 못했습니다")
            print("안테나 연결과 하늘 보기 상태를 확인하세요")
        
        # 리소스 정리
        gps_max_m10s.terminate_gps(i2c)
        
        return fix_count > 0
        
    except Exception as e:
        print(f"✗ GPS 모듈 테스트 실패: {e}")
        return False

def test_gps_app():
    """GPS 앱 통합 테스트"""
    print("\n=== GPS 앱 통합 테스트 ===")
    try:
        # GPS 앱 임포트 테스트
        from gps import gpsapp
        print("✓ GPS 앱 임포트 성공")
        
        # GPS 앱 클래스 테스트
        gps_app = gpsapp.GpsApp()
        print("✓ GPS 앱 클래스 생성 성공")
        
        # 앱 중지
        gps_app.stop()
        print("✓ GPS 앱 중지 성공")
        
        return True
        
    except Exception as e:
        print(f"✗ GPS 앱 테스트 실패: {e}")
        return False

def test_dependencies():
    """필요한 라이브러리 확인"""
    print("=== 의존성 확인 ===")
    
    required_packages = [
        'board',
        'busio', 
        'adafruit_gps',
        'adafruit_bus_device'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (설치 필요)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n설치가 필요한 패키지: {', '.join(missing_packages)}")
        print("다음 명령어로 설치하세요:")
        print("pip3 install adafruit-circuitpython-gps adafruit-blinka")
        return False
    
    return True

def test_project_structure():
    """프로젝트 구조 확인"""
    print("\n=== 프로젝트 구조 확인 ===")
    
    required_files = [
        'gps/gps_max_m10s.py',
        'gps/gpsapp.py',
        'lib/appargs.py',
        'lib/msgstructure.py',
        'lib/logging.py'
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"✓ {file_path}")
        else:
            print(f"✗ {file_path} (파일 없음)")
            missing_files.append(file_path)
    
    if missing_files:
        print(f"\n누락된 파일: {', '.join(missing_files)}")
        return False
    
    return True

def main():
    """메인 테스트 함수"""
    print("MAX-M10S GPS 통합 테스트")
    print("=" * 40)
    
    # 테스트 결과
    results = {}
    
    # 1. 프로젝트 구조 확인
    results['project_structure'] = test_project_structure()
    
    # 2. 의존성 확인
    results['dependencies'] = test_dependencies()
    
    # 3. I2C 장치 스캔
    results['i2c_scan'] = test_i2c_devices()
    
    # 4. GPS 모듈 테스트
    if results['dependencies']:
        results['gps_module'] = test_gps_module()
    else:
        results['gps_module'] = False
    
    # 5. GPS 앱 통합 테스트
    if results['project_structure']:
        results['gps_app'] = test_gps_app()
    else:
        results['gps_app'] = False
    
    # 결과 요약
    print("\n" + "=" * 40)
    print("테스트 결과 요약")
    print("=" * 40)
    
    for test_name, result in results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name}: {status}")
    
    # 전체 결과
    all_passed = all(results.values())
    print(f"\n전체 결과: {'✓ 모든 테스트 통과' if all_passed else '✗ 일부 테스트 실패'}")
    
    if all_passed:
        print("\n🎉 MAX-M10S GPS 통합이 성공적으로 완료되었습니다!")
        print("이제 main.py를 실행하여 전체 CANSAT 시스템을 테스트할 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("위의 오류 메시지를 확인하고 문제를 해결한 후 다시 테스트하세요.")
    
    return all_passed

if __name__ == "__main__":
    main()
