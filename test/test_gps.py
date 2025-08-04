#!/usr/bin/env python3
"""
GPS 시스템 점검 스크립트
GPS 연결 상태와 데이터 수신을 테스트합니다.
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
    print("1. GPS 시리얼 포트 확인...")
    
    try:
        # GPS용 시리얼 포트 확인
        gps_port = '/dev/serial0'
        
        if os.path.exists(gps_port):
            print(f"   ✅ GPS 시리얼 포트 발견: {gps_port}")
            
            # 권한 확인
            try:
                with open(gps_port, 'r') as f:
                    pass
                print("   ✅ GPS 시리얼 포트 읽기 권한 확인")
                return gps_port
            except PermissionError:
                print("   ⚠️ GPS 시리얼 포트 권한 없음")
                print("   💡 해결방법: sudo usermod -a -G dialout $USER")
                return None
        else:
            print(f"   ✗ GPS 시리얼 포트 없음: {gps_port}")
            return None
            
    except Exception as e:
        print(f"   ✗ GPS 시리얼 포트 확인 오류: {e}")
        return None

def test_gps_connection(port):
    """GPS 연결 테스트"""
    print(f"2. GPS 연결 테스트 ({port})...")
    
    try:
        import serial
        
        # 시리얼 포트 열기
        ser = serial.Serial(port, 9600, timeout=1)
        print(f"   ✅ GPS 시리얼 포트 열기 성공: {port}")
        
        # 초기 데이터 읽기
        print("   🔍 GPS 데이터 읽기 중...")
        time.sleep(2)  # GPS 모듈 초기화 대기
        
        # 버퍼 클리어
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # NMEA 데이터 읽기 시도
        data_received = False
        for attempt in range(5):
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                if data:
                    print(f"   ✅ GPS 데이터 수신: {len(data)} bytes")
                    data_received = True
                    break
            time.sleep(1)
        
        if not data_received:
            print("   ⚠️ GPS 데이터 수신 없음 (정상일 수 있음)")
        
        ser.close()
        print("   ✅ GPS 연결 테스트 완료")
        return True
        
    except Exception as e:
        print(f"   ✗ GPS 연결 테스트 실패: {e}")
        return False

def test_gps_module():
    """GPS 모듈 테스트"""
    print("3. GPS 모듈 테스트...")
    
    try:
        from gps import gps
        
        # GPS 초기화
        gps_instance = gps.init_gps()
        if gps_instance:
            print("   ✅ GPS 모듈 초기화 성공")
            
            # GPS 데이터 읽기 테스트
            print("   🔍 GPS 데이터 읽기 테스트...")
            time.sleep(3)  # GPS 데이터 수집 대기
            
            # NMEA 데이터 읽기
            nmea_lines = gps.read_gps(gps_instance, timeout=5.0)
            if nmea_lines:
                print(f"   ✅ NMEA 데이터 수신: {len(nmea_lines)} 라인")
                
                # NMEA 데이터 파싱 테스트
                gps_data = gps.parse_gps_data(nmea_lines)
                if gps_data:
                    print("   ✅ NMEA 데이터 파싱 성공")
                    print(f"   📊 GGA 데이터: {gps_data[0] if len(gps_data) > 0 else 'None'}")
                    print(f"   📊 RMC 데이터: {gps_data[1] if len(gps_data) > 1 else 'None'}")
                else:
                    print("   ⚠️ NMEA 데이터 파싱 실패 (정상일 수 있음)")
            else:
                print("   ⚠️ NMEA 데이터 수신 없음 (정상일 수 있음)")
            
            # GPS 데이터 읽기 함수 테스트
            gps_result = gps.gps_readdata(gps_instance)
            print(f"   📊 GPS 결과: {gps_result}")
            
            # GPS 종료
            gps.terminate_gps(gps_instance)
            return True
        else:
            print("   ✗ GPS 모듈 초기화 실패")
            return False
            
    except Exception as e:
        print(f"   ✗ GPS 모듈 테스트 실패: {e}")
        return False

def test_gps_app():
    """GPS 앱 테스트"""
    print("4. GPS 앱 테스트...")
    
    try:
        from gps import gpsapp
        
        # GPS 앱 초기화 테스트
        gps_instance = gpsapp.gpsapp_init()
        if gps_instance:
            print("   ✅ GPS 앱 초기화 성공")
            
            # GPS 데이터 변수 확인
            print(f"   📊 GPS 데이터 변수:")
            print(f"      LAT: {gpsapp.GPS_LAT}")
            print(f"      LON: {gpsapp.GPS_LON}")
            print(f"      ALT: {gpsapp.GPS_ALT}")
            print(f"      TIME: {gpsapp.GPS_TIME}")
            print(f"      SATS: {gpsapp.GPS_SATS}")
            
            # GPS 앱 종료
            gpsapp.gpsapp_terminate()
            return True
        else:
            print("   ✗ GPS 앱 초기화 실패")
            return False
            
    except Exception as e:
        print(f"   ✗ GPS 앱 테스트 실패: {e}")
        return False

def test_nmea_parsing():
    """NMEA 데이터 파싱 테스트"""
    print("5. NMEA 데이터 파싱 테스트...")
    
    try:
        from gps import gps
        
        # 샘플 NMEA 데이터
        sample_nmea = [
            b'$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47\n',
            b'$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A\n'
        ]
        
        # NMEA 파싱 테스트
        parsed_data = gps.parse_gps_data(sample_nmea)
        if parsed_data:
            print("   ✅ NMEA 파싱 성공")
            print(f"   📊 파싱된 데이터: {parsed_data}")
            
            # GPS 데이터 읽기 테스트
            gps_result = gps.gps_readdata(None)  # 시리얼 없이 테스트
            print(f"   📊 GPS 읽기 결과: {gps_result}")
            
            return True
        else:
            print("   ✗ NMEA 파싱 실패")
            return False
            
    except Exception as e:
        print(f"   ✗ NMEA 파싱 테스트 실패: {e}")
        return False

def test_coordinate_conversion():
    """좌표 변환 테스트"""
    print("6. 좌표 변환 테스트...")
    
    try:
        from gps import gps
        
        # 위도 변환 테스트
        test_lat = "4807.038"  # 48도 07.038분
        converted_lat = gps.unit_convert_deg(test_lat)
        expected_lat = 48.0 + 7.038/60.0
        print(f"   📊 위도 변환: {test_lat} → {converted_lat:.6f} (예상: {expected_lat:.6f})")
        
        # 경도 변환 테스트 (서경 보정)
        test_lon = "01131.000"  # 11도 31.000분
        converted_lon = -gps.unit_convert_deg(test_lon)
        expected_lon = -(11.0 + 31.000/60.0)
        print(f"   📊 경도 변환: {test_lon} → {converted_lon:.6f} (예상: {expected_lon:.6f})")
        
        # 오차 확인
        lat_error = abs(converted_lat - expected_lat)
        lon_error = abs(converted_lon - expected_lon)
        
        if lat_error < 0.0001 and lon_error < 0.0001:
            print("   ✅ 좌표 변환 정확")
            return True
        else:
            print("   ⚠️ 좌표 변환 오차 있음")
            return False
            
    except Exception as e:
        print(f"   ✗ 좌표 변환 테스트 실패: {e}")
        return False

def test_gps_communication():
    """GPS 통신 테스트"""
    print("7. GPS 통신 테스트...")
    
    try:
        from lib import appargs
        from lib import msgstructure
        
        # GPS App ID 확인
        print(f"   📊 GPS App ID: {appargs.GpsAppArg.AppID}")
        print(f"   📊 GPS MID 목록:")
        print(f"      SendHK: {appargs.GpsAppArg.MID_SendHK}")
        print(f"      SendGpsTlmData: {appargs.GpsAppArg.MID_SendGpsTlmData}")
        print(f"      SendGpsFlightLogicData: {appargs.GpsAppArg.MID_SendGpsFlightLogicData}")
        
        # 메시지 구조체 테스트
        test_msg = msgstructure.MsgStructure()
        test_data = "37.5665,126.9780,100.5,12:34:56,8"
        
        # 메시지 패킹 테스트
        packed = msgstructure.pack_msg(test_msg, 
                                     appargs.GpsAppArg.AppID,
                                     appargs.CommAppArg.AppID,
                                     appargs.GpsAppArg.MID_SendGpsTlmData,
                                     test_data)
        
        if packed:
            print("   ✅ 메시지 패킹 성공")
            
            # 메시지 언패킹 테스트
            unpacked = msgstructure.unpack_msg(test_msg, packed)
            if unpacked:
                print("   ✅ 메시지 언패킹 성공")
                print(f"   📊 메시지 데이터: {test_msg.data}")
                return True
            else:
                print("   ✗ 메시지 언패킹 실패")
                return False
        else:
            print("   ✗ 메시지 패킹 실패")
            return False
            
    except Exception as e:
        print(f"   ✗ GPS 통신 테스트 실패: {e}")
        return False

def test_gps_logging():
    """GPS 로깅 테스트"""
    print("8. GPS 로깅 테스트...")
    
    try:
        # 로그 디렉토리 확인
        log_dir = './sensorlogs'
        gps_log_file = os.path.join(log_dir, 'gps.txt')
        
        if os.path.exists(log_dir):
            print(f"   ✅ 로그 디렉토리 존재: {log_dir}")
            
            if os.path.exists(gps_log_file):
                print(f"   ✅ GPS 로그 파일 존재: {gps_log_file}")
                
                # 로그 파일 크기 확인
                file_size = os.path.getsize(gps_log_file)
                print(f"   📊 로그 파일 크기: {file_size} bytes")
                
                # 최근 로그 확인
                try:
                    with open(gps_log_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"   📊 로그 라인 수: {len(lines)}")
                            print(f"   📋 최근 로그: {lines[-1].strip()}")
                        else:
                            print("   ⚠️ 로그 파일이 비어있음")
                except Exception as e:
                    print(f"   ⚠️ 로그 파일 읽기 실패: {e}")
                
                return True
            else:
                print("   ⚠️ GPS 로그 파일 없음")
                return True  # 로그 파일이 없어도 정상
        else:
            print("   ⚠️ 로그 디렉토리 없음")
            return True  # 로그 디렉토리가 없어도 정상
            
    except Exception as e:
        print(f"   ✗ GPS 로깅 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("=== GPS 시스템 점검 시작 ===")
    print(f"테스트 시간: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 테스트 결과 저장
    test_results = {}
    
    # 각 테스트 실행
    port = test_serial_ports()
    test_results['serial_ports'] = port is not None
    
    if port:
        test_results['gps_connection'] = test_gps_connection(port)
    else:
        test_results['gps_connection'] = False
    
    test_results['gps_module'] = test_gps_module()
    test_results['gps_app'] = test_gps_app()
    test_results['nmea_parsing'] = test_nmea_parsing()
    test_results['coordinate_conversion'] = test_coordinate_conversion()
    test_results['gps_communication'] = test_gps_communication()
    test_results['gps_logging'] = test_gps_logging()
    
    # 결과 요약
    print("\n=== 테스트 결과 요약 ===")
    passed = sum(test_results.values())
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✓ 통과" if result else "✗ 실패"
        print(f"{test_name:25}: {status}")
    
    print(f"\n전체 결과: {passed}/{total} 테스트 통과")
    
    if passed == total:
        print("🎉 모든 테스트 통과! GPS 시스템이 정상적으로 작동합니다.")
        return True
    elif passed >= total - 2:
        print("⚠️ 대부분의 테스트 통과. GPS 연결만 확인하세요.")
        return True
    else:
        print("❌ 일부 테스트 실패. GPS 설정을 확인하세요.")
        return False

if __name__ == "__main__":
    main() 