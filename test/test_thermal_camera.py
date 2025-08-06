#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""Thermal Camera 센서 테스트 코드"""

import time
import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from thermal_camera.thermo_camera import thermo_camera as tcam

def test_thermal_camera():
    """Thermal Camera 센서 테스트"""
    print("=" * 50)
    print("Thermal Camera 센서 테스트 시작")
    print("=" * 50)
    
    try:
        # 센서 초기화
        print("1. Thermal Camera 센서 초기화 중...")
        i2c, cam = tcam.init_thermal_camera()
        
        if cam is None:
            print("❌ Thermal Camera 초기화 실패")
            return False
            
        print("✅ Thermal Camera 초기화 성공")
        
        # 데이터 읽기 테스트
        print("\n2. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 50)
        
        frame_count = 0
        start_time = time.time()
        
        while True:
            try:
                # 센서 데이터 읽기
                data = tcam.read_cam(cam)
                
                if data:
                    min_temp, max_temp, avg_temp = data
                    frame_count += 1
                    elapsed = time.time() - start_time
                    
                    print(f"📊 Thermal Camera 데이터 (프레임 {frame_count}):")
                    print(f"   최소 온도: {min_temp:.2f} °C")
                    print(f"   최대 온도: {max_temp:.2f} °C")
                    print(f"   평균 온도: {avg_temp:.2f} °C")
                    print(f"   온도 범위: {max_temp - min_temp:.2f} °C")
                    print(f"   실행 시간: {elapsed:.1f}s")
                    print("-" * 30)
                else:
                    print("❌ 데이터 읽기 실패")
                
                time.sleep(0.5)  # 2Hz
                
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 데이터 읽기 오류: {e}")
                time.sleep(1)
        
        # 결과 요약
        if frame_count > 0:
            elapsed = time.time() - start_time
            print(f"\n📊 테스트 결과:")
            print(f"   총 프레임 수: {frame_count}")
            print(f"   총 시간: {elapsed:.1f}초")
            print(f"   평균 FPS: {frame_count/elapsed:.2f}")
        
        # 정리
        print("\n3. 센서 정리 중...")
        tcam.terminate_cam(i2c)
        print("✅ Thermal Camera 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ Thermal Camera 테스트 실패: {e}")
        return False

if __name__ == "__main__":
    test_thermal_camera() 