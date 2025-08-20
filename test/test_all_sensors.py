#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""모든 센서 통합 테스트 코드"""

import time
import sys
import os
import subprocess
import threading

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def run_sensor_test(sensor_name, test_file):
    """개별 센서 테스트 실행"""
    print(f"\n{'='*60}")
    print(f"🚀 {sensor_name} 센서 테스트 시작")
    print(f"{'='*60}")
    
    try:
        # 테스트 파일 실행
        result = subprocess.run([sys.executable, test_file], 
                              capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print(f"✅ {sensor_name} 테스트 성공")
            return True
        else:
            print(f"❌ {sensor_name} 테스트 실패")
            print(f"오류: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"⏰ {sensor_name} 테스트 타임아웃 (30초)")
        return False
    except Exception as e:
        print(f"❌ {sensor_name} 테스트 실행 오류: {e}")
        return False

def test_all_sensors():
    """모든 센서 테스트"""
    print("=" * 80)
    print("🎯 HEPHAESTUS CANSAT 모든 센서 테스트")
    print("=" * 80)
    
    # 테스트할 센서 목록
    sensors = [
        ("Barometer", "test_barometer.py"),
        ("IMU", "test_imu.py"),
        ("FIR1", "test_fir1.py"),
        ("TMP007", "test_tmp007.py"),
        ("Thermal Camera", "test_thermal_camera.py"),

        ("Thermo", "test_thermo.py"),
        ("Thermis", "test_thermis.py"),
        ("GPS", "test_gps.py"),
    ]
    
    results = {}
    
    print(f"📋 총 {len(sensors)}개 센서 테스트 예정")
    print("각 센서는 30초 타임아웃으로 테스트됩니다.")
    print("개별 센서 테스트는 Ctrl+C로 중단할 수 있습니다.")
    
    # 각 센서 테스트 실행
    for sensor_name, test_file in sensors:
        if os.path.exists(test_file):
            success = run_sensor_test(sensor_name, test_file)
            results[sensor_name] = success
        else:
            print(f"❌ {test_file} 파일을 찾을 수 없습니다.")
            results[sensor_name] = False
    
    # 결과 요약
    print(f"\n{'='*80}")
    print("📊 테스트 결과 요약")
    print(f"{'='*80}")
    
    success_count = 0
    for sensor_name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"{sensor_name:15} : {status}")
        if success:
            success_count += 1
    
    print(f"\n총 {len(sensors)}개 중 {success_count}개 센서 테스트 성공")
    
    if success_count == len(sensors):
        print("🎉 모든 센서가 정상 작동합니다!")
    else:
        print(f"⚠️  {len(sensors) - success_count}개 센서에 문제가 있습니다.")
        print("개별 테스트 파일을 실행하여 자세한 오류를 확인하세요.")

def test_single_sensor():
    """단일 센서 테스트"""
    print("=" * 60)
    print("🎯 단일 센서 테스트")
    print("=" * 60)
    
    sensors = {
        "1": ("Barometer", "test_barometer.py"),
        "2": ("IMU", "test_imu.py"),
        "3": ("FIR1", "test_fir1.py"),
        "4": ("TMP007", "test_tmp007.py"),
        "5": ("Thermal Camera", "test_thermal_camera.py"),

        "7": ("Thermo", "test_thermo.py"),
        "8": ("Thermis", "test_thermis.py"),
        "9": ("GPS", "test_gps.py"),
    }
    
    print("테스트할 센서를 선택하세요:")
    for key, (name, _) in sensors.items():
        print(f"  {key}. {name}")
    print("  0. 모든 센서 테스트")
    
    try:
        choice = input("\n선택 (0-9): ").strip()
        
        if choice == "0":
            test_all_sensors()
        elif choice in sensors:
            sensor_name, test_file = sensors[choice]
            run_sensor_test(sensor_name, test_file)
        else:
            print("❌ 잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--all":
            test_all_sensors()
        else:
            print("사용법:")
            print("  python test_all_sensors.py          # 단일 센서 선택")
            print("  python test_all_sensors.py --all    # 모든 센서 테스트")
    else:
        test_single_sensor() 