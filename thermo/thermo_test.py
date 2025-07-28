#!/usr/bin/env python3
"""
Thermo 센서 단독 테스트 스크립트
DHT11/DHT12 자동 감지 및 테스트
"""

import time
import os
from datetime import datetime

# ──────────────────────────────────────────────────────────
# 1) 로그 파일 준비
# ──────────────────────────────────────────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)

thermolog_file = open(os.path.join(LOG_DIR, "thermo.txt"), "a")  # append mode

def log_thermo(text: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    thermolog_file.write(f"{t},{text}\n")
    thermolog_file.flush()

# ──────────────────────────────────────────────────────────
# 2) DHT11/DHT12 초기화 / 측정 / 종료
# ──────────────────────────────────────────────────────────
def init_dht(pin=None):
    """
    * DHT11 : 단선 GPIO, adafruit_dht 사용
    * DHT12 : I2C(0x5C),  adafruit_dht12 사용
    """
    try:
        # ① DHT12 (I2C) 우선 시도
        print("🔍 DHT12 (I2C) 센서 감지 중...")
        import adafruit_dht12
        import board, busio
        i2c = busio.I2C(board.SCL, board.SDA)
        sensor = adafruit_dht12.DHT12(i2c)
        sensor_type = "DHT12(I2C)"
        print("✅ DHT12 (I2C) 센서 발견!")
        return sensor_type, sensor
    except Exception as e:
        # I2C 디바이스가 없으면 → DHT11 걸로 fallback
        print(f"❌ DHT12 감지 실패: {e}")
        print("🔍 DHT11 (GPIO) 센서 감지 중...")
        try:
            import adafruit_dht, board
            if pin is None:
                pin = board.D4  # GPIO 7번 핀
            sensor = adafruit_dht.DHT11(pin, use_pulseio=False)
            sensor_type = "DHT11(GPIO)"
            print("✅ DHT11 (GPIO) 센서 발견!")
            return sensor_type, sensor
        except Exception as e2:
            print(f"❌ DHT11 감지 실패: {e2}")
            print("❌ DHT 센서를 찾을 수 없습니다!")
            return None, None

def read_dht(sensor_tuple):
    if sensor_tuple[0] is None:
        return None, None
        
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
# 3) 단독 실행 시 데모 루프
# ──────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌡️  Thermo 센서 테스트 시작...")
    print("=" * 50)
    
    sensor = init_dht()
    
    if sensor[0] is None:
        print("❌ 센서 초기화 실패")
        print("\n💡 연결 확인:")
        print("   DHT11: GPIO 4번 핀에 연결")
        print("   DHT12: I2C (SDA, SCL)에 연결")
        exit(1)

    print(f"📡 센서 타입: {sensor[0]}")
    print("🔄 측정 시작... (Ctrl+C로 종료)")
    print("-" * 50)

    try:
        while True:
            t, h = read_dht(sensor)
            if t is not None and h is not None:
                print(f"🌡️  온도: {t}°C | 💧 습도: {h}%")
            else:
                print("❌ 센서 읽기 실패")
            time.sleep(2.0)  # DHT11 은 최소 1 ~ 2 초 간격 필요
    except KeyboardInterrupt:
        print("\n⏹️  테스트 종료")
    finally:
        terminate_dht(sensor)
        print("🔌 센서 연결 해제") 
