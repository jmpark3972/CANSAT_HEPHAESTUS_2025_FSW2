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
        ser = serial.Serial(SERIAL_PORT, BAUDRATE, timeout=1)
        return ser
    except serial.SerialException as e:
        print(f"Serial init failed: {e}")
        return None


def read_gps(ser, timeout=1.0):
    NMEA_lines = []
    buffer = b''
    start = time.time()
    while time.time() - start < timeout:
        if ser.in_waiting:
            buffer += ser.read(ser.in_waiting)
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                NMEA_lines.append(line + b'\n')
        else:
            time.sleep(0.01)
    return NMEA_lines


def parse_gps_data(NMEA_lines):
    gga_data = None
    rmc_data = None
    for line in NMEA_lines:
        try:
            decoded_line = line.decode('utf-8').strip()
        except UnicodeDecodeError:
            continue
        if decoded_line.startswith('$GPGGA'):
            parts = decoded_line.split(',')
            if len(parts) > 7:
                gga_data = parts
        elif decoded_line.startswith('$GPRMC'):
            parts = decoded_line.split(',')
            if len(parts) > 10:
                rmc_data = parts
    if gga_data and rmc_data:
        return [gga_data, rmc_data]
    return None


def unit_convert_deg(raw_angle):
    deg = int(raw_angle // 100)
    minutes = raw_angle - deg * 100
    return deg + minutes / 60


def gps_readdata(ser):
    NMEA_lines = read_gps(ser)
    gps_data = parse_gps_data(NMEA_lines)
    if gps_data:
        try:
            gps_time_raw = gps_data[0][1]
            gps_time = f"{gps_time_raw[0:2]}:{gps_time_raw[2:4]}:{gps_time_raw[4:6]}"
        except:
            gps_time = "00:00:00"
        try:
            alt = round(float(gps_data[0][9]), 2)
        except:
            alt = 0
        try:
            lat = unit_convert_deg(float(gps_data[0][2]))
        except:
            lat = 0
        try:
            lon = -unit_convert_deg(float(gps_data[0][4]))  # 서경 보정
        except:
            lon = 0
        try:
            fixed_sat = int(gps_data[0][7])
        except:
            fixed_sat = 0
        log_gps(f"{gps_time},{alt},{lat},{lon},{fixed_sat}")
        return [gps_time, alt, lat, lon, fixed_sat]
    return ["00:00:00", 0, 0, 0, 0]


def terminate_gps(ser):
    if ser:
        ser.close()


if __name__ == "__main__":
    ser = init_gps()
    if ser:
        try:
            while True:
                data = gps_readdata(ser)
                print(data)
                time.sleep(0.5)
        except KeyboardInterrupt:
            terminate_gps(ser)
