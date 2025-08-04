#!/usr/bin/env python3
"""TMP007 센서 직접 I2C 연결 테스트 스크립트"""

import sys
import os
import time
import board
import busio

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_tmp007_direct_i2c():
    """TMP007 센서 직접 I2C 연결 테스트"""
    print("=== TMP007 직접 I2C 연결 테스트 시작 ===")
    
    try:
        # I2C 버스 초기화 (Qwiic Mux 없이 직접 연결)
        print("1. I2C 버스 초기화 중...")
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C 버스 초기화 성공")
        
        # TMP007 I2C 주소 스캔
        print("\n2. I2C 디바이스 스캔 중...")
        i2c.try_lock()
        addresses = []
        for address in range(0x08, 0x78):
            if i2c.try_lock():
                try:
                    i2c.writeto(address, b'')
                    addresses.append(hex(address))
                except OSError:
                    pass
                finally:
                    i2c.unlock()
        
        print(f"발견된 I2C 디바이스: {addresses}")
        
        # TMP007 주소 확인 (0x40)
        tmp007_address = 0x40
        if hex(tmp007_address) in addresses:
            print(f"✓ TMP007 센서 발견 (주소: 0x{tmp007_address:02X})")
        else:
            print(f"⚠ TMP007 센서를 찾을 수 없음 (주소: 0x{tmp007_address:02X})")
            print("다른 주소에서 시도해보겠습니다...")
        
        # TMP007 레지스터 읽기 테스트
        print("\n3. TMP007 레지스터 읽기 테스트...")
        
        # 디바이스 ID 레지스터 (0x1F) 읽기
        try:
            i2c.try_lock()
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x1F]), result)
            dev_id = (result[0] << 8) | result[1]
            print(f"디바이스 ID: 0x{dev_id:04X} (예상: 0x0078)")
            
            if dev_id == 0x78:
                print("✓ 올바른 TMP007 디바이스 ID 확인")
            else:
                print("⚠ 예상과 다른 디바이스 ID")
                
        except Exception as e:
            print(f"디바이스 ID 읽기 실패: {e}")
        
        # 설정 레지스터 (0x02) 읽기
        try:
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x02]), result)
            config = (result[0] << 8) | result[1]
            print(f"설정 레지스터: 0x{config:04X}")
            
        except Exception as e:
            print(f"설정 레지스터 읽기 실패: {e}")
        
        # 온도 데이터 읽기 테스트
        print("\n4. 온도 데이터 읽기 테스트...")
        
        # 객체 온도 레지스터 (0x03) 읽기
        try:
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x03]), result)
            tobj_raw = (result[0] << 8) | result[1]
            
            # 온도 변환 (14비트, 0.03125°C/LSB)
            if tobj_raw & 0x8000:  # 음수 온도
                temperature = -((~tobj_raw + 1) & 0x7FFF) * 0.03125
            else:
                temperature = (tobj_raw & 0x7FFF) * 0.03125
            
            print(f"객체 온도: {temperature:.2f}°C (raw: 0x{tobj_raw:04X})")
            
        except Exception as e:
            print(f"객체 온도 읽기 실패: {e}")
        
        # 다이 온도 레지스터 (0x01) 읽기
        try:
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x01]), result)
            tdie_raw = (result[0] << 8) | result[1]
            
            # 온도 변환 (14비트, 0.03125°C/LSB)
            if tdie_raw & 0x8000:  # 음수 온도
                die_temp = -((~tdie_raw + 1) & 0x7FFF) * 0.03125
            else:
                die_temp = (tdie_raw & 0x7FFF) * 0.03125
            
            print(f"다이 온도: {die_temp:.2f}°C (raw: 0x{tdie_raw:04X})")
            
        except Exception as e:
            print(f"다이 온도 읽기 실패: {e}")
        
        # 전압 레지스터 (0x00) 읽기
        try:
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x00]), result)
            voltage_raw = (result[0] << 8) | result[1]
            
            # 전압 변환 (14비트, 156.25μV/LSB)
            if voltage_raw & 0x8000:  # 음수 전압
                voltage = -((~voltage_raw + 1) & 0x7FFF) * 156.25
            else:
                voltage = (voltage_raw & 0x7FFF) * 156.25
            
            print(f"전압: {voltage:.2f}μV (raw: 0x{voltage_raw:04X})")
            
        except Exception as e:
            print(f"전압 읽기 실패: {e}")
        
        # 상태 레지스터 (0x04) 읽기
        try:
            result = bytearray(2)
            i2c.writeto_then_readfrom(tmp007_address, bytes([0x04]), result)
            status = (result[0] << 8) | result[1]
            print(f"상태 레지스터: 0x{status:04X}")
            
            # 상태 비트 해석
            data_ready = bool(status & 0x4000)
            object_high = bool(status & 0x2000)
            object_low = bool(status & 0x1000)
            object_fault = bool(status & 0x0800)
            
            print(f"  데이터 준비: {data_ready}")
            print(f"  객체 온도 높음: {object_high}")
            print(f"  객체 온도 낮음: {object_low}")
            print(f"  객체 온도 오류: {object_fault}")
            
        except Exception as e:
            print(f"상태 레지스터 읽기 실패: {e}")
        
        # 연속 측정 테스트
        print("\n5. 연속 측정 테스트 (10초)...")
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < 10:
            try:
                # 객체 온도 읽기
                result = bytearray(2)
                i2c.writeto_then_readfrom(tmp007_address, bytes([0x03]), result)
                tobj_raw = (result[0] << 8) | result[1]
                
                if tobj_raw & 0x8000:
                    temperature = -((~tobj_raw + 1) & 0x7FFF) * 0.03125
                else:
                    temperature = (tobj_raw & 0x7FFF) * 0.03125
                
                count += 1
                if count % 4 == 0:  # 4초마다 출력
                    print(f"  측정 {count}: {temperature:.2f}°C")
                
                time.sleep(0.25)  # 4Hz
                
            except Exception as e:
                print(f"  측정 오류: {e}")
                time.sleep(0.25)
        
        print(f"  총 {count}회 측정 완료")
        
        # I2C 버스 해제
        i2c.unlock()
        print("\n6. I2C 버스 해제...")
        print("✓ I2C 버스 해제 완료")
        
        print("\n=== TMP007 직접 I2C 연결 테스트 완료 ===")
        return True
        
    except Exception as e:
        print(f"\n❌ TMP007 직접 I2C 연결 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("TMP007 센서 직접 I2C 연결 테스트 스크립트")
    print("=" * 50)
    
    try:
        success = test_tmp007_direct_i2c()
        
        if success:
            print("\n✅ 모든 테스트 성공!")
        else:
            print("\n❌ 일부 테스트 실패")
            return 1
            
    except KeyboardInterrupt:
        print("\n\n⚠ 사용자에 의해 중단됨")
        return 1
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 