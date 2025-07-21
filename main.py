# Main Flight Software Code for Cansat Mission
# Author : Hyeon Lee

# Sys library is needed to exit app
import sys
import os

MAINAPP_RUNSTATUS = True

# Custum libraries
from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types

# Multiprocessing Library is used on Python FSW V2
# Each application should have its own runloop
# Import the application and execute the runloop here.

from multiprocessing import Process, Queue, Pipe, connection

# Load configuration files
from lib import config
if config.FSW_CONF == config.CONF_NONE:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, "CONFIG IS SELECTED AS NONE, TERMINATING FSW")
    sys.exit(0)

# Read prev state, altitude calibration for recovery
from lib import prevstate
PREV_ALT_CAL = 0
PREV_STATE  = 0
PREV_MAX_ALT = 0
PREV_THERMO_TOFF = 0.0
PREV_THERMO_HOFF = 0.0

prevstate_file_path = 'lib/prevstate.txt'

def write_prevstate_file():
    global PREV_ALT_CAL, PREV_STATE, PREV_MAX_ALT, PREV_THERMO_TOFF, PREV_THERMO_HOFF
    content = f"""# Prevstate.txt
# The Config below stores the prev flight data
# DO NOT EDIT MANUALLY
STATE={PREV_STATE}
ALTCAL={PREV_ALT_CAL}
MAXALT={PREV_MAX_ALT}
THERMO_TOFF={PREV_THERMO_TOFF}
THERMO_HOFF={PREV_THERMO_HOFF}"""
    with open(prevstate_file_path, 'w') as file:
        file.write(content)

def update_thermocal(temp_off: float, humi_off: float):
    global PREV_THERMO_TOFF, PREV_THERMO_HOFF
    PREV_THERMO_TOFF = temp_off
    PREV_THERMO_HOFF = humi_off
    write_prevstate_file()

def init_prevstate():
    global PREV_STATE, PREV_ALT_CAL, PREV_MAX_ALT, PREV_THERMO_TOFF, PREV_THERMO_HOFF
    if not os.path.exists(prevstate_file_path):
        print("#################################################################\n\nPrevstate file does not exist, Using initial state\n\n#################################################################")
        write_prevstate_file()
    else:
        with open(prevstate_file_path, 'r') as file:
            lines = file.readlines()
        prevstate_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
        for prevstate_line in prevstate_lines:
            prevstate_line = prevstate_line.strip().replace(" ", "").replace("\t", "")
            if "STATE=" in prevstate_line:
                prev_state = prevstate_line.split("=")[1].strip()
                if prev_state == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev state is NONE")
                    PREV_STATE = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev state is {prev_state}")
                    PREV_STATE = int(prev_state)
            elif "ALTCAL=" in prevstate_line:
                prev_altcal = prevstate_line.split("=")[1].strip()
                if prev_altcal == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev calibration is NONE")
                    PREV_ALT_CAL = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev calibration is {prev_altcal}")
                    PREV_ALT_CAL = float(prev_altcal)
            elif "MAXALT=" in prevstate_line:
                prev_maxalt = prevstate_line.split("=")[1].strip()
                if prev_maxalt == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev maxalt is NONE")
                    PREV_MAX_ALT = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev maxalt is {prev_maxalt}")
                    PREV_MAX_ALT = float(prev_maxalt)
            elif "THERMO_TOFF=" in prevstate_line:
                try:
                    PREV_THERMO_TOFF = float(prevstate_line.split("=")[1].strip())
                except Exception:
                    PREV_THERMO_TOFF = 0.0
            elif "THERMO_HOFF=" in prevstate_line:
                try:
                    PREV_THERMO_HOFF = float(prevstate_line.split("=")[1].strip())
                except Exception:
                    PREV_THERMO_HOFF = 0.0
    return

# Define the multiprocessing queue structure
# Every runloop should take this queue as an argument
# for message routing
main_queue = Queue()

# When the main app receives the message entry from the queue
# It checks the message ID and destination application then routes the message
# Each application should establish a pipe with main app to receive routed message

# App element stores main process of app, pipe that can send SB message to app
class app_elements:
    process : Process = None
    pipe : connection.Connection = None
# The app dictionary has key as AppID, app elements as Value
#app_dict = dict[types.AppID, app_elements]()
app_dict: dict[types.AppID, app_elements] = {}
"""
# e.g importing test app and executing runloop
#########################################################
# SampleApp                                             #
#########################################################
from sampleapp import sampleapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
sampleapp_elements = app_elements()
sampleapp_elements.process = Process(target = sampleapp.sampleapp_main, args = (main_queue, child_pipe, ))
sampleapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.SampleAppArg.AppID] = sampleapp_elements
"""

#########################################################
# HK APP                                                #
#########################################################
from hk import hkapp
parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
hkapp_elements = app_elements()
hkapp_elements.process = Process(target = hkapp.hkapp_main, args = (main_queue, child_pipe, ))
hkapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.HkAppArg.AppID] = hkapp_elements

#########################################################
# BarometerApp                                          #
#########################################################
from barometer import barometerapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
barometerapp_elements = app_elements()
barometerapp_elements.process = Process(target = barometerapp.barometerapp_main, args = (main_queue, child_pipe, ))
barometerapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.BarometerAppArg.AppID] = barometerapp_elements


#########################################################
# GpsApp                                                #
#########################################################
from gps import gpsapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
gpsapp_elements = app_elements()
gpsapp_elements.process = Process(target = gpsapp.gpsapp_main, args = (main_queue, child_pipe, ))
gpsapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.GpsAppArg.AppID] = gpsapp_elements


#########################################################
# ImuApp                                                #
#########################################################
from imu import imuapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
imuapp_elements = app_elements()
imuapp_elements.process = Process(target = imuapp.imuapp_main, args = (main_queue, child_pipe, ))
imuapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.ImuAppArg.AppID] = imuapp_elements


#########################################################
# FlightlogicApp                                        #
#########################################################
from flight_logic import flightlogicapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
flightlogicapp_elements = app_elements()
flightlogicapp_elements.process = Process(target = flightlogicapp.flightlogicapp_main, args = (main_queue, child_pipe, ))
flightlogicapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.FlightlogicAppArg.AppID] = flightlogicapp_elements


#########################################################
# CommApp                                               #
#########################################################
from comm import commapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
commapp_elements = app_elements()
commapp_elements.process = Process(target = commapp.commapp_main, args = (main_queue, child_pipe, ))
commapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.CommAppArg.AppID] = commapp_elements



#########################################################
# Gimbalmotorapp                                        #
#########################################################
from motor import motorapp


parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
motorapp_elements = app_elements()
motorapp_elements.process = Process(target = motorapp.motorapp_main, args = (main_queue, child_pipe, ))
motorapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.MotorAppArg.AppID] = motorapp_elements

#########################################################
# FIRApp                                                #
#########################################################

from fir import firapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
firapp_elements = app_elements()
firapp_elements.process = Process(target = firapp.firapp_main, args = (main_queue, child_pipe, ))
firapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.FirAppArg.AppID] = firapp_elements

#########################################################
# NIRApp                                                #
#########################################################
"""""
from NIR import Nirapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
cameraapp_elements = app_elements()
cameraapp_elements.process = Process(target = firapp.firapp_main, args = (main_queue, child_pipe, ))
cameraapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.FirAppArg.AppID] = cameraapp_elements
"""
#########################################################
# CameraApp                                             #
#########################################################

from thermal_camera import thermo_cameraapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
thermo_cameraapp_elements = app_elements()
thermo_cameraapp_elements.process = Process(target = thermo_cameraapp.thermocamapp_main, args = (main_queue, child_pipe, ))
thermo_cameraapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.ThermalcameraAppArg.AppID] = thermo_cameraapp_elements

#########################################################
# THERMOApp                                             #
#########################################################

from thermo import thermoapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
thermoapp_elements = app_elements()
thermoapp_elements.process = Process(target = thermoapp.thermoapp_main, args = (main_queue, child_pipe, ))
thermoapp_elements.pipe = parent_pipe

# Add the process to dictionaryF
app_dict[appargs.ThermoAppArg.AppID] = thermoapp_elements




#########################################################
# Add Apps HERE                                         #
#########################################################


#########################################################
# Application Management                                #
# Functions for (re)starting, terminating applications  # 
#########################################################

def run_app(AppID : types.AppID) :
    if AppID in app_dict:
        #app_process : Process = app_dict[AppID][0]
        app_process: Process = app_dict[AppID].process
        app_process.start()
    else:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"AppID {AppID} not in app dictionary")

#########################################################
# Termination Process                                   #
# Jobs need to be done when terminating process         # 
#########################################################

def terminate_FSW():
    global MAINAPP_RUNSTATUS
    # Set all Runstatus to false
    MAINAPP_RUNSTATUS = False

    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)

    # Send termination message to kill every process
    for appID in app_dict:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID}")
        app_dict[appID].pipe.send(termination_message_to_send)

    # Join all processes to make sure every processes is killed
    for appID in app_dict:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Joining AppID {appID}")
        app_dict[appID].process.join()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID} complete")

    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Manual termination! Resetting prev state file")
    prevstate.reset_prevstate()
    
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"All Termination Process complete, terminating FSW")
    sys.exit()
    return
# Import and execute each app's runloop HERE

# Check run status, restart correspoding app when run status is false
# TBD
def checkrunstatus():
    return

# Main Runloop
def runloop(Main_Queue : Queue):
    global MAINAPP_RUNSTATUS
    try:
        while MAINAPP_RUNSTATUS:
            # Recv Message from queue
            recv_msg = Main_Queue.get()

            # Unpack the message to Check receiver
            unpacked_msg = msgstructure.MsgStructure()
            msgstructure.unpack_msg(unpacked_msg, recv_msg)
            
            if unpacked_msg.receiver_app in app_dict:
                app_dict[unpacked_msg.receiver_app].pipe.send(recv_msg)
            else:
                #events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, "Error : Received MID in not in app dictionary")
                continue

    except KeyboardInterrupt:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "KeyboardInterrupt Detected, Terminating FSW")
        MAINAPP_RUNSTATUS = False

    terminate_FSW()
    return


# Operation starts HERE
if __name__ == '__main__':

    # Start each app's process
    for appID in app_dict:
        app_dict[appID].process.start()

    # Main app runloop
    runloop(main_queue)
