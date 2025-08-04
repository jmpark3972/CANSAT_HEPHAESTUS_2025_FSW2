# Python FSW V2 Barometer App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types
from lib import prevstate

import signal
from multiprocessing import Queue, connection
import threading
import time

from barometer import barometer

# Runstatus of application. Application is terminated when false
BAROMETERAPP_RUNSTATUS = True

# Mutex to prevent two process sharing the same barometer instance
OFFSET_MUTEX = threading.Lock()

# Mutex to prevent sending of logic data when resetting
MAXALT_RESET_MUTEX = threading.Lock()

# MUX instance for channel 4 management
BAROMETER_MUX = None

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (Main_Queue:Queue, recv_msg : msgstructure.MsgStructure, barometer_instance):
    global BAROMETERAPP_RUNSTATUS
    global BAROMETER_OFFSET
    global MAXALT_RESET_MUTEX

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"BAROMETERAPP TERMINATION DETECTED")
        BAROMETERAPP_RUNSTATUS = False

    # Calibrate Barometer when calibrate command is input
    if recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        
        # Use mutex to prevent multiple thread accessing barometer instance at the same time
        with OFFSET_MUTEX:
            caldata = barometer.read_barometer(barometer_instance, 0)
            # altitude is the third index
            BAROMETER_OFFSET = float(caldata[2])

        # Use mutex to prevent the barometer process sending the wrong maxalt
        with MAXALT_RESET_MUTEX:
            ResetBarometerMaxAltCmd = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, ResetBarometerMaxAltCmd, appargs.BarometerAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.BarometerAppArg.MID_ResetBarometerMaxAlt, "")

            # sleep for 0.5 seconds to ensure the max alt reset. Since the mutex is holding, no barometer data can be sent to flightlogic
            time.sleep(0.5)

        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Barometer offset changed to {BAROMETER_OFFSET}")

        prevstate.update_altcal(BAROMETER_OFFSET)

    else:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global BAROMETERAPP_RUNSTATUS
    while BAROMETERAPP_RUNSTATUS:
        barometerHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, barometerHK, appargs.BarometerAppArg.AppID, appargs.HkAppArg.AppID, appargs.BarometerAppArg.MID_SendHK, str(BAROMETERAPP_RUNSTATUS))
        # 더 빠른 종료를 위해 짧은 간격으로 체크
        for _ in range(10):  # 1초를 10개 구간으로 나누어 체크
            if not BAROMETERAPP_RUNSTATUS:
                break
            time.sleep(0.1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def barometerapp_init():
    global BAROMETERAPP_RUNSTATUS
    global BAROMETER_OFFSET

    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Initializating barometerapp")
        ## User Defined Initialization goes HERE

        # Init barometer sensor
        i2c_instance, barometer_instance, mux_instance = barometer.init_barometer()
        
        # Store MUX instance globally for proper channel management
        global BAROMETER_MUX
        BAROMETER_MUX = mux_instance
        
        # Calibrate barometer if prev calibration value exists
        BAROMETER_OFFSET = (float(prevstate.PREV_ALT_CAL))

        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Barometerapp Initialization Complete")

        return i2c_instance, barometer_instance
    
    except Exception as e:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"Error during initialization: {e}")
        BAROMETERAPP_RUNSTATUS = False
        return None, None

# Termination
def barometerapp_terminate(i2c_instance):
    global BAROMETERAPP_RUNSTATUS, BAROMETER_MUX

    BAROMETERAPP_RUNSTATUS = False
    events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Terminating barometerapp")
    # Termination Process Comes Here

    # Close MUX connection
    if BAROMETER_MUX:
        try:
            BAROMETER_MUX.close()
        except Exception as e:
            events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"MUX 종료 오류: {e}")

    barometer.terminate_barometer(i2c_instance)
    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        try:
            thread_dict[thread_name].join(timeout=3)  # 3초 타임아웃
            if thread_dict[thread_name].is_alive():
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.warning, f"Thread {thread_name} did not terminate gracefully")
        except Exception as e:
            events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"Error joining thread {thread_name}: {e}")
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.info, "Terminating barometerapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################
PRESSURE = 0
TEMPERATURE = 0
ALTITUDE = 0
# Set the offset of baromter
BAROMETER_OFFSET = 0

def read_barometer_data(barometer_instance, BAROMETER_OFFSET):
    global PRESSURE, TEMPERATURE, ALTITUDE, BAROMETERAPP_RUNSTATUS
    while BAROMETERAPP_RUNSTATUS:
        try:
            pressure, temperature, altitude = barometer.read_barometer(barometer_instance, BAROMETER_OFFSET)
            PRESSURE = pressure
            TEMPERATURE = temperature
            ALTITUDE = altitude
        except Exception:
            # 에러 메시지 출력하지 않고, 이전 값 유지
            pass
        time.sleep(0.2)

def send_barometer_data(Main_Queue : Queue):
    global PRESSURE
    global TEMPERATURE
    global ALTITUDE
    global MAXALT_RESET_MUTEX

    # Do not forget to use runstatus variable on a global scope
    global BAROMETERAPP_RUNSTATUS

    # Create Message structure
    BarometerDataToTlmMsg = msgstructure.MsgStructure()
    BarometerDataToFlightLogicMsg = msgstructure.MsgStructure()

    msg_send_count = 0

    while BAROMETERAPP_RUNSTATUS:
        
        with MAXALT_RESET_MUTEX:
            # Send Message to Flight Logic in 10Hz
            status = msgstructure.send_msg(Main_Queue,
                                            BarometerDataToFlightLogicMsg,
                                            appargs.BarometerAppArg.AppID,
                                            appargs.FlightlogicAppArg.AppID,
                                            appargs.BarometerAppArg.MID_SendBarometerFlightLogicData,
                                            f"{ALTITUDE}")
            if status == False:
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Error When sending Barometer Flight Logic Message")

        if msg_send_count > 10 : 
            # Send telemetry message to COMM app in 1Hz
            status = msgstructure.send_msg(Main_Queue, 
                                        BarometerDataToTlmMsg, 
                                        appargs.BarometerAppArg.AppID,
                                        appargs.CommAppArg.AppID,
                                        appargs.BarometerAppArg.MID_SendBarometerTlmData,
                                        f"{PRESSURE},{TEMPERATURE},{ALTITUDE}")
            if status == False:
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Error When sending Barometer Tlm Message")

            msg_send_count = 0
        
        # Increment message send counter, Sleep 1 second
        msg_send_count += 1
        time.sleep(0.1)
    return

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while BAROMETERAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            time.sleep(1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

# This method is called from main app. Initialization, runloop process
def barometerapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global BAROMETERAPP_RUNSTATUS
    BAROMETERAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, barometer_instance = barometerapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendBarometerData_Thread"] = threading.Thread(target=send_barometer_data, args=(Main_Queue, ), name="SendBarometerData_Thread")
    thread_dict["READ"] = resilient_thread(read_barometer_data, args=(barometer_instance, BAROMETER_OFFSET), name="READ")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while BAROMETERAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            # Non-blocking receive with timeout
            if Main_Pipe.poll(1.0):  # 1초 타임아웃
                try:
                    message = Main_Pipe.recv()
                except:
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from barometerapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.BarometerAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(Main_Queue, recv_msg, barometer_instance)
            else:
                events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, "Receiver MID does not match with barometerapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.BarometerAppArg.AppName, events.EventType.error, f"barometerapp error : {e}")
        BAROMETERAPP_RUNSTATUS = False

    # Termination Process after runloop
    barometerapp_terminate(i2c_instance)

    return
