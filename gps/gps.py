import time
import os
from datetime import datetime

RX_pin = 22

############################################################
#log 데이터 수신
############################################################

## Create sensor log file
log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

gpslogfile = open(os.path.join(log_dir, 'gps.txt'), 'a')

def log_gps(text):
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    gpslogfile.write(string_to_write)
    gpslogfile.flush()


##############################################################
# GPS 데이터 수신
##############################################################
import pigpio

def init_gps():
    pi = pigpio.pi()
    try:
        pi.set_mode(RX_pin, pigpio.INPUT)
        pi.exceptions = False
        try:
            pi.bb_serial_read_close(RX_pin)
        except:
            pass
        pi.bb_serial_read_open(RX_pin, 9600, 8)
    except pigpio.error:
        pi = None
        
    return pi


def read_gps(pi, timeout: float = 1.0):
    NMEA_lines = []
    buffer = b''
    start = time.time()
    if pi:
        while time.time() - start < timeout:
            (count, data) = pi.bb_serial_read(RX_pin)
            if count:
                buffer += data
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    NMEA_lines.append(line + b'\n')
                    time.sleep(0.01)
            else:
                time.sleep(0.01)
    else:
        pass

    return NMEA_lines


def parse_gps_data(NMEA_lines):
    gga_data = None
    rmc_data = None
    gps_data = None
    for line in NMEA_lines:
        try:
            if isinstance(line, bytes):
                decoded_line = line.decode('utf-8').strip()
            else:
                decoded_line = line.strip()
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
        else:
            continue

    if gga_data and rmc_data:
        gps_data = [gga_data,rmc_data]
    else:
        pass

    return gps_data

def terminate_gps(pi):
    try:    
        pi.bb_serial_read_close(RX_pin)
    except pigpio.error:
        pass
    pi.stop()
    return

##############################################################
# GPS 데이터 가공
##############################################################
def unit_convert_deg(raw_angle):
    deg = int(raw_angle // 100)            
    minutes = raw_angle - deg*100          
    decimal_deg = deg + minutes/60   
    return decimal_deg


def gps_readdata(pi):
    NMEA_lines = read_gps(pi)
    gps_data = parse_gps_data(NMEA_lines)
    modified_gps_data = []
    if gps_data is not None:
        if gps_data[0][1]:
            gps_time_raw = gps_data[0][1]
            hour, minute, second = gps_time_raw[0:2], gps_time_raw[2:4], gps_time_raw[4:6]
            gps_time =f"{hour}:{minute}:{second}"
            
        else:
            gps_time = "00:00:00"

        try:
            alt = round(float(gps_data[0][9]), 2) if gps_data[0][9] else 0
        except ValueError:
            alt = 0

        try:
            lat = unit_convert_deg(float(gps_data[0][2])) if gps_data[0][2] else 0
        except ValueError:
            lat = 0

        try:
            lon = unit_convert_deg(float(gps_data[0][4])) if gps_data[0][4] else 0
            lon = lon * -1
        except ValueError:
            lon = 0
        
        try:
            fixed_sat = int(gps_data[0][7]) if gps_data[0][7] else 0
        except ValueError:
            fixed_sat = 0
        modified_gps_data = [gps_time, alt, lat, lon, fixed_sat]
        log_gps(f"{gps_time},{alt},{lat},{lon},{fixed_sat}")
        
        return modified_gps_data
    
    else:
       return ["00:00:00", 0, 0, 0, 0]

'''
pi = init_gps()
while True:
    gps_data = gps_readdata(pi)
    NMEA_lines = read_gps(pi)
    if gps_data:
        print(NMEA_lines)
        print(gps_data)
        
    else:
        print("No GPS data received.")
    time.sleep(0.1)

'''
