#### sudo apt install -y python3-gpiozero
#### #!/usr/bin/env python3 지우면 안됩니다

#!/usr/bin/env python3

#from gpiozero import AngularServo
#import math, random, time

import pigpio
import time


pi = pigpio.pi()


PAYLOAD_MOTOR_PIN = 12

# Calibrate the pulse range
PAYLOAD_MOTOR_MIN_PULSE = 500
PAYLOAD_MOTOR_MAX_PULSE = 2500



def angle_to_pulse(angle):
    if angle < int(0):
        angle = int(0)
    elif angle > int(180):
        angle = int(180)

    return int(PAYLOAD_MOTOR_MIN_PULSE + ((angle/180)*(PAYLOAD_MOTOR_MAX_PULSE - PAYLOAD_MOTOR_MIN_PULSE)))



pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, 2500)

for i in range(10):
    ang = int(input("asdf"))
    pi.set_servo_pulsewidth(PAYLOAD_MOTOR_PIN, angle_to_pulse(ang))
pi.stop()
