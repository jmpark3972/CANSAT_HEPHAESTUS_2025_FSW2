#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
gps_i2c.py – MAX-M10S GPS module I2C interface helper
"""

import os, time
from datetime import datetime
import board, busio

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
gps_log = open(os.path.join(LOG_DIR, "gps_i2c.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    gps_log.write(f"{t},{line}\n")
    gps_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_gps_i2c():
    """MAX-M10S GPS 객체를 I2C로 초기화해 (i2c, gps) 튜플 반환."""
    try:
        # I2C 초기화 (MAX-M10S는 보통 100kHz에서 작동)
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        
        # MAX-M10S I2C 주소 (일반적으로 0x42 또는 0x43)
        # 실제 주소는 i2c.scan()으로 확인 필요
        gps_address = 0x42
        
        # I2C 스캔으로 GPS 모듈 확인
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        if gps_address not in devices:
            # 대체 주소 시도
            gps_address = 0x43
            if gps_address not in devices:
                _log(f"GPS module not found. Available devices: {[hex(d) for d in devices]}")
                return None, None
        
        _log(f"GPS module found at address: {hex(gps_address)}")
        return i2c, gps_address
        
    except Exception as e:
        _log(f"GPS I2C init error: {e}")
        return None, None

def terminate_gps_i2c(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass
    gps_log.close()

# ─────────────────────────────
# 3) I2C 통신 함수들
# ─────────────────────────────
def i2c_write(i2c, address, data):
    """I2C로 데이터 쓰기"""
    try:
        i2c.try_lock()
        i2c.writeto(address, bytes(data))
        i2c.unlock()
        return True
    except Exception as e:
        _log(f"I2C write error: {e}")
        return False

def i2c_read(i2c, address, length):
    """I2C로 데이터 읽기"""
    try:
        i2c.try_lock()
        data = bytearray(length)
        i2c.readfrom_into(address, data)
        i2c.unlock()
        return data
    except Exception as e:
        _log(f"I2C read error: {e}")
        return None

def i2c_write_read(i2c, address, write_data, read_length):
    """I2C로 쓰고 읽기"""
    try:
        i2c.try_lock()
        i2c.writeto_then_readfrom(address, bytes(write_data), data, in_end=read_length)
        i2c.unlock()
        return data
    except Exception as e:
        _log(f"I2C write_read error: {e}")
        return None

# ─────────────────────────────
# 4) GPS 명령어들
# ─────────────────────────────
def send_gps_command(i2c, address, command):
    """GPS 모듈에 명령어 전송"""
    # MAX-M10S 명령어 형식: $PMTK<command>*<checksum><CR><LF>
    cmd_str = f"$PMTK{command}"
    checksum = 0
    for char in cmd_str[1:]:  # $ 제외하고 체크섬 계산
        checksum ^= ord(char)
    
    full_cmd = f"{cmd_str}*{checksum:02X}\r\n"
    return i2c_write(i2c, address, full_cmd.encode())

def read_gps_data(i2c, address, timeout=1.0):
    """GPS 데이터 읽기"""
    start_time = time.time()
    data_buffer = b''
    
    while time.time() - start_time < timeout:
        # GPS 모듈에서 데이터 읽기 (예시)
        data = i2c_read(i2c, address, 64)  # 64바이트씩 읽기
        if data:
            data_buffer += data
            # NMEA 문장이 완성되었는지 확인
            if b'\r\n' in data_buffer:
                lines = data_buffer.split(b'\r\n')
                data_buffer = lines[-1]  # 마지막 불완전한 라인은 버퍼에 유지
                
                for line in lines[:-1]:
                    if line.startswith(b'$'):
                        try:
                            decoded_line = line.decode('utf-8').strip()
                            _log(f"GPS: {decoded_line}")
                            return decoded_line
                        except UnicodeDecodeError:
                            continue
        
        time.sleep(0.01)
    
    return None

# ─────────────────────────────
# 5) GPS 데이터 파싱
# ─────────────────────────────
def parse_nmea_data(nmea_line):
    """NMEA 데이터 파싱"""
    if not nmea_line or not nmea_line.startswith('$'):
        return None
    
    try:
        if nmea_line.startswith('$GPGGA'):
            return parse_gga(nmea_line)
        elif nmea_line.startswith('$GPRMC'):
            return parse_rmc(nmea_line)
        else:
            return None
    except Exception as e:
        _log(f"NMEA parse error: {e}")
        return None

def parse_gga(gga_line):
    """GPGGA 문장 파싱"""
    parts = gga_line.split(',')
    if len(parts) < 15:
        return None
    
    try:
        # 시간
        time_str = parts[1] if parts[1] else "000000"
        gps_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        # 위도
        lat_raw = float(parts[2]) if parts[2] else 0
        lat = convert_dm_to_dd(lat_raw)
        if parts[3] == 'S':
            lat = -lat
        
        # 경도
        lon_raw = float(parts[4]) if parts[4] else 0
        lon = convert_dm_to_dd(lon_raw)
        if parts[5] == 'W':
            lon = -lon
        
        # 고도
        altitude = float(parts[9]) if parts[9] else 0
        
        # 위성 수
        satellites = int(parts[7]) if parts[7] else 0
        
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

def parse_rmc(rmc_line):
    """GPRMC 문장 파싱"""
    parts = rmc_line.split(',')
    if len(parts) < 12:
        return None
    
    try:
        # 시간
        time_str = parts[1] if parts[1] else "000000"
        gps_time = f"{time_str[0:2]}:{time_str[2:4]}:{time_str[4:6]}"
        
        # 위도
        lat_raw = float(parts[3]) if parts[3] else 0
        lat = convert_dm_to_dd(lat_raw)
        if parts[4] == 'S':
            lat = -lat
        
        # 경도
        lon_raw = float(parts[5]) if parts[5] else 0
        lon = convert_dm_to_dd(lon_raw)
        if parts[6] == 'W':
            lon = -lon
        
        # 속도 (knots)
        speed = float(parts[7]) if parts[7] else 0
        
        # 방향
        course = float(parts[8]) if parts[8] else 0
        
        return {
            'time': gps_time,
            'latitude': lat,
            'longitude': lon,
            'speed': speed,
            'course': course,
            'type': 'RMC'
        }
    except Exception as e:
        _log(f"RMC parse error: {e}")
        return None

def convert_dm_to_dd(dm_value):
    """도분(DDMM.MMMM)을 십진도(DD.DDDDDD)로 변환"""
    degrees = int(dm_value // 100)
    minutes = dm_value - (degrees * 100)
    return degrees + (minutes / 60)

# ─────────────────────────────
# 6) 메인 GPS 읽기 함수
# ─────────────────────────────
def read_gps_i2c(i2c, address):
    """GPS 데이터 읽기 및 파싱"""
    try:
        # GPS 데이터 읽기
        nmea_data = read_gps_data(i2c, address)
        if not nmea_data:
            return None
        
        # NMEA 데이터 파싱
        parsed_data = parse_nmea_data(nmea_data)
        if not parsed_data:
            return None
        
        # 표준 형식으로 변환
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

def get_satellite_info(gps_data):
    """위성 수 정보를 상세히 반환"""
    if not gps_data or len(gps_data) < 5:
        return "No GPS data"
    
    satellites = gps_data[4]
    
    if satellites == 0:
        return f"위성 수: {satellites}개 (신호 없음)"
    elif satellites < 3:
        return f"위성 수: {satellites}개 (2D 위치 측정 불가, 3개 이상 필요)"
    elif satellites < 4:
        return f"위성 수: {satellites}개 (2D 위치 측정 가능)"
    else:
        return f"위성 수: {satellites}개 (3D 위치 측정 가능)"

# ─────────────────────────────
# 7) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    i2c, address = init_gps_i2c()
    if i2c is None or address is None:
        print("GPS module not found!")
        exit(1)
    
    try:
        print("GPS I2C 테스트 시작...")
        print("=" * 80)
        while True:
            gps_data = read_gps_i2c(i2c, address)
            if gps_data:
                sat_info = get_satellite_info(gps_data)
                print(f"시간: {gps_data[0]} | "
                      f"고도: {gps_data[1]:.2f}m | "
                      f"위도: {gps_data[2]:.6f}° | "
                      f"경도: {gps_data[3]:.6f}° | "
                      f"{sat_info}")
            else:
                print("GPS 데이터 없음")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_gps_i2c(i2c) 