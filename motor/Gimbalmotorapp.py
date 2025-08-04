# Python FSW V2 Gimbalmotor App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types
from lib import config

import signal
from multiprocessing import Queue, connection
import threading
import time

# Import Motor Libraries
from motor import payload_motor
from motor import container_motor
from motor import rocket_motor

# Runstatus of application. Application is terminated when false
GIMBALMOTORAPP_RUNSTATUS = True

# Flag that determines the activation of payload motor
PAYLOAD_MOTOR_ENABLE = True

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure, motor_instance):
    global GIMBALMOTORAPP_RUNSTATUS
    global PAYLOAD_MOTOR_ENABLE

    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"GIMBALMOTORAPP TERMINATION DETECTED")
        GIMBALMOTORAPP_RUNSTATUS = False

    # On receiving yaw data
    elif recv_msg.MsgID == appargs.ImuAppArg.MID_SendYawData:
        # Control motor only if config is payload and is activated
        if config.FSW_CONF == config.CONF_PAYLOAD and PAYLOAD_MOTOR_ENABLE == True:
            recv_yaw = float(recv_msg.data)
            payload_motor.rotate_MG92B_ByYaw(motor_instance, recv_yaw)
        else:
            return

    # On rocket motor activation command
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_RocketMotorActivate:
        # This command should only be activated on rocket
        if config.FSW_CONF == config.CONF_ROCKET:
            activaterocketmotor(motor_instance)
        else:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Not Performing Rocket Motor Activation, current conf : {config.FSW_CONF}")

    # On rocket motor standby command
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_RocketMotorStandby:
        # This command should only be activated on rocket
        if config.FSW_CONF == config.CONF_ROCKET:
            standbyrocketmotor(motor_instance)
        else:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Not Performing Rocket Motor Standby, current conf : {config.FSW_CONF}")

    # On Payload Release motor activation command
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_PayloadReleaseMotorActivate:

        if config.FSW_CONF == config.CONF_CONTAINER:
            activatepayloadreleasemotor(motor_instance)
        else:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Not Performing Payload Release Motor Activation, current conf : {config.FSW_CONF}")

    # On Payload Release motor standby command
    elif recv_msg.MsgID == appargs.FlightlogicAppArg.MID_PayloadReleaseMotorStandby:

        if config.FSW_CONF == config.CONF_CONTAINER:
            standbypayloadreleasemotor(motor_instance)
        else:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Not Performing Payload Release Motor Standby, current conf : {config.FSW_CONF}")


    elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_MEC:
        if config.FSW_CONF == config.CONF_ROCKET:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"MEC : Current conf : rocket, activating rocket motor...")
            activaterocketmotor(motor_instance)

        elif config.FSW_CONF == config.CONF_CONTAINER:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"MEC : Current conf : container, Current Option : {recv_msg.data}...")
            if recv_msg.data == "ON":
                activatepayloadreleasemotor(motor_instance)
            elif recv_msg.data == "OFF":
                freepayloadreleasemotor(motor_instance)
            else:
                events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, f"Error Activating container motor, invalid option : {recv_msg.data}")

        elif config.FSW_CONF == config.CONF_PAYLOAD:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"MEC : Current conf : payload, Current Option : {recv_msg.data}")
            if recv_msg.data == "ON":
                PAYLOAD_MOTOR_ENABLE = True
            elif recv_msg.data == "OFF":
                PAYLOAD_MOTOR_ENABLE = False
            else:
                events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, f"Error Activating payload motor, invalid option : {recv_msg.data}")
            
    else:
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global GIMBALMOTORAPP_RUNSTATUS
    while GIMBALMOTORAPP_RUNSTATUS:
        gimbalmotorHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, gimbalmotorHK, appargs.GimbalmotorAppArg.AppID, appargs.HkAppArg.AppID, appargs.GimbalmotorAppArg.MID_SendHK, str(GIMBALMOTORAPP_RUNSTATUS))
        time.sleep(1)
    return

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def gimbalmotorapp_init():
    global GIMBALMOTORAPP_RUNSTATUS
    try:
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Initializating gimbalmotorapp")
        ## User Defined Initialization goes HERE
        motor_instance = None

        if config.FSW_CONF == config.CONF_PAYLOAD:
            motor_instance = payload_motor.init_MG92B()
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Payload motor standby")


        else:
            events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "No Valid configuration!")
            GIMBALMOTORAPP_RUNSTATUS = False
            return None

        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Gimbalmotorapp Initialization Complete")
        return motor_instance
    
    except Exception as e:
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, "Error during initialization")
        GIMBALMOTORAPP_RUNSTATUS = False
    
# Termination
def gimbalmotorapp_terminate(motor_instance):
    global GIMBALMOTORAPP_RUNSTATUS

    GIMBALMOTORAPP_RUNSTATUS = False
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Terminating gimbalmotorapp - rotating to 180°")
    # Termination Process Comes Here

    # Terminate each motor - 180도로 회전 후 종료
    if config.FSW_CONF == config.CONF_PAYLOAD:
        # 종료 시 모터를 180도로 회전
        payload_motor.rotate_MG92B_ByYaw(motor_instance, 180)
        time.sleep(1)  # 모터가 회전할 시간을 줌
        payload_motor.terminate_MG92B(motor_instance)
    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Terminating gimbalmotorapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

# Activate Rocket Release Motor
def activaterocketmotor(motor_instance):
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Activating Rocket Motor")
    rocket_motor.rocket_deploy_state(motor_instance)

    return
def standbyrocketmotor(motor_instance):
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Standby Rocket Motor")
    rocket_motor.rocket_initial_state(motor_instance)
    return

def activatepayloadreleasemotor(motor_instance):
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Activating Payload Release Motor")
    container_motor.container_release(motor_instance)
    return

def standbypayloadreleasemotor(motor_instance):
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Standby Payload Release Motor")
    container_motor.container_initial(motor_instance)
    return

def freepayloadreleasemotor(motor_instance):
    events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.info, "Free Payload Release Motor")
    container_motor.container_free(motor_instance)
    return

def controlgimbalmotor(motor_instance, yaw):
    payload_motor.rotate_MG92B_ByYaw(motor_instance, yaw)
    return

# Put user-defined methods here!

######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def gimbalmotorapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global GIMBALMOTORAPP_RUNSTATUS
    GIMBALMOTORAPP_RUNSTATUS = True

    # Initialization Process
    motor_instance = gimbalmotorapp_init()

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while GIMBALMOTORAPP_RUNSTATUS:
            # Receive Message From Pipe with timeout
            try:
                message = Main_Pipe.recv(timeout=1.0)  # 1초 타임아웃 추가
            except:
                # 타임아웃 시 루프 계속
                continue
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from gimbalmotorapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.GimbalmotorAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg, motor_instance)
            else:
                events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, "Receiver MID does not match with gimbalmotorapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.GimbalmotorAppArg.AppName, events.EventType.error, f"gimbalmotorapp error : {e}")
        GIMBALMOTORAPP_RUNSTATUS = False

    # Termination Process after runloop
    gimbalmotorapp_terminate(motor_instance)

    return