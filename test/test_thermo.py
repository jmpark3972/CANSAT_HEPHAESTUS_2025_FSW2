# test.py
import time
from smbus2 import SMBus, i2c_msg

I2C_BUS  = 1
I2C_ADDR = 0x5C  # DHT12 기본 주소

def read_dht12(bus, addr):
    # 1) 레지스터 포인터 0x00 전송
    write = i2c_msg.write(addr, [0x00])
    read  = i2c_msg.read(addr, 5)
    bus.i2c_rdwr(write, read)

    data = list(read)
    if len(data) != 5:
        raise RuntimeError(f"Expected 5 bytes, got {len(data)}")

    # 습도·온도·체크섬 분해
    h_int, h_dec, t_int, t_dec_raw, checksum = data

    # 체크섬 검사
    if ((h_int + h_dec + t_int + t_dec_raw) & 0xFF) != checksum:
        raise RuntimeError(f"Checksum mismatch: {data}")

    # 습도 계산
    humidity = h_int + (h_dec * 0.1)

    # 온도 계산 (부호 비트 검사)
    negative = bool(t_dec_raw & 0x80)
    t_dec    = t_dec_raw & 0x7F
    temp     = t_int + (t_dec * 0.1)
    if negative:
        temp = -temp

    return temp, humidity

def main():
    with SMBus(I2C_BUS) as bus:
        print("Starting DHT12 I²C read (0x5C)…\nCtrl-C to exit\n")
        while True:
            try:
                temp, hum = read_dht12(bus, I2C_ADDR)
                print(f"Temp = {temp:.1f} °C   Humidity = {hum:.1f} %")
            except Exception as e:
                print("Read error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
