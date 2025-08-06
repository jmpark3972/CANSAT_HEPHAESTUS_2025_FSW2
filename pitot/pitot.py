#!/usr/bin/env python3
"""
Pitot tube differential-pressure sensor 헬퍼 모듈
ΔP : ±500 Pa, 온도 : –40 ~ +85 °C (I2C, 35 ms 변환)
"""

import time
import os
import math
from datetime import datetime
from smbus2 import SMBus, i2c_msg

# ──────────────────────────────────────────────────────────
# 1) 로그 파일 준비
# ──────────────────────────────────────────────────────────
LOG_DIR = "sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)

pitotlog_file = open(os.path.join(LOG_DIR, "pitot.txt"), "a")  # append mode

def _log(line: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    pitotlog_file.write(f"{t},{line}\n")
    pitotlog_file.flush()

# ──────────────────────────────────────────────────────────
# 2) Pitot 센서 설정
# ──────────────────────────────────────────────────────────
I2C_ADDR = 0x00      # 실제 센서 주소 (0x00 이면 General-Call)
FORCE_MODE = True    # addr 0x00 접근 시 커널 우회
MEAS_DELAY_MS = 35   # 변환 대기 ≥30 ms

# ──────────────────────────────────────────────────────────
# 3) 유속도 계산 상수
# ──────────────────────────────────────────────────────────
AIR_DENSITY_SEA_LEVEL = 1.225  # kg/m³ (해수면 기준)
GRAVITY = 9.80665  # m/s²
GAS_CONSTANT_AIR = 287.1  # J/(kg·K) (공기)
TEMP_SEA_LEVEL = 288.15  # K (15°C)

# ──────────────────────────────────────────────────────────
# 4) Pitot 초기화 / 측정 / 종료
# ──────────────────────────────────────────────────────────
def init_pitot():
    """Pitot 센서 초기화 - 직접 I2C 연결"""
    try:
        # 직접 I2C 연결
        import board
        import busio
        
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        time.sleep(0.1)  # 안정화 대기
        
        # SMBus를 통해 I2C 버스 1에 접근
        bus = SMBus(1)
        time.sleep(0.1)  # 안정화 대기
        
        print("Pitot 센서 초기화 완료 (직접 I2C 연결)")
        _log("Pitot sensor initialized successfully (direct I2C)")
        return bus, None  # mux는 None으로 반환
    except Exception as e:
        print(f"Pitot 초기화 실패: {e}")
        _log(f"INIT_ERROR,{e}")
        return None, None

def read_pitot(bus, mux=None):
    """Pitot 센서 데이터 읽기 - 차압과 온도"""
    try:
        # 측정 트리거
        trigger_measure(bus)
        time.sleep(MEAS_DELAY_MS / 1000.0)
        
        # 데이터 읽기
        buf = read_7bytes(bus)
        dp, temp = convert(buf)
        
        # 값 반올림
        dp = round(dp, 2)
        temp = round(temp, 2)
        
        _log(f"DP:{dp},TEMP:{temp}")
        return dp, temp
        
    except Exception as e:
        _log(f"READ_ERROR,{e}")
        return None, None

def read_pitot_detailed(bus, mux=None):
    """Pitot 센서 상세 데이터 읽기 - 총압, 정압, 온도"""
    try:
        # 측정 트리거
        trigger_measure(bus)
        time.sleep(MEAS_DELAY_MS / 1000.0)
        
        # 데이터 읽기
        buf = read_7bytes(bus)
        total_p, static_p, temp = convert_detailed(buf)
        
        # 값 반올림
        total_p = round(total_p, 2)
        static_p = round(static_p, 2)
        temp = round(temp, 2)
        
        _log(f"TOTAL_P:{total_p},STATIC_P:{static_p},TEMP:{temp}")
        return total_p, static_p, temp
        
    except Exception as e:
        _log(f"READ_DETAILED_ERROR,{e}")
        return None, None, None

def calculate_airspeed(delta_pressure, temperature, altitude=0):
    """
    베르누이 방정식을 사용한 유속도 계산
    
    Args:
        delta_pressure: 차압 (Pa)
        temperature: 온도 (°C)
        altitude: 고도 (m) - 기본값 0 (해수면)
    
    Returns:
        airspeed: 유속도 (m/s)
    """
    try:
        # 온도를 켈빈으로 변환
        temp_k = temperature + 273.15
        
        # 고도에 따른 대기압 계산 (국제표준대기모델)
        if altitude > 0:
            # 고도에 따른 온도 감소 (대류권 기준)
            temp_alt = TEMP_SEA_LEVEL - 0.0065 * altitude
            # 고도에 따른 압력 감소
            pressure_alt = 101325 * (temp_alt / TEMP_SEA_LEVEL) ** 5.256
            # 고도에 따른 공기 밀도 계산
            air_density = pressure_alt / (GAS_CONSTANT_AIR * temp_alt)
        else:
            air_density = AIR_DENSITY_SEA_LEVEL
        
        # 베르누이 방정식: v = sqrt(2 * ΔP / ρ)
        # 여기서 ΔP는 동압 (dynamic pressure)
        if delta_pressure > 0:
            airspeed = math.sqrt(2 * abs(delta_pressure) / air_density)
        else:
            airspeed = 0.0
        
        return round(airspeed, 2)
        
    except Exception as e:
        _log(f"AIRSPEED_CALC_ERROR,{e}")
        return 0.0

def calculate_airspeed_from_pressures(total_pressure, static_pressure, temperature, altitude=0):
    """
    총압과 정압으로부터 유속도 계산
    
    Args:
        total_pressure: 총압 (Pa)
        static_pressure: 정압 (Pa)
        temperature: 온도 (°C)
        altitude: 고도 (m)
    
    Returns:
        airspeed: 유속도 (m/s)
    """
    try:
        # 동압 계산 (총압 - 정압)
        dynamic_pressure = total_pressure - static_pressure
        
        # 유속도 계산
        airspeed = calculate_airspeed(dynamic_pressure, temperature, altitude)
        
        return airspeed
        
    except Exception as e:
        _log(f"AIRSPEED_FROM_PRESSURES_ERROR,{e}")
        return 0.0

def calculate_mach_number(airspeed, temperature):
    """
    마하 수 계산
    
    Args:
        airspeed: 유속도 (m/s)
        temperature: 온도 (°C)
    
    Returns:
        mach: 마하 수
    """
    try:
        # 온도를 켈빈으로 변환
        temp_k = temperature + 273.15
        
        # 음속 계산: a = sqrt(γ * R * T)
        # γ (gamma) = 1.4 (공기의 비열비)
        # R = 287.1 J/(kg·K) (공기의 기체상수)
        gamma = 1.4
        R = 287.1
        speed_of_sound = math.sqrt(gamma * R * temp_k)
        
        # 마하 수 계산
        mach = airspeed / speed_of_sound
        
        return round(mach, 4)
        
    except Exception as e:
        _log(f"MACH_CALC_ERROR,{e}")
        return 0.0

def calculate_air_density(temperature, altitude=0):
    """
    공기 밀도 계산
    
    Args:
        temperature: 온도 (°C)
        altitude: 고도 (m)
    
    Returns:
        density: 공기 밀도 (kg/m³)
    """
    try:
        # 온도를 켈빈으로 변환
        temp_k = temperature + 273.15
        
        # 고도에 따른 대기압 계산
        if altitude > 0:
            temp_alt = TEMP_SEA_LEVEL - 0.0065 * altitude
            pressure_alt = 101325 * (temp_alt / TEMP_SEA_LEVEL) ** 5.256
        else:
            pressure_alt = 101325  # 해수면 기압
        
        # 공기 밀도 계산: ρ = P / (R * T)
        density = pressure_alt / (GAS_CONSTANT_AIR * temp_k)
        
        return round(density, 4)
        
    except Exception as e:
        _log(f"DENSITY_CALC_ERROR,{e}")
        return AIR_DENSITY_SEA_LEVEL

def calculate_reynolds_number(airspeed, characteristic_length=0.1, temperature=15, altitude=0):
    """
    레이놀즈 수 계산
    
    Args:
        airspeed: 유속도 (m/s)
        characteristic_length: 특성 길이 (m) - 기본값 0.1m
        temperature: 온도 (°C)
        altitude: 고도 (m)
    
    Returns:
        reynolds: 레이놀즈 수
    """
    try:
        # 공기 밀도 계산
        density = calculate_air_density(temperature, altitude)
        
        # 동점성계수 계산 (Sutherland 공식)
        temp_k = temperature + 273.15
        # 15°C에서의 동점성계수: 1.48e-5 m²/s
        mu_0 = 1.48e-5
        T_0 = 288.15  # 15°C
        S = 110.4  # Sutherland 상수
        
        kinematic_viscosity = mu_0 * (temp_k / T_0) ** 1.5 * (T_0 + S) / (temp_k + S)
        
        # 레이놀즈 수 계산: Re = ρ * v * L / μ
        reynolds = density * airspeed * characteristic_length / kinematic_viscosity
        
        return round(reynolds, 0)
        
    except Exception as e:
        _log(f"REYNOLDS_CALC_ERROR,{e}")
        return 0.0

def read_pitot_advanced(bus, mux=None, altitude=0):
    """
    Pitot 센서 고급 데이터 읽기 - 모든 계산된 값들 포함
    
    Returns:
        tuple: (delta_pressure, temperature, airspeed, total_pressure, static_pressure, 
                mach_number, air_density, reynolds_number, dynamic_pressure)
    """
    try:
        # 기본 데이터 읽기
        total_p, static_p, temp = read_pitot_detailed(bus, mux)
        
        if total_p is None or static_p is None or temp is None:
            return None, None, None, None, None, None, None, None, None
        
        # 동압 계산
        dynamic_pressure = total_p - static_p
        
        # 유속도 계산
        airspeed = calculate_airspeed(dynamic_pressure, temp, altitude)
        
        # 추가 계산값들
        mach_number = calculate_mach_number(airspeed, temp)
        air_density = calculate_air_density(temp, altitude)
        reynolds_number = calculate_reynolds_number(airspeed, 0.1, temp, altitude)
        
        # 로그 기록
        _log(f"ADVANCED_DATA,DP:{dynamic_pressure:.2f},TEMP:{temp:.2f},SPEED:{airspeed:.2f},"
             f"MACH:{mach_number:.4f},DENSITY:{air_density:.4f},REYNOLDS:{reynolds_number:.0f}")
        
        return (dynamic_pressure, temp, airspeed, total_p, static_p, 
                mach_number, air_density, reynolds_number, dynamic_pressure)
        
    except Exception as e:
        _log(f"ADVANCED_READ_ERROR,{e}")
        return None, None, None, None, None, None, None, None, None

def terminate_pitot(bus):
    """Pitot 센서 종료"""
    try:
        if bus:
            bus.close()
        _log("Pitot sensor terminated")
    except Exception as e:
        _log(f"TERMINATE_ERROR,{e}")

# ──────────────────────────────────────────────────────────
# 5) Pitot 센서 내부 함수들
# ──────────────────────────────────────────────────────────
def trigger_measure(bus: SMBus):
    """측정 트리거 - 0xAA 레지스터에 0x0080 쓰면 1-shot 전환 시작"""
    bus.write_i2c_block_data(I2C_ADDR, 0xAA, [0x00, 0x80], force=FORCE_MODE)

def read_7bytes(bus: SMBus):
    """7바이트 데이터 읽기 - 1-byte dummy 주소 0x01 → 7-byte burst read"""
    bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, [0x01]),
                 rd := i2c_msg.read(I2C_ADDR, 7))
    return list(rd)  # [status, P2, P1, P0, T2, T1, T0]

def convert(buf):
    """원시 데이터를 압력과 온도로 변환 (차압 방식)"""
    # ─ 압력 (14-bit, 2's-complement) ─
    rawP = ((buf[1] << 8) | buf[2]) >> 2     # [23:10]
    if rawP & 0x2000:                         # 부호 확장
        rawP -= 1 << 14
    dp = rawP * 500.0 / 8192.0               # ±500 Pa FS

    # ─ 온도 (16-bit, unsigned) ─
    rawT = (buf[4] << 8) | buf[5]            # [23:08]
    temp = (rawT / 65536.0) * 125.0 - 40.0   # –40 ~ +85 °C

    return dp, temp

def convert_detailed(buf):
    """원시 데이터를 총압, 정압, 온도로 변환"""
    # ─ 압력 (14-bit, 2's-complement) ─
    rawP = ((buf[1] << 8) | buf[2]) >> 2     # [23:10]
    if rawP & 0x2000:                         # 부호 확장
        rawP -= 1 << 14
    
    # 센서가 차압을 측정하므로, 정압을 기준으로 총압 계산
    # 실제로는 센서의 출력이 차압이므로, 정압을 추정해야 함
    # 여기서는 대기압을 정압으로 가정하고, 총압 = 정압 + 차압으로 계산
    static_pressure = 101325  # 표준 대기압 (Pa)
    delta_pressure = rawP * 500.0 / 8192.0   # ±500 Pa FS
    total_pressure = static_pressure + delta_pressure

    # ─ 온도 (16-bit, unsigned) ─
    rawT = (buf[4] << 8) | buf[5]            # [23:08]
    temp = (rawT / 65536.0) * 125.0 - 40.0   # –40 ~ +85 °C

    return total_pressure, static_pressure, temp 