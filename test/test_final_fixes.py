#!/usr/bin/env python3
"""
최종 수정사항 테스트 스크립트
"""

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """모든 모듈 import 테스트"""
    print("=== Import 테스트 ===")
    
    try:
        import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from lib import appargs
        print("✅ lib.appargs import 성공")
        
        # TelemetryAppArg 확인
        if hasattr(appargs, 'TelemetryAppArg'):
            print("✅ TelemetryAppArg 존재 확인")
        else:
            print("❌ TelemetryAppArg 없음")
            
        # FlightlogicAppArg 확인
        if hasattr(appargs, 'FlightlogicAppArg'):
            print("✅ FlightlogicAppArg 존재 확인")
        else:
            print("❌ FlightlogicAppArg 없음")
            
    except Exception as e:
        print(f"❌ lib.appargs import 실패: {e}")
        return False
    
    try:
        from camera.camera import camera
        print("✅ camera.camera import 성공")
    except Exception as e:
        print(f"❌ camera.camera import 실패: {e}")
        return False
    
    try:
        from camera.cameraapp import cameraapp
        print("✅ camera.cameraapp import 성공")
    except Exception as e:
        print(f"❌ camera.cameraapp import 실패: {e}")
        return False
    
    return True

def test_camera_functions():
    """카메라 함수 테스트"""
    print("\n=== 카메라 함수 테스트 ===")
    
    try:
        from camera.camera import camera
        
        # 디렉토리 생성 테스트
        result = camera.ensure_directories()
        print(f"디렉토리 생성: {'성공' if result else '실패'}")
        
        # 하드웨어 확인 테스트
        result = camera.check_camera_hardware()
        print(f"하드웨어 확인: {'성공' if result else '실패'}")
        
        # 드라이버 확인 테스트
        result = camera.check_camera_driver()
        print(f"드라이버 확인: {'성공' if result else '실패'}")
        
        # FFmpeg 확인 테스트
        result = camera.check_ffmpeg()
        print(f"FFmpeg 확인: {'성공' if result else '실패'}")
        
        return True
        
    except Exception as e:
        print(f"❌ 카메라 함수 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("최종 수정사항 테스트 시작")
    print("=" * 50)
    
    # Import 테스트
    import_success = test_imports()
    
    # 카메라 함수 테스트
    camera_success = test_camera_functions()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"Import 테스트: {'성공' if import_success else '실패'}")
    print(f"카메라 함수 테스트: {'성공' if camera_success else '실패'}")
    
    if import_success and camera_success:
        print("\n🎉 모든 테스트가 성공했습니다!")
        print("메인 애플리케이션을 실행할 준비가 되었습니다.")
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다.")
        print("문제를 해결한 후 다시 시도하세요.")

if __name__ == "__main__":
    main() 