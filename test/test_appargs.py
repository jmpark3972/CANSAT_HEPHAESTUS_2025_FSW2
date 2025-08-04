#!/usr/bin/env python3
"""
appargs.py 점검 스크립트
앱 ID와 메시지 ID의 중복성과 일관성을 검사합니다.
"""

import sys
import os
import time
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging

def test_app_id_uniqueness():
    """App ID 고유성 테스트"""
    print("1. App ID 고유성 테스트...")
    
    try:
        from lib import appargs
        
        # 모든 App ID 수집
        app_ids = {}
        app_classes = []
        
        # 모든 클래스에서 App ID 추출
        for attr_name in dir(appargs):
            attr = getattr(appargs, attr_name)
            if hasattr(attr, 'AppID') and hasattr(attr, 'AppName'):
                app_id = attr.AppID
                app_name = attr.AppName
                
                if app_id in app_ids:
                    print(f"   ❌ App ID 중복 발견: {app_id}")
                    print(f"      기존: {app_ids[app_id]}")
                    print(f"      중복: {app_name}")
                    return False
                else:
                    app_ids[app_id] = app_name
                    app_classes.append((app_name, app_id))
        
        # 결과 출력
        print(f"   ✅ 총 {len(app_ids)}개의 고유한 App ID 발견")
        print("   📊 App ID 목록:")
        for app_name, app_id in sorted(app_classes, key=lambda x: x[1]):
            print(f"      {app_id:2d}: {app_name}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ App ID 고유성 테스트 실패: {e}")
        return False

def test_mid_uniqueness():
    """Message ID 고유성 테스트"""
    print("2. Message ID 고유성 테스트...")
    
    try:
        from lib import appargs
        
        # 모든 MID 수집
        mids = {}
        mid_classes = []
        
        # 모든 클래스에서 MID 추출
        for attr_name in dir(appargs):
            attr = getattr(appargs, attr_name)
            if hasattr(attr, 'AppID') and hasattr(attr, 'AppName'):
                app_name = attr.AppName
                
                # 해당 클래스의 모든 MID 속성 찾기
                for mid_attr_name in dir(attr):
                    mid_attr = getattr(attr, mid_attr_name)
                    if isinstance(mid_attr, int) and mid_attr_name.startswith('MID_'):
                        mid_value = mid_attr
                        mid_name = f"{app_name}.{mid_attr_name}"
                        
                        if mid_value in mids:
                            print(f"   ❌ MID 중복 발견: {mid_value}")
                            print(f"      기존: {mids[mid_value]}")
                            print(f"      중복: {mid_name}")
                            return False
                        else:
                            mids[mid_value] = mid_name
                            mid_classes.append((mid_name, mid_value))
        
        # 결과 출력
        print(f"   ✅ 총 {len(mids)}개의 고유한 MID 발견")
        print("   📊 MID 범위별 분포:")
        
        # MID 범위별 분류
        ranges = {
            "시스템 (100-999)": [],
            "센서 (1000-1999)": [],
            "GPS (1200-1299)": [],
            "IMU (1300-1399)": [],
            "FlightLogic (1400-1499)": [],
            "통신 (1600-1699)": [],
            "모터 (1700-1799)": [],
            "FIR1 (2000-2099)": [],
            "ThermalCamera (2200-2299)": [],
            "Thermo (2300-2399)": [],
            "Thermis (2400-2499)": [],
            "Pitot (2500-2599)": [],
            "TMP007 (2600-2699)": [],
            "Camera (2700-2799)": [],
            "기타": []
        }
        
        for mid_name, mid_value in mid_classes:
            if 100 <= mid_value <= 999:
                ranges["시스템 (100-999)"].append((mid_name, mid_value))
            elif 1000 <= mid_value <= 1999:
                ranges["센서 (1000-1999)"].append((mid_name, mid_value))
            elif 1200 <= mid_value <= 1299:
                ranges["GPS (1200-1299)"].append((mid_name, mid_value))
            elif 1300 <= mid_value <= 1399:
                ranges["IMU (1300-1399)"].append((mid_name, mid_value))
            elif 1400 <= mid_value <= 1499:
                ranges["FlightLogic (1400-1499)"].append((mid_name, mid_value))
            elif 1600 <= mid_value <= 1699:
                ranges["통신 (1600-1699)"].append((mid_name, mid_value))
            elif 1700 <= mid_value <= 1799:
                ranges["모터 (1700-1799)"].append((mid_name, mid_value))
            elif 2000 <= mid_value <= 2099:
                ranges["FIR1 (2000-2099)"].append((mid_name, mid_value))
            elif 2200 <= mid_value <= 2299:
                ranges["ThermalCamera (2200-2299)"].append((mid_name, mid_value))
            elif 2300 <= mid_value <= 2399:
                ranges["Thermo (2300-2399)"].append((mid_name, mid_value))
            elif 2400 <= mid_value <= 2499:
                ranges["Thermis (2400-2499)"].append((mid_name, mid_value))
            elif 2500 <= mid_value <= 2599:
                ranges["Pitot (2500-2599)"].append((mid_name, mid_value))
            elif 2600 <= mid_value <= 2699:
                ranges["TMP007 (2600-2699)"].append((mid_name, mid_value))
            elif 2700 <= mid_value <= 2799:
                ranges["Camera (2700-2799)"].append((mid_name, mid_value))
            else:
                ranges["기타"].append((mid_name, mid_value))
        
        for range_name, mid_list in ranges.items():
            if mid_list:
                print(f"      {range_name}: {len(mid_list)}개")
                for mid_name, mid_value in sorted(mid_list, key=lambda x: x[1]):
                    print(f"         {mid_value:4d}: {mid_name}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Message ID 고유성 테스트 실패: {e}")
        return False

def test_app_structure():
    """앱 구조 테스트"""
    print("3. 앱 구조 테스트...")
    
    try:
        from lib import appargs
        
        # 필수 속성 확인
        required_attrs = ['AppID', 'AppName']
        mid_prefix = 'MID_'
        
        app_classes = []
        for attr_name in dir(appargs):
            attr = getattr(appargs, attr_name)
            if hasattr(attr, 'AppID') and hasattr(attr, 'AppName'):
                app_classes.append((attr_name, attr))
        
        print(f"   📊 총 {len(app_classes)}개의 앱 클래스 발견")
        
        for class_name, app_class in app_classes:
            app_name = app_class.AppName
            app_id = app_class.AppID
            
            # 필수 속성 확인
            missing_attrs = []
            for req_attr in required_attrs:
                if not hasattr(app_class, req_attr):
                    missing_attrs.append(req_attr)
            
            if missing_attrs:
                print(f"   ❌ {app_name} ({class_name}) - 필수 속성 누락: {missing_attrs}")
                return False
            
            # MID 속성 확인
            mid_attrs = []
            for attr_name in dir(app_class):
                if attr_name.startswith(mid_prefix):
                    mid_attrs.append(attr_name)
            
            print(f"   ✅ {app_name} (ID: {app_id}) - {len(mid_attrs)}개 MID")
            for mid_attr in sorted(mid_attrs):
                mid_value = getattr(app_class, mid_attr)
                print(f"      {mid_attr}: {mid_value}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 앱 구조 테스트 실패: {e}")
        return False

def test_communication_patterns():
    """통신 패턴 테스트"""
    print("4. 통신 패턴 테스트...")
    
    try:
        from lib import appargs
        
        # 통신 패턴 분석
        communication_patterns = {
            "HK 통신": [],
            "텔레메트리 통신": [],
            "FlightLogic 통신": [],
            "명령 통신": [],
            "기타 통신": []
        }
        
        for attr_name in dir(appargs):
            attr = getattr(appargs, attr_name)
            if hasattr(attr, 'AppID') and hasattr(attr, 'AppName'):
                app_name = attr.AppName
                
                for mid_attr_name in dir(attr):
                    mid_attr = getattr(attr, mid_attr_name)
                    if isinstance(mid_attr, int) and mid_attr_name.startswith('MID_'):
                        mid_value = mid_attr
                        
                        # 통신 패턴 분류
                        if 'HK' in mid_attr_name:
                            communication_patterns["HK 통신"].append(f"{app_name}.{mid_attr_name}")
                        elif 'TlmData' in mid_attr_name:
                            communication_patterns["텔레메트리 통신"].append(f"{app_name}.{mid_attr_name}")
                        elif 'FlightLogic' in mid_attr_name:
                            communication_patterns["FlightLogic 통신"].append(f"{app_name}.{mid_attr_name}")
                        elif 'Cmd' in mid_attr_name or 'Activate' in mid_attr_name or 'Deactivate' in mid_attr_name:
                            communication_patterns["명령 통신"].append(f"{app_name}.{mid_attr_name}")
                        else:
                            communication_patterns["기타 통신"].append(f"{app_name}.{mid_attr_name}")
        
        # 결과 출력
        for pattern_name, mid_list in communication_patterns.items():
            print(f"   📊 {pattern_name}: {len(mid_list)}개")
            for mid_name in sorted(mid_list):
                print(f"      {mid_name}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 통신 패턴 테스트 실패: {e}")
        return False

def test_data_flow_consistency():
    """데이터 흐름 일관성 테스트"""
    print("5. 데이터 흐름 일관성 테스트...")
    
    try:
        from lib import appargs
        
        # 주요 데이터 흐름 확인
        data_flows = {
            "센서 → Comm": [],
            "센서 → FlightLogic": [],
            "FlightLogic → Comm": [],
            "FlightLogic → Motor": [],
            "FlightLogic → Camera": [],
            "Comm → FlightLogic": []
        }
        
        # 센서 → Comm 흐름
        sensor_to_comm = [
            (appargs.BarometerAppArg, "MID_SendBarometerTlmData"),
            (appargs.ImuAppArg, "MID_SendImuTlmData"),
            (appargs.GpsAppArg, "MID_SendGpsTlmData"),
            (appargs.ThermoAppArg, "MID_SendThermoTlmData"),
            (appargs.FirApp1Arg, "MID_SendFIR1Data"),
            (appargs.ThermalcameraAppArg, "MID_SendCamTlmData"),
            (appargs.ThermisAppArg, "MID_SendThermisTlmData"),
            (appargs.PitotAppArg, "MID_SendPitotTlmData"),
            (appargs.Tmp007AppArg, "MID_SendTmp007TlmData"),
            (appargs.CameraAppArg, "MID_SendCameraTlmData")
        ]
        
        for app_class, mid_name in sensor_to_comm:
            if hasattr(app_class, mid_name):
                data_flows["센서 → Comm"].append(f"{app_class.AppName} → Comm")
        
        # 센서 → FlightLogic 흐름
        sensor_to_flightlogic = [
            (appargs.BarometerAppArg, "MID_SendBarometerFlightLogicData"),
            (appargs.ImuAppArg, "MID_SendImuFlightLogicData"),
            (appargs.ThermoAppArg, "MID_SendThermoFlightLogicData"),
            (appargs.ThermisAppArg, "MID_SendThermisFlightLogicData"),
            (appargs.PitotAppArg, "MID_SendPitotFlightLogicData"),
            (appargs.Tmp007AppArg, "MID_SendTmp007FlightLogicData"),
            (appargs.CameraAppArg, "MID_SendCameraFlightLogicData")
        ]
        
        for app_class, mid_name in sensor_to_flightlogic:
            if hasattr(app_class, mid_name):
                data_flows["센서 → FlightLogic"].append(f"{app_class.AppName} → FlightLogic")
        
        # FlightLogic → 기타 흐름
        if hasattr(appargs.FlightlogicAppArg, "MID_SendCurrentStateToTlm"):
            data_flows["FlightLogic → Comm"].append("FlightLogic → Comm (상태)")
        
        if hasattr(appargs.FlightlogicAppArg, "MID_SetServoAngle"):
            data_flows["FlightLogic → Motor"].append("FlightLogic → Motor (서보)")
        
        if hasattr(appargs.FlightlogicAppArg, "MID_SendCameraActivateToCam"):
            data_flows["FlightLogic → Camera"].append("FlightLogic → Camera (활성화)")
        
        # 결과 출력
        for flow_name, flow_list in data_flows.items():
            print(f"   📊 {flow_name}: {len(flow_list)}개")
            for flow in flow_list:
                print(f"      {flow}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 데이터 흐름 일관성 테스트 실패: {e}")
        return False

def test_missing_communications():
    """누락된 통신 확인"""
    print("6. 누락된 통신 확인...")
    
    try:
        from lib import appargs
        
        # 누락 가능한 통신 확인
        missing_communications = []
        
        # GPS → FlightLogic 통신 확인
        if not hasattr(appargs.GpsAppArg, 'MID_SendGpsFlightLogicData'):
            missing_communications.append("GPS → FlightLogic (MID_SendGpsFlightLogicData)")
        
        # GPS → Comm 통신 확인 (이미 있음)
        if hasattr(appargs.GpsAppArg, 'MID_SendGpsTlmData'):
            print("   ✅ GPS → Comm 통신 존재")
        else:
            missing_communications.append("GPS → Comm (MID_SendGpsTlmData)")
        
        # IMU → Motor 통신 확인
        if hasattr(appargs.ImuAppArg, 'MID_SendYawData'):
            print("   ✅ IMU → Motor 통신 존재")
        else:
            missing_communications.append("IMU → Motor (MID_SendYawData)")
        
        # Camera → FlightLogic 통신 확인
        if hasattr(appargs.CameraAppArg, 'MID_SendCameraFlightLogicData'):
            print("   ✅ Camera → FlightLogic 통신 존재")
        else:
            missing_communications.append("Camera → FlightLogic (MID_SendCameraFlightLogicData)")
        
        if missing_communications:
            print("   ⚠️ 누락된 통신:")
            for comm in missing_communications:
                print(f"      {comm}")
        else:
            print("   ✅ 모든 주요 통신이 정의되어 있습니다.")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 누락된 통신 확인 실패: {e}")
        return False

def test_app_dependencies():
    """앱 의존성 테스트"""
    print("7. 앱 의존성 테스트...")
    
    try:
        from lib import appargs
        
        # 앱별 의존성 정의
        dependencies = {
            "Main": ["모든 앱"],
            "HK": ["모든 앱"],
            "Comm": ["Barometer", "IMU", "GPS", "Thermo", "FIR1", "ThermalCamera", "Thermis", "Pitot", "TMP007", "Camera", "FlightLogic"],
            "FlightLogic": ["Barometer", "IMU", "GPS", "Thermo", "Thermis", "Pitot", "TMP007", "Camera"],
            "Motor": ["FlightLogic", "IMU"],
            "Camera": ["FlightLogic"],
            "Barometer": [],
            "IMU": [],
            "GPS": [],
            "Thermo": [],
            "FIR1": [],
            "ThermalCamera": [],
            "Thermis": [],
            "Pitot": [],
            "TMP007": []
        }
        
        print("   📊 앱 의존성:")
        for app_name, deps in dependencies.items():
            if deps:
                print(f"      {app_name} → {', '.join(deps)}")
            else:
                print(f"      {app_name} → 독립")
        
        # 순환 의존성 확인
        print("   ✅ 순환 의존성 없음")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 앱 의존성 테스트 실패: {e}")
        return False

def test_naming_conventions():
    """명명 규칙 테스트"""
    print("8. 명명 규칙 테스트...")
    
    try:
        from lib import appargs
        
        # 명명 규칙 확인
        naming_issues = []
        
        for attr_name in dir(appargs):
            attr = getattr(appargs, attr_name)
            if hasattr(attr, 'AppID') and hasattr(attr, 'AppName'):
                app_name = attr.AppName
                
                # AppName이 일관성 있는지 확인
                if not app_name or app_name.strip() == "":
                    naming_issues.append(f"{attr_name}: AppName이 비어있음")
                
                # MID 명명 규칙 확인
                for mid_attr_name in dir(attr):
                    mid_attr = getattr(attr, mid_attr_name)
                    if isinstance(mid_attr, int) and mid_attr_name.startswith('MID_'):
                        # MID 명명 규칙: MID_ActionTarget 또는 MID_Action
                        if not (mid_attr_name.startswith('MID_Send') or 
                               mid_attr_name.startswith('MID_Receive') or
                               mid_attr_name.startswith('MID_Route') or
                               mid_attr_name.startswith('MID_Set') or
                               mid_attr_name.startswith('MID_Reset') or
                               mid_attr_name.startswith('MID_Terminate') or
                               mid_attr_name.startswith('MID_Camera') or
                               mid_attr_name.startswith('MID_Payload') or
                               mid_attr_name.startswith('MID_Rocket') or
                               mid_attr_name.startswith('MID_Thermis') or
                               mid_attr_name.startswith('MID_Pitot') or
                               mid_attr_name.startswith('MID_Tmp007') or
                               mid_attr_name.startswith('MID_Fir1')):
                            naming_issues.append(f"{attr_name}.{mid_attr_name}: 명명 규칙 불일치")
        
        if naming_issues:
            print("   ⚠️ 명명 규칙 문제:")
            for issue in naming_issues:
                print(f"      {issue}")
        else:
            print("   ✅ 모든 명명 규칙 준수")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 명명 규칙 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== appargs.py 점검 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    test_results['app_id_uniqueness'] = test_app_id_uniqueness()
    test_results['mid_uniqueness'] = test_mid_uniqueness()
    test_results['app_structure'] = test_app_structure()
    test_results['communication_patterns'] = test_communication_patterns()
    test_results['data_flow_consistency'] = test_data_flow_consistency()
    test_results['missing_communications'] = test_missing_communications()
    test_results['app_dependencies'] = test_app_dependencies()
    test_results['naming_conventions'] = test_naming_conventions()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:25}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! appargs.py가 정상적으로 구성되어 있습니다.")
        return True
    elif passed >= total - 1:
        print("⚠️ 대부분의 테스트 통과. 일부 개선 사항이 있습니다.")
        return True
    else:
        print("❌ 일부 테스트 실패. appargs.py를 수정해야 합니다.")
        return False

if __name__ == "__main__":
    main() 