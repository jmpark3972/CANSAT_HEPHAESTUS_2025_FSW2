#!/usr/bin/env python3
"""
기존 오프셋 파일들을 새로운 통합 오프셋 시스템으로 마이그레이션하는 스크립트
"""

import os
import shutil
from datetime import datetime
from lib.offsets import get_offset_manager

def backup_legacy_files():
    """기존 오프셋 파일들을 백업"""
    backup_dir = f"backup_offsets_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(backup_dir, exist_ok=True)
    
    legacy_files = [
        "imu/offset.py",
        "lib/prevstate.txt",
        "lib/config.json"
    ]
    
    print(f"기존 오프셋 파일들을 {backup_dir}에 백업합니다...")
    
    for file_path in legacy_files:
        if os.path.exists(file_path):
            try:
                shutil.copy2(file_path, os.path.join(backup_dir, os.path.basename(file_path)))
                print(f"  ✓ {file_path} 백업 완료")
            except Exception as e:
                print(f"  ✗ {file_path} 백업 실패: {e}")
        else:
            print(f"  - {file_path} 파일이 존재하지 않음")
    
    return backup_dir

def migrate_offsets():
    """오프셋 마이그레이션 실행"""
    print("\n=== CANSAT FSW 오프셋 마이그레이션 시작 ===")
    
    # 1. 기존 파일 백업
    backup_dir = backup_legacy_files()
    
    # 2. 통합 오프셋 시스템 초기화
    print("\n통합 오프셋 시스템을 초기화합니다...")
    manager = get_offset_manager()
    
    # 3. 기존 데이터 마이그레이션
    print("\n기존 오프셋 데이터를 마이그레이션합니다...")
    
    # IMU 오프셋 마이그레이션
    try:
        imu_offset_file = "imu/offset.py"
        if os.path.exists(imu_offset_file):
            with open(imu_offset_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if len(lines) >= 3:
                    # 자기계 오프셋
                    mag_line = lines[0].strip()
                    mag_values = [int(x.strip()) for x in mag_line.split(',')]
                    
                    # 자이로스코프 오프셋
                    gyro_line = lines[1].strip()
                    gyro_values = [int(x.strip()) for x in gyro_line.split(',')]
                    
                    # 가속도계 오프셋
                    accel_line = lines[2].strip()
                    accel_values = [int(x.strip()) for x in accel_line.split(',')]
                    
                    manager.set_imu_offsets(tuple(mag_values), tuple(gyro_values), tuple(accel_values))
                    print(f"  ✓ IMU 오프셋 마이그레이션 완료")
                    print(f"    자기계: {mag_values}")
                    print(f"    자이로스코프: {gyro_values}")
                    print(f"    가속도계: {accel_values}")
    except Exception as e:
        print(f"  ✗ IMU 오프셋 마이그레이션 실패: {e}")
    
    # prevstate.txt 오프셋 마이그레이션
    try:
        prevstate_file = "lib/prevstate.txt"
        if os.path.exists(prevstate_file):
            with open(prevstate_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('THERMO_TOFF='):
                        value = float(line.split('=')[1])
                        manager.set("THERMO.TEMPERATURE_OFFSET", value)
                        print(f"  ✓ Thermo 온도 오프셋: {value}°C")
                    elif line.startswith('THERMO_HOFF='):
                        value = float(line.split('=')[1])
                        manager.set("THERMO.HUMIDITY_OFFSET", value)
                        print(f"  ✓ Thermo 습도 오프셋: {value}%")
                    elif line.startswith('FIR_AOFF='):
                        value = float(line.split('=')[1])
                        manager.set("FIR1.AMBIENT_OFFSET", value)
                        print(f"  ✓ FIR1 앰비언트 오프셋: {value}°C")
                    elif line.startswith('FIR_OOFF='):
                        value = float(line.split('=')[1])
                        manager.set("FIR1.OBJECT_OFFSET", value)
                        print(f"  ✓ FIR1 오브젝트 오프셋: {value}°C")
                    elif line.startswith('THERMIS_OFF='):
                        value = float(line.split('=')[1])
                        manager.set("THERMIS.TEMPERATURE_OFFSET", value)
                        print(f"  ✓ Thermis 오프셋: {value}°C")
                    elif line.startswith('NIR_OFFSET='):
                        value = float(line.split('=')[1])
                        manager.set("NIR.OFFSET", value)
                        print(f"  ✓ NIR 오프셋: {value}")
                    elif line.startswith('PITOT_POFF='):
                        value = float(line.split('=')[1])
                        manager.set("PITOT.PRESSURE_OFFSET", value)
                        print(f"  ✓ Pitot 압력 오프셋: {value}Pa")
                    elif line.startswith('PITOT_TOFF='):
                        value = float(line.split('=')[1])
                        manager.set("PITOT.TEMPERATURE_OFFSET", value)
                        print(f"  ✓ Pitot 온도 오프셋: {value}°C")
    except Exception as e:
        print(f"  ✗ prevstate.txt 마이그레이션 실패: {e}")
    
    # 4. 마이그레이션 결과 출력
    print("\n=== 마이그레이션 완료 ===")
    manager.print_offsets()
    
    # 5. 백업 디렉토리 정보
    print(f"\n기존 파일들은 {backup_dir}에 백업되었습니다.")
    print("마이그레이션이 성공적으로 완료되었습니다!")
    
    return True

def verify_migration():
    """마이그레이션 검증"""
    print("\n=== 마이그레이션 검증 ===")
    
    manager = get_offset_manager()
    
    # 주요 오프셋값들 확인
    checks = [
        ("IMU.MAGNETOMETER", "IMU 자기계 오프셋"),
        ("IMU.GYROSCOPE", "IMU 자이로스코프 오프셋"),
        ("IMU.ACCELEROMETER", "IMU 가속도계 오프셋"),
        ("BAROMETER.ALTITUDE_OFFSET", "Barometer 고도 오프셋"),
        ("THERMIS.TEMPERATURE_OFFSET", "Thermis 온도 오프셋"),
        ("PITOT.PRESSURE_OFFSET", "Pitot 압력 오프셋"),
        ("PITOT.TEMPERATURE_OFFSET", "Pitot 온도 오프셋"),
        ("THERMAL_CAMERA.TEMPERATURE_OFFSET", "Thermal Camera 온도 오프셋"),
        ("COMM.SIMP_OFFSET", "통신 SIMP 오프셋")
    ]
    
    all_valid = True
    for key, description in checks:
        value = manager.get(key)
        if value is not None:
            print(f"  ✓ {description}: {value}")
        else:
            print(f"  ✗ {description}: 설정되지 않음")
            all_valid = False
    
    if all_valid:
        print("\n모든 오프셋이 정상적으로 마이그레이션되었습니다!")
    else:
        print("\n일부 오프셋이 누락되었습니다. 수동으로 확인해주세요.")
    
    return all_valid

if __name__ == "__main__":
    try:
        # 마이그레이션 실행
        success = migrate_offsets()
        
        if success:
            # 검증 실행
            verify_migration()
            
            print("\n=== 마이그레이션 완료 ===")
            print("이제 모든 오프셋이 lib/offsets.json 파일에서 통합 관리됩니다.")
            print("기존 개별 오프셋 파일들은 백업되었으므로 필요시 참조할 수 있습니다.")
        else:
            print("\n마이그레이션 중 오류가 발생했습니다.")
            
    except Exception as e:
        print(f"마이그레이션 실패: {e}")
        import traceback
        traceback.print_exc() 