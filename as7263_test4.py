#from as7263 import AS7263
import time
import board, busio
from adafruit_as726x import AS726x_I2C as AS7263
i2c = busio.I2C(board.SCL, board.SDA)

try:
    sensor = AS7263(i2c)
    sensor.set_measurement_mode(2) # Continuous reading of all channels
    sensor.set_illumination_led(1) # Turn on the onboard LED

    print("Reading AS7263 data...")
    while True:
        # Check if data is available
        if sensor.data_available():
            # Get calibrated values
            nir_values = sensor.get_calibrated_values()
            print(f"NIR Values: {nir_values}")
            time.sleep(1) # Wait for a second before next reading

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    # Clean up or turn off LEDs if necessary
    if 'sensor' in locals() and sensor.illumination_led_enabled():
        sensor.set_illumination_led(0)
