#!/usr/bin/env python3
"""
main.py import 테스트
"""

import os
import sys

def main():
    print("🔍 main.py import 테스트")
    print("=" * 40)
    
    # 프로젝트 루트를 Python 경로에 추가
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    sys.path.insert(0, project_root)
    
    print(f"프로젝트 루트: {project_root}")
    
    # main.py에서 사용하는 모듈들
    modules_to_test = [
        # 표준 라이브러리
        'sys', 'os', 'signal', 'atexit', 'time', 'datetime',
        'multiprocessing', 'multiprocessing.Process', 'multiprocessing.Queue', 
        'multiprocessing.Pipe', 'multiprocessing.connection',
        
        # 커스텀 라이브러리
        'lib.appargs', 'lib.msgstructure', 'lib.logging', 'lib.types',
        'lib.config', 'lib.resource_manager', 'lib.prevstate',
        
        # 앱 모듈들
        'hk.hkapp', 'barometer.barometerapp', 'gps.gpsapp', 'imu.imuapp',
        'flight_logic.flightlogicapp', 'comm.commapp', 'motor.motorapp',
        'fir1.firapp1', 'thermis.thermisapp', 'pitot.pitotapp',
        'thermo.thermoapp', 'tmp007.tmp007app', 'camera.cameraapp',
        'thermal_camera.thermo_cameraapp'
    ]
    
    failed_imports = []
    
    for module_name in modules_to_test:
        try:
            __import__(module_name)
            print(f"✅ {module_name}")
        except ImportError as e:
            print(f"❌ {module_name} - {e}")
            failed_imports.append((module_name, str(e)))
        except Exception as e:
            print(f"⚠️ {module_name} - 예상치 못한 오류: {e}")
            failed_imports.append((module_name, str(e)))
    
    print("\n" + "=" * 40)
    if failed_imports:
        print(f"❌ {len(failed_imports)}개 모듈 import 실패:")
        for module, error in failed_imports:
            print(f"  - {module}: {error}")
    else:
        print("🎉 모든 모듈 import 성공!")

if __name__ == "__main__":
    main() 