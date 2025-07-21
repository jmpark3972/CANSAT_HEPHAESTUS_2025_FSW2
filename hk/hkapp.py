# Python FSW V2 Hk App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types

import os
import signal
from multiprocessing import Queue, connection
import threading
import time
import sys

# Runstatus of application. Application is terminated when false
HKAPP_RUNSTATUS = True

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

hk_dict = {}

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global HKAPP_RUNSTATUS
    global hk_dict

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, f"HKAPP TERMINATION DETECTED")
        HKAPP_RUNSTATUS = False

    else:
        if recv_msg.sender_app not in hk_dict:
            hk_dict[recv_msg.sender_app] = 0
        else:
            hk_dict[recv_msg.sender_app] += 1
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def hkapp_init():
    global HKAPP_RUNSTATUS
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, "Initializating hkapp")
        ## User Defined Initialization goes HERE
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, "hkapp Initialization Complete")

    except:
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.error, "Error during initialization")

# Termination
def hkapp_terminate():
    global HKAPP_RUNSTATUS

    HKAPP_RUNSTATUS = False
    events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, "Terminating hkapp")
    # Termination Process Comes Here

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.HkAppArg.AppName, events.EventType.info, "Terminating hkapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

def print_hk_status():
    global HKAPP_RUNSTATUS

    while HKAPP_RUNSTATUS:
        #print(hk_dict)
        time.sleep(1)

    return

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def hkapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global HKAPP_RUNSTATUS
    HKAPP_RUNSTATUS = True

    # Initialization Process
    hkapp_init()

    thread_dict["PrintHKStat_Thread"] = threading.Thread(target=print_hk_status, name="PrintHKStat_Thread")

    #Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
        while HKAPP_RUNSTATUS:
            # Receive Message From Pipe
            message = Main_Pipe.recv()
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from hkapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.HkAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg)
            else:
                events.LogEvent(appargs.HkAppArg.AppName, events.EventType.error, "Receiver MID does not match with hkapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.HkAppArg.AppName, events.EventType.error, f"hkapp error : {e}")
        HKAPP_RUNSTATUS = False

    # Termination Process after runloop
    hkapp_terminate()

    return