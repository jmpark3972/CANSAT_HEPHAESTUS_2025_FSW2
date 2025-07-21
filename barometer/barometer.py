# SPDX-FileCopyrightText: 2021 ladyada for Adafruit Industries
# SPDX-License-Identifier: MIT

import time
import os
from datetime import datetime

log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file
barometerlogfile = open(os.path.join(log_dir, 'barometer.txt'), 'a')

def log_barometer(text):

    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    barometerlogfile.write(string_to_write)
    barometerlogfile.flush()
    
def init_barometer():
    import adafruit_bmp3xx
    import board
    import busio
    # I2C setup
    # i2c = board.I2C()
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    bmp = adafruit_bmp3xx.BMP3XX_I2C(i2c)

    bmp.pressure_oversampling = 8
    bmp.temperature_oversampling = 2

    return i2c, bmp

# Read Barometer data and returns tuple (pressure, temperature, altitude)
def read_barometer(bmp, offset:float):
    global altitude_altZero
    
    pressure = bmp.pressure
    temperature = bmp.temperature
    altitude = bmp.altitude

    # Type Checking of barometer data
    if type(pressure) == float:
        pressure = round(pressure, 2)
    else:
        pressure = 0

    if type(temperature) == float:
        temperature = round(temperature, 2)
    else:
        temperature = 0

    if type(altitude) == float:
        altitude = round(altitude, 2)
    else:
        altitude = 0

    # Apply offset
    altitude = round(altitude - offset, 2)

    log_barometer(f"{pressure:.2f}, {temperature:.2f}, {altitude:.2f}")
    
    return ( pressure, temperature, altitude )

def terminate_barometer(i2c):
    try:
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        elif hasattr(i2c, "close"):
            i2c.close()
    except Exception as e:
        print(f"I2C cleanup failed: {e}")

if __name__ == "__main__":
    i2c, bmp = init_barometer()
    try:
        while True:
            data = read_barometer(bmp, 0)
            print(data)
            time.sleep(1)
    except KeyboardInterrupt:
        terminate_barometer(i2c)
