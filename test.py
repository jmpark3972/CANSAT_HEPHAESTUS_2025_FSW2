import time
import board
import adafruit_dht

def init_dht11():
    # dht11 시작, GPIO 4번 가정
    sensor = adafruit_dht.DHT11(board.D4)
    return sensor
    
def read_sensor_data(sensor):
    temperature = sensor.temperature
    humidity = sensor.humidity 

    return temperature, humidity


#예시 루프
sensor = init_dht11()
while True:
    temperature, humidity = read_sensor_data(sensor)
    try:
        print(f'{temperature:.1f} C, {humidity:.2f} %')
    except RuntimeError as error:
        print(error.args[0])
        time.sleep(3.0)
        continue
    except Exception as error:
        sensor.exit()
        raise error
        
    time.sleep(2.0)
