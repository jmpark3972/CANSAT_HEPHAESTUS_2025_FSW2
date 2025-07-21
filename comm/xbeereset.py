import time

# GPIO number for xbee reset pin
XBEE_RESET_PIN = 18

def send_reset_pulse():
    import pigpio

    pi = pigpio.pi()
    
    # Firstly, set the pin to floating
    pi.set_mode(XBEE_RESET_PIN, pigpio.INPUT)
    pi.set_pull_up_down(XBEE_RESET_PIN, pigpio.PUD_OFF)

    time.sleep(0.1)

    # Drive the line low for reset
    pi.set_mode(XBEE_RESET_PIN, pigpio.OUTPUT)
    pi.write(XBEE_RESET_PIN, 0)

    # From the XBee documentation, the reset pulse length should be at least 200ns, we take 0.1 second
    time.sleep(0.1)

    # Enough pulse has been given, set the line to floating again

    pi.set_mode(XBEE_RESET_PIN, pigpio.INPUT)

    return
    
