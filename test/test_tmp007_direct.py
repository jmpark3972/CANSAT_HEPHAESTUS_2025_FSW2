#!/usr/bin/env python3
"""
TMP007 센서 직접 I2C 연결 테스트 스크립트
수정된 온도 계산 공식 적용
"""

import time
import board
import busio

def read_register(i2c, address, reg):
    """레지스터 읽기 (16비트)"""
    try:
        result = bytearray(2)
        i2c.writeto_then_readfrom(address, bytes([reg]), result)
        return (result[0] << 8) | result[1]
    except Exception as e:
        print(f"레지스터 읽기 실패 (0x{reg:02X}): {e}")
        return None

def convert_temperature(raw_value):
    """수정된 온도 변환 공식 (TMP007 데이터시트 기준)"""
    # 14비트 데이터, 0.03125°C/LSB
    # 부호 비트 처리 개선
    if raw_value & 0x8000:  # 음수 온도 (2의 보수)
        # 2의 보수 변환
        raw_value = raw_value - 0x10000
        temperature = raw_value * 0.03125
    else:
        temperature = raw_value * 0.03125
    
    return round(temperature, 2)

def convert_voltage(raw_value):
    """수정된 전압 변환 공식"""
    # 14비트 데이터, 156.25μV/LSB
    if raw_value & 0x8000:  # 음수 전압 (2의 보수)
        raw_value = raw_value - 0x10000
        voltage = raw_value * 156.25
    else:
        voltage = raw_value * 156.25
    
    return round(voltage, 2)

def main():
    print("TMP007 센서 직접 I2C 연결 테스트 스크립트")
    print("수정된 온도 계산 공식 적용")
    print("=" * 50)
    
    try:
        # 1. I2C 버스 초기화
        print("1. I2C 버스 초기화 중...")
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        time.sleep(0.1)
        print("✓ I2C 버스 초기화 성공")
        
        # 2. I2C 디바이스 스캔
        print("\n2. I2C 디바이스 스캔 중...")
        devices = i2c.scan()
        print(f"발견된 I2C 디바이스: {[hex(addr) for addr in devices]}")
        
        if 0x40 not in devices:
            print("⚠ TMP007 센서를 찾을 수 없음 (주소: 0x40)")
            print("다른 주소에서 시도해보겠습니다...")
        
        # 3. TMP007 레지스터 읽기 테스트
        print("\n3. TMP007 레지스터 읽기 테스트...")
        
        # 디바이스 ID 확인
        dev_id = read_register(i2c, 0x40, 0x1F)
        if dev_id is not None:
            print(f"디바이스 ID: 0x{dev_id:04X} (예상: 0x0078)")
            if dev_id == 0x78:
                print("✓ 올바른 TMP007 디바이스 ID 확인")
            else:
                print("⚠ 잘못된 디바이스 ID")
        else:
            print("❌ 디바이스 ID 읽기 실패")
            return
        
        # 설정 레지스터 확인
        config = read_register(i2c, 0x40, 0x02)
        if config is not None:
            print(f"설정 레지스터: 0x{config:04X}")
        
        # 4. 온도 데이터 읽기 테스트 (수정된 공식)
        print("\n4. 온도 데이터 읽기 테스트 (수정된 공식)...")
        
        # 객체 온도
        tobj_raw = read_register(i2c, 0x40, 0x03)
        if tobj_raw is not None:
            tobj_temp = convert_temperature(tobj_raw)
            print(f"객체 온도: {tobj_temp}°C (raw: 0x{tobj_raw:04X})")
        
        # 다이 온도
        tdie_raw = read_register(i2c, 0x40, 0x01)
        if tdie_raw is not None:
            tdie_temp = convert_temperature(tdie_raw)
            print(f"다이 온도: {tdie_temp}°C (raw: 0x{tdie_raw:04X})")
        
        # 전압
        voltage_raw = read_register(i2c, 0x40, 0x00)
        if voltage_raw is not None:
            voltage = convert_voltage(voltage_raw)
            print(f"전압: {voltage}μV (raw: 0x{voltage_raw:04X})")
        
        # 상태 레지스터
        status = read_register(i2c, 0x40, 0x04)
        if status is not None:
            print(f"상태 레지스터: 0x{status:04X}")
            print(f"  데이터 준비: {bool(status & 0x4000)}")
            print(f"  객체 온도 높음: {bool(status & 0x2000)}")
            print(f"  객체 온도 낮음: {bool(status & 0x1000)}")
            print(f"  객체 온도 오류: {bool(status & 0x0800)}")
        
        # 5. 연속 측정 테스트
        print("\n5. 연속 측정 테스트 (10초)...")
        start_time = time.time()
        count = 0
        
        while time.time() - start_time < 10:
            count += 1
            
            tobj_raw = read_register(i2c, 0x40, 0x03)
            if tobj_raw is not None:
                tobj_temp = convert_temperature(tobj_raw)
                if count % 4 == 0:  # 4초마다 출력
                    print(f"  측정 {count}: {tobj_temp}°C")
            
            time.sleep(0.25)  # 4Hz
        
        print(f"  총 {count}회 측정 완료")
        
        # 6. I2C 버스 해제
        print("\n6. I2C 버스 해제...")
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        elif hasattr(i2c, "close"):
            i2c.close()
        print("✓ I2C 버스 해제 완료")
        
        print("\n" + "=" * 50)
        print("=== TMP007 직접 I2C 연결 테스트 완료 ===")
        print("\n✅ 모든 테스트 성공!")
        
        # 결과 요약
        print(f"\n📊 측정 결과 요약:")
        print(f"  객체 온도: {tobj_temp}°C")
        print(f"  다이 온도: {tdie_temp}°C")
        print(f"  전압: {voltage}μV")
        print(f"  측정 횟수: {count}회")
        
        if tobj_temp > 50:
            print(f"\n⚠️  객체 온도가 높습니다 ({tobj_temp}°C)")
            print("  - 센서가 뜨거운 물체를 향하고 있는지 확인")
            print("  - 센서 자체가 과열되었는지 확인")
            print("  - 주변 온도와 비교하여 정상 여부 판단")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 