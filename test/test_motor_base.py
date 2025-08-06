#!/usr/bin/env python3
"""
모터 기본 기능 테스트 스크립트
"""

import pigpio
import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_motor_control():
    """모터 제어 테스트"""
    print("=== 모터 제어 테스트 시작 ===")
    
    try:
        pi = pigpio.pi()
        if not pi.connected:
            print("❌ pigpio 연결 실패")
            return False
            
        print("✅ pigpio 연결 성공")
        
        PAYLOAD_MOTOR_PIN = 12
        PAYLOAD_MOTOR_MIN_PULSE = 500
        PAYLOAD_MOTOR_MAX_PULSE = 2500
        
        def angle_to_pulse(angle):
            if angle < 0:
                angle = 0
            elif angle > 180:
                angle = 180
            return int(PAYLOAD_MOTOR_MIN_PULSE + ((angle/180)*(PAYLOAD_MOTOR_MAX_PULSE - PAYLOAD_MOTOR_MIN_PULSE)))
        
        # 테스트 각도들
        test_angles = [0, 90, 180, 45, 135]
        
        print("모터 펄스 테스트:")
        for angle in test_angles:
            pulse = angle_to_pulse(angle)
            print(f"  각도 {angle}° → 펄스 {pulse}")
            
            # 실제 모터 제어 (짧은 시간만)
            pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, pulse)
            time.sleep(0.1)  # 0.1초만 대기
        
        # 모터를 안전한 위치로 이동
        pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, angle_to_pulse(0))
        time.sleep(0.5)
        
        pi.stop()
        print("✅ 모터 제어 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ 모터 제어 테스트 실패: {e}")
        return False

def main():
    """메인 테스트 함수"""
    print("모터 기본 기능 테스트")
    print("=" * 40)
    
    success = test_motor_control()
    
    print("=" * 40)
    if success:
        print("🎉 모든 테스트가 성공했습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다.")

if __name__ == "__main__":
    main()
