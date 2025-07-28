import time, board, busio
from adafruit_as726x import AS726x_I2C

i2c = busio.I2C(board.SCL, board.SDA)
s   = AS726x_I2C(i2c)

s.driver_led       = False    # 내부 LED 완전 OFF
s.indicator_led    = False
s.gain             = 1        # 가장 낮은 1×
s.integration_time = 3        # 범위 2.8-714 ms 중 최소치≈3 ms


while True:
    if s.data_ready:
        raw = [s.read_channel(i) for i in range(1,7)]
        print(raw)                  # 각 채널 수천 단위로 요동
