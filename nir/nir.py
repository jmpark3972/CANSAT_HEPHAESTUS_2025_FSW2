import time
import os
from datetime import datetime

log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file
firlogfile = open(os.path.join(log_dir, 'fir.txt'), 'a')

def log_fir(text):

    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    firlogfile.write(string_to_write)
    firlogfile.flush()
    

def init_mlx90614():
    import busio
    import board
    import adafruit_mlx90614

    i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
    sensor = adafruit_mlx90614.MLX90614(i2c)
    return i2c, sensor


def read_sensor_data(sensor):
    ambient_temp = sensor.ambient_temperature
    object_temp = sensor.object_temperature

    log_fir(f"Ambient Temp: {ambient_temp:.2f} C, Object Temp: {object_temp:.2f} C")
    return ambient_temp, object_temp



def terminate_fir(i2c):
    i2c.deinit()
    return

if __name__ == "__main__":
    i2c, sensor = init_mlx90614()
    try:
        while True:
            try:
                ambient_temp, object_temp = read_sensor_data(sensor)
                print(f"Ambient Temperature: {ambient_temp:.2f} C, Object Temperature: {object_temp:.2f} C")
            except Exception as e:
                print(f"Error reading sensor data: {e}")
            time.sleep(1.0)
    except KeyboardInterrupt:
        terminate_fir(i2c)
