#!/usr/bin/env python3
"""
BNO055 Temperature Reading Test
Tests the BNO055 temperature sensor reading functionality
"""

import time
import board
import busio
import adafruit_bno055
from lib.logging import safe_log
# QwiicMux import 제거됨 - 직접 I2C 통신 사용

def test_bno055_temperature():
    """BNO055 온도 센서 테스트"""
    safe_log("BNO055 온도 센서 테스트 시작...", "INFO", True)
    
    try:
        # I2C 버스 초기화
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        safe_log("I2C 버스 초기화 성공", "INFO", True)
        
        # 직접 I2C 통신 사용 (Qwiic Mux 없음)
        safe_log("직접 I2C 통신으로 IMU 온도 테스트", "INFO", True)
        
        # BNO055 센서 초기화
        try:
            imu = adafruit_bno055.BNO055_I2C(i2c, address=0x28)
            safe_log("BNO055 초기화 성공 (주소: 0x28)", "INFO", True)
        except Exception as e:
            safe_log(f"BNO055 초기화 실패: {e}", "ERROR", True)
            return False
        
        # 센서 안정화 대기
        time.sleep(1.0)
        
        # 온도 읽기 테스트 (20회)
        safe_log("온도 읽기 테스트 (20회) 시작", "INFO", True)
        temperatures = []
        
        for i in range(20):
            try:
                # 온도 읽기
                temp = imu.temperature
                if temp is not None:
                    temperatures.append(temp)
                    safe_log(f"온도 측정 {i+1:2d}: {temp:.2f}°C", "DEBUG", True)
                else:
                    safe_log(f"온도 측정 {i+1:2d}: 사용 불가", "WARNING", True)
                
                # 온도 소스 확인 (가능한 경우)
                try:
                    temp_source = imu.temperature_source
                    safe_log(f"온도소스: {temp_source}", "DEBUG", False)
                except Exception as e:
                    safe_log(f"온도 소스 확인 오류: {e}", "WARNING", False)
                
                time.sleep(0.5)
            except Exception as e:
                safe_log(f"온도 측정 {i+1:2d} 오류: {e}", "ERROR", True)
                time.sleep(0.5)
        
        # 통계 계산
        if temperatures:
            avg_temp = sum(temperatures) / len(temperatures)
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            
            safe_log("온도 통계:", "INFO", True)
            safe_log(f"  평균: {avg_temp:.2f}°C", "INFO", True)
            safe_log(f"  최소: {min_temp:.2f}°C", "INFO", True)
            safe_log(f"  최대: {max_temp:.2f}°C", "INFO", True)
            safe_log(f"  범위: {max_temp - min_temp:.2f}°C", "INFO", True)
            safe_log(f"  샘플 수: {len(temperatures)}", "INFO", True)
        
        safe_log("BNO055 온도 센서 테스트 완료!", "INFO", True)
        return True
        
    except Exception as e:
        safe_log(f"BNO055 온도 센서 테스트 실패: {e}", "ERROR", True)
        return False

if __name__ == "__main__":
    test_bno055_temperature() 