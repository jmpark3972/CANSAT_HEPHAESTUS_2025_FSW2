# Main Flight Software Code for Cansat Mission
# Author : Hyeon Lee

# Sys library is needed to exit app
import sys
import os
import signal
import atexit

MAINAPP_RUNSTATUS = True
_termination_in_progress = False

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

prevstate_file_path = 'lib/prevstate.txt'

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

def terminate_FSW():
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        return  # Already terminating
    _termination_in_progress = True
    print(f"\nFSW 종료 프로세스 시작...")
    # Set all Runstatus to false
    MAINAPP_RUNSTATUS = False

    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)

    # Send termination message to kill every process
    for appID in app_dict:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID}")
        try:
            app_dict[appID].pipe.send(termination_message_to_send)
        except Exception as e:
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send termination to {appID}: {e}")

    # Join all processes to make sure every processes is killed
    for appID in app_dict:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Joining AppID {appID}")
        try:
            # 먼저 정상 종료 시도
            app_dict[appID].process.join(timeout=3)  # 3초로 단축
            if app_dict[appID].process.is_alive():
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force terminating AppID {appID}")
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=2)
                if app_dict[appID].process.is_alive():
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force killing AppID {appID}")
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=1)
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID} complete")
        except Exception as e:
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Error joining {appID}: {e}")
            # 예외 발생 시 강제 종료
            try:
                app_dict[appID].process.kill()
            except:
                pass

    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Manual termination! Resetting prev state file")
    prevstate.reset_prevstate()
    
    # 강제 종료를 위한 최종 확인
    print("FSW 종료 완료. 프로그램을 종료합니다.")
    os._exit(0)
    
    # 이중 로깅 시스템 종료
    try:
        logging.close_dual_logging_system()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "이중 로깅 시스템 종료 완료")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"이중 로깅 시스템 종료 실패: {e}")
    
    print("FSW 종료 완료")
    os._exit(0)
    try:
        from lib import logging
        logging.close_dual_logging_system()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "이중 로깅 시스템 종료 완료")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"이중 로깅 시스템 종료 오류: {e}")
    
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"All Termination Process complete, terminating FSW")
    
    # 최종 강제 종료 보장
    try:
        import os
        os._exit(0)  # 강제 종료
    except:
        sys.exit(0)
    return

# Flag to prevent multiple termination calls
_termination_in_progress = False

# Signal handler for graceful termination
def signal_handler(signum, frame):
    """시그널 핸들러 - Ctrl+C 등으로 인한 종료 처리"""
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        return  # Already terminating
    print(f"\n시그널 {signum} 수신, FSW 종료 중...")
    MAINAPP_RUNSTATUS = False
    # 실제 종료 프로세스 호출
    terminate_FSW()
    # 강제 종료를 위한 os._exit 추가
    os._exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
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
# FIR1App (MLX90614 Channel 0)                          #
#########################################################

from fir1 import firapp1

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
firapp1_elements = app_elements()
firapp1_elements.process = Process(target = firapp1.firapp1_main, args = (main_queue, child_pipe, ))
firapp1_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.FirApp1Arg.AppID] = firapp1_elements

#########################################################
# FIR2App (MLX90614 Channel 1)                          #
#########################################################

from fir2 import firapp2

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
firapp2_elements = app_elements()
firapp2_elements.process = Process(target = firapp2.firapp2_main, args = (main_queue, child_pipe, ))
firapp2_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.FirApp2Arg.AppID] = firapp2_elements

#########################################################
# THERMISApp                                            #
#########################################################

from thermis import thermisapp
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'pitot'))
import pitotapp

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
thermisapp_elements = app_elements()
thermisapp_elements.process = Process(target = thermisapp.thermisapp_main, args = (main_queue, child_pipe, ))
thermisapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.ThermisAppArg.AppID] = thermisapp_elements



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
# PitotApp                                              #
#########################################################

parent_pipe, child_pipe = Pipe()

# Add Process, pipe to elements dictionary
pitotapp_elements = app_elements()
pitotapp_elements.process = Process(target = pitotapp.pitotapp_main, args = (main_queue, child_pipe, ))
pitotapp_elements.pipe = parent_pipe

# Add the process to dictionary
app_dict[appargs.PitotAppArg.AppID] = pitotapp_elements

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


# Import and execute each app's runloop HERE

# Main Runloop
def runloop(Main_Queue : Queue):
    global MAINAPP_RUNSTATUS
    try:
        while MAINAPP_RUNSTATUS:
            try:
                # Recv Message from queue with timeout
                recv_msg = Main_Queue.get(timeout=1.0)  # 1 second timeout

                # Unpack the message to Check receiver
                unpacked_msg = msgstructure.MsgStructure()
                msgstructure.unpack_msg(unpacked_msg, recv_msg)
                
                if unpacked_msg.receiver_app in app_dict:
                    try:
                        app_dict[unpacked_msg.receiver_app].pipe.send(recv_msg)
                    except Exception as e:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send message to {unpacked_msg.receiver_app}: {e}")
                else:
                    #events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, "Error : Received MID in not in app dictionary")
                    continue
            except Exception as e:
                # Handle queue timeout and other exceptions gracefully
                if "Empty" not in str(e):  # Not a timeout
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error: {e}")

    except KeyboardInterrupt:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "KeyboardInterrupt Detected, Terminating FSW")
        MAINAPP_RUNSTATUS = False
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical error in main loop: {e}")
        MAINAPP_RUNSTATUS = False

    terminate_FSW()
    # 강제 종료를 위한 최종 확인
    print("메인 루프 종료 완료. 프로그램을 종료합니다.")
    os._exit(0)
    return


# Operation starts HERE
if __name__ == '__main__':

    # 이중 로깅 시스템 초기화
    try:
        from lib import logging
        logging.init_dual_logging_system()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "이중 로깅 시스템 초기화 완료")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"이중 로깅 시스템 초기화 실패: {e}")

    # Start each app's process
    for appID in app_dict:
        app_dict[appID].process.start()

    # Main app runloop
    runloop(main_queue)
