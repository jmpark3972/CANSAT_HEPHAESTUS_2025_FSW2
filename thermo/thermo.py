# thermo.py


import time
import os
from datetime import datetime
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from lib import prevstate
# ──────────────────────────────────────────────────────────
# 1)  로그 파일 준비
# ──────────────────────────────────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)

thermolog_file = open(os.path.join(LOG_DIR, "thermo.txt"), "a")  # append mode
#getattr(prevstate, "PREV_THERMO_TOFF", 0)

def log_thermo(text: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    thermolog_file.write(f"{t},{text}\n")
    thermolog_file.flush()


# ──────────────────────────────────────────────────────────
# 2)  DHT11 초기화 / 측정 / 종료
# ──────────────────────────────────────────────────────────
def init_dht(pin=None):
    """
    * DHT11 : 단선 GPIO, adafruit_dht 사용
    * DHT12 : I2C(0x5C),  adafruit_dht12 사용
    """
    THERMO_TOFF = getattr(prevstate, "PREV_THERMO_TOFF", 0)
    try:
        # ① DHT12 (I2C) 우선 시도
        import adafruit_dht12
        import board, busio
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_dht12.DHT12(i2c)
        sensor_type = "DHT12(I2C)"
        return sensor_type, sensor     # sensor.temperature, sensor.humidity
    except Exception as e:
        # I2C 디바이스가 없으면 → DHT11 걸로 fallback
        import adafruit_dht, board
        if pin is None:
            pin = board.D17  # GPIO 7번 핀
        sensor = adafruit_dht.DHT11(pin, use_pulseio=False)
        sensor_type = "DHT11(GPIO)"
        return sensor_type, sensor

def read_dht(sensor_tuple):
    sensor_type, sensor = sensor_tuple
    try:
        if sensor_type.startswith("DHT12"):
            temp_c = sensor.temperature         # °C
            humidity = sensor.humidity          # %
        else:                                   # DHT11
            temp_c = sensor.temperature
            humidity = sensor.humidity
    except Exception as e:
        log_thermo(f"READ_ERROR,{e}")
        return None, None

    # 값 반올림 & 로그
    temp_c = None if temp_c is None else round(float(temp_c), 1)
    humidity = None if humidity is None else round(float(humidity), 1)

    log_thermo(f"{temp_c},{humidity}")
    return temp_c, humidity

def terminate_dht(dht_device):
    try:
        dht_device.exit()
    except AttributeError:
        pass  # 라이브러리 버전에 따라 exit() 없을 수도 있음


# ──────────────────────────────────────────────────────────
# 3)  단독 실행 시 데모 루프
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    sensor = init_dht()

    try:
        while True:
            t, h = read_dht(sensor)
            # Temp = {t} °C,  Humidity = {h} %
            time.sleep(2.0)  # DHT11 은 최소 1 ~ 2 초 간격 필요
    except KeyboardInterrupt:
        pass
    finally:
        terminate_dht(sensor)
