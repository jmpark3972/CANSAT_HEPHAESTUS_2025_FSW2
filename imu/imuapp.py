# Python FSW V2 Imu App
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

# Import IMU sensor library
from imu import imu

# Runstatus of application. Application is terminated when false
IMUAPP_RUNSTATUS = True

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure):
    global IMUAPP_RUNSTATUS

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"IMUAPP TERMINATION DETECTED")
        IMUAPP_RUNSTATUS = False

    else:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global IMUAPP_RUNSTATUS
    while IMUAPP_RUNSTATUS:
        imuHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, imuHK, appargs.ImuAppArg.AppID, appargs.HkAppArg.AppID, appargs.ImuAppArg.MID_SendHK, str(IMUAPP_RUNSTATUS))
        time.sleep(1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def imuapp_init():
    global IMUAPP_RUNSTATUS
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Initializating imuapp")
        ## User Defined Initialization goes HERE
        
        #Initialize IMU Sensor
        i2c_instance, imu_instance = imu.init_imu()
        
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Imuapp Initialization Complete")
        return i2c_instance, imu_instance
    
    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Error during initialization")
        IMUAPP_RUNSTATUS = False

# Termination
def imuapp_terminate(i2c_instance):
    global IMUAPP_RUNSTATUS

    IMUAPP_RUNSTATUS = False
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp")
    # Termination Process Comes Here

    imu.imu_terminate(i2c_instance)

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.info, "Terminating imuapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

IMU_ROLL: float = 0.0
IMU_PITCH: float = 0.0
IMU_YAW: float = 0.0
IMU_ACCX: float = 0.0
IMU_ACCY: float = 0.0
IMU_ACCZ: float = 0.0
IMU_MAGX: float = 0.0
IMU_MAGY: float = 0.0
IMU_MAGZ: float = 0.0
IMU_GYRX: float = 0.0
IMU_GYRY: float = 0.0
IMU_GYRZ: float = 0.0

def read_imu_data(imu_instance):

    global IMU_ROLL
    global IMU_PITCH
    global IMU_YAW
    global IMU_ACCX
    global IMU_ACCY
    global IMU_ACCZ
    global IMU_MAGX
    global IMU_MAGY
    global IMU_MAGZ
    global IMU_GYRX
    global IMU_GYRY
    global IMU_GYRZ
    
    global IMUAPP_RUNSTATUS
    while IMUAPP_RUNSTATUS:
        # Read data from IMU
        rcv_data = imu.read_sensor_data(imu_instance)

        # Continue if Quaternion data is empty
        if rcv_data == False:
            continue
        else:         
            #새로운 자세 정보 저장
            IMU_ROLL        = rcv_data[0]
            IMU_PITCH       = rcv_data[1]
            IMU_YAW         = rcv_data[2]
            
            IMU_ACCX        = rcv_data[3]
            IMU_ACCY        = rcv_data[4]
            IMU_ACCZ        = rcv_data[5]

            IMU_MAGX        = rcv_data[6]
            IMU_MAGY        = rcv_data[7]
            IMU_MAGZ        = rcv_data[8]

            IMU_GYRX        = rcv_data[9]
            IMU_GYRY        = rcv_data[10]
            IMU_GYRZ        = rcv_data[11]

        # The imu runs on 100Hz
        time.sleep(0.01)

    return

def send_imu_data(Main_Queue : Queue):
    global IMU_ROLL
    global IMU_PITCH
    global IMU_YAW
    global IMU_ACCX
    global IMU_ACCY
    global IMU_ACCZ
    global IMU_MAGX
    global IMU_MAGY
    global IMU_MAGZ
    global IMU_GYRX
    global IMU_GYRY
    global IMU_GYRZ
    
    global IMUAPP_RUNSTATUS

    ImuDataToTlmMsg = msgstructure.MsgStructure()
    YawDataToMotorMsg = msgstructure.MsgStructure()
    
    send_counter = 0

    while IMUAPP_RUNSTATUS:
        
        send_counter += 1

        # Send Yaw data to motor
        # msgstructure.send_msg(Main_Queue, 
        #                       YawDataToMotorMsg,
        #                       appargs.ImuAppArg.AppID,
        #                       appargs.MotorAppArg.AppID,
        #                       appargs.ImuAppArg.MID_SendYawData,
        #                       f"{IMU_YAW:.2f}")
        
        # Sending data to COMMS app occurs once a second

        if send_counter >= 10 :
            # Send telemetry message to COMM app
            status = msgstructure.send_msg(Main_Queue, 
                                        ImuDataToTlmMsg, 
                                        appargs.ImuAppArg.AppID,
                                        appargs.CommAppArg.AppID,
                                        appargs.ImuAppArg.MID_SendImuTlmData,
                                        f"{IMU_ROLL:.2f},{IMU_PITCH:.2f},{IMU_YAW:.2f},{IMU_ACCX:.2f},{IMU_ACCY:.2f},{IMU_ACCZ:.2f},{IMU_MAGX:.2f},{IMU_MAGY:.2f},{IMU_MAGZ:.2f},{IMU_GYRX:.2f},{IMU_GYRY:.2f},{IMU_GYRZ:.2f}")
            if status == False:
                events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, "Error When sending Imu Tlm Message")
            send_counter = 0
            
        # Sleep 1 second
        time.sleep(0.1)

    return  


# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def imuapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global IMUAPP_RUNSTATUS
    IMUAPP_RUNSTATUS = True

    # Initialization Process
    i2c_instance, imu_instance = imuapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["ReadImuData_Thread"] = threading.Thread(target=read_imu_data, args=(imu_instance, ), name="ReadImuData_Thread")
    thread_dict["SendImuData_Thread"] = threading.Thread(target=send_imu_data, args=(Main_Queue, ), name="SendImuData_Thread")


    # Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
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

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.ImuAppArg.AppName, events.EventType.error, f"imuapp error : {e}")
        IMUAPP_RUNSTATUS = False

    # Termination Process after runloop
    imuapp_terminate(i2c_instance)

    return
