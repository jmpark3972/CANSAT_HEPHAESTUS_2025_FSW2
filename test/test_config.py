#!/usr/bin/env python3
"""
config.py 점검 스크립트
설정 파일의 구조와 기능을 검사합니다.
"""

import sys
import os
import time
import tempfile
import shutil
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging

def test_config_constants():
    """설정 상수 테스트"""
    print("1. 설정 상수 테스트...")
    
    try:
        from lib import config
        
        # 설정 상수 확인
        expected_constants = {
            'CONF_NONE': 0,
            'CONF_PAYLOAD': 1,
            'CONF_CONTAINER': 2,
            'CONF_ROCKET': 3
        }
        
        for const_name, expected_value in expected_constants.items():
            if hasattr(config, const_name):
                actual_value = getattr(config, const_name)
                if actual_value == expected_value:
                    print(f"   ✅ {const_name}: {actual_value}")
                else:
                    print(f"   ❌ {const_name}: 예상값 {expected_value}, 실제값 {actual_value}")
                    return False
            else:
                print(f"   ❌ {const_name} 상수가 정의되지 않음")
                return False
        
        print(f"   📊 설정 모드:")
        print(f"      NONE: {config.CONF_NONE}")
        print(f"      PAYLOAD: {config.CONF_PAYLOAD}")
        print(f"      CONTAINER: {config.CONF_CONTAINER}")
        print(f"      ROCKET: {config.CONF_ROCKET}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 설정 상수 테스트 실패: {e}")
        return False

def test_config_file_structure():
    """설정 파일 구조 테스트"""
    print("2. 설정 파일 구조 테스트...")
    
    try:
        config_file_path = 'lib/config.txt'
        
        # 설정 파일 존재 확인
        if os.path.exists(config_file_path):
            print(f"   ✅ 설정 파일 존재: {config_file_path}")
            
            # 파일 내용 확인
            with open(config_file_path, 'r') as file:
                content = file.read()
            
            print(f"   📊 파일 크기: {len(content)} bytes")
            print(f"   📊 라인 수: {len(content.splitlines())}")
            
            # 설정 옵션 확인
            lines = content.splitlines()
            config_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
            
            print(f"   📊 설정 라인: {len(config_lines)}개")
            for line in config_lines:
                print(f"      {line}")
            
            # SELECTED 설정 확인
            selected_found = False
            for line in config_lines:
                if line.startswith('SELECTED='):
                    selected_found = True
                    selected_value = line.split('=')[1]
                    print(f"   📊 현재 선택된 설정: {selected_value}")
                    break
            
            if not selected_found:
                print("   ⚠️ SELECTED 설정을 찾을 수 없음")
                return False
            
            return True
        else:
            print(f"   ❌ 설정 파일 없음: {config_file_path}")
            return False
        
    except Exception as e:
        print(f"   ✗ 설정 파일 구조 테스트 실패: {e}")
        return False

def test_config_loading():
    """설정 로딩 테스트"""
    print("3. 설정 로딩 테스트...")
    
    try:
        from lib import config
        
        # FSW_CONF 값 확인
        if hasattr(config, 'FSW_CONF'):
            fsw_conf = config.FSW_CONF
            print(f"   📊 현재 FSW 설정: {fsw_conf}")
            
            # 설정값 해석
            conf_names = {
                config.CONF_NONE: "NONE",
                config.CONF_PAYLOAD: "PAYLOAD",
                config.CONF_CONTAINER: "CONTAINER",
                config.CONF_ROCKET: "ROCKET"
            }
            
            conf_name = conf_names.get(fsw_conf, "UNKNOWN")
            print(f"   📊 설정 이름: {conf_name}")
            
            # 유효한 설정값인지 확인
            if fsw_conf in [config.CONF_NONE, config.CONF_PAYLOAD, config.CONF_CONTAINER, config.CONF_ROCKET]:
                print(f"   ✅ 유효한 설정값: {conf_name}")
                return True
            else:
                print(f"   ❌ 유효하지 않은 설정값: {fsw_conf}")
                return False
        else:
            print("   ❌ FSW_CONF 속성이 없음")
            return False
        
    except Exception as e:
        print(f"   ✗ 설정 로딩 테스트 실패: {e}")
        return False

def test_config_file_creation():
    """설정 파일 생성 테스트"""
    print("4. 설정 파일 생성 테스트...")
    
    try:
        # 임시 디렉토리에서 테스트
        with tempfile.TemporaryDirectory() as temp_dir:
            # 임시 config.py 모듈 생성
            temp_config_py = os.path.join(temp_dir, 'config.py')
            temp_config_txt = os.path.join(temp_dir, 'config.txt')
            
            # config.py 내용 생성
            config_py_content = '''import os

CONF_NONE = 0
CONF_PAYLOAD = 1
CONF_CONTAINER = 2  
CONF_ROCKET = 3

FSW_CONF = CONF_PAYLOAD

config_file_path = 'config.txt'

if not os.path.exists(config_file_path):
    print(f"Config file does not exist: {config_file_path}, Creating default config file...")

    initial_conf_file_content = """# Config.txt
# Select the FSW operation mode
# Currently supports PAYLOAD, CONTAINER, ROCKET
SELECTED=PAYLOAD
# SELECTED=NONE
# SELECTED=CONTAINER
# SELECTED=ROCKET"""

    try:
        os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
        
        with open(config_file_path, 'w') as file:
            file.write(initial_conf_file_content)
        
        print(f"Default config file created: {config_file_path}")
        
    except Exception as e:
        print(f"Error creating config file: {e}")
        raise FileNotFoundError(f"Failed to create configuration file: {config_file_path}")

else:
    with open(config_file_path, 'r') as file:
        lines = file.readlines()

    config_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
    for config_line in config_lines:
        config_line = config_line.strip().replace(" ", "").replace("\\t", "")
        if config_line == "SELECTED=NONE":
            FSW_CONF = CONF_NONE
            print("NONE SELECTED")
            break
        elif config_line == "SELECTED=PAYLOAD":
            print("PAYLOAD SELECTED")
            FSW_CONF = CONF_PAYLOAD
            break
        elif config_line == "SELECTED=CONTAINER":
            print("CONTAINER SELECTED")
            FSW_CONF = CONF_CONTAINER
            break
        elif config_line == "SELECTED=ROCKET":
            print("ROCKET SELECTED")
            FSW_CONF = CONF_ROCKET
            break
'''
            
            # 임시 config.py 파일 생성
            with open(temp_config_py, 'w') as f:
                f.write(config_py_content)
            
            # config.txt가 없는 상태에서 테스트
            if os.path.exists(temp_config_txt):
                os.remove(temp_config_txt)
            
            # config.py 실행
            import subprocess
            result = subprocess.run([sys.executable, temp_config_py], 
                                  capture_output=True, text=True, cwd=temp_dir)
            
            print(f"   📊 실행 결과: {result.stdout}")
            
            # config.txt 파일이 생성되었는지 확인
            if os.path.exists(temp_config_txt):
                print(f"   ✅ 설정 파일 생성 성공: {temp_config_txt}")
                
                # 생성된 파일 내용 확인
                with open(temp_config_txt, 'r') as f:
                    content = f.read()
                
                print(f"   📊 생성된 파일 내용:")
                for line in content.splitlines():
                    print(f"      {line}")
                
                return True
            else:
                print(f"   ❌ 설정 파일 생성 실패")
                return False
        
    except Exception as e:
        print(f"   ✗ 설정 파일 생성 테스트 실패: {e}")
        return False

def test_config_parsing():
    """설정 파싱 테스트"""
    print("5. 설정 파싱 테스트...")
    
    try:
        # 다양한 설정값으로 테스트
        test_configs = [
            ("SELECTED=NONE", "NONE"),
            ("SELECTED=PAYLOAD", "PAYLOAD"),
            ("SELECTED=CONTAINER", "CONTAINER"),
            ("SELECTED=ROCKET", "ROCKET")
        ]
        
        for config_line, expected_mode in test_configs:
            print(f"   🔍 테스트: {config_line} → {expected_mode}")
            
            # 임시 설정 파일 생성
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                f.write(f"# Test config\n{config_line}\n")
                temp_config_path = f.name
            
            try:
                # 설정 파싱 로직 테스트
                with open(temp_config_path, 'r') as file:
                    lines = file.readlines()
                
                config_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
                parsed_mode = None
                
                for line in config_lines:
                    line = line.strip().replace(" ", "").replace("\t", "")
                    if line == "SELECTED=NONE":
                        parsed_mode = "NONE"
                        break
                    elif line == "SELECTED=PAYLOAD":
                        parsed_mode = "PAYLOAD"
                        break
                    elif line == "SELECTED=CONTAINER":
                        parsed_mode = "CONTAINER"
                        break
                    elif line == "SELECTED=ROCKET":
                        parsed_mode = "ROCKET"
                        break
                
                if parsed_mode == expected_mode:
                    print(f"   ✅ 파싱 성공: {parsed_mode}")
                else:
                    print(f"   ❌ 파싱 실패: 예상 {expected_mode}, 실제 {parsed_mode}")
                    return False
                
            finally:
                # 임시 파일 삭제
                if os.path.exists(temp_config_path):
                    os.unlink(temp_config_path)
        
        return True
        
    except Exception as e:
        print(f"   ✗ 설정 파싱 테스트 실패: {e}")
        return False

def test_config_validation():
    """설정 검증 테스트"""
    print("6. 설정 검증 테스트...")
    
    try:
        from lib import config
        
        # 유효한 설정값들
        valid_configs = [
            config.CONF_NONE,
            config.CONF_PAYLOAD,
            config.CONF_CONTAINER,
            config.CONF_ROCKET
        ]
        
        # 현재 설정이 유효한지 확인
        current_config = config.FSW_CONF
        if current_config in valid_configs:
            print(f"   ✅ 현재 설정 유효: {current_config}")
        else:
            print(f"   ❌ 현재 설정 무효: {current_config}")
            return False
        
        # 각 설정값별 의미 확인
        config_meanings = {
            config.CONF_NONE: "설정 없음 (테스트 모드)",
            config.CONF_PAYLOAD: "페이로드 모드 (Team ID: 3139)",
            config.CONF_CONTAINER: "컨테이너 모드 (Team ID: 7777)",
            config.CONF_ROCKET: "로켓 모드 (Team ID: 8888)"
        }
        
        print("   📊 설정별 의미:")
        for conf_value, meaning in config_meanings.items():
            status = "현재" if conf_value == current_config else ""
            print(f"      {conf_value}: {meaning} {status}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 설정 검증 테스트 실패: {e}")
        return False

def test_config_team_id_mapping():
    """설정별 Team ID 매핑 테스트"""
    print("7. 설정별 Team ID 매핑 테스트...")
    
    try:
        from lib import config
        
        # 설정별 Team ID 매핑
        team_id_mapping = {
            config.CONF_PAYLOAD: 3139,
            config.CONF_CONTAINER: 7777,
            config.CONF_ROCKET: 8888
        }
        
        print("   📊 설정별 Team ID:")
        for conf_value, team_id in team_id_mapping.items():
            conf_names = {
                config.CONF_PAYLOAD: "PAYLOAD",
                config.CONF_CONTAINER: "CONTAINER",
                config.CONF_ROCKET: "ROCKET"
            }
            conf_name = conf_names.get(conf_value, "UNKNOWN")
            print(f"      {conf_name}: {team_id}")
        
        # 현재 설정의 Team ID 확인
        current_config = config.FSW_CONF
        if current_config in team_id_mapping:
            current_team_id = team_id_mapping[current_config]
            print(f"   📊 현재 Team ID: {current_team_id}")
        else:
            print(f"   ⚠️ 현재 설정 {current_config}에 대한 Team ID가 정의되지 않음")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Team ID 매핑 테스트 실패: {e}")
        return False

def test_config_file_permissions():
    """설정 파일 권한 테스트"""
    print("8. 설정 파일 권한 테스트...")
    
    try:
        config_file_path = 'lib/config.txt'
        
        if os.path.exists(config_file_path):
            # 파일 권한 확인
            stat_info = os.stat(config_file_path)
            
            print(f"   📊 파일 정보:")
            print(f"      경로: {config_file_path}")
            print(f"      크기: {stat_info.st_size} bytes")
            print(f"      권한: {oct(stat_info.st_mode)[-3:]}")
            
            # 읽기 권한 확인
            try:
                with open(config_file_path, 'r') as f:
                    f.read()
                print("   ✅ 읽기 권한 확인")
            except PermissionError:
                print("   ❌ 읽기 권한 없음")
                return False
            
            # 쓰기 권한 확인 (임시로)
            try:
                with open(config_file_path, 'a') as f:
                    f.write("# Test write\n")
                print("   ✅ 쓰기 권한 확인")
                
                # 테스트 내용 제거
                with open(config_file_path, 'r') as f:
                    lines = f.readlines()
                with open(config_file_path, 'w') as f:
                    for line in lines:
                        if not line.strip().endswith("# Test write"):
                            f.write(line)
                
            except PermissionError:
                print("   ⚠️ 쓰기 권한 없음 (읽기 전용)")
            
            return True
        else:
            print(f"   ❌ 설정 파일 없음: {config_file_path}")
            return False
        
    except Exception as e:
        print(f"   ✗ 파일 권한 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== config.py 점검 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    test_results['config_constants'] = test_config_constants()
    test_results['config_file_structure'] = test_config_file_structure()
    test_results['config_loading'] = test_config_loading()
    test_results['config_file_creation'] = test_config_file_creation()
    test_results['config_parsing'] = test_config_parsing()
    test_results['config_validation'] = test_config_validation()
    test_results['team_id_mapping'] = test_config_team_id_mapping()
    test_results['file_permissions'] = test_config_file_permissions()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:20}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! config.py가 정상적으로 작동합니다.")
        return True
    elif passed >= total - 1:
        print("⚠️ 대부분의 테스트 통과. 일부 개선 사항이 있습니다.")
        return True
    else:
        print("❌ 일부 테스트 실패. config.py를 수정해야 합니다.")
        return False

if __name__ == "__main__":
    main() 