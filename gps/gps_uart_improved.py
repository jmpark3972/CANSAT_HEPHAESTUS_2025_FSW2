#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
gps_uart_improved.py – MAX-M10S GPS module UART interface (improved version)
"""

import time
import os
from datetime import datetime
import serial
import pynmea2

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
gps_log = open(os.path.join(LOG_DIR, "gps_uart.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    gps_log.write(f"{t},{line}\n")
    gps_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_gps_uart(port='/dev/serial0', baudrate=9600):
    """MAX-M10S GPS 객체를 UART로 초기화"""
    try:
        # 시리얼 포트 설정
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # GPS 모듈 초기화 명령어들
        init_commands = [
            "$PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28",  # GGA, RMC만 출력
            "$PMTK220,100*2F",  # 10Hz 업데이트
            "$PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28",  # 다시 설정
        ]
        
        for cmd in init_commands:
            ser.write((cmd + '\r\n').encode())
            time.sleep(0.1)
        
        _log(f"GPS UART initialized on {port} at {baudrate} baud")
        return ser
        
    except Exception as e:
        _log(f"GPS UART init error: {e}")
        return None

def terminate_gps_uart(ser):
    try:
        if ser and ser.is_open:
            ser.close()
    except Exception as e:
        _log(f"GPS UART terminate error: {e}")
    gps_log.close()

# ─────────────────────────────
# 3) GPS 데이터 읽기
# ─────────────────────────────
def read_gps_uart(ser, timeout=1.0):
    """UART로 GPS 데이터 읽기"""
    if not ser or not ser.is_open:
        return None
    
    try:
        # 타임아웃 설정
        ser.timeout = timeout
        
        # 데이터 읽기
        line = ser.readline()
        if line:
            try:
                decoded_line = line.decode('ascii', errors='replace').strip()
                if decoded_line.startswith('$'):
                    _log(f"GPS: {decoded_line}")
                    return decoded_line
            except UnicodeDecodeError:
                pass
        
        return None
        
    except Exception as e:
        _log(f"GPS UART read error: {e}")
        return None

# ─────────────────────────────
# 4) GPS 데이터 파싱
# ─────────────────────────────
def parse_gps_data(nmea_line):
    """NMEA 데이터 파싱 (개선된 버전)"""
    if not nmea_line or not nmea_line.startswith('$'):
        return None
    
    try:
        # pynmea2 라이브러리 사용
        msg = pynmea2.parse(nmea_line)
        
        if msg.sentence_type == 'GGA':
            return parse_gga_improved(msg)
        elif msg.sentence_type == 'RMC':
            return parse_rmc_improved(msg)
        else:
            return None
            
    except Exception as e:
        _log(f"NMEA parse error: {e}")
        return None

def parse_gga_improved(msg):
    """GPGGA 문장 파싱 (개선된 버전)"""
    try:
        # 시간
        if hasattr(msg, 'timestamp') and msg.timestamp:
            gps_time = msg.timestamp.strftime("%H:%M:%S")
        else:
            gps_time = "00:00:00"
        
        # 위도/경도
        lat = msg.latitude if hasattr(msg, 'latitude') and msg.latitude else 0
        lon = msg.longitude if hasattr(msg, 'longitude') and msg.longitude else 0
        
        # 고도
        altitude = msg.altitude if hasattr(msg, 'altitude') and msg.altitude else 0
        
        # 위성 수
        satellites = msg.num_sats if hasattr(msg, 'num_sats') and msg.num_sats else 0
        
        return {
            'time': gps_time,
            'latitude': lat,
            'longitude': lon,
            'altitude': altitude,
            'satellites': satellites,
            'type': 'GGA'
        }
        
    except Exception as e:
        _log(f"GGA parse error: {e}")
        return None

def parse_rmc_improved(msg):
    """GPRMC 문장 파싱 (개선된 버전)"""
    try:
        # 시간
        if hasattr(msg, 'timestamp') and msg.timestamp:
            gps_time = msg.timestamp.strftime("%H:%M:%S")
        else:
            gps_time = "00:00:00"
        
        # 위도/경도
        lat = msg.latitude if hasattr(msg, 'latitude') and msg.latitude else 0
        lon = msg.longitude if hasattr(msg, 'longitude') and msg.longitude else 0
        
        # 속도 (knots를 m/s로 변환)
        speed = msg.spd_over_grnd if hasattr(msg, 'spd_over_grnd') and msg.spd_over_grnd else 0
        speed_ms = speed * 0.514444  # knots to m/s
        
        # 방향
        course = msg.true_course if hasattr(msg, 'true_course') and msg.true_course else 0
        
        return {
            'time': gps_time,
            'latitude': lat,
            'longitude': lon,
            'speed': speed_ms,
            'course': course,
            'type': 'RMC'
        }
        
    except Exception as e:
        _log(f"RMC parse error: {e}")
        return None

# ─────────────────────────────
# 5) 메인 GPS 읽기 함수
# ─────────────────────────────
def read_gps_uart_data(ser):
    """GPS 데이터 읽기 및 파싱 (표준 형식 반환)"""
    try:
        # GPS 데이터 읽기
        nmea_data = read_gps_uart(ser)
        if not nmea_data:
            return None
        
        # NMEA 데이터 파싱
        parsed_data = parse_gps_data(nmea_data)
        if not parsed_data:
            return None
        
        # 표준 형식으로 변환 (기존 gps.py와 호환)
        if parsed_data['type'] == 'GGA':
            return [
                parsed_data['time'],
                parsed_data['altitude'],
                parsed_data['latitude'],
                parsed_data['longitude'],
                parsed_data['satellites']
            ]
        elif parsed_data['type'] == 'RMC':
            return [
                parsed_data['time'],
                0,  # RMC에는 고도 정보가 없음
                parsed_data['latitude'],
                parsed_data['longitude'],
                0   # RMC에는 위성 수 정보가 없음
            ]
        
        return None
        
    except Exception as e:
        _log(f"GPS read error: {e}")
        return None

# ─────────────────────────────
# 6) GPS 상태 확인
# ─────────────────────────────
def check_gps_fix(parsed_data):
    """GPS 수신 상태 확인"""
    if not parsed_data:
        return False, "No data"
    
    # 위성 수 확인
    if parsed_data['type'] == 'GGA' and parsed_data['satellites'] < 3:
        return False, f"Low satellites: {parsed_data['satellites']}"
    
    # 좌표 확인
    if parsed_data['latitude'] == 0 and parsed_data['longitude'] == 0:
        return False, "No position fix"
    
    return True, "GPS fix OK"

# ─────────────────────────────
# 7) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    # Windows에서는 COM 포트 사용
    import platform
    if platform.system() == "Windows":
        port = "COM3"  # 실제 포트에 맞게 수정
    else:
        port = "/dev/serial0"
    
    ser = init_gps_uart(port)
    if ser is None:
        print("GPS module not found!")
        exit(1)
    
    try:
        print("GPS UART test started...")
        while True:
            gps_data = read_gps_uart_data(ser)
            if gps_data:
                fix_ok, status = check_gps_fix(gps_data)
                print(f"GPS: Time={gps_data[0]}, Alt={gps_data[1]:.2f}m, "
                      f"Lat={gps_data[2]:.6f}, Lon={gps_data[3]:.6f}, "
                      f"Sats={gps_data[4]}, Status={status}")
            else:
                print("No GPS data")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_gps_uart(ser) 