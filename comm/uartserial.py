import threading
import time
import serial

SERIAL_PORT = "/dev/serial0"
SERIAL_BAUD = 9600
SERIAL_TIMEOUT = 1

def init_serial():

    # Open serial port (adjust the port and baudrate as needed)
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)

    return ser

def send_serial_data(ser, string_to_write:str):

    if ser == None:
        return
    
    ser.write(string_to_write.encode())

def receive_serial_data(ser) -> str:

    if ser == None:
        return ""
    
    try:
        read_data = ser.readline().decode().strip()
        return read_data
    except serial.SerialException as e:
        print(f"Serial communication error: {e}")
        return ""
    except UnicodeDecodeError as e:
        print(f"Data decode error: {e}")
        return ""
    except Exception as e:
        print(f"Unexpected error in serial read: {e}")
        return ""

def terminate_serial(ser):
    if ser == None:
        return
    # Close the serial port
    ser.close()

DEBUG_RUNSTATUS = True

def debug_send_tlm_thread(ser):
    global DEBUG_RUNSTATUS
    while DEBUG_RUNSTATUS:
        send_serial_data(ser, "Hello World!")
        time.sleep(1)
    return

if __name__ == "__main__":
    print("DEBUG MODE")
    serial_instance = init_serial()

    try:
        threading.Thread(target = debug_send_tlm_thread, args=(serial_instance,), daemon=True ).start()

        while DEBUG_RUNSTATUS:
            rcv_data = receive_serial_data(serial_instance)
            if rcv_data == "":
                print("TIMEOUT")
            else:
                print(rcv_data)
            time.sleep(1)

    except KeyboardInterrupt:
        print("Keyboard Interrupt!")
        
    finally:
        DEBUG_RUNSTATUS = False
        terminate_serial(serial_instance)
