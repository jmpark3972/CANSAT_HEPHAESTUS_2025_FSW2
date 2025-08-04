#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""MLX90640 Thermal Camera 고급 테스트 코드"""

import time
import sys
import os
import statistics
import argparse

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import board
    import busio
    import adafruit_mlx90640 as mlxlib
except ImportError as e:
    print(f"❌ 라이브러리 누락: {e}")
    print("다음 명령어로 설치하세요:")
    print("pip3 install adafruit-circuitpython-mlx90640")
    sys.exit(1)

def test_thermal_camera_advanced(refresh_rate=2, frames=0):
    """MLX90640 Thermal Camera 고급 테스트"""
    print("=" * 60)
    print("🔥 MLX90640 Thermal Camera 고급 테스트")
    print("=" * 60)
    
    # I2C 설정
    I2C_FREQ = 400_000  # 400 kHz - MLX90640 권장
    
    try:
        print(f"1. I²C 초기화 중... (주파수: {I2C_FREQ//1000} kHz)")
        i2c = busio.I2C(board.SCL, board.SDA, frequency=I2C_FREQ)
        print("✅ I²C 초기화 성공")
        
        # MLX90640 초기화
        print("2. MLX90640 센서 초기화 중...")
        mlx = mlxlib.MLX90640(i2c, address=0x33)
        print("✅ MLX90640 초기화 성공")
        
        # 시리얼 번호 출력
        print(f"   시리얼 번호: {[hex(x) for x in mlx.serial_number]}")
        
        # 리프레시 레이트 설정
        refresh_map = {
            1: mlxlib.RefreshRate.REFRESH_1_HZ,
            2: mlxlib.RefreshRate.REFRESH_2_HZ,
            4: mlxlib.RefreshRate.REFRESH_4_HZ,
            8: mlxlib.RefreshRate.REFRESH_8_HZ,
            16: mlxlib.RefreshRate.REFRESH_16_HZ,
        }
        
        mlx.refresh_rate = refresh_map[refresh_rate]
        print(f"   리프레시 레이트: {refresh_rate} Hz")
        
        # 프레임 버퍼 할당 (32×24 = 768 floats)
        frame = [0.0] * 768
        
        # 데이터 읽기 테스트
        print("\n3. 데이터 읽기 테스트 시작...")
        print("Ctrl+C로 종료")
        print("-" * 60)
        print("프레임 | 최소온도 | 최대온도 | 평균온도 | FPS | 프레임시간")
        print("-" * 60)
        
        frame_count = 0
        start_time_global = time.time()
        fps_history = []
        
        while True:
            t0 = time.time()
            
            try:
                # 프레임 읽기
                mlx.getFrame(frame)
                
                # 온도 통계 계산
                tmin = min(frame)
                tmax = max(frame)
                tavg = statistics.fmean(frame)
                
                # FPS 계산
                frame_time = time.time() - t0
                fps = 1.0 / frame_time
                fps_history.append(fps)
                
                # 출력 (최근 10개 FPS의 평균)
                avg_fps = statistics.fmean(fps_history[-10:]) if fps_history else fps
                
                print(f"{frame_count:05d} | {tmin:7.2f}°C | {tmax:7.2f}°C | {tavg:7.2f}°C | {avg_fps:4.1f} | {frame_time:6.3f}s")
                
                frame_count += 1
                
                # 지정된 프레임 수만큼 실행
                if frames > 0 and frame_count >= frames:
                    break
                    
            except RuntimeError as e:
                print(f"⚠️  프레임 읽기 오류: {e}")
                time.sleep(0.1)
                continue
            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
                break
            except Exception as e:
                print(f"❌ 예상치 못한 오류: {e}")
                time.sleep(1)
        
        # 결과 요약
        elapsed = time.time() - start_time_global
        if frame_count > 0:
            print(f"\n{'='*60}")
            print("📊 테스트 결과 요약")
            print(f"{'='*60}")
            print(f"총 프레임 수: {frame_count}")
            print(f"총 시간: {elapsed:.1f}초")
            print(f"실제 FPS: {frame_count/elapsed:.2f}")
            print(f"목표 FPS: {refresh_rate}")
            
            if fps_history:
                print(f"평균 FPS: {statistics.fmean(fps_history):.2f}")
                print(f"최소 FPS: {min(fps_history):.2f}")
                print(f"최대 FPS: {max(fps_history):.2f}")
            
            # 온도 범위 분석
            if frame_count > 0:
                print(f"\n🌡️ 온도 분석:")
                print(f"최소 온도: {tmin:.2f}°C")
                print(f"최대 온도: {tmax:.2f}°C")
                print(f"평균 온도: {tavg:.2f}°C")
                print(f"온도 범위: {tmax - tmin:.2f}°C")
        
        print("\n✅ Thermal Camera 고급 테스트 완료")
        return True
        
    except Exception as e:
        print(f"❌ Thermal Camera 테스트 실패: {e}")
        return False

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="MLX90640 Thermal Camera 고급 테스트",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-r", "--rate", 
        type=int, 
        choices=[1, 2, 4, 8, 16], 
        default=2, 
        help="MLX90640 리프레시 레이트 (Hz)"
    )
    parser.add_argument(
        "-n", "--frames", 
        type=int, 
        default=0, 
        help="캡처할 프레임 수 (0 = 무한 실행)"
    )
    
    args = parser.parse_args()
    
    print(f"🎯 설정: 리프레시 레이트 = {args.rate} Hz")
    if args.frames > 0:
        print(f"🎯 설정: 프레임 수 = {args.frames}")
    else:
        print("🎯 설정: 무한 실행 (Ctrl+C로 중단)")
    
    test_thermal_camera_advanced(args.rate, args.frames)

if __name__ == "__main__":
    main() 