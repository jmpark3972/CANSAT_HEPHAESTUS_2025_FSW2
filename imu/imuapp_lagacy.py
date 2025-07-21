# Python FSW V2 Imu App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types

import os
from multiprocessing import Queue, connection
import threading
import time
import sys

# Runstatus of application. Application is terminated when false
IMUAPP_RUNSTATUS = True

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# This fuction is spawned as an independent thread
# Listens SB messages routed from main app using pipe
def SB_listner (Main_Pipe : connection.Connection):
    global IMUAPP_RUNSTATUS
    while IMUAPP_RUNSTATUS:
        # Receive Message From Pipe
        message = Main_Pipe.recv()
        recv_msg = msgstructure.MsgStructure()

        # Unpack Message, Skip this message if unpacked message is not valid
        if msgstructure.unpack_msg(recv_msg, message) == False:
            continue
        
        # Validate Message, Skip this message if target AppID different from imuapp's AppID
        # Exception when the message is from main app
        if recv_msg.receiver_app == appargs.ImuAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
            # Handle Command According to Message ID
            command_handler(recv_msg)
        else:
            events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Receiver MID does not match with imuapp MID")
    return

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    if recv_msg.MsgID == appargs.ImuAppArg.MID_SendHK:
        print(recv_msg.data)

    elif recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        global IMUAPP_RUNSTATUS
        IMUAPP_RUNSTATUS = False

    else:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return



######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def imuapp_init():
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Starting imuapp")
    ## User Defined Initialization goes HERE
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Initializing IMU sensor")
    imu.init_imu()
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "IMU initialization complete")

    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "imuapp Started")

# Termination
def imuapp_terminate():
    global IMUAPP_RUNSTATUS

    current_thread = threading.current_thread().name
        
    IMUAPP_RUNSTATUS = False
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp")
    # Termination Process Comes Here

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        if thread_name != current_thread:
            thread_dict[thread_name].join()
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp complete")
    sys.exit()
    return

######################################################
## USER METHOD                                      ##
######################################################

from imu import imu

IMU_ROLL:float = 0
IMU_PITCH:float = 0
IMU_YAW:float = 0

def read_imu_data():

    global IMU_ROLL
    global IMU_PITCH
    global IMU_YAW


    while IMUAPP_RUNSTATUS:
        # Read data from IMU
        rcv_data = imu.read_sensor_data()

        # Continue if Quaternion data is empty
        if rcv_data[0:3] == (0, 0, 0): 
            continue
        else:         
            #새로운 자세 정보 저장
            IMU_YAW         = rcv_data[0]
            IMU_ROLL        = rcv_data[1]
            IMU_PITCH       = rcv_data[2]
            raw_IMU_ACCX        = rcv_data[3]
            raw_IMU_ACCY        = rcv_data[4]
            raw_IMU_ACCZ        = rcv_data[5]
            raw_IMU_MAGX        = rcv_data[6]
            raw_IMU_MAGY        = rcv_data[7]
            raw_IMU_MAGZ        = rcv_data[8]
            raw_IMU_GYRX        = rcv_data[9]
            raw_IMU_GYRY        = rcv_data[10]
            raw_IMU_GYRZ        = rcv_data[11]
            raw_IMU_LIN_ACCX    = rcv_data[12]
            raw_IMU_LIN_ACCY    = rcv_data[13]
            raw_IMU_LIN_ACCZ    = rcv_data[14]
            raw_IMU_GRAVX       = rcv_data[15]
            raw_IMU_GRAVY       = rcv_data[16]
            raw_IMU_GRAVZ       = rcv_data[17]


def send_imu_data(Main_Queue:Queue):
    ImuDataMsg = msgstructure.MsgStructure()
    toapp_datatosend = f"{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f}"
    msgstructure.send_msg(Main_Queue, ImuDataMsg, appargs.ImuAppArg.AppID, appargs.ToAppArg.AppID, appargs.ImuAppArg.MID_SendIMUData, toapp_datatosend)

    HeadingDataMsg = msgstructure.MsgStructure()
    motorapp_datatosend = f"{IMU_ROLL:.2f}"
    msgstructure.send_msg(Main_Queue, HeadingDataMsg, appargs.ImuAppArg.AppID, appargs.MotorAppArg.AppID,appargs.ImuAppArg.MID_SendHeadingData, motorapp_datatosend)

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def imuapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global IMUAPP_RUNSTATUS
    IMUAPP_RUNSTATUS = True

    # Initialization Process
    imuapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["SBListner_Thread"] = threading.Thread(target=SB_listner, args=(Main_Pipe, ), name="SBListner_Thread")
    thread_dict["IMUReader_Thread"] = threading.Thread(target=read_imu_data, name="IMUReader_Thread")
    # Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
        # Runloop
        while IMUAPP_RUNSTATUS:
            imuHK = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, imuHK, appargs.ImuAppArg.AppID, appargs.HkAppArg.AppID, appargs.HkAppArg.MID_ReceiveHK, str(IMUAPP_RUNSTATUS))
            send_imu_data(Main_Queue)

            time.sleep(0.1)
    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"imuapp error : {e}")
        IMUAPP_RUNSTATUS = False

    # Termination Process after runloop
    imuapp_terminate()

    return
