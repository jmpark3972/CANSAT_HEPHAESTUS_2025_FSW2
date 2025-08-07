

import os, time
from datetime import datetime
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
        # 24x32 픽셀 데이터 읽기
        frame = [0] * 768  # 24x32 = 768 pixels
        sensor.getFrame(frame)
        
        # 온도 계산 (섭씨로 변환)
        temps = [temp - 273.15 for temp in frame]  # 켈빈을 섭씨로 변환
        min_temp = min(temps)
        max_temp = max(temps)
        avg_temp = sum(temps) / len(temps)
        
        return min_temp, max_temp, avg_temp, temps
        
    except Exception as e:
        print(f"Thermal Camera 데이터 읽기 오류: {e}")
        return None, None, None, None

# ──────────────────────
# 4)  열화상 데이터 처리 (OpenCV 없이)
# ──────────────────────
def process_thermal_data(temps):
    """온도 데이터 처리 및 통계 계산"""
    try:
        if temps is None or len(temps) == 0:
            return 0.0, 0.0, 0.0
        
        temp_array = np.array(temps)
        min_temp = np.min(temp_array)
        max_temp = np.max(temp_array)
        avg_temp = np.mean(temp_array)
        
        return min_temp, max_temp, avg_temp
        
    except Exception as e:
        print(f"열화상 데이터 처리 오류: {e}")
        return 0.0, 0.0, 0.0

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
