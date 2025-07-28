#!/usr/bin/env python3
"""
Pitot 센서 단독 테스트 스크립트
"""

import time
import sys
import os

# 상위 디렉토리 경로 추가
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from pitot import pitot

def test_pitot():
    """Pitot 센서 테스트"""
    print("🌪️  Pitot 차압 센서 테스트 시작...")
    print("=" * 60)
    
    # Pitot 센서 초기화
    bus = pitot.init_pitot()
    if not bus:
        print("❌ Pitot 센서 초기화 실패")
        print("\n💡 연결 확인:")
        print("   - I2C 연결 확인 (SDA, SCL)")
        print("   - 전원 공급 확인 (3.3V)")
        print("   - 센서 주소 확인 (0x00)")
        return False
    
    print("✅ Pitot 센서 초기화 완료")
    print("📊 측정 시작... (Ctrl+C로 종료)")
    print("-" * 60)
    
    try:
        while True:
            # Pitot 데이터 읽기
            dp, temp = pitot.read_pitot(bus)
            
            if dp is not None and temp is not None:
                print(f"🌪️  차압: {dp:8.2f} Pa | 🌡️  온도: {temp:6.2f} °C")
            else:
                print("❌ 센서 읽기 실패")
            
            time.sleep(0.2)  # 5Hz (200ms 간격)
            
    except KeyboardInterrupt:
        print("\n⏹️  테스트 종료")
    finally:
        pitot.terminate_pitot(bus)
        print("🔌 센서 연결 해제")
    
    return True

if __name__ == "__main__":
    test_pitot() 