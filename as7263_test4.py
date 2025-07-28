#from as7263 import AS7263
import time
import board, busio
from adafruit_as726x import AS726x_I2C as AS7263
i2c = busio.I2C(board.SCL, board.SDA)

try:
    sensor = AS7263(i2c)
    
    # 센서 설정 최적화 - 감도 향상
    sensor.set_measurement_mode(2)  # Continuous reading of all channels
    
    # 게인 설정 - 높은 게인으로 감도 향상 (1=1x, 2=3.7x, 3=16x, 4=64x)
    sensor.set_gain(4)  # 최대 게인으로 설정
    
    # 통합 시간 설정 - 더 긴 통합 시간으로 신호 강화 (0=2.8ms ~ 255=714ms)
    sensor.set_integration_time(100)  # 약 280ms 통합 시간
    
    # LED 설정
    sensor.set_illumination_led(1)  # Turn on the onboard LED
    
    print("Reading AS7263 data with enhanced sensitivity...")
    print(f"Gain: {sensor.get_gain()}")
    print(f"Integration Time: {sensor.get_integration_time()} cycles")
    
    # 이전 값과 비교를 위한 변수
    prev_values = None
    
    while True:
        # Check if data is available
        if sensor.data_available():
            # 원시 값과 보정된 값 모두 가져오기
            raw_values = sensor.get_raw_values()
            calibrated_values = sensor.get_calibrated_values()
            
            # 개별 채널 값들 출력
            print("\n" + "="*50)
            print(f"Raw Values: {raw_values}")
            print(f"Calibrated Values: {calibrated_values}")
            
            # 개별 채널별 상세 정보
            channels = ['610nm', '680nm', '730nm', '760nm', '810nm', '860nm']
            for i, channel in enumerate(channels):
                raw_val = raw_values[i] if i < len(raw_values) else 0
                cal_val = calibrated_values[i] if i < len(calibrated_values) else 0
                print(f"{channel}: Raw={raw_val:8.2f}, Calibrated={cal_val:8.4f}")
            
            # 변화량 계산 및 출력
            if prev_values is not None:
                changes = []
                for i in range(min(len(calibrated_values), len(prev_values))):
                    change = calibrated_values[i] - prev_values[i]
                    change_percent = (change / prev_values[i] * 100) if prev_values[i] != 0 else 0
                    changes.append((change, change_percent))
                
                print("\nChanges from previous reading:")
                for i, (change, change_percent) in enumerate(changes):
                    if i < len(channels):
                        print(f"{channels[i]}: Δ={change:8.4f} ({change_percent:6.2f}%)")
            
            prev_values = calibrated_values.copy()
            
            # 더 빠른 샘플링 (0.5초)
            time.sleep(0.5)

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()
finally:
    # Clean up or turn off LEDs if necessary
    if 'sensor' in locals() and sensor.illumination_led_enabled():
        sensor.set_illumination_led(0)
