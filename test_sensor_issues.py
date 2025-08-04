#!/usr/bin/env python3
"""
Comprehensive test script to diagnose sensor issues
"""
import time
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_qwiic_mux():
    print("=== Qwiic Mux 테스트 ===")
    try:
        from lib.qwiic_mux import QwiicMux
        import board
        import busio
        
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        
        print("Qwiic Mux 초기화 성공")
        
        # Scan all channels
        print("\n채널 스캔 결과:")
        devices = mux.scan_channels()
        for channel, device_list in devices.items():
            print(f"  채널 {channel}: {device_list}")
        
        mux.close()
        return True
    except Exception as e:
        print(f"Qwiic Mux 테스트 실패: {e}")
        return False

def test_fir_sensors():
    print("\n=== FIR 센서 테스트 ===")
    
    try:
        # Test FIR1
        print("FIR1 (Channel 0) 테스트:")
        from fir1 import fir1
        mux1, sensor1 = fir1.init_fir1()
        
        if mux1 and sensor1:
            print("  FIR1 초기화 성공")
            for i in range(3):
                amb1, obj1 = fir1.read_fir1(mux1, sensor1)
                if amb1 is not None:
                    print(f"  FIR1: Ambient={amb1:.2f}°C, Object={obj1:.2f}°C")
                else:
                    print("  FIR1 읽기 실패")
                time.sleep(1)
            fir1.terminate_fir1(mux1)
        else:
            print("  FIR1 초기화 실패")
        
        time.sleep(2)
        
        # Test FIR2
        print("FIR2 (Channel 1) 테스트:")
        from fir2 import fir2
        mux2, sensor2 = fir2.init_fir2()
        
        if mux2 and sensor2:
            print("  FIR2 초기화 성공")
            for i in range(3):
                amb2, obj2 = fir2.read_fir2(mux2, sensor2)
                if amb2 is not None:
                    print(f"  FIR2: Ambient={amb2:.2f}°C, Object={obj2:.2f}°C")
                else:
                    print("  FIR2 읽기 실패")
                time.sleep(1)
            fir2.terminate_fir2(mux2)
        else:
            print("  FIR2 초기화 실패")
        
        return True
    except Exception as e:
        print(f"FIR 센서 테스트 실패: {e}")
        return False

def test_pitot_sensor():
    print("\n=== Pitot 센서 테스트 ===")
    
    try:
        from pitot import pitot
        
        bus, mux = pitot.init_pitot()
        if bus and mux:
            print("Pitot 센서 초기화 성공")
            
            for i in range(5):
                dp, temp = pitot.read_pitot(bus, mux)
                if dp is not None and temp is not None:
                    print(f"Pitot: Pressure={dp:.2f} Pa, Temperature={temp:.2f}°C")
                else:
                    print("Pitot 읽기 실패")
                time.sleep(0.5)
            
            pitot.terminate_pitot(bus)
            if mux:
                mux.close()
            return True
        else:
            print("Pitot 센서 초기화 실패")
            return False
    except Exception as e:
        print(f"Pitot 센서 테스트 실패: {e}")
        return False

def main():
    print("센서 문제 진단 테스트 시작...")
    
    # Test Qwiic Mux
    mux_ok = test_qwiic_mux()
    
    # Test FIR sensors
    fir_ok = test_fir_sensors()
    
    # Test Pitot sensor
    pitot_ok = test_pitot_sensor()
    
    print("\n=== 테스트 결과 요약 ===")
    print(f"Qwiic Mux: {'성공' if mux_ok else '실패'}")
    print(f"FIR 센서: {'성공' if fir_ok else '실패'}")
    print(f"Pitot 센서: {'성공' if pitot_ok else '실패'}")

if __name__ == "__main__":
    main() 