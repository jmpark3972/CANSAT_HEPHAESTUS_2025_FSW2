import serial
import time
import pynmea2

# 시리얼 포트와 보드레이트(MTK 기본 9600bps)
ser = serial.Serial('/dev/serial0', 9600, timeout=1)

try:
    while True:
        raw = ser.readline().decode('ascii', errors='replace').strip()
        if not raw:
            continue
        # GPRMC나 GPGGA 문장 파싱
        if raw.startswith('$GPRMC') or raw.startswith('$GPGGA'):
            msg = pynmea2.parse(raw)
            lat, lon = msg.latitude, msg.longitude
            print(f"{msg.sentence_type}: {lat:.6f}, {lon:.6f}")
        time.sleep(0.1)
finally:
    ser.close()

