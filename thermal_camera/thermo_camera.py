

import os, time
from datetime import datetime
import cv2
import numpy as np

# ──────────────────────
# 1)  로그 파일 준비
# ──────────────────────
LOG_DIR = "./sensorlogs"
VIDEO_DIR = "./logs/thermal_videos"  # 열화상 영상 저장 디렉토리
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)
logfile = open(os.path.join(LOG_DIR, "thermal_cam.txt"), "a")

def log_thermal(text: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    logfile.write(f"{t},{text}\n")
    logfile.flush()

# ──────────────────────
# 2)  초기화 / 종료
# ──────────────────────
def init_thermal_camera():
    """Thermal Camera 센서 초기화 (직접 I2C 연결)"""
    import board
    import busio
    import adafruit_mlx90640
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    try:
        # Thermal Camera 센서 직접 연결 (MLX90640 at 0x33)
        sensor = adafruit_mlx90640.MLX90640(i2c, address=0x33)
        sensor.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
        time.sleep(0.1)
        print("Thermal Camera MLX90640 센서 초기화 완료 (주소: 0x33)")
        return i2c, sensor
    except Exception as e:
        print(f"Thermal Camera 초기화 실패: {e}")
        raise Exception(f"Thermal Camera 초기화 실패: {e}")

def terminate_cam(i2c) -> None:
    try:
        i2c.deinit()
    except AttributeError:
        pass  # busio 버전에 따라 deinit() 없을 수도 있음

# ──────────────────────
# 3)  프레임 읽기
# ──────────────────────
def _ascii_pixel(val: float) -> str:
    """온도 값 → ASCII 글리프 매핑 (20 °C 기준)."""
    if val < 20:  return " "
    if val < 23:  return "."
    if val < 25:  return "-"
    if val < 27:  return "*"
    if val < 29:  return "+"
    if val < 31:  return "x"
    if val < 33:  return "%"
    if val < 35:  return "#"
    if val < 37:  return "X"
    return "&"

def read_cam(sensor, ascii: bool = False):
    """Thermal Camera 센서 데이터 읽기 (MLX90640)"""
    try:
        # 24x32 픽셀 데이터 읽기 (재시도 로직 추가)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                frame = [0] * 768  # 24x32 = 768 pixels
                sensor.getFrame(frame)
                break  # 성공하면 루프 탈출
            except Exception as retry_error:
                if attempt < max_retries - 1:
                    time.sleep(0.1)  # 잠시 대기 후 재시도
                    continue
                else:
                    raise retry_error  # 마지막 시도에서도 실패하면 예외 발생
        
        # 온도 계산 (섭씨로 변환 후 +273.15 오프셋 추가)
        temps = [temp - 273.15 + 273.15 for temp in frame]  # 섭씨로 변환 후 +273.15 오프셋 (실제로는 원본 켈빈 값)
        min_temp = min(temps)
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        # 738개 전체 데이터를 로그에 저장
        try:
            timestamp = datetime.now().isoformat(sep=" ", timespec="milliseconds")
            temp_str = ",".join([f"{temp:.2f}" for temp in temps])
            log_thermal(f"THERMAL_DATA:{temp_str}")
        except Exception as log_e:
            print(f"Thermal data logging error: {log_e}")
        
        return min_temp, max_temp, avg_temp, temps
        
    except Exception as e:
        print(f"Thermal Camera 데이터 읽기 오류: {e}")
        return None, None, None, None

# ──────────────────────
# 4)  열화상 영상 저장 기능
# ──────────────────────
def create_thermal_video_frame(temps, width=320, height=240):
    """온도 데이터를 영상 프레임으로 변환"""
    try:
        # 24x32 온도 데이터를 320x240으로 확대
        temp_array = np.array(temps).reshape(24, 32)
        
        # 온도 범위 정규화 (0-255)
        temp_min = np.min(temp_array)
        temp_max = np.max(temp_array)
        if temp_max > temp_min:
            normalized = ((temp_array - temp_min) / (temp_max - temp_min) * 255).astype(np.uint8)
        else:
            normalized = np.zeros((24, 32), dtype=np.uint8)
        
        # 320x240으로 확대
        resized = cv2.resize(normalized, (width, height), interpolation=cv2.INTER_LINEAR)
        
        # 컬러맵 적용 (jet 컬러맵)
        colored = cv2.applyColorMap(resized, cv2.COLORMAP_JET)
        
        return colored
        
    except Exception as e:
        print(f"열화상 프레임 생성 오류: {e}")
        return np.zeros((height, width, 3), dtype=np.uint8)

def record_thermal_video(sensor, duration=5, fps=2):
    """열화상 영상 녹화"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_filename = f"thermal_video_{timestamp}.mp4"
        video_path = os.path.join(VIDEO_DIR, video_filename)
        
        # 비디오 작성자 설정
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, fps, (320, 240))
        
        start_time = time.time()
        frame_count = 0
        
        print(f"열화상 영상 녹화 시작: {duration}초")
        
        while time.time() - start_time < duration:
            # 온도 데이터 읽기
            min_temp, max_temp, avg_temp, temps = read_cam(sensor)
            
            if temps is not None:
                # 프레임 생성
                frame = create_thermal_video_frame(temps)
                
                # 텍스트 추가
                cv2.putText(frame, f"Min: {min_temp:.1f}C", (10, 30), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Max: {max_temp:.1f}C", (10, 60), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(frame, f"Avg: {avg_temp:.1f}C", (10, 90), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                
                # 프레임 저장
                out.write(frame)
                frame_count += 1
            
            time.sleep(1.0 / fps)  # FPS에 맞춰 대기
        
        out.release()
        print(f"열화상 영상 녹화 완료: {video_path} ({frame_count} 프레임)")
        return video_path
        
    except Exception as e:
        print(f"열화상 영상 녹화 오류: {e}")
        return None

# ──────────────────────
# 5)  단독 실행 데모
# ──────────────────────
if __name__ == "__main__":
    i2c, cam = init_thermal_camera()   # 2 Hz
    try:
        while True:
            stamp = time.monotonic()
            data = read_cam(cam, ascii=True)
            if data is not None:
                tmin, tmax, tavg, temps = data
                print(f"Frame OK in {time.monotonic() - stamp:.2f}s  "
                      f"min={tmin:.1f}°C  max={tmax:.1f}°C  avg={tavg:.1f}°C")
            time.sleep(0.1)   # refresh_hz=2 → 0.5 s 주기, 살짝 여유
    except KeyboardInterrupt:
        pass
    finally:
        terminate_cam(i2c)
