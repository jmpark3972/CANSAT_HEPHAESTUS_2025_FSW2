import time, board, adafruit_dht

def init_dht11():
    # Raspberry Pi에서는 use_pulseio=False 가 안전
    return adafruit_dht.DHT11(board.D4, use_pulseio=False)

sensor = init_dht11()

while True:
    try:
        temp = sensor.temperature      # °C
        humi = sensor.humidity         # %
        print(f"{temp:.1f} °C  {humi:.1f} %")
    except RuntimeError as e:
        # 신호 오류는 흔하므로 재시도
        print("Retrying:", e)
    except Exception as e:
        sensor.exit()                  # GPIO 핀 해제
        raise e
    time.sleep(2)
