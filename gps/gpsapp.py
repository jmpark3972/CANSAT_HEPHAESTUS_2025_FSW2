# Python FSW V2 Gps App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types

import signal
from multiprocessing import Queue, connection
import threading
import time

from gps import gps

# Runstatus of application. Application is terminated when false
GPSAPP_RUNSTATUS = True
gps_instance = None
######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global GPSAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, f"GPSAPP TERMINATION DETECTED")
        GPSAPP_RUNSTATUS = False

    else:
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global GPSAPP_RUNSTATUS
    while GPSAPP_RUNSTATUS:
        gpsHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, gpsHK, appargs.GpsAppArg.AppID, appargs.HkAppArg.AppID, appargs.GpsAppArg.MID_SendHK, str(GPSAPP_RUNSTATUS))
        time.sleep(1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################
# Initialization
def gpsapp_init():
    global GPSAPP_RUNSTATUS
    global gps_instance
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, "Initializating gpsapp")
        ## User Defined Initialization goes HERE
        gps_instance = gps.init_gps()
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, "Gpsapp Initialization Complete")
        return gps_instance
    except Exception as e:
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.error, "Error during initialization")
        GPSAPP_RUNSTATUS = False

# Termination
def gpsapp_terminate():
    global GPSAPP_RUNSTATUS
    global gps_instance
    GPSAPP_RUNSTATUS = False
    events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, "Terminating gpsapp")
    # Termination Process Comes Here

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    if gps_instance is not None:
        gps.terminate_gps(gps_instance)
        gps_instance = None
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, "GPS connection terminated")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.info, "Terminating gpsapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################


def read_and_send_gps_data(Main_Queue : Queue, gps_instance):
    global GPSAPP_RUNSTATUS
    SendGPSTlmDataMsg = msgstructure.MsgStructure()

    while GPSAPP_RUNSTATUS:
        # add function that Reads the GPS data
        rcv_data = gps.gps_readdata(gps_instance)
        GPS_TIME = rcv_data[0]
        GPS_ALT  = rcv_data[1]
        GPS_LAT  = rcv_data[2]
        GPS_LON  = rcv_data[3]
        GPS_SATS = rcv_data[4]
        msgstructure.send_msg(Main_Queue, 
                              SendGPSTlmDataMsg,
                              appargs.GpsAppArg.AppID,
                              appargs.CommAppArg.AppID,
                              appargs.GpsAppArg.MID_SendGpsTlmData,
                              f"{GPS_TIME},{GPS_ALT},{GPS_LAT},{GPS_LON},{GPS_SATS}")

        time.sleep(1)
        
    return
    
# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def gpsapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global GPSAPP_RUNSTATUS
    GPSAPP_RUNSTATUS = True

    # Initialization Process
    gps_instance = gpsapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["ReadAndSendGpsData_Thread"] = threading.Thread(target=read_and_send_gps_data, args=(Main_Queue, gps_instance,  ), name="ReadAndSendGpsData_Thread")

    # Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
        while GPSAPP_RUNSTATUS:
            # Receive Message From Pipe
            message = Main_Pipe.recv()
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from gpsapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.GpsAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg)
            else:
                events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.error, "Receiver MID does not match with gpsapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.GpsAppArg.AppName, events.EventType.error, f"gpsapp error : {e}")
        GPSAPP_RUNSTATUS = False

    # Termination Process after runloop
    gpsapp_terminate()

    return
