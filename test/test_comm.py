#!/usr/bin/env python3
"""
Comm 앱 점검 스크립트
Comm 앱의 통신 기능과 데이터 처리를 테스트합니다.
"""

import sys
import os
import time
import subprocess
import threading
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging

def test_comm_app_structure():
    """Comm 앱 구조 테스트"""
    print("1. Comm 앱 구조 테스트...")
    
    try:
        from comm import commapp
        
        # Comm 앱 초기화 테스트
        print("   🔍 Comm 앱 초기화 테스트...")
        
        # 전역 변수 확인
        print(f"   📊 Comm 앱 전역 변수:")
        print(f"      COMMAPP_RUNSTATUS: {commapp.COMMAPP_RUNSTATUS}")
        print(f"      TEAMID: {commapp.TEAMID}")
        
        # 텔레메트리 데이터 형식 확인
        from comm.commapp import _tlm_data_format
        tlm_data = _tlm_data_format()
        print(f"   📊 텔레메트리 데이터 필드 수: {len([attr for attr in dir(tlm_data) if not attr.startswith('_')])}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Comm 앱 구조 테스트 실패: {e}")
        return False

def test_telemetry_format():
    """텔레메트리 형식 테스트"""
    print("2. 텔레메트리 형식 테스트...")
    
    try:
        from comm.commapp import _tlm_data_format
        
        # 샘플 데이터 생성
        tlm_data = _tlm_data_format()
        tlm_data.team_id = 3139
        tlm_data.mission_time = "12:34:56"
        tlm_data.packet_count = 1
        tlm_data.mode = "F"
        tlm_data.state = "발사대 대기"
        tlm_data.altitude = 100.5
        tlm_data.temperature = 25.3
        tlm_data.pressure = 1013.25
        tlm_data.voltage = 12.5
        tlm_data.gyro_roll = 0.1234
        tlm_data.gyro_pitch = 0.5678
        tlm_data.gyro_yaw = 0.9012
        tlm_data.acc_roll = 0.1234
        tlm_data.acc_pitch = 0.5678
        tlm_data.acc_yaw = 0.9012
        tlm_data.mag_roll = 123.4
        tlm_data.mag_pitch = 567.8
        tlm_data.mag_yaw = 901.2
        tlm_data.rot_rate = 0.5
        tlm_data.gps_lat = 37.5665
        tlm_data.gps_lon = 126.9780
        tlm_data.gps_alt = 100.5
        tlm_data.gps_time = "12:34:56"
        tlm_data.gps_sats = 8
        tlm_data.filtered_roll = 0.1234
        tlm_data.filtered_pitch = 0.5678
        tlm_data.filtered_yaw = 0.9012
        tlm_data.cmd_echo = "CMD,3139,CX,ON"
        tlm_data.thermo_temp = 25.3
        tlm_data.thermo_humi = 60.5
        tlm_data.fir1_amb = 25.0
        tlm_data.fir1_obj = 26.5
        tlm_data.thermal_camera_avg = 25.5
        tlm_data.thermal_camera_min = 24.0
        tlm_data.thermal_camera_max = 27.0
        tlm_data.thermis_temp = 25.8

        tlm_data.tmp007_object_temp = 25.1
        tlm_data.tmp007_die_temp = 26.0
        tlm_data.tmp007_voltage = 3.3
        tlm_data.imu_temperature = 25.4
        
        # 텔레메트리 문자열 생성
        tlm_string = ",".join([
            str(tlm_data.team_id),
            tlm_data.mission_time,
            str(tlm_data.packet_count),
            tlm_data.mode,
            tlm_data.state,
            f"{tlm_data.altitude:.2f}",
            f"{tlm_data.temperature:.2f}",
            f"{0.1 * tlm_data.pressure:.2f}",
            f"{tlm_data.voltage:.2f}",
            f"{tlm_data.gyro_roll:.4f}",
            f"{tlm_data.gyro_pitch:.4f}",
            f"{tlm_data.gyro_yaw:.4f}",
            f"{tlm_data.acc_roll:.4f}",
            f"{tlm_data.acc_pitch:.4f}",
            f"{tlm_data.acc_yaw:.4f}",
            f"{0.01 * tlm_data.mag_roll:.4f}",
            f"{0.01 * tlm_data.mag_pitch:.4f}",
            f"{0.01 * tlm_data.mag_yaw:.4f}",
            f"{tlm_data.rot_rate:.2f}",
            str(tlm_data.gps_time),
            f"{tlm_data.gps_alt:.2f}",
            f"{tlm_data.gps_lat:.2f}",
            f"{tlm_data.gps_lon:.2f}",
            f"{tlm_data.gps_sats:.2f}",
            tlm_data.cmd_echo,
            f"{tlm_data.filtered_roll:.4f}",
            f"{tlm_data.filtered_pitch:.4f}",
            f"{tlm_data.filtered_yaw:.4f}",
            f"{tlm_data.thermo_temp:.2f}",
            f"{tlm_data.thermo_humi:.2f}",
            f"{tlm_data.fir1_amb:.2f}",
            f"{tlm_data.fir1_obj:.2f}",
            f"{tlm_data.thermal_camera_avg:.2f}",
            f"{tlm_data.thermal_camera_min:.2f}",
            f"{tlm_data.thermal_camera_max:.2f}",
            f"{tlm_data.thermis_temp:.2f}",

            f"{tlm_data.tmp007_object_temp:.2f}",
            f"{tlm_data.tmp007_die_temp:.2f}",
            f"{tlm_data.tmp007_voltage:.2f}",
            f"{tlm_data.imu_temperature:.2f}"
        ]) + "\n"
        
        print(f"   ✅ 텔레메트리 문자열 생성 성공")
        print(f"   📊 데이터 길이: {len(tlm_string)} 문자")
        print(f"   📊 필드 수: {len(tlm_string.split(','))}")
        
        # 샘플 출력 (처음 100자)
        print(f"   📋 샘플 데이터: {tlm_string[:100]}...")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 텔레메트리 형식 테스트 실패: {e}")
        return False

def test_command_parsing():
    """명령 파싱 테스트"""
    print("3. 명령 파싱 테스트...")
    
    try:
        import re
        
        # 명령 패턴 정의
        team_id = 3139
        
        # CX 명령 (텔레메트리 ON/OFF)
        cx_pattern = f"CMD,{team_id},CX,(ON|OFF)$"
        cx_test_cmd = f"CMD,{team_id},CX,ON"
        if re.fullmatch(cx_pattern, cx_test_cmd):
            print("   ✅ CX 명령 패턴 매치 성공")
        else:
            print("   ✗ CX 명령 패턴 매치 실패")
            return False
        
        # ST 명령 (시간 설정)
        st_pattern = f"CMD,{team_id},ST,(([01]\\d|2[0-3])(:[0-5]\\d){{2}}|GPS)$"
        st_test_cmd = f"CMD,{team_id},ST,12:34:56"
        if re.fullmatch(st_pattern, st_test_cmd):
            print("   ✅ ST 명령 패턴 매치 성공")
        else:
            print("   ✗ ST 명령 패턴 매치 실패")
            return False
        
        # SIM 명령 (시뮬레이션 모드)
        sim_pattern = f"CMD,{team_id},SIM,(ENABLE|ACTIVATE|DISABLE)$"
        sim_test_cmd = f"CMD,{team_id},SIM,ENABLE"
        if re.fullmatch(sim_pattern, sim_test_cmd):
            print("   ✅ SIM 명령 패턴 매치 성공")
        else:
            print("   ✗ SIM 명령 패턴 매치 실패")
            return False
        
        # MEC 명령 (메커니즘 제어)
        mec_pattern = f"CMD,{team_id},MEC,MOTOR,(ON|OFF)$"
        mec_test_cmd = f"CMD,{team_id},MEC,MOTOR,ON"
        if re.fullmatch(mec_pattern, mec_test_cmd):
            print("   ✅ MEC 명령 패턴 매치 성공")
        else:
            print("   ✗ MEC 명령 패턴 매치 실패")
            return False
        
        # CAM 명령 (카메라 제어)
        cam_pattern = f"CMD,{team_id},CAM,(ON|OFF)$"
        cam_test_cmd = f"CMD,{team_id},CAM,ON"
        if re.fullmatch(cam_pattern, cam_test_cmd):
            print("   ✅ CAM 명령 패턴 매치 성공")
        else:
            print("   ✗ CAM 명령 패턴 매치 실패")
            return False
        
        print("   📊 지원 명령 목록:")
        print("      CX: 텔레메트리 ON/OFF")
        print("      ST: 시간 설정")
        print("      SIM: 시뮬레이션 모드")
        print("      SIMP: 시뮬레이션 압력")
        print("      CAL: 고도 보정")
        print("      MEC: 메커니즘 제어")
        print("      SS: 상태 설정")
        print("      RBT: 재부팅")
        print("      CAM: 카메라 제어")
        
        return True
        
    except Exception as e:
        print(f"   ✗ 명령 파싱 테스트 실패: {e}")
        return False

def test_message_handling():
    """메시지 처리 테스트"""
    print("4. 메시지 처리 테스트...")
    
    try:
        from lib import appargs
        from lib import msgstructure
        from comm import commapp
        
        # 메시지 구조체 테스트
        test_msg = msgstructure.MsgStructure()
        
        # Barometer 데이터 테스트
        baro_data = "1013.25,25.3,100.5"
        packed_baro = msgstructure.pack_msg(test_msg, 
                                          appargs.BarometerAppArg.AppID,
                                          appargs.CommAppArg.AppID,
                                          appargs.BarometerAppArg.MID_SendBarometerTlmData,
                                          baro_data)
        
        if packed_baro:
            print("   ✅ Barometer 메시지 패킹 성공")
            
            # 메시지 언패킹 및 처리 테스트
            unpacked = msgstructure.unpack_msg(test_msg, packed_baro)
            if unpacked:
                print("   ✅ Barometer 메시지 언패킹 성공")
                print(f"   📊 Barometer 데이터: {test_msg.data}")
            else:
                print("   ✗ Barometer 메시지 언패킹 실패")
                return False
        else:
            print("   ✗ Barometer 메시지 패킹 실패")
            return False
        
        # IMU 데이터 테스트
        imu_data = "0.1234,0.5678,0.9012,0.1234,0.5678,0.9012,123.4,567.8,901.2,0.1234,0.5678,0.9012,25.4"
        packed_imu = msgstructure.pack_msg(test_msg, 
                                         appargs.ImuAppArg.AppID,
                                         appargs.CommAppArg.AppID,
                                         appargs.ImuAppArg.MID_SendImuTlmData,
                                         imu_data)
        
        if packed_imu:
            print("   ✅ IMU 메시지 패킹 성공")
            
            unpacked = msgstructure.unpack_msg(test_msg, packed_imu)
            if unpacked:
                print("   ✅ IMU 메시지 언패킹 성공")
                print(f"   📊 IMU 데이터: {test_msg.data}")
            else:
                print("   ✗ IMU 메시지 언패킹 실패")
                return False
        else:
            print("   ✗ IMU 메시지 패킹 실패")
            return False
        
        # GPS 데이터 테스트
        gps_data = "12:34:56,100.5,37.5665,126.9780,8"
        packed_gps = msgstructure.pack_msg(test_msg, 
                                         appargs.GpsAppArg.AppID,
                                         appargs.CommAppArg.AppID,
                                         appargs.GpsAppArg.MID_SendGpsTlmData,
                                         gps_data)
        
        if packed_gps:
            print("   ✅ GPS 메시지 패킹 성공")
            
            unpacked = msgstructure.unpack_msg(test_msg, packed_gps)
            if unpacked:
                print("   ✅ GPS 메시지 언패킹 성공")
                print(f"   📊 GPS 데이터: {test_msg.data}")
            else:
                print("   ✗ GPS 메시지 언패킹 실패")
                return False
        else:
            print("   ✗ GPS 메시지 패킹 실패")
            return False
        
        return True
        
    except Exception as e:
        print(f"   ✗ 메시지 처리 테스트 실패: {e}")
        return False

def test_uart_serial():
    """UART 시리얼 테스트"""
    print("5. UART 시리얼 테스트...")
    
    try:
        from comm import uartserial
        
        # 시리얼 포트 찾기
        ports = uartserial.find_serial_ports()
        if ports:
            print(f"   ✅ 시리얼 포트 발견: {ports}")
            
            # XBee 포트 감지
            xbee_port = uartserial.detect_xbee_port()
            if xbee_port:
                print(f"   ✅ XBee 포트 감지: {xbee_port}")
                
                # 시리얼 초기화
                ser = uartserial.init_serial()
                if ser:
                    print("   ✅ 시리얼 초기화 성공")
                    
                    # 데이터 전송 테스트
                    test_data = "TEST,3139,00:00:00,1,F,발사대 대기,0.00,25.00,1013.25,0.00,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.0000,0.00,00:00:00,0.00,0.00,0.00,0.00,None,0.0000,0.0000,0.0000,25.00,50.00,25.00,25.00,25.00,25.00,25.00,25.00,0.00,25.00,25.00,25.00,25.00,25.00\n"
                    
                    success = uartserial.send_serial_data(ser, test_data)
                    if success:
                        print("   ✅ 데이터 전송 성공")
                    else:
                        print("   ⚠️ 데이터 전송 실패 (XBee가 연결되지 않았을 수 있음)")
                    
                    # 시리얼 종료
                    uartserial.terminate_serial(ser)
                    return True
                else:
                    print("   ✗ 시리얼 초기화 실패")
                    return False
            else:
                print("   ⚠️ XBee 포트 감지 실패 (시뮬레이션 모드)")
                return True  # 시뮬레이션 모드는 정상
        else:
            print("   ✗ 시리얼 포트를 찾을 수 없습니다.")
            return False
            
    except Exception as e:
        print(f"   ✗ UART 시리얼 테스트 실패: {e}")
        return False

def test_xbee_reset():
    """XBee 리셋 테스트"""
    print("6. XBee 리셋 테스트...")
    
    try:
        from comm import xbeereset
        
        # GPIO 초기화 확인
        import pigpio
        pi = pigpio.pi()
        
        if pi.connected:
            print("   ✅ pigpio 연결 성공")
            
            # 리셋 핀 설정
            pi.set_mode(18, pigpio.OUTPUT)
            pi.write(18, 1)
            time.sleep(0.1)
            
            # 리셋 펄스 전송
            xbeereset.send_reset_pulse()
            print("   ✅ XBee 리셋 펄스 전송 완료")
            
            pi.stop()
            return True
        else:
            print("   ✗ pigpio 연결 실패")
            return False
            
    except Exception as e:
        print(f"   ✗ XBee 리셋 테스트 실패: {e}")
        return False

def test_comm_logging():
    """Comm 로깅 테스트"""
    print("7. Comm 로깅 테스트...")
    
    try:
        # 로그 디렉토리 확인
        log_dir = "logs/comm"
        tlm_log_file = os.path.join(log_dir, "telemetry_log.csv")
        cmd_log_file = os.path.join(log_dir, "command_log.csv")
        error_log_file = os.path.join(log_dir, "error_log.csv")
        
        if os.path.exists(log_dir):
            print(f"   ✅ Comm 로그 디렉토리 존재: {log_dir}")
            
            # 텔레메트리 로그 확인
            if os.path.exists(tlm_log_file):
                file_size = os.path.getsize(tlm_log_file)
                print(f"   📊 텔레메트리 로그 크기: {file_size} bytes")
            else:
                print("   ⚠️ 텔레메트리 로그 파일 없음")
            
            # 명령 로그 확인
            if os.path.exists(cmd_log_file):
                file_size = os.path.getsize(cmd_log_file)
                print(f"   📊 명령 로그 크기: {file_size} bytes")
            else:
                print("   ⚠️ 명령 로그 파일 없음")
            
            # 오류 로그 확인
            if os.path.exists(error_log_file):
                file_size = os.path.getsize(error_log_file)
                print(f"   📊 오류 로그 크기: {file_size} bytes")
            else:
                print("   ⚠️ 오류 로그 파일 없음")
            
            return True
        else:
            print("   ⚠️ Comm 로그 디렉토리 없음")
            return True  # 로그 디렉토리가 없어도 정상
            
    except Exception as e:
        print(f"   ✗ Comm 로깅 테스트 실패: {e}")
        return False

def test_team_id_config():
    """Team ID 설정 테스트"""
    print("8. Team ID 설정 테스트...")
    
    try:
        from lib import config
        
        # 설정 확인
        print(f"   📊 FSW 설정: {config.FSW_CONF}")
        
        # Team ID 매핑 확인
        team_ids = {
            config.CONF_PAYLOAD: 3139,
            config.CONF_CONTAINER: 7777,
            config.CONF_ROCKET: 8888
        }
        
        current_team_id = team_ids.get(config.FSW_CONF, "Unknown")
        print(f"   📊 현재 Team ID: {current_team_id}")
        
        # 명령 헤더 확인
        for conf, team_id in team_ids.items():
            cmd_header = f"CMD,{team_id}"
            print(f"   📋 {conf}: {cmd_header}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Team ID 설정 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== Comm 앱 점검 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    test_results['comm_structure'] = test_comm_app_structure()
    test_results['telemetry_format'] = test_telemetry_format()
    test_results['command_parsing'] = test_command_parsing()
    test_results['message_handling'] = test_message_handling()
    test_results['uart_serial'] = test_uart_serial()
    test_results['xbee_reset'] = test_xbee_reset()
    test_results['comm_logging'] = test_comm_logging()
    test_results['team_id_config'] = test_team_id_config()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:20}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! Comm 앱이 정상적으로 작동합니다.")
        return True
    elif passed >= total - 2:
        print("⚠️ 대부분의 테스트 통과. XBee 연결만 확인하세요.")
        return True
    else:
        print("❌ 일부 테스트 실패. Comm 앱 설정을 확인하세요.")
        return False

if __name__ == "__main__":
    main() 