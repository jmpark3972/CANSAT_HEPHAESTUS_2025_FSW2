

import os, time
from datetime import datetime

# ──────────────────────
# 1)  로그 파일 준비
# ──────────────────────
LOG_DIR = "./sensorlogs"
os.makedirs(LOG_DIR, exist_ok=True)
logfile = open(os.path.join(LOG_DIR, "thermal_cam.txt"), "a")

def log_thermal(text: str) -> None:
    t = datetime.now().isoformat(sep=" ", timespec="milliseconds")
    logfile.write(f"{t},{text}\n")
    logfile.flush()

# ──────────────────────
# 2)  초기화 / 종료
# ──────────────────────
def init_cam(refresh_hz: int | float = 2):
    """
    MLX90640 센서를 초기화 후 mlx 객체를 반환.
    refresh_hz : 0.5, 1, 2, 4, 8, 16, 32, 64 중 택1
    """
    import board, busio, adafruit_mlx90640 as mlxlib

    hz_map = {
        0.5: mlxlib.RefreshRate.REFRESH_0_5_HZ,
        1  : mlxlib.RefreshRate.REFRESH_1_HZ,
        2  : mlxlib.RefreshRate.REFRESH_2_HZ,
        4  : mlxlib.RefreshRate.REFRESH_4_HZ,
        8  : mlxlib.RefreshRate.REFRESH_8_HZ,
        16 : mlxlib.RefreshRate.REFRESH_16_HZ,
        32 : mlxlib.RefreshRate.REFRESH_32_HZ,
        64 : mlxlib.RefreshRate.REFRESH_64_HZ,
    }
    if refresh_hz not in hz_map:
        raise ValueError("refresh_hz must be one of " + ", ".join(map(str, hz_map)))

    # I2C: 800 kHz 권장 (MLX90640 데이터시트)
    i2c = busio.I2C(board.SCL, board.SDA, frequency=800_000)
    
    # Qwiic Mux 초기화 및 채널 4 선택 (Thermal Camera 위치)
    from lib.qwiic_mux import QwiicMux
    mux = QwiicMux(i2c_bus=i2c, mux_address=0x70)
    mux.select_channel(4)  # Thermal Camera는 채널 4에 연결
    time.sleep(0.1)  # 안정화 대기
    
    # MLX90640 일반적인 I2C 주소들 시도
    mlx_addresses = [0x33, 0x32, 0x34]
    mlx = None
    
    for addr in mlx_addresses:
        try:
            print(f"Thermal Camera I2C 주소 0x{addr:02X} 시도 중...")
            mlx = mlxlib.MLX90640(i2c, address=addr)
            mlx.refresh_rate = hz_map[refresh_hz]
            print(f"Thermal Camera 초기화 성공 (주소: 0x{addr:02X})")
            break
        except Exception as e:
            print(f"주소 0x{addr:02X} 실패: {e}")
            continue
    
    if mlx is None:
        raise Exception("Thermal Camera를 찾을 수 없습니다. I2C 연결을 확인하세요.")
    
    mlx.refresh_rate = hz_map[refresh_hz]
    
    return i2c, mlx, mux

    print("MLX90640 serial:", [hex(x) for x in mlx.serial_number])
    return i2c, mlx

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

def read_cam(mlx, ascii: bool = False):
    """
    한 프레임(768 픽셀)을 읽어 리스트로 반환하고 로그에 기록.
    오류(ValueError) 발생 시 None 반환.
    ascii=True 이면 콘솔에 ASCII 아트 출력.
    """
    frame = [0.0] * 768
    try:
        mlx.getFrame(frame)
    except ValueError:
        log_thermal("READ_ERROR")
        return None

    # 통계치 계산
    t_min, t_max = min(frame), max(frame)
    t_avg = round(sum(frame) / len(frame), 2)

    # CSV 한 줄로 저장: <avg>,<min>,<max>,<768val...>
    csv_line = ",".join(
        [f"{t_avg:.2f}", f"{t_min:.2f}", f"{t_max:.2f}"]
        + [f"{v:.2f}" for v in frame]
    )
    log_thermal(csv_line)

    # (옵션) ASCII 아트
    if ascii:
        for h in range(24):
            row = "".join(_ascii_pixel(frame[h * 32 + w]) for w in range(32))
            print(row)
        print()

    return frame, t_min, t_max, t_avg

# ──────────────────────
# 4)  단독 실행 데모
# ──────────────────────
if __name__ == "__main__":
    i2c, cam = init_cam(2)   # 2 Hz
    try:
        while True:
            stamp = time.monotonic()
            data = read_cam(cam, ascii=True)
            if data is not None:
                _, tmin, tmax, tavg = data
                print(f"Frame OK in {time.monotonic() - stamp:.2f}s  "
                      f"min={tmin:.1f}°C  max={tmax:.1f}°C  avg={tavg:.1f}°C")
            time.sleep(0.1)   # refresh_hz=2 → 0.5 s 주기, 살짝 여유
    except KeyboardInterrupt:
        pass
    finally:
        terminate_cam(i2c)
