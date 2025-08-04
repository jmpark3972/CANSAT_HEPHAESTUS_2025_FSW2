#!/usr/bin/env python3
"""
Utility functions for CANSAT FSW
- I2C scanning and debugging
- Sensor testing utilities
- System diagnostics
"""

import time
import board
import busio
from datetime import datetime
import os

def scan_i2c_devices():
    """I2C 버스에서 모든 장치를 스캔하고 주소 목록을 반환"""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        print(f"I2C 스캔 결과: {len(devices)}개 장치 발견")
        for device in devices:
            print(f"  주소: 0x{device:02X} ({device})")
        
        return devices
    except Exception as e:
        print(f"I2C 스캔 오류: {e}")
        return []

def test_i2c_connection(address):
    """특정 I2C 주소의 연결을 테스트"""
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        if address in devices:
            print(f"✅ 주소 0x{address:02X} 연결 성공")
            return True
        else:
            print(f"❌ 주소 0x{address:02X} 연결 실패")
            return False
    except Exception as e:
        print(f"❌ 주소 0x{address:02X} 테스트 오류: {e}")
        return False

def test_qwiic_mux():
    """Qwiic Mux 연결 및 채널 테스트"""
    try:
        from lib.qwiic_mux import QwiicMux
        
        i2c = busio.I2C(board.SCL, board.SDA)
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        
        print("Qwiic Mux 테스트 시작...")
        
        # 각 채널 테스트
        for channel in range(8):
            try:
                mux.select_channel(channel)
                time.sleep(0.1)
                
                # 해당 채널에서 I2C 장치 스캔
                i2c.try_lock()
                devices = i2c.scan()
                i2c.unlock()
                
                if devices:
                    print(f"  채널 {channel}: {len(devices)}개 장치 발견 - {[f'0x{d:02X}' for d in devices]}")
                else:
                    print(f"  채널 {channel}: 장치 없음")
                    
            except Exception as e:
                print(f"  채널 {channel}: 오류 - {e}")
        
        print("Qwiic Mux 테스트 완료")
        return True
        
    except Exception as e:
        print(f"Qwiic Mux 테스트 실패: {e}")
        return False

def test_sensor_initialization():
    """주요 센서들의 초기화 테스트"""
    print("센서 초기화 테스트 시작...")
    
    # I2C 스캔
    devices = scan_i2c_devices()
    
    # 주요 센서 주소들 테스트
    sensor_addresses = {
        "IMU (BNO055)": [0x28, 0x29],
        "Thermal Camera (MLX90640)": [0x33, 0x32, 0x34],
        "Barometer (BMP280)": [0x76, 0x77],
        "FIR1 (MLX90614)": [0x5A],
        "FIR2 (MLX90614)": [0x5A],
        "THERMIS (ADS1115)": [0x48],
    }
    
    results = {}
    
    for sensor_name, addresses in sensor_addresses.items():
        print(f"\n{sensor_name} 테스트:")
        for addr in addresses:
            if test_i2c_connection(addr):
                results[sensor_name] = f"0x{addr:02X}"
                break
        else:
            results[sensor_name] = "실패"
    
    # 결과 요약
    print("\n" + "="*50)
    print("센서 초기화 테스트 결과:")
    print("="*50)
    for sensor, result in results.items():
        status = "✅" if result != "실패" else "❌"
        print(f"{status} {sensor}: {result}")
    
    return results

def create_system_report():
    """시스템 상태 보고서 생성"""
    report = []
    report.append("="*60)
    report.append("CANSAT FSW 시스템 상태 보고서")
    report.append(f"생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("="*60)
    
    # I2C 스캔 결과
    devices = scan_i2c_devices()
    report.append(f"\nI2C 장치: {len(devices)}개 발견")
    for device in devices:
        report.append(f"  - 0x{device:02X} ({device})")
    
    # 센서 테스트 결과
    sensor_results = test_sensor_initialization()
    report.append("\n센서 상태:")
    for sensor, result in sensor_results.items():
        status = "정상" if result != "실패" else "오류"
        report.append(f"  - {sensor}: {result} ({status})")
    
    # Qwiic Mux 테스트
    report.append("\nQwiic Mux:")
    if test_qwiic_mux():
        report.append("  - 정상 작동")
    else:
        report.append("  - 오류 발생")
    
    report.append("\n" + "="*60)
    
    # 보고서 저장
    report_text = "\n".join(report)
    os.makedirs("logs", exist_ok=True)
    with open(f"logs/system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt", "w") as f:
        f.write(report_text)
    
    print(report_text)
    return report_text

def quick_diagnostic():
    """빠른 진단 - 주요 문제점만 확인"""
    print("빠른 진단 시작...")
    
    issues = []
    
    # I2C 기본 연결 확인
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        if not devices:
            issues.append("❌ I2C 버스에 장치가 없습니다")
        else:
            print(f"✅ I2C 버스 정상 ({len(devices)}개 장치)")
            
    except Exception as e:
        issues.append(f"❌ I2C 버스 오류: {e}")
    
    # 주요 센서 확인
    critical_sensors = {
        "IMU": [0x28, 0x29],
        "Barometer": [0x76, 0x77],
        "FIR1": [0x5A],
    }
    
    for sensor, addresses in critical_sensors.items():
        found = False
        for addr in addresses:
            if addr in devices:
                found = True
                break
        if not found:
            issues.append(f"❌ {sensor} 센서를 찾을 수 없습니다")
        else:
            print(f"✅ {sensor} 센서 정상")
    
    if issues:
        print("\n발견된 문제점:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ 모든 주요 센서가 정상입니다")
    
    return len(issues) == 0

if __name__ == "__main__":
    print("CANSAT FSW 유틸리티")
    print("1. I2C 스캔")
    print("2. 센서 초기화 테스트")
    print("3. Qwiic Mux 테스트")
    print("4. 시스템 보고서 생성")
    print("5. 빠른 진단")
    
    choice = input("\n선택하세요 (1-5): ")
    
    if choice == "1":
        scan_i2c_devices()
    elif choice == "2":
        test_sensor_initialization()
    elif choice == "3":
        test_qwiic_mux()
    elif choice == "4":
        create_system_report()
    elif choice == "5":
        quick_diagnostic()
    else:
        print("잘못된 선택입니다") 