import time
import busio
import board
import adafruit_mlx90614

def init_mlx90614():
    i2c = busio.I2C(board.SCL, board.SDA, frequency=100000)
    sensor = adafruit_mlx90614.MLX90614(i2c)
    return i2c, sensor

def read_sensor_data(sensor):
    ambient_temp = sensor.ambient_temperature
    object_temp = sensor.object_temperature
    return ambient_temp, object_temp



#메인 루프 예시
sensor = init_mlx90614()
while True:
    try:
        ambient_temp, object_temp = read_sensor_data(sensor)
        print(f"Ambient Temperature: {ambient_temp:.2f} C, Object Temperature: {object_temp:.2f} C")
    except Exception as e:
        print(f"Error reading sensor data: {e}")
        time.sleep(1.0)
    time.sleep(1.0)  




