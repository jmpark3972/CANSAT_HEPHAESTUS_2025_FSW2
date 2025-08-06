#!/usr/bin/env python3
"""
main.py import 테스트
"""

import os
import sys

def test_imports():
    """모든 import 테스트"""
    print("🔍 main.py import 테스트")
    print("=" * 40)
    
    # 프로젝트 루트를 Python 경로에 추가
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)
    
    # main.py에서 사용하는 모든 모듈들
    modules_to_test = [
        # 기본 라이브러리
        ("sys", "sys"),
        ("os", "os"),
        ("signal", "signal"),
        ("atexit", "atexit"),
        ("time", "time"),
        ("datetime", "datetime"),
        ("multiprocessing", "multiprocessing"),
        
        # 커스텀 라이브러리
        ("lib.appargs", "appargs"),
        ("lib.msgstructure", "msgstructure"),
        ("lib.logging", "logging"),
        ("lib.types", "types"),
        ("lib.config", "config"),
        ("lib.resource_manager", "resource_manager"),
        ("lib.prevstate", "prevstate"),
        
        # 앱 모듈들
        ("comm.commapp", "commapp"),
        ("flight_logic.flightlogicapp", "flightlogicapp"),
        ("hk.hkapp", "hkapp"),
        ("barometer.barometerapp", "barometerapp"),
        ("imu.imuapp", "imuapp"),
        ("thermo.thermoapp", "thermoapp"),
        ("thermis.thermisapp", "thermisapp"),
        ("tmp007.tmp007app", "tmp007app"),
        ("pitot.pitotapp", "pitotapp"),
        ("thermal_camera.thermo_cameraapp", "thermo_cameraapp"),
        ("camera.cameraapp", "cameraapp"),
        ("motor.motorapp", "motorapp"),
        ("fir1.firapp1", "firapp1"),
    ]
    
    failed_imports = []
    
    for module_name, display_name in modules_to_test:
        try:
            if module_name.startswith("lib."):
                # lib 모듈들은 특별 처리
                module = __import__(module_name, fromlist=[display_name])
            else:
                module = __import__(module_name)
            print(f"✅ {display_name}")
        except ImportError as e:
            print(f"❌ {display_name} - {e}")
            failed_imports.append((display_name, str(e)))
        except Exception as e:
            print(f"❌ {display_name} - {e}")
            failed_imports.append((display_name, str(e)))
    
    print("\n" + "=" * 40)
    if failed_imports:
        print("❌ Import 실패 목록:")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
    else:
        print("🎉 모든 import 성공!")
    
    return len(failed_imports) == 0

def test_config():
    """config 테스트"""
    print("\n🔧 Config 테스트")
    print("-" * 20)
    
    try:
        from lib import config
        
        # FSW_MODE 확인
        fsw_mode = config.get_config("FSW_MODE")
        print(f"FSW_MODE: {fsw_mode}")
        
        if fsw_mode == "NONE":
            print("❌ FSW_MODE가 NONE으로 설정되어 있습니다!")
            return False
        else:
            print("✅ FSW_MODE 정상")
            return True
            
    except Exception as e:
        print(f"❌ Config 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🚀 main.py 시작 준비 테스트")
    print("=" * 50)
    
    # Import 테스트
    import_success = test_imports()
    
    # Config 테스트
    config_success = test_config()
    
    print("\n" + "=" * 50)
    print("📊 테스트 결과")
    print("=" * 50)
    
    if import_success and config_success:
        print("🎉 모든 테스트 통과! main.py를 실행할 수 있습니다.")
        print("\n💡 다음 명령어로 main.py를 실행하세요:")
        print("cd .. && python3 main.py")
    else:
        print("❌ 일부 테스트 실패. main.py 실행에 문제가 있습니다.")
        print("\n💡 해결 방법:")
        if not import_success:
            print("1. 누락된 모듈 설치")
            print("2. 가상환경 활성화 확인")
        if not config_success:
            print("3. config.json 파일 확인")
            print("4. FSW_MODE 설정 확인")

if __name__ == "__main__":
    main() 