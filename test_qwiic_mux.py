#!/usr/bin/env python3
"""
Qwiic Mux and FIR Sensors Test
Qwiic Mux를 통해 연결된 FIR 센서들을 테스트하는 스크립트
현재 설정: 채널 0=FIR1, 채널 1=FIR2, 채널 2=기타 센서들
"""

import time
import board
import busio
import adafruit_mlx90614
from lib.qwiic_mux import QwiicMux

def test_qwiic_mux():
    """Qwiic Mux 테스트"""
    print("=== Qwiic Mux 및 FIR 센서 테스트 ===")
    print("현재 설정:")
    print("  - 채널 0: FIR1")
    print("  - 채널 1: FIR2")
    print("  - 채널 2: 기타 센서들")
    print()
    
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
        
        # 채널 2 테스트 (기타 센서들)
        print("\n   채널 2 (기타 센서들) 테스트:")
        if 2 in devices:
            print(f"   ✓ 채널 2에 {len(devices[2])}개 디바이스 발견: {devices[2]}")
        else:
            print("   ⚠️  채널 2에 연결된 디바이스 없음")
        
        # 채널 전환 테스트
        print("\n3. 채널 전환 테스트...")
        for channel in range(8):
            if mux.select_channel(channel):
                current_ch = mux.get_current_channel()
                device_count = len(devices.get(channel, []))
                print(f"   채널 {channel} 선택됨 (현재: {current_ch}, 디바이스: {device_count}개)")
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
    """FIR 모듈 개별 테스트"""
    print("\n=== FIR 모듈 개별 테스트 ===")
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        
        # Qwiic Mux 초기화
        mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
        
        # FIR1 테스트
        print("\nFIR1 모듈 테스트 (채널 0):")
        mux.select_channel(0)
        time.sleep(0.1)
        
        try:
            fir1 = adafruit_mlx90614.MLX90614(i2c)
            print("FIR1 센서 초기화 성공")
            
            # 연속 측정
            for i in range(10):
                amb = round(float(fir1.ambient_temperature), 2)
                obj = round(float(fir1.object_temperature), 2)
                print(f"  측정 {i+1:2d}: Ambient={amb:6.2f}°C, Object={obj:6.2f}°C")
                time.sleep(0.5)
                
        except Exception as e:
            print(f"FIR1 센서 오류: {e}")
        
        # FIR2 테스트
        print("\nFIR2 모듈 테스트 (채널 1):")
        mux.select_channel(1)
        time.sleep(0.1)
        
        try:
            fir2 = adafruit_mlx90614.MLX90614(i2c)
            print("FIR2 센서 초기화 성공")
            
            # 연속 측정
            for i in range(10):
                amb = round(float(fir2.ambient_temperature), 2)
                obj = round(float(fir2.object_temperature), 2)
                print(f"  측정 {i+1:2d}: Ambient={amb:6.2f}°C, Object={obj:6.2f}°C")
                time.sleep(0.5)
                
        except Exception as e:
            print(f"FIR2 센서 오류: {e}")
        
        # 리소스 정리
        mux.close()
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
        print("센서 로거 초기화 중...")
        logger = MultiSensorLogger()
        
        # 데이터 로깅 테스트
        print("데이터 로깅 테스트 (5회)...")
        for i in range(5):
            logger.log_data()
            time.sleep(1)
        
        # 리소스 정리
        logger.cleanup()
        print("✓ 센서 로거 테스트 완료")
        return True
        
    except Exception as e:
        print(f"✗ 센서 로거 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    print("Qwiic Mux 및 FIR 센서 종합 테스트")
    print("=" * 50)
    
    # 1. Qwiic Mux 기본 테스트
    success1 = test_qwiic_mux()
    
    # 2. FIR 모듈 개별 테스트
    success2 = test_fir_modules()
    
    # 3. 센서 로거 테스트
    success3 = test_sensor_logger()
    
    # 결과 요약
    print("\n" + "=" * 50)
    print("테스트 결과 요약:")
    print(f"  Qwiic Mux 테스트: {'✓ 성공' if success1 else '✗ 실패'}")
    print(f"  FIR 모듈 테스트: {'✓ 성공' if success2 else '✗ 실패'}")
    print(f"  센서 로거 테스트: {'✓ 성공' if success3 else '✗ 실패'}")
    
    if all([success1, success2, success3]):
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️  일부 테스트 실패. 하드웨어 연결을 확인하세요.") 