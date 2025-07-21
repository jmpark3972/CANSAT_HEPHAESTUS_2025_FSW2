import time
import board
import busio
from adafruit_ads1x15.ads1115 import ADS1115
from adafruit_ads1x15.analog_in import AnalogIn

###사실상 ads1115의 코드

def init_ads1115():
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS1115(i2c)
    chan0 = AnalogIn(ads, 0)  #A0 채널
    chan1 = AnalogIn(ads, 1)  #A1 채널
    return chan0, chan1

print("G-TPCO-035, ads1115 테스트")
print("------------------------------------")

v_in = 3.3
r_ref = 220
sensitivity = 0.034
t_offset = -82
while True:
    chan0,chan1 = init_ads1115()
    voltage = chan0.voltage
    v_rtd = chan1.voltage
    r_rtd = (v_rtd / (v_in - v_rtd)) * r_ref
    t_sensor = (r_rtd / 1000 - 1) / 0.006178 
    t_target = (voltage/ sensitivity) + t_sensor + t_offset
    print(f'Voltage: {voltage:.6f} V, R_rtd = {r_rtd:.6f}ohm, Temperature: {t_target:.6f} C')
    time.sleep(1)

