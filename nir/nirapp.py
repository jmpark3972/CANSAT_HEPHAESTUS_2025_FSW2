# Python FSW V2 Fir App
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

from CANSAT_HEPHAESTUS_2025_NIR.nir import fir

# Runstatus of application. Application is terminated when false
FIRAPP_RUNSTATUS = True

# Mutex to prevent two process sharing the same fir instance
OFFSET_MUTEX = threading.Lock()

# Mutex to prevent sending of logic data when resetting
MAXALT_RESET_MUTEX = threading.Lock()

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (Main_Queue:Queue, recv_msg : msgstructure.MsgStructure, fir_instance):
    global FIRAPP_RUNSTATUS
    global FIR_OFFSET
    global MAXALT_RESET_MUTEX

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, f"FIRAPP TERMINATION DETECTED")
        FIRAPP_RUNSTATUS = False

    # Calibrate Fir when calibrate command is input
    if recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        
        # Use mutex to prevent multiple thread accessing fir instance at the same time
        with OFFSET_MUTEX:
            caldata = fir.read_fir(fir_instance, 0)
            # altitude is the third index
            FIR_OFFSET = float(caldata[2])

        # Use mutex to prevent the fir process sending the wrong maxalt
        with MAXALT_RESET_MUTEX:
            ResetFirMaxAltCmd = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, ResetFirMaxAltCmd, appargs.FirAppArg.AppID, appargs.FlightlogicAppArg.AppID, appargs.FirAppArg.MID_ResetFirMaxAlt, "")

            # sleep for 0.5 seconds to ensure the max alt reset. Since the mutex is holding, no fir data can be sent to flightlogic
            time.sleep(0.5)

        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, f"Fir offset changed to {FIR_OFFSET}")

        prevstate.update_altcal(FIR_OFFSET)

    else:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global FIRAPP_RUNSTATUS
    while FIRAPP_RUNSTATUS:
        firHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, firHK, appargs.FirAppArg.AppID, appargs.HkAppArg.AppID, appargs.FirAppArg.MID_SendHK, str(FIRAPP_RUNSTATUS))
        time.sleep(1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def firapp_init():
    global FIRAPP_RUNSTATUS
    global FIR_OFFSET

    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, "Initializating firapp")
        ## User Defined Initialization goes HERE

        # Init fir sensor
        i2c_instance, fir_instance = fir.init_fir()
        
        # Calibrate fir if prev calibration value exists
        FIR_OFFSET = (float(prevstate.PREV_ALT_CAL))

        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, "Firapp Initialization Complete")

        return i2c_instance, fir_instance
    
    except Exception as e:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, f"Error during initialization: {e}")
        FIRAPP_RUNSTATUS = False
        return None, None

# Termination
def firapp_terminate(i2c_instance):
    global FIRAPP_RUNSTATUS

    FIRAPP_RUNSTATUS = False
    events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, "Terminating firapp")
    # Termination Process Comes Here

    fir.terminate_fir(i2c_instance)
    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info, "Terminating firapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################
PRESSURE = 0
TEMPERATURE = 0
ALTITUDE = 0
# Set the offset of baromter
FIR_OFFSET = 0

def read_fir_data(fir_instance):
    global PRESSURE
    global TEMPERATURE
    global ALTITUDE
    global FIR_OFFSET
    global OFFSET_MUTEX

    # Do not forget to use runstatus variable on a global scope
    global FIRAPP_RUNSTATUS

    while FIRAPP_RUNSTATUS:
        # Read data from Fir
        with OFFSET_MUTEX:
            PRESSURE, TEMPERATURE, ALTITUDE = fir.read_fir(fir_instance, FIR_OFFSET)

        # Sleep for 0.1 second
        time.sleep(0.1)

def send_fir_data(Main_Queue : Queue):
    global PRESSURE
    global TEMPERATURE
    global ALTITUDE
    global MAXALT_RESET_MUTEX

    # Do not forget to use runstatus variable on a global scope
    global FIRAPP_RUNSTATUS

    # Create Message structure
    FirDataToTlmMsg = msgstructure.MsgStructure()
    FirDataToFlightLogicMsg = msgstructure.MsgStructure()

    msg_send_count = 0

    while FIRAPP_RUNSTATUS:
        
        with MAXALT_RESET_MUTEX:
            # Send Message to Flight Logic in 10Hz
            status = msgstructure.send_msg(Main_Queue,
                                            FirDataToFlightLogicMsg,
                                            appargs.FirAppArg.AppID,
                                            appargs.FlightlogicAppArg.AppID,
                                            appargs.FirAppArg.MID_SendFirFlightLogicData,
                                            f"{ALTITUDE}")
            if status == False:
                events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, "Error When sending Fir Flight Logic Message")

        if msg_send_count > 10 : 
            # Send telemetry message to COMM app in 1Hz
            status = msgstructure.send_msg(Main_Queue, 
                                        FirDataToTlmMsg, 
                                        appargs.FirAppArg.AppID,
                                        appargs.CommAppArg.AppID,
                                        appargs.FirAppArg.MID_SendFirTlmData,
                                        f"{PRESSURE},{TEMPERATURE},{ALTITUDE}")
            if status == False:
                events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, "Error When sending Fir Tlm Message")

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

# This method is called from main app. Initialization, runloop process
def firapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global FIRAPP_RUNSTATUS
    FIRAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, fir_instance = firapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendFirData_Thread"] = threading.Thread(target=send_fir_data, args=(Main_Queue, ), name="SendFirData_Thread")
    thread_dict["ReadFirData_Thread"] = threading.Thread(target=read_fir_data, args=(fir_instance, ), name="ReadFirData_Thread")

    # Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
        while FIRAPP_RUNSTATUS:
            # Receive Message From Pipe
            message = Main_Pipe.recv()
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from firapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.FirAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(Main_Queue, recv_msg, fir_instance)
            else:
                events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, "Receiver MID does not match with firapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error, f"firapp error : {e}")
        FIRAPP_RUNSTATUS = False

    # Termination Process after runloop
    firapp_terminate(i2c_instance)

    return
