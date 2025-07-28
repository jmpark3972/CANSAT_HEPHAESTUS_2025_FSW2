import time, math, board, busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn

i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
chan = AnalogIn(ads, ADS.P1)      # ← A1으로 변경

VCC   = 3.3
R_fix = 10000.0
R0    = 10000.0
T0    = 298.15
B     = 3435.0

while True:
    voltage = chan.voltage
    if voltage <= 0.0 or voltage >= VCC:
        print(f"Ignored invalid voltage reading: {voltage:.4f} V")
    else:
        R_th = R_fix * (VCC - voltage) / voltage
        ratio = R_th / R0
        if ratio <= 0.0:
            print(f"Ignored invalid resistance ratio: R_th={R_th:.1f} Ω")
        else:
            T_kelvin  = 1.0 / (1.0/T0 + (1.0/B) * math.log(ratio))
            T_celsius = T_kelvin - 273.15
            print(f"Measured Temperature: {T_celsius:.2f} °C")
    time.sleep(1)
