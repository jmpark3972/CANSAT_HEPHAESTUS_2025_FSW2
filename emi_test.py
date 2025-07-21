# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT
import time
import board
import busio
import adafruit_dht
import adafruit_mlx90614
import adafruit_mlx90640

PRINT_TEMPERATURES = False  # True로 바꾸면 수치 출력
PRINT_ASCIIART     = True    # 싱글 프레임 ASCII 아트

FRAME_SIZE = 24 * 32
frame = [0.0] * FRAME_SIZE   # MLX90640 한 프레임 버퍼

# ────────────────────────────────────────────────
# 초기화 함수
# ────────────────────────────────────────────────
def init_dht11(pin=board.D4):
    return adafruit_dht.DHT11(pin)

def init_i2c(frequency=100_000):        # 100 kHz: 두 센서 모두 호환
    return busio.I2C(board.SCL, board.SDA, frequency=frequency)

def init_mlx90614(i2c):
    return adafruit_mlx90614.MLX90614(i2c)

def init_mlx90640(i2c):
    sensor = adafruit_mlx90640.MLX90640(i2c)
    sensor.refresh_rate = adafruit_mlx90640.RefreshRate.REFRESH_2_HZ
    return sensor

# ────────────────────────────────────────────────
# 센서 판독 래퍼
# ────────────────────────────────────────────────
def read_dht11(sensor):
    return sensor.temperature, sensor.humidity

def read_mlx90614(sensor):
    return sensor.ambient_temperature, sensor.object_temperature

# ────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────
def main():
    # 공용 I²C 버스 100 kHz
    i2c_bus = init_i2c()

    # 센서들
    dht11        = init_dht11()
    mlx90614     = init_mlx90614(i2c_bus)
    mlx90640     = init_mlx90640(i2c_bus)

    while True:
        # DHT11
        try:
            t_air, rh = read_dht11(dht11)
            print(f"DHT11  : {t_air:5.1f} °C, {rh:5.1f} %RH")
        except RuntimeError as e:               # CRC 오류 등
            print(f"DHT11  : {e}")
        except Exception as e:
            print(f"DHT11  치명 오류: {e}")
            break

        # MLX90614 (1-pixel IR thermometer)
        try:
            tamb, tobj = read_mlx90614(mlx90614)
            print(f"MLX90614: Tamb {tamb:5.2f} °C  Tobj {tobj:5.2f} °C")
        except Exception as e:
            print(f"MLX90614 읽기 오류: {e}")

        # MLX90640 (24×32 열화상)
        try:
            mlx90640.getFrame(frame)
        except ValueError:
            print("MLX90640 프레임 오류")
        else:
            if PRINT_ASCIIART:
                for h in range(24):
                    row = ""
                    for w in range(32):
                        t = frame[h * 32 + w]
                        if   t < 20: row += " "
                        elif t < 23: row += "."
                        elif t < 25: row += "-"
                        elif t < 27: row += "*"
                        elif t < 29: row += "+"
                        elif t < 31: row += "x"
                        elif t < 33: row += "%"
                        elif t < 35: row += "#"
                        elif t < 37: row += "X"
                        else:        row += "&"
                    print(row)
                print()

            if PRINT_TEMPERATURES:
                print(", ".join(f"{t:0.1f}" for t in frame))

        time.sleep(1.0)

if __name__ == "__main__":
    main()
