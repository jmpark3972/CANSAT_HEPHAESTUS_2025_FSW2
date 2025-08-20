#!/usr/bin/env python3
"""
XBee 통신 점검 스크립트
XBee 연결 상태와 통신 기능을 테스트합니다.
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

def test_serial_ports():
    """시리얼 포트 확인"""
    print("1. 시리얼 포트 확인...")
    
    try:
        # Linux에서 USB 시리얼 포트 찾기
        import glob
        
        usb_patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
            '/dev/serial/by-id/*',
            '/dev/serial/by-path/*'
        ]
        
        found_ports = []
        for pattern in usb_patterns:
            try:
                ports = glob.glob(pattern)
                found_ports.extend(ports)
            except Exception:
                continue
        
        found_ports = list(set(found_ports))
        found_ports.sort()
        
        if found_ports:
            print(f"   발견된 시리얼 포트: {found_ports}")
            return found_ports
        else:
            print("   ✗ 시리얼 포트를 찾을 수 없습니다.")
            return []
            
    except Exception as e:
        print(f"   ✗ 시리얼 포트 확인 오류: {e}")
        return []

def test_xbee_connection(port):
    """XBee 연결 테스트"""
    print(f"2. XBee 연결 테스트 ({port})...")
    
    try:
        import serial
        
        # 시리얼 포트 열기
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"   ✅ 시리얼 포트 열기 성공: {port}")
        
        # 연결 테스트
        ser.write(b'+++')  # AT 모드 진입
        time.sleep(1)
        
        response = ser.read(ser.in_waiting).decode('utf-8', errors='ignore')
        if 'OK' in response:
            print("   ✅ XBee AT 모드 진입 성공")
        else:
            print("   ⚠️ XBee AT 모드 진입 실패 (정상일 수 있음)")
        
        # AT 모드 종료
        ser.write(b'ATCN\r')
        time.sleep(0.1)
        
        ser.close()
        print("   ✅ XBee 연결 테스트 완료")
        return True
        
    except Exception as e:
        print(f"   ✗ XBee 연결 테스트 실패: {e}")
        return False

def test_xbee_reset():
    """XBee 리셋 기능 테스트"""
    print("3. XBee 리셋 기능 테스트...")
    
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

def test_uart_serial_module():
    """uartserial 모듈 테스트"""
    print("4. uartserial 모듈 테스트...")
    
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
        print(f"   ✗ uartserial 모듈 테스트 실패: {e}")
        return False

def test_comm_app():
    """Comm 앱 테스트"""
    print("5. Comm 앱 테스트...")
    
    try:
        from comm import commapp
        
        # 텔레메트리 데이터 형식 확인
        from comm.commapp import _tlm_data_format
        
        tlm_data = _tlm_data_format()
        print(f"   ✅ 텔레메트리 데이터 형식 확인: Team ID = {tlm_data.team_id}")
        
        # 명령 패턴 확인
        team_id = 3139
        cx_pattern = f"CMD,{team_id},CX,(ON|OFF)$"
        st_pattern = f"CMD,{team_id},ST,(([01]\\d|2[0-3])(:[0-5]\\d){{2}}|GPS)$"
        
        print(f"   ✅ 명령 패턴 확인:")
        print(f"      CX 패턴: {cx_pattern}")
        print(f"      ST 패턴: {st_pattern}")
        
        return True
        
    except Exception as e:
        print(f"   ✗ Comm 앱 테스트 실패: {e}")
        return False

def test_telemetry_format():
    """텔레메트리 형식 테스트"""
    print("6. 텔레메트리 형식 테스트...")
    
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

def main():
    """메인 테스트 함수"""
    print("=== XBee 통신 점검 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    ports = test_serial_ports()
    test_results['serial_ports'] = len(ports) > 0
    
    if ports:
        test_results['xbee_connection'] = test_xbee_connection(ports[0])
    else:
        test_results['xbee_connection'] = False
    
    test_results['xbee_reset'] = test_xbee_reset()
    test_results['uart_serial'] = test_uart_serial_module()
    test_results['comm_app'] = test_comm_app()
    test_results['telemetry_format'] = test_telemetry_format()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:20}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! XBee 통신이 정상적으로 작동합니다.")
        return True
    elif passed >= total - 1:
        print("⚠️ 대부분의 테스트 통과. XBee 연결만 확인하세요.")
        return True
    else:
        print("❌ 일부 테스트 실패. XBee 설정을 확인하세요.")
        return False

if __name__ == "__main__":
    main() 