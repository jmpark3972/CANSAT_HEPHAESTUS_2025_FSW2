#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""
thermis.py – ADS1115 thermistor temperature sensor helper
"""

import os, time, math
from datetime import datetime

# ─────────────────────────────
# 1) 로그 파일 준비
# ─────────────────────────────
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
thermis_log = open(os.path.join(LOG_DIR, "thermis.txt"), "a")

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    thermis_log.write(f"{t},{line}\n")
    thermis_log.flush()

# ─────────────────────────────
# 2) 초기화 / 종료
# ─────────────────────────────
def init_thermis():
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
    from lib.qwiic_mux import QwiicMux
    
    # I2C 버스 초기화
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    time.sleep(0.1)  # I2C 버스 안정화
    
    # Qwiic Mux 초기화 및 채널 5 선택 (Thermis 위치 - 실제 연결된 채널)
    try:
        from lib.qwiic_mux import create_mux_instance
        mux = create_mux_instance(i2c_bus=i2c, mux_address=0x70)
        
        # channel_guard를 사용하여 안전하게 채널 선택 및 센서 초기화
        ads = None
        with mux.channel_guard(5):  # 🔒 채널 5 점유
            print("Qwiic Mux 채널 5 선택 완료 (Thermis)")
            
            # 여러 I2C 주소에서 ADS1115 찾기 시도
            ads_addresses = [0x48, 0x49, 0x4A, 0x4B]  # ADS1115 일반적인 주소들
            
            for addr in ads_addresses:
                try:
                    print(f"Thermis ADS1115 I2C 주소 0x{addr:02X} 시도 중...")
                    ads = ADS.ADS1115(i2c, address=addr)
                    # 센서 상태 확인
                    if ads is not None:
                        print(f"Thermis ADS1115 초기화 성공 (주소: 0x{addr:02X})")
                        break
                except Exception as e:
                    print(f"주소 0x{addr:02X} 실패: {e}")
                    continue
        
        if ads is None:
            raise Exception("Thermis ADS1115를 찾을 수 없습니다. I2C 연결을 확인하세요.")
        
        # Analog input 설정
        chan = AnalogIn(ads, ADS.P0)
        
        return i2c, ads, chan, mux
        
    except Exception as e:
        print(f"Qwiic Mux 초기화 실패: {e}")
        raise Exception(f"Qwiic Mux 초기화 실패: {e}")

def terminate_thermis(i2c):
    try:
        i2c.deinit()
    except AttributeError:
        pass  # busio 버전에 따라 deinit() 없음
    thermis_log.close()

# ─────────────────────────────
# 3) 데이터 읽기
# ─────────────────────────────
def read_thermis(chan, mux):
    """
    온도값을 반환.
    오류 발생 시 None + 로그 기록.
    """
    VCC = 3.3
    R_fix = 10000.0
    R0 = 10000.0
    T0 = 298.15
    B = 3435.0
    
    try:
        # channel_guard를 사용하여 안전하게 센서 읽기
        with mux.channel_guard(5):  # 🔒 채널 5 점유
            voltage = chan.voltage
            if voltage <= 0.0 or voltage >= VCC:
                _log(f"READ_ERROR,Invalid voltage: {voltage:.4f} V")
                return None
                
            R_th = R_fix * (VCC - voltage) / voltage
            ratio = R_th / R0
            if ratio <= 0.0:
                _log(f"READ_ERROR,Invalid resistance ratio: R_th={R_th:.1f} Ω")
                return None
                
            T_kelvin = 1.0 / (1.0/T0 + (1.0/B) * math.log(ratio))
            T_celsius = T_kelvin - 273.15
            temp = round(T_celsius, 2)
            
            _log(f"{temp:.2f}")
            return temp
        
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None

# ─────────────────────────────
# 4) 데모 루프
# ─────────────────────────────
if __name__ == "__main__":
    i2c, ads, chan, mux = init_thermis()
    try:
        while True:
            temp = read_thermis(chan, mux)
            if temp is not None:
                print(f"Temperature: {temp:.2f} °C")
            time.sleep(1.0)
    except KeyboardInterrupt:
        pass
    finally:
        terminate_thermis(i2c) 