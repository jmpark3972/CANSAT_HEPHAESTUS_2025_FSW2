#!/usr/bin/env python3
"""
테스트 스크립트: commapp의 debug 텍스트 출력 확인
"""

import os
import sys
import time
from datetime import datetime

# 환경변수 설정
os.environ["LOG_LEVEL"] = "DEBUG"

# 프로젝트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_debug_output():
    """debug 텍스트 출력 테스트"""
    print("=== CommApp Debug Output Test ===")
    
    try:
        # commapp 모듈 임포트
        from comm.commapp import safe_log, _tlm_data_format
        
        print("✓ CommApp 모듈 임포트 성공")
        
        # 테스트용 텔레메트리 데이터 생성
        tlm_data = _tlm_data_format()
        tlm_data.team_id = 3139
        tlm_data.mission_time = "12:34:56"
        tlm_data.packet_count = 123
        tlm_data.mode = "F"
        tlm_data.state = "테스트 상태"
        tlm_data.altitude = 100.5
        tlm_data.temperature = 25.3
        tlm_data.pressure = 1013.25
        tlm_data.barometer_sea_level_pressure = 1013.25
        tlm_data.thermo_temp = 24.8
        tlm_data.thermo_humi = 45.2
        tlm_data.tmp007_object_temp = 23.1
        tlm_data.tmp007_die_temp = 25.0
        tlm_data.tmp007_voltage = 3.3
        tlm_data.thermis_temp = 26.5
        tlm_data.fir1_amb = 24.2
        tlm_data.fir1_obj = 23.8
        tlm_data.thermal_camera_avg = 24.5
        tlm_data.thermal_camera_min = 20.1
        tlm_data.thermal_camera_max = 28.9
        tlm_data.gyro_roll = 0.1
        tlm_data.gyro_pitch = -0.2
        tlm_data.gyro_yaw = 0.05
        tlm_data.acc_roll = 0.0
        tlm_data.acc_pitch = 0.0
        tlm_data.acc_yaw = 9.81
        tlm_data.mag_roll = 0.3
        tlm_data.mag_pitch = -0.1
        tlm_data.mag_yaw = 0.2
        tlm_data.filtered_roll = 0.15
        tlm_data.filtered_pitch = -0.12
        tlm_data.filtered_yaw = 0.08
        tlm_data.imu_temperature = 25.1
        tlm_data.gps_lat = 37.5665
        tlm_data.gps_lon = 126.9780
        tlm_data.gps_alt = 50.2
        tlm_data.gps_time = "12:34:56"
        tlm_data.gps_sats = 8
        tlm_data.motor_status = 1
        
        print("✓ 테스트 데이터 생성 완료")
        
        # debug 텍스트 생성 (commapp.py와 동일한 형식)
        tlm_debug_text = f"\n=== TELEMETRY DEBUG INFO ===\n" \
                f"ID : {tlm_data.team_id} TIME : {tlm_data.mission_time}, PCK_CNT : {tlm_data.packet_count}, MODE : {tlm_data.mode}, STATE : {tlm_data.state}\n"\
                f"Barometer : Altitude({tlm_data.altitude}), Temperature({tlm_data.temperature}), Pressure({tlm_data.pressure}), SeaLevelP({tlm_data.barometer_sea_level_pressure})\n" \
                 f"Thermo : Temperature({tlm_data.thermo_temp}), Humidity({tlm_data.thermo_humi})\n" \
                 f"TMP007 : Object({tlm_data.tmp007_object_temp}), Die({tlm_data.tmp007_die_temp}), Voltage({tlm_data.tmp007_voltage})\n" \
                 f"Thermis : Temperature({tlm_data.thermis_temp})\n" \
                 f"FIR1 : Ambient({tlm_data.fir1_amb}), Object({tlm_data.fir1_obj})\n" \
                 f"Thermal_camera : Average({tlm_data.thermal_camera_avg}), Min({tlm_data.thermal_camera_min}), Max({tlm_data.thermal_camera_max})\n" \
                 f"IMU : Gyro({tlm_data.gyro_roll}, {tlm_data.gyro_pitch}, {tlm_data.gyro_yaw}), " \
                 f"Accel({tlm_data.acc_roll}, {tlm_data.acc_pitch}, {tlm_data.acc_yaw}), " \
                 f"Mag({tlm_data.mag_roll}, {tlm_data.mag_pitch}, {tlm_data.mag_yaw})\n" \
                 f"Euler angle({tlm_data.filtered_roll:.6f}, {tlm_data.filtered_pitch:.4f}, {tlm_data.filtered_yaw:.4f}), " \
                 f"Temperature({tlm_data.imu_temperature:.2f}°C)\n" \
                 f"Gps : Lat({tlm_data.gps_lat}), Lon({tlm_data.gps_lon}), Alt({tlm_data.gps_alt}), " \
                 f"Time({tlm_data.gps_time}), Sats({tlm_data.gps_sats})\n" \
                 f"Motor : Status({tlm_data.motor_status}) \n" \
                 f"=== END DEBUG INFO ===\n"
        
        print("✓ Debug 텍스트 생성 완료")
        
        # 로그 출력 테스트
        print("\n--- INFO 레벨 로그 테스트 ---")
        safe_log(tlm_debug_text, "INFO", True)
        
        print("\n--- DEBUG 레벨 로그 테스트 ---")
        safe_log(tlm_debug_text, "DEBUG", True)
        
        print("\n--- 간단한 요약 정보 테스트 ---")
        safe_log(f"Telemetry Summary - ID: {tlm_data.team_id}, Time: {tlm_data.mission_time}, Mode: {tlm_data.mode}, State: {tlm_data.state}", "INFO", True)
        
        print("\n=== 테스트 완료 ===")
        print("✓ 모든 테스트가 성공적으로 완료되었습니다.")
        print("✓ 이제 실제 commapp에서도 debug 텍스트가 표시될 것입니다.")
        
    except ImportError as e:
        print(f"✗ 모듈 임포트 실패: {e}")
        print("프로젝트 경로를 확인하거나 가상환경을 활성화하세요.")
    except Exception as e:
        print(f"✗ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_debug_output() 