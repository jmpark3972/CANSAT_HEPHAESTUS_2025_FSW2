import time, board, busio, adafruit_mlx90640, numpy as np

I2C_FREQ = 800_000
i2c = busio.I2C(board.SCL, board.SDA, frequency=I2C_FREQ)

mlx = adafruit_mlx90640.MLX90640(i2c, address=0x33)
mlx.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ   # 2 fps

frame = np.zeros((24*32,), dtype=float)     # NumPy 배열로 받기

def grab_frame():
    """1장의 프레임을 (24,32) 모양 2D 배열로 리턴"""
    while True:
        try:
            mlx.getFrame(frame)
            return frame.reshape((24, 32))
        except ValueError:          # CRC 오류 등
            continue

if __name__ == "__main__":
    while True:
        t0 = time.monotonic()
        img = grab_frame()
        print(f"{time.monotonic()-t0:0.3f}s  min={img.min():.1f}°C  max={img.max():.1f}°C")
        # TODO: 여기서 SD카드에 저장하거나 RF 전송
