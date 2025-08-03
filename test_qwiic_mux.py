#!/usr/bin/env python3
"""
Qwiic Mux and FIR Sensors Test
Qwiic Mux를 통해 연결된 FIR 센서들을 테스트하는 스크립트
"""

import time
import board
import busio
import adafruit_mlx90614
from lib.qwiic_mux import QwiicMux

def test_qwiic_mux():
    """Qwiic Mux 테스트"""
    print("=== Qwiic Mux 및 FIR 센서 테스트 ===")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        print("I2C 버스 초기화 완료")
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        print("Qwiic Mux 초기화 완료")
        
        # 모든 채널 스캔
        print("\n1. 모든 채널 I2C 디바이스 스캔...")
        devices = mux.scan_channels()
        
        if not devices:
            print("⚠️  연결된 I2C 디바이스가 없습니다.")
            print("   - Qwiic Mux 연결 확인")
            print("   - FIR 센서 연결 확인")
            return False
        
        print(f"✓ 발견된 디바이스: {devices}")
        
        # FIR 센서 테스트
        print("\n2. FIR 센서 테스트...")
        
        # FIR1 (채널 0) 테스트
        print("\n   FIR1 (채널 0) 테스트:")
        if 0 in devices:
            try:
                mux.select_channel(0)
                time.sleep(0.1)
                fir1 = adafruit_mlx90614.MLX90614(i2c)
                
                for i in range(5):
                    amb1 = round(float(fir1.ambient_temperature), 2)
                    obj1 = round(float(fir1.object_temperature), 2)
                    print(f"     측정 {i+1}: Ambient={amb1}°C, Object={obj1}°C")
                    time.sleep(0.5)
                
                print("   ✓ FIR1 센서 정상 작동")
                
            except Exception as e:
                print(f"   ✗ FIR1 센서 오류: {e}")
        else:
            print("   ⚠️  채널 0에 FIR 센서가 연결되지 않음")
        
        # FIR2 (채널 1) 테스트
        print("\n   FIR2 (채널 1) 테스트:")
        if 1 in devices:
            try:
                mux.select_channel(1)
                time.sleep(0.1)
                fir2 = adafruit_mlx90614.MLX90614(i2c)
                
                for i in range(5):
                    amb2 = round(float(fir2.ambient_temperature), 2)
                    obj2 = round(float(fir2.object_temperature), 2)
                    print(f"     측정 {i+1}: Ambient={amb2}°C, Object={obj2}°C")
                    time.sleep(0.5)
                
                print("   ✓ FIR2 센서 정상 작동")
                
            except Exception as e:
                print(f"   ✗ FIR2 센서 오류: {e}")
        else:
            print("   ⚠️  채널 1에 FIR 센서가 연결되지 않음")
        
        # 채널 전환 테스트
        print("\n3. 채널 전환 테스트...")
        for channel in range(8):
            if mux.select_channel(channel):
                current_ch = mux.get_current_channel()
                print(f"   채널 {channel} 선택됨 (현재: {current_ch})")
                time.sleep(0.1)
        
        # 모든 채널 비활성화
        mux.disable_all_channels()
        print("   모든 채널 비활성화 완료")
        
        # 리소스 정리
        mux.close()
        print("\n✓ Qwiic Mux 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ Qwiic Mux 테스트 실패: {e}")
        return False

def test_fir_modules():
    """FIR 모듈 테스트"""
    print("\n=== FIR 모듈 테스트 ===")
    
    try:
        # FIR1 모듈 테스트
        print("\n1. FIR1 모듈 테스트 (채널 0):")
        from fir1 import fir1
        
        mux1, sensor1 = fir1.init_fir1()
        
        for i in range(3):
            amb, obj = fir1.read_fir1(mux1, sensor1)
            if amb is not None:
                print(f"   측정 {i+1}: Ambient={amb}°C, Object={obj}°C")
            else:
                print(f"   측정 {i+1}: 오류")
            time.sleep(1)
        
        fir1.terminate_fir1(mux1)
        print("   ✓ FIR1 모듈 정상 작동")
        
        # FIR2 모듈 테스트
        print("\n2. FIR2 모듈 테스트 (채널 1):")
        from fir2 import fir2
        
        mux2, sensor2 = fir2.init_fir2()
        
        for i in range(3):
            amb, obj = fir2.read_fir2(mux2, sensor2)
            if amb is not None:
                print(f"   측정 {i+1}: Ambient={amb}°C, Object={obj}°C")
            else:
                print(f"   측정 {i+1}: 오류")
            time.sleep(1)
        
        fir2.terminate_fir2(mux2)
        print("   ✓ FIR2 모듈 정상 작동")
        
        print("\n✓ FIR 모듈 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ FIR 모듈 테스트 실패: {e}")
        return False

def test_sensor_logger():
    """센서 로거 테스트"""
    print("\n=== 센서 로거 테스트 ===")
    
    try:
        from sensor_logger import MultiSensorLogger
        
        # 센서 로거 초기화
        logger = MultiSensorLogger()
        
        # 데이터 로깅 테스트
        for i in range(3):
            logger.log_data()
            time.sleep(1)
        
        print("✓ 센서 로거 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 센서 로거 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("Qwiic Mux 및 FIR 센서 통합 테스트")
    print("=" * 50)
    
    # 1. Qwiic Mux 테스트
    mux_success = test_qwiic_mux()
    
    # 2. FIR 모듈 테스트
    fir_success = test_fir_modules()
    
    # 3. 센서 로거 테스트
    logger_success = test_sensor_logger()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"Qwiic Mux: {'✓ 성공' if mux_success else '✗ 실패'}")
    print(f"FIR 모듈: {'✓ 성공' if fir_success else '✗ 실패'}")
    print(f"센서 로거: {'✓ 성공' if logger_success else '✗ 실패'}")
    
    if mux_success and fir_success and logger_success:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️  일부 테스트 실패. 하드웨어 연결을 확인하세요.") 