#!/usr/bin/env python3
"""
Test script to verify FIR sensors are working on different channels
"""
import time
import sys
import os

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

def test_fir_channels():
    print("FIR 센서 채널 테스트 시작...")
    
    try:
        # Test FIR1 (Channel 0)
        print("\n=== FIR1 (Channel 0) 테스트 ===")
        from fir1 import fir1
        mux1, sensor1 = fir1.init_fir1()
        
        if mux1 and sensor1:
            print("FIR1 초기화 성공")
            for i in range(5):
                amb1, obj1 = fir1.read_fir1(mux1, sensor1)
                if amb1 is not None:
                    print(f"FIR1 (Ch0): Ambient={amb1:.2f}°C, Object={obj1:.2f}°C")
                else:
                    print("FIR1 읽기 실패")
                time.sleep(1)
            fir1.terminate_fir1(mux1)
        else:
            print("FIR1 초기화 실패")
        
        time.sleep(2)  # 안정화 대기
        
        # Test FIR2 (Channel 1)
        print("\n=== FIR2 (Channel 1) 테스트 ===")
        from fir2 import fir2
        mux2, sensor2 = fir2.init_fir2()
        
        if mux2 and sensor2:
            print("FIR2 초기화 성공")
            for i in range(5):
                amb2, obj2 = fir2.read_fir2(mux2, sensor2)
                if amb2 is not None:
                    print(f"FIR2 (Ch1): Ambient={amb2:.2f}°C, Object={obj2:.2f}°C")
                else:
                    print("FIR2 읽기 실패")
                time.sleep(1)
            fir2.terminate_fir2(mux2)
        else:
            print("FIR2 초기화 실패")
            
    except Exception as e:
        print(f"테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    test_fir_channels() 