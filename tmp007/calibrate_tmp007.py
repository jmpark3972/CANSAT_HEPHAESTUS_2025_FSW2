#!/usr/bin/env python3
"""
TMP007 센서 실온 캘리브레이션 스크립트
실온에서 센서를 보정하여 정확한 온도 측정을 가능하게 합니다.
"""

import time
import sys
import os

# 상위 디렉토리의 tmp007 모듈 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tmp007 import tmp007

def main():
    try:
        print("=" * 50)
        print("TMP007 센서 실온 캘리브레이션")
        print("=" * 50)
        
        # 실제 실온 입력받기
        room_temp = input("현재 실제 실온을 입력하세요 (기본값: 25.0°C): ")
        if room_temp.strip() == "":
            room_temp = 25.0
        else:
            room_temp = float(room_temp)
        
        print(f"\n기준 온도: {room_temp}°C")
        
        # 센서 초기화
        print("\n1. 센서 초기화 중...")
        i2c, sensor = tmp007.init_tmp007()
        
        # 센서 안정화 대기
        print("2. 센서 안정화 대기 (10초)...")
        for i in range(10, 0, -1):
            print(f"   {i}초 남음...", end="\r")
            time.sleep(1)
        print("   완료!          ")
        
        # 캘리브레이션 전 현재 상태 확인
        print("\n3. 캘리브레이션 전 측정값:")
        for i in range(5):
            data = tmp007.read_tmp007_data(sensor)
            if data:
                print(f"   측정 {i+1}: 객체온도={data['object_temperature']}°C, 다이온도={data['die_temperature']}°C")
            time.sleep(1)
        
        # 캘리브레이션 수행
        print(f"\n4. 캘리브레이션 수행 중...")
        calibration_offset = sensor.calibrate_room_temperature(room_temp)
        
        print(f"\n캘리브레이션 결과:")
        print(f"   필요한 오프셋: {calibration_offset:.2f}°C")
        
        # 캘리브레이션 결과를 파일에 저장
        config_file = "tmp007/calibration_config.txt"
        with open(config_file, 'w', encoding='utf-8') as f:
            f.write(f"# TMP007 캘리브레이션 설정\n")
            f.write(f"# 캘리브레이션 날짜: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"# 기준 온도: {room_temp}°C\n")
            f.write(f"object_temperature_offset={calibration_offset:.4f}\n")
            f.write(f"die_temperature_offset={calibration_offset-15:.4f}\n")  # 다이 온도는 보통 조금 다름
        
        print(f"   캘리브레이션 설정이 {config_file}에 저장되었습니다.")
        
        # 권장사항 출력
        print(f"\n5. 권장사항:")
        print(f"   - tmp007.py의 온도 오프셋을 {calibration_offset:.2f}°C로 수정하세요")
        print(f"   - 110번째 줄: temperature_corrected = temperature - {calibration_offset:.1f}")
        print(f"   - 137번째 줄: temperature_corrected = temperature - {calibration_offset-15:.1f}")
        
    except KeyboardInterrupt:
        print("\n\n캘리브레이션이 중단되었습니다.")
    except Exception as e:
        print(f"\n캘리브레이션 오류: {e}")
    finally:
        try:
            tmp007.terminate_tmp007(i2c)
        except:
            pass
        print("\n캘리브레이션 완료.")

if __name__ == "__main__":
    main()

