#!/usr/bin/env python3
"""
Hybrid GPS System Test for CANSAT HEPHAESTUS 2025
하이브리드 GPS + WiFi + Cell Tower 시스템 테스트
"""

import os
import sys
import time
import subprocess
from datetime import datetime

def test_dependencies():
    """필요한 라이브러리 확인"""
    print("=== 의존성 확인 ===")
    
    required_packages = [
        'board',
        'busio', 
        'adafruit_gps',
        'adafruit_bus_device',
        'requests',
        'dataclasses'
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
        print("pip3 install adafruit-circuitpython-gps adafruit-blinka requests")
        return False
    
    return True

def test_i2c_devices():
    """I2C 장치 스캔 테스트"""
    print("\n=== I2C 장치 스캔 ===")
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

def test_wifi_scan():
    """WiFi 스캔 테스트"""
    print("\n=== WiFi 스캔 테스트 ===")
    try:
        # WiFi 인터페이스 확인
        result = subprocess.run(['iwconfig'], capture_output=True, text=True)
        if result.returncode == 0:
            print("WiFi 인터페이스 확인됨")
            
            # WiFi 스캔 시도
            scan_result = subprocess.run(['sudo', 'iwlist', 'wlan0', 'scan'], 
                                       capture_output=True, text=True, timeout=15)
            if scan_result.returncode == 0:
                networks = []
                for line in scan_result.stdout.split('\n'):
                    if 'ESSID:' in line:
                        essid = line.split('"')[1] if '"' in line else line.split(':')[1].strip()
                        if essid and essid != '':
                            networks.append(essid)
                
                print(f"✓ WiFi 네트워크 {len(networks)}개 발견")
                if networks:
                    print(f"   발견된 네트워크: {', '.join(networks[:5])}")
                return True
            else:
                print("✗ WiFi 스캔 실패")
                return False
        else:
            print("✗ WiFi 인터페이스 없음")
            return False
    except Exception as e:
        print(f"WiFi 스캔 오류: {e}")
        return False

def test_hybrid_gps_module():
    """하이브리드 GPS 모듈 테스트"""
    print("\n=== 하이브리드 GPS 모듈 테스트 ===")
    try:
        # 하이브리드 GPS 모듈 임포트
        from gps import hybrid_gps
        from gps.hybrid_gps import LocationSource
        
        print("✓ 하이브리드 GPS 모듈 임포트 성공")
        
        # 하이브리드 GPS 시스템 초기화
        print("하이브리드 GPS 시스템 초기화 중...")
        hybrid_system = hybrid_gps.init_hybrid_gps()
        
        if not hybrid_system:
            print("✗ 하이브리드 GPS 시스템 초기화 실패")
            return False
        
        print("✓ 하이브리드 GPS 시스템 초기화 성공")
        
        # 위치 정보 획득 테스트
        print("하이브리드 위치 정보 획득 테스트 (30초)...")
        start_time = time.time()
        fix_count = 0
        
        while time.time() - start_time < 30:
            location_data = hybrid_gps.read_hybrid_location()
            
            if location_data:
                fix_count += 1
                print(f"Fix #{fix_count}: Lat={location_data.latitude:.6f}, Lon={location_data.longitude:.6f}")
                print(f"   정확도: {location_data.accuracy:.1f}m, 소스: {location_data.source.value}")
                
                if location_data.satellites:
                    print(f"   위성 수: {location_data.satellites}")
                
                if fix_count >= 5:
                    print("✓ 하이브리드 GPS 테스트 성공!")
                    break
            else:
                print(".", end="", flush=True)
            
            time.sleep(2)
        
        if fix_count == 0:
            print("\n⚠️ 하이브리드 위치 정보를 얻지 못했습니다")
            print("GPS 안테나, WiFi 연결, 또는 API 키를 확인하세요")
        
        # 위치 시스템 상태 확인
        status = hybrid_gps.get_location_status()
        print(f"\n위치 시스템 상태:")
        print(f"  GPS 사용 가능: {status.get('gps_available', False)}")
        print(f"  GPS 픽스: {status.get('gps_has_fix', False)}")
        print(f"  GPS 위성 수: {status.get('gps_satellites', 0)}")
        print(f"  WiFi 사용 가능: {status.get('wifi_available', False)}")
        
        # 리소스 정리
        hybrid_gps.cleanup_hybrid_gps()
        
        return fix_count > 0
        
    except Exception as e:
        print(f"✗ 하이브리드 GPS 모듈 테스트 실패: {e}")
        return False

def test_hybrid_gps_app():
    """하이브리드 GPS 앱 테스트"""
    print("\n=== 하이브리드 GPS 앱 테스트 ===")
    try:
        # 하이브리드 GPS 앱 임포트
        from gps import hybrid_gpsapp
        print("✓ 하이브리드 GPS 앱 임포트 성공")
        
        # 하이브리드 GPS 앱 클래스 테스트
        hybrid_app = hybrid_gpsapp.HybridGpsApp()
        print("✓ 하이브리드 GPS 앱 클래스 생성 성공")
        
        # 앱 중지
        hybrid_app.stop()
        print("✓ 하이브리드 GPS 앱 중지 성공")
        
        return True
        
    except Exception as e:
        print(f"✗ 하이브리드 GPS 앱 테스트 실패: {e}")
        return False

def test_google_api_key():
    """Google API 키 확인"""
    print("\n=== Google API 키 확인 ===")
    
    api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
    if api_key:
        print("✓ Google Maps API 키 설정됨")
        print(f"   키 길이: {len(api_key)} 문자")
        return True
    else:
        print("⚠️ Google Maps API 키가 설정되지 않음")
        print("   WiFi 위치 기능이 제한될 수 있습니다")
        print("   환경변수 설정: export GOOGLE_MAPS_API_KEY='your_api_key'")
        return False

def test_project_structure():
    """프로젝트 구조 확인"""
    print("\n=== 프로젝트 구조 확인 ===")
    
    required_files = [
        'gps/hybrid_gps.py',
        'gps/hybrid_gpsapp.py',
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
    print("하이브리드 GPS 시스템 테스트")
    print("=" * 50)
    
    # 테스트 결과
    results = {}
    
    # 1. 프로젝트 구조 확인
    results['project_structure'] = test_project_structure()
    
    # 2. 의존성 확인
    results['dependencies'] = test_dependencies()
    
    # 3. I2C 장치 스캔
    results['i2c_scan'] = test_i2c_devices()
    
    # 4. WiFi 스캔 테스트
    results['wifi_scan'] = test_wifi_scan()
    
    # 5. Google API 키 확인
    results['google_api'] = test_google_api_key()
    
    # 6. 하이브리드 GPS 모듈 테스트
    if results['dependencies']:
        results['hybrid_gps_module'] = test_hybrid_gps_module()
    else:
        results['hybrid_gps_module'] = False
    
    # 7. 하이브리드 GPS 앱 테스트
    if results['project_structure']:
        results['hybrid_gps_app'] = test_hybrid_gps_app()
    else:
        results['hybrid_gps_app'] = False
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name}: {status}")
    
    # 전체 결과
    all_passed = all(results.values())
    print(f"\n전체 결과: {'✓ 모든 테스트 통과' if all_passed else '✗ 일부 테스트 실패'}")
    
    if all_passed:
        print("\n🎉 하이브리드 GPS 시스템이 성공적으로 설정되었습니다!")
        print("이제 main.py를 실행하여 전체 CANSAT 시스템을 테스트할 수 있습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("위의 오류 메시지를 확인하고 문제를 해결한 후 다시 테스트하세요.")
        
        # 실패한 테스트에 대한 해결 방법 제시
        if not results.get('dependencies', True):
            print("\n💡 해결 방법:")
            print("1. 필요한 패키지를 설치하세요:")
            print("   pip3 install adafruit-circuitpython-gps adafruit-blinka requests")
        
        if not results.get('google_api', True):
            print("\n💡 Google API 키 설정:")
            print("1. Google Cloud Console에서 API 키를 생성하세요")
            print("2. 환경변수로 설정하세요:")
            print("   export GOOGLE_MAPS_API_KEY='your_api_key'")
    
    return all_passed

if __name__ == "__main__":
    main()
