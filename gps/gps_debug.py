#!/usr/bin/env python3
"""
GPS 모듈 디버깅 스크립트
"""

import time
import board
import busio

def debug_gps_i2c():
    """GPS I2C 모듈 상세 디버깅"""
    print("GPS I2C 디버깅 시작...")
    print("=" * 60)
    
    try:
        # I2C 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=100_000)
        gps_address = 0x42
        
        print(f"✅ I2C 초기화 완료")
        print(f"✅ GPS 주소: 0x{gps_address:02X}")
        
        # GPS 모듈 존재 확인
        i2c.try_lock()
        devices = i2c.scan()
        i2c.unlock()
        
        if gps_address not in devices:
            print(f"❌ GPS 모듈을 찾을 수 없습니다.")
            return False
        
        print(f"✅ GPS 모듈 발견: 0x{gps_address:02X}")
        
        # GPS 모듈과 통신 테스트
        print("\n📡 GPS 모듈 통신 테스트...")
        
        # 1. 기본 읽기 테스트
        print("1. 기본 읽기 테스트:")
        try:
            i2c.try_lock()
            data = bytearray(64)
            i2c.readfrom_into(gps_address, data)
            i2c.unlock()
            
            print(f"   읽은 데이터: {data}")
            print(f"   데이터 길이: {len(data)} 바이트")
            
            # NMEA 문장 찾기
            nmea_data = ""
            for byte in data:
                if 32 <= byte <= 126:  # 출력 가능한 ASCII 문자
                    nmea_data += chr(byte)
            
            if nmea_data:
                print(f"   ASCII 데이터: {nmea_data}")
            else:
                print("   출력 가능한 ASCII 데이터 없음")
                
        except Exception as e:
            print(f"   ❌ 읽기 오류: {e}")
        
        # 2. GPS 명령어 전송 테스트
        print("\n2. GPS 명령어 전송 테스트:")
        try:
            # GPS 모듈 초기화 명령어
            commands = [
                b"$PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28\r\n",  # GGA, RMC만 출력
                b"$PMTK220,100*2F\r\n",  # 10Hz 업데이트
            ]
            
            for i, cmd in enumerate(commands):
                print(f"   명령어 {i+1}: {cmd}")
                try:
                    i2c.try_lock()
                    i2c.writeto(gps_address, cmd)
                    i2c.unlock()
                    print(f"   ✅ 명령어 전송 성공")
                    time.sleep(0.1)
                except Exception as e:
                    print(f"   ❌ 명령어 전송 실패: {e}")
        
        except Exception as e:
            print(f"   ❌ 명령어 테스트 오류: {e}")
        
        # 3. 연속 데이터 읽기 테스트
        print("\n3. 연속 데이터 읽기 테스트:")
        print("   5초간 GPS 데이터 모니터링...")
        
        start_time = time.time()
        data_count = 0
        
        while time.time() - start_time < 5:
            try:
                i2c.try_lock()
                data = bytearray(64)
                i2c.readfrom_into(gps_address, data)
                i2c.unlock()
                
                # NMEA 문장 찾기
                nmea_lines = []
                current_line = ""
                
                for byte in data:
                    if byte == 13:  # CR
                        if current_line.startswith('$'):
                            nmea_lines.append(current_line)
                        current_line = ""
                    elif 32 <= byte <= 126:  # 출력 가능한 ASCII 문자
                        current_line += chr(byte)
                
                if nmea_lines:
                    data_count += 1
                    print(f"   데이터 {data_count}: {nmea_lines}")
                
                time.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ 읽기 오류: {e}")
                break
        
        if data_count == 0:
            print("   ❌ 5초간 GPS 데이터를 받지 못했습니다.")
            print("\n가능한 원인:")
            print("1. GPS 모듈이 I2C 모드가 아닌 UART 모드로 설정됨")
            print("2. GPS 모듈에 안테나가 연결되지 않음")
            print("3. GPS 모듈이 실내에서 신호를 받지 못함")
            print("4. GPS 모듈 초기화가 필요함")
        else:
            print(f"   ✅ {data_count}개의 GPS 데이터 수신 성공")
        
        return True
        
    except Exception as e:
        print(f"❌ GPS 디버깅 오류: {e}")
        return False

if __name__ == "__main__":
    debug_gps_i2c() 