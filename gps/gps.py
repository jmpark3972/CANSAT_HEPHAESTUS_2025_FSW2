import time
import os
import serial
from datetime import datetime

# serial0은 기본적으로 GPIO 14 (TX) / GPIO 15 (RX)에 매핑되어 있음
SERIAL_PORT = '/dev/serial0'
BAUDRATE = 9600

# 로그 디렉토리 설정
log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)
gpslogfile = open(os.path.join(log_dir, 'gps.txt'), 'a')

def log_gps(text):
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    gpslogfile.write(f'{t},{text}\n')
    gpslogfile.flush()


def init_gps():
    try:
        # MTK3339 GPS 모듈 초기화 개선
        ser = serial.Serial(
            port=SERIAL_PORT,
            baudrate=BAUDRATE,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        # 시리얼 포트가 열렸는지 확인
        if ser.is_open:
            print(f"GPS serial port {SERIAL_PORT} opened successfully")
            log_gps("GPS serial port opened successfully")
            
            # GPS 모듈 초기화를 위한 대기 시간
            time.sleep(2)
            
            # 초기 데이터 읽기 (캐시 클리어)
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            
            return ser
        else:
            print(f"Failed to open GPS serial port {SERIAL_PORT}")
            log_gps(f"Failed to open GPS serial port {SERIAL_PORT}")
            return None
            
    except serial.SerialException as e:
        print(f"Serial init failed: {e}")
        log_gps(f"Serial init failed: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error during GPS init: {e}")
        log_gps(f"Unexpected error during GPS init: {e}")
        return None


def read_gps(ser, timeout=2.0):
    NMEA_lines = []
    buffer = b''
    start = time.time()
    
    if not ser or not ser.is_open:
        print("GPS serial port is not open")
        return NMEA_lines
    
    while time.time() - start < timeout:
        try:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)
                buffer += data
                
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    if line.strip():  # 빈 라인 제외
                        NMEA_lines.append(line + b'\n')
            else:
                time.sleep(0.01)
        except serial.SerialException as e:
            print(f"Serial read error: {e}")
            log_gps(f"Serial read error: {e}")
            break
        except Exception as e:
            print(f"Unexpected error during GPS read: {e}")
            log_gps(f"Unexpected error during GPS read: {e}")
            break
    
    return NMEA_lines


def parse_gps_data(NMEA_lines):
    gga_data = None
    rmc_data = None
    
    for line in NMEA_lines:
        try:
            decoded_line = line.decode('utf-8').strip()
            log_gps(f"Raw NMEA: {decoded_line}")
            
            if decoded_line.startswith('$GPGGA'):
                parts = decoded_line.split(',')
                if len(parts) > 7:
                    gga_data = parts
                    log_gps(f"GGA parsed: {parts}")
            elif decoded_line.startswith('$GPRMC'):
                parts = decoded_line.split(',')
                if len(parts) > 10:
                    rmc_data = parts
                    log_gps(f"RMC parsed: {parts}")
        except UnicodeDecodeError as e:
            log_gps(f"Unicode decode error: {e}")
            continue
        except Exception as e:
            log_gps(f"Parse error: {e}")
            continue
    
    if gga_data and rmc_data:
        return [gga_data, rmc_data]
    return None


def unit_convert_deg(raw_angle):
    try:
        raw_angle = float(raw_angle)
        deg = int(raw_angle // 100)
        minutes = raw_angle - deg * 100
        return deg + minutes / 60
    except (ValueError, TypeError):
        return 0.0


def gps_readdata(ser):
    if not ser or not ser.is_open:
        log_gps("GPS serial port not available")
        return ["00:00:00", 0, 0, 0, 0]
    
    NMEA_lines = read_gps(ser)
    gps_data = parse_gps_data(NMEA_lines)
    
    if gps_data:
        try:
            # GPS 시간 파싱 (UTC → KST 변환)
            gps_time_raw = gps_data[0][1]
            if gps_time_raw and len(gps_time_raw) >= 6:
                # UTC 시간을 파싱
                utc_hour = int(gps_time_raw[0:2])
                utc_minute = int(gps_time_raw[2:4])
                utc_second = int(gps_time_raw[4:6])
                
                # UTC → KST 변환 (UTC + 9시간)
                kst_hour = utc_hour + 9
                if kst_hour >= 24:
                    kst_hour -= 24
                
                gps_time = f"{kst_hour:02d}:{utc_minute:02d}:{utc_second:02d}"
            else:
                gps_time = "00:00:00"
        except:
            gps_time = "00:00:00"
        
        try:
            # 고도 파싱
            alt_raw = gps_data[0][9]
            alt = round(float(alt_raw), 2) if alt_raw else 0
        except:
            alt = 0
        
        try:
            # 위도 파싱
            lat_raw = gps_data[0][2]
            lat = unit_convert_deg(float(lat_raw)) if lat_raw else 0
        except:
            lat = 0
        
        try:
            # 경도 파싱 (서경 보정)
            lon_raw = gps_data[0][4]
            lon = -unit_convert_deg(float(lon_raw)) if lon_raw else 0
        except:
            lon = 0
        
        try:
            # 위성 수 파싱
            sats_raw = gps_data[0][7]
            fixed_sat = int(sats_raw) if sats_raw else 0
        except:
            fixed_sat = 0
        
        result = [gps_time, alt, lat, lon, fixed_sat]
        log_gps(f"GPS data: {result}")
        return result
    else:
        log_gps("No valid GPS data received")
        return ["00:00:00", 0, 0, 0, 0]


def terminate_gps(ser):
    if ser and ser.is_open:
        try:
            ser.close()
            print("GPS serial port closed")
            log_gps("GPS serial port closed")
        except Exception as e:
            print(f"Error closing GPS serial port: {e}")
            log_gps(f"Error closing GPS serial port: {e}")


if __name__ == "__main__":
    print("GPS Module Test - MTK3339")
    ser = init_gps()
    if ser:
        try:
            print("Starting GPS data reading...")
            while True:
                data = gps_readdata(ser)
                print(f"GPS Data: {data}")
                time.sleep(1)
        except KeyboardInterrupt:
            print("GPS test interrupted")
        finally:
            terminate_gps(ser)
    else:
        print("Failed to initialize GPS module")
