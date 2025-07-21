# Python FSW V2 Flightlogic App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types
from lib import prevstate
from lib import config

import signal
from multiprocessing import Queue, connection
import threading
import time

# Runstatus of application. Application is terminated when false
FLIGHTLOGICAPP_RUNSTATUS = True

# <NEW/> 현재 환경 측정값
CURRENT_TEMP: float = 0.0  # DHT11 temperature (°C)
CURRENT_ALT:  float = 0.0  # Barometer altitude (m)
# <NEW/> 마지막으로 실제 서보에 지시한 각도 (스팸 방지용). –1이면 미전송 상태
MOTOR_TARGET_ANGLE: int = -1


######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure, Main_Queue:Queue):
    global SIMULATION_ACTIVATE
    global MAX_ALT
    global recent_alt
    global FLIGHTLOGICAPP_RUNSTATUS, SIMULATION_ENABLE, SIMULATION_ACTIVATE
    global MAX_ALT, recent_alt, CURRENT_TEMP


    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        # Change Runstatus to false to start termination process
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"FLIGHTLOGICAPP TERMINATION DETECTED")
        FLIGHTLOGICAPP_RUNSTATUS = False

    elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SIM:
        # When simulation command is input
        option = recv_msg.data
        if option == "ENABLE":
            SIMULATION_ENABLE = True
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Enabled")
        if option == "ACTIVATE":
            SIMULATION_ACTIVATE = True
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Activated")
        if option == "DISABLE":
            SIMULATION_ACTIVATE = False
            SIMULATION_ENABLE = False
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Disabled")
            
        check_simulation_status(Main_Queue)

    # Simulation pressure data
    elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SIMP:
        if SIMULATION_ACTIVATE and SIMULATION_ENABLE:

            simulated_altitude = float(recv_msg.data)
            
            barometer_logic(Main_Queue, simulated_altitude)
        else:
            return

    # Receive Sensor data
    # Barometer Data input at 10Hz
    elif recv_msg.MsgID == appargs.BarometerAppArg.MID_SendBarometerFlightLogicData:
        # Ignore the barometer data when simulation is activated
        if SIMULATION_ENABLE and SIMULATION_ACTIVATE:
            return
        
        recv_altitude = float(recv_msg.data)

        # Perform barometer logic
        barometer_logic(Main_Queue, recv_altitude)

    elif recv_msg.MsgID == getattr(appargs, "ThermoAppArg").MID_SendThermoFlightLogicData:
        try:
            temp_str, _ = recv_msg.data.split(",")
            CURRENT_TEMP = float(temp_str)
        except Exception:
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                            "Thermo data parse error")
            return
        evaluate_motor_logic(Main_Queue)
        return

    elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SS:
        # When received Set State command
        recv_state = int(recv_msg.data)

        # LAUNCHPAD
        if recv_state == 0:
            launchpad_state_transition(Main_Queue)

        # ASCENT
        elif recv_state == 1:
            ascent_state_transition(Main_Queue)

        # APOGEE
        elif recv_state == 2:
            apogee_state_transition(Main_Queue)

        # DESCENT
        elif recv_state == 3:
            descent_state_transition(Main_Queue)

        # PROBE RELEASE
        elif recv_state == 4:
            probe_release_state_transition(Main_Queue)

        # LANDED
        elif recv_state == 5:
            landed_state_transition(Main_Queue)
            
        # Received State out of state range
        else: 
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"Error receiving SS message, Expected state value of 0 ~ {len(STATE_LIST) - 1}, received {recv_state}")

    # When reset message from barometer app is received, set the max alt to 0
    elif recv_msg.MsgID == appargs.BarometerAppArg.MID_ResetBarometerMaxAlt:
        MAX_ALT = 0
        recent_alt.clear()

    else:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    return

def send_hk(Main_Queue : Queue):
    global FLIGHTLOGICAPP_RUNSTATUS
    while FLIGHTLOGICAPP_RUNSTATUS:
        flightlogicHK = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, flightlogicHK, appargs.FlightlogicAppArg.AppID, appargs.HkAppArg.AppID, appargs.FlightlogicAppArg.MID_SendHK, str(FLIGHTLOGICAPP_RUNSTATUS))
        time.sleep(1)
    return

######################################################
# Motor‑control helpers <NEW/>
######################################################

def set_motor_angle(Main_Queue: Queue, angle: int) -> None:
    """MotorApp 로 각도 명령 전송 (스팸 방지)."""
    global MOTOR_TARGET_ANGLE
    angle = 0 if angle < 0 else 180 if angle > 180 else int(angle)
    if angle == MOTOR_TARGET_ANGLE:
        return  # 이미 같은 각도로 지시함
    MOTOR_TARGET_ANGLE = angle

    msg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, msg,
                          appargs.FlightlogicAppArg.AppID,
                          appargs.MotorAppArg.AppID,
                          appargs.FlightlogicAppArg.MID_SetServoAngle,
                          str(angle))
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info,
                    f"Motor angle cmd → {angle}°")


def evaluate_motor_logic(Main_Queue: Queue) -> None:
    """현재 고도·온도 조건을 보고 서보 목표각 결정."""
    desired = 0  # 기본은 0°
    if CURRENT_ALT > 70:
        if CURRENT_TEMP > 50:
            desired = 180
    # alt ≤70 이면 항상 0° (안전)
    set_motor_angle(Main_Queue, desired)

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def flightlogicapp_init(Main_Queue : Queue):
    try:
        global FLIGHTLOGICAPP_RUNSTATUS
        global CURRENT_STATE
        global MAX_ALT
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Initializating flightlogicapp")
        ## User Defined Initialization goes HERE

        # For recovery, set the prev state as the current state.
        CURRENT_STATE = int(prevstate.PREV_STATE)

        # Perform state transition according to state
        if CURRENT_STATE == 0:
            launchpad_state_transition(Main_Queue)
        elif CURRENT_STATE == 1:
            ascent_state_transition(Main_Queue)
        elif CURRENT_STATE == 2 :
            descent_state_transition(Main_Queue)
        elif CURRENT_STATE == 3 :
            apogee_state_transition(Main_Queue)
        elif CURRENT_STATE == 4 :
            probe_release_state_transition(Main_Queue)
        elif CURRENT_STATE == 5:
            landed_state_transition(Main_Queue)
            
        # For recovery set the max altitude
        MAX_ALT = float(prevstate.PREV_MAX_ALT)

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Setting Current state to {CURRENT_STATE}")

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Flightlogicapp Initialization Complete")
    except Exception as e:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, "Error during initialization")
        FLIGHTLOGICAPP_RUNSTATUS = False

# Termination
def flightlogicapp_terminate():
    global FLIGHTLOGICAPP_RUNSTATUS

    FLIGHTLOGICAPP_RUNSTATUS = False
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Terminating flightlogicapp")
    # Termination Process Comes Here

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Terminating flightlogicapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

STATE_LIST = ["LAUNCH_PAD",
              "ASCENT",
              "APOGEE",
              "DESCENT",
              "PROBE_RELEASE",
              "LANDED"]

CURRENT_STATE = 0

# Simulation Mode Flags, both ENABLE and ACTIVATE should be true to use simulation mode
SIMULATION_ENABLE = False
SIMULATION_ACTIVATE = False

# Variable used in state determination
MAX_ALT = 0
PAYLOAD_SEP_ALT_THRESHOLD = 0

# counters for each state transition. State will change when counter > 3,
# counter + 1 when state transition condition satisfies, counter - 2 when not
BAROMETER_ASCENT_COUNTER = 0
BAROMETER_APOGEE_COUNTER = 0
BAROMETER_DESCENT_COUNTER = 0
BAROMETER_PROBE_RELEASE_COUNTER = 0
BAROMETER_LANDED_COUNTER = 0

# Tilt data beyond threshold will be considered as a deploy condition.
IMU_ROLL_THRESHOLD = 70
IMU_PITCH_THRESHOLD = 70

recent_alt = []

def barometer_logic(Main_Queue:Queue, altitude:float):
    # 최대 고도 찍고 감소하면 -> Descening State
    # Descending State에서 75% 고도 되면 Payload Release State
    # 이렇게 하면 될듯?
    global MAX_ALT
    global PAYLOAD_SEP_ALT_THRESHOLD
    global CURRENT_STATE
    global BAROMETER_ASCENT_COUNTER
    global BAROMETER_DESCENT_COUNTER
    global BAROMETER_APOGEE_COUNTER
    global BAROMETER_PROBE_RELEASE_COUNTER
    global BAROMETER_LANDED_COUNTER
    
    global recent_alt

    recent_alt.append(altitude)
    if len(recent_alt) > 3:
        recent_alt.pop(0)

    if len(recent_alt) > 2:
        sorted_alts = sorted(recent_alt, reverse=True)
        second_max = sorted_alts[1]

        if sorted_alts[1] > MAX_ALT:
            MAX_ALT = second_max
            prevstate.update_maxalt(second_max)

    PAYLOAD_SEP_ALT_THRESHOLD = MAX_ALT * 0.75
    #print(f"alt : {altitude} , max : {MAX_ALT}")
    if len(recent_alt) < 3:
        # Do not perform any logic before filter is enabled
        return

    if BAROMETER_ASCENT_COUNTER <= 0 :
        BAROMETER_ASCENT_COUNTER = 0

    if BAROMETER_APOGEE_COUNTER <= 0 :
        BAROMETER_APOGEE_COUNTER = 0

    if BAROMETER_DESCENT_COUNTER <= 0 :
        BAROMETER_DESCENT_COUNTER = 0
    
    if BAROMETER_PROBE_RELEASE_COUNTER <= 0:
        BAROMETER_PROBE_RELEASE_COUNTER = 0

    if BAROMETER_LANDED_COUNTER <= 0 :
        BAROMETER_LANDED_COUNTER = 0
        
    # At Standby State
    if CURRENT_STATE == 0:

        # When Altitude is higher than 75 meters
        if (altitude > 75):
            BAROMETER_ASCENT_COUNTER += 1
        else:
            BAROMETER_ASCENT_COUNTER -= 2
        
        # When the counter is larger than 3 ; when the altitude is higher than 50 meter 3 times in a row
        if BAROMETER_ASCENT_COUNTER >= 3:
            ascent_state_transition(Main_Queue)
    
    # At Ascent State
    if CURRENT_STATE == 1:

        # When Altitude is 20 meter lower than max altitude

        if (altitude <= MAX_ALT - 20):
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2
        
        # 0.25 meter is the resolution of BMP390
        if (altitude < MAX_ALT - 0.25 and altitude > MAX_ALT - 20):
            BAROMETER_APOGEE_COUNTER += 1
        else:
            BAROMETER_APOGEE_COUNTER -= 2

        # When the counter is larger than 2; When the altitude is 2 meter lower than max altitude 2 times in a row
        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

        if BAROMETER_APOGEE_COUNTER >= 2:
            apogee_state_transition(Main_Queue)

    # At Apogee State
    if CURRENT_STATE == 2:
        
        # Check for descent
        if (altitude <= MAX_ALT - 20):
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2

        # When the counter is larger than 3; When the altitude is 2 meter lower than max altitude 3 times in a row
        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

    # At Descent State
    if CURRENT_STATE == 3:
        # When Altitude is 75% of max altitude

        if (altitude <= MAX_ALT * 0.75):
            BAROMETER_PROBE_RELEASE_COUNTER += 1
        else:
            BAROMETER_PROBE_RELEASE_COUNTER -= 2

        # When the counter is larger than 3; When the altitude is 75% of max altitude 2 times in a row
        if BAROMETER_PROBE_RELEASE_COUNTER >= 2:
            probe_release_state_transition(Main_Queue)
    
    # At Probe Release State

    if CURRENT_STATE == 4:
        # When altitude is almost zero

        if altitude <= 15:
            BAROMETER_LANDED_COUNTER += 1
        else:
            BAROMETER_LANDED_COUNTER -= 2

        if BAROMETER_LANDED_COUNTER >= 3:
            landed_state_transition(Main_Queue)
        

    return

def launchpad_state_transition(Main_Queue : Queue):
    global CURRENT_STATE
    global MAX_ALT
    global recent_alt

    # Set the Current State to 0 ; Standby
    CURRENT_STATE = 0
    # Set the max alt to 0 and clear the recent alt list
    MAX_ALT = 0
    recent_alt.clear()

    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO STANDBY")
    
    # Store the current state to prev state file
    prevstate.update_prevstate(CURRENT_STATE)

    # Reset the mechanism depending on the FSW config
    #if config.FSW_CONF == config.CONF_CONTAINER:
    #    PayloadReleaseMotorStandbyMsg = msgstructure.MsgStructure()
    #    msgstructure.send_msg(Main_Queue, PayloadReleaseMotorStandbyMsg, appargs.FlightlogicAppArg.AppID, appargs.GimbalmotorAppArg.AppID, appargs.FlightlogicAppArg.MID_PayloadReleaseMotorStandby, "")

    #if config.FSW_CONF == config.CONF_ROCKET:
    #    RocketMotorStandbyMsg = msgstructure.MsgStructure()
    #    msgstructure.send_msg(Main_Queue, RocketMotorStandbyMsg, appargs.FlightlogicAppArg.AppID, appargs.GimbalmotorAppArg.AppID, appargs.FlightlogicAppArg.MID_RocketMotorStandby, "")

    return

def ascent_state_transition(Main_Queue : Queue):
    global CURRENT_STATE
    
    # Set the Current State to 1 ; Ascent
    CURRENT_STATE = 1
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO ASCENT")

    # Store the current state to prev state file
    prevstate.update_prevstate(CURRENT_STATE)

    # Perform Action for Ascent State

    ActivateCameraToCamappMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, ActivateCameraToCamappMsg, appargs.FlightlogicAppArg.AppID, appargs.CameraAppArg.AppID, appargs.FlightlogicAppArg.MID_SendCameraActivateToCam, "")

    return

def apogee_state_transition(Main_Queue : Queue):
    global CURRENT_STATE

    # Set the Current State to 2 ; Apogee
    CURRENT_STATE = 2

    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO APOGEE")
    prevstate.update_prevstate(CURRENT_STATE)


def descent_state_transition(Main_Queue:Queue):
    global CURRENT_STATE
    
    # Set the Current State to 3 ; Deploy
    CURRENT_STATE = 3
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO DESCENT")

    # Store the current state to prev state file
    prevstate.update_prevstate(CURRENT_STATE)

    # Perform Action for Deploy State

    ActivateCameraToCamappMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, ActivateCameraToCamappMsg, appargs.FlightlogicAppArg.AppID, appargs.CameraAppArg.AppID, appargs.FlightlogicAppArg.MID_SendCameraActivateToCam, "")

    # Rocket -> Activate Motor to release container. Only for test launch!
    #RocketMotorActivateMsg = msgstructure.MsgStructure()
    #msgstructure.send_msg(Main_Queue, RocketMotorActivateMsg, appargs.FlightlogicAppArg.AppID, appargs.GimbalmotorAppArg.AppID, appargs.FlightlogicAppArg.MID_RocketMotorActivate, "")

    return

def probe_release_state_transition(Main_Queue:Queue):
    global CURRENT_STATE
    
    # Set the Current State to 4 ; Payload Sep
    CURRENT_STATE = 4
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO PROBE RELEASE")

    # Store the current state to prev state file
    prevstate.update_prevstate(CURRENT_STATE)

    # Perform Action for Payload Separation State

    ActivateCameraToCamappMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, ActivateCameraToCamappMsg, appargs.FlightlogicAppArg.AppID, appargs.CameraAppArg.AppID, appargs.FlightlogicAppArg.MID_SendCameraActivateToCam, "")

    PayloadReleaseMotorActivateMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, PayloadReleaseMotorActivateMsg, appargs.FlightlogicAppArg.AppID, appargs.GimbalmotorAppArg.AppID, appargs.FlightlogicAppArg.MID_PayloadReleaseMotorActivate, "")
    
    # Container -> Activate Motor to release payload

    return

def landed_state_transition(Main_Queue : Queue):
    global CURRENT_STATE
    
    # Set the Current State to 5 ; Landing
    CURRENT_STATE = 5
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "CHANGED STATE TO LANDED")

    # Store the current state to prev state file
    prevstate.update_prevstate(CURRENT_STATE)

    # Perform Action for Landing State

    return

def check_simulation_status(Main_Queue:Queue):
    simulation_status = "F"

    if SIMULATION_ENABLE and SIMULATION_ACTIVATE:
        simulation_status = "S"
        
    SimulationStatusToTlmMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, SimulationStatusToTlmMsg, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.MID_SendSimulationStatustoTlm, simulation_status)   

# Put user-defined methods here!

def send_current_state(Main_Queue:Queue):
    global FLIGHTLOGICAPP_RUNSTATUS
    global CURRENT_STATE

    SendCurrentStateMsg = msgstructure.MsgStructure()
    while FLIGHTLOGICAPP_RUNSTATUS:
        msgstructure.send_msg(Main_Queue, SendCurrentStateMsg, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.MID_SendCurrentStateToTlm, STATE_LIST[CURRENT_STATE])
        time.sleep(1)
    
    return
######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def flightlogicapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global FLIGHTLOGICAPP_RUNSTATUS
    FLIGHTLOGICAPP_RUNSTATUS = True

    # Initialization Process
    flightlogicapp_init(Main_Queue)

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendCurrentState_Thread"] = threading.Thread(target=send_current_state, args=(Main_Queue, ), name="SendCurrentState_Thread")

    # Spawn Each Threads
    for thread_name in thread_dict:
        thread_dict[thread_name].start()

    try:
        while FLIGHTLOGICAPP_RUNSTATUS:
            # Receive Message From Pipe
            message = Main_Pipe.recv()
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from flightlogicapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.FlightlogicAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg, Main_Queue)
            else:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, "Receiver MID does not match with flightlogicapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"flightlogicapp error : {e}")
        FLIGHTLOGICAPP_RUNSTATUS = False

    # Termination Process after runloop
    flightlogicapp_terminate()

    return
