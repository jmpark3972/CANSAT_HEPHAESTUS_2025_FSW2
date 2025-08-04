# Main Flight Software Code for Cansat Mission
# Author : Hyeon Lee

# Sys library is needed to exit app
import sys
import os
import signal
import atexit
import time

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

# 시스템 안전성 검사
def system_safety_check():
    """시스템 안전성 검사"""
    try:
        # 메모리 사용량 확인
        try:
            import psutil
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"High memory usage: {memory.percent}%")
            
            # 디스크 공간 확인
            disk = psutil.disk_usage('/')
            if disk.percent > 95:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Low disk space: {disk.percent}% used")
        except ImportError:
            # psutil이 없는 경우 기본 검사만
            pass
        
        # 프로세스 수 확인
        try:
            import threading
            active_threads = threading.active_count()
            if active_threads > 50:  # 스레드 수 제한
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"High thread count: {active_threads}")
        except:
            pass
            
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Safety check error: {e}")

def check_system_limits():
    """시스템 리소스 한계 확인"""
    try:
        import resource
        import threading
        
        # 현재 스레드 수 확인
        current_threads = threading.active_count()
        
        # 시스템 한계 확인
        soft, hard = resource.getrlimit(resource.RLIMIT_NPROC)
        
        print(f"시스템 리소스 상태:")
        print(f"  - 현재 스레드 수: {current_threads}")
        print(f"  - 프로세스 한계: {soft}/{hard}")
        
        # psutil이 있는 경우 프로세스 수도 확인
        try:
            import psutil
            current_processes = len(psutil.pids())
            print(f"  - 현재 프로세스 수: {current_processes}")
            
            if current_processes > soft * 0.8:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"High process count detected: {current_processes}")
                return False
        except ImportError:
            # psutil이 없는 경우 프로세스 수 확인 건너뛰기
            pass
        
        if current_threads > 30:
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"High thread count detected: {current_threads}")
            return False
            
        return True
        
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"System limits check error: {e}")
        return False

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

    # 이중 로깅 시스템 종료
    try:
        from lib import logging
        logging.close_dual_logging_system()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "이중 로깅 시스템 종료 완료")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"이중 로깅 시스템 종료 실패: {e}")

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
    
    # 잠시 대기 후 강제 종료 시작
    time.sleep(0.5)

    # Join all processes to make sure every processes is killed
    for appID in app_dict:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Joining AppID {appID}")
        try:
            # 더 빠른 강제 종료를 위해 즉시 terminate 시도
            if app_dict[appID].process.is_alive():
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force terminating AppID {appID}")
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1)  # 1초로 단축
                if app_dict[appID].process.is_alive():
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force killing AppID {appID}")
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=0.5)  # 0.5초로 단축
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
    
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"All Termination Process complete, terminating FSW")
    
    # 추가 정리: 모든 자식 프로세스 강제 종료
    try:
        import psutil
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            try:
                child.terminate()
                child.wait(timeout=1)
            except:
                try:
                    child.kill()
                except:
                    pass
    except ImportError:
        # psutil이 없는 경우 기본 방법 사용
        pass
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Child process cleanup error: {e}")
    
    print("FSW 종료 완료. 프로그램을 종료합니다.")
    # 최종 강제 종료
    os._exit(0)

# Flag to prevent multiple termination calls
_termination_in_progress = False

# Signal handler for graceful termination
def signal_handler(signum, frame):
    """시그널 핸들러 - Ctrl+C 등으로 인한 종료 처리"""
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        print("이미 종료 중입니다. 강제 종료 실행...")
        os._exit(0)
        return
    
    print(f"\n시그널 {signum} 수신, FSW 종료 중...")
    _termination_in_progress = True
    MAINAPP_RUNSTATUS = False
    
    # 모든 프로세스 강제 종료
    try:
        for appID in app_dict:
            if app_dict[appID].process and app_dict[appID].process.is_alive():
                print(f"강제 종료: {appID}")
                try:
                    app_dict[appID].process.terminate()
                    app_dict[appID].process.join(timeout=0.5)
                    if app_dict[appID].process.is_alive():
                        app_dict[appID].process.kill()
                        app_dict[appID].process.join(timeout=0.5)
                except:
                    try:
                        app_dict[appID].process.kill()
                    except:
                        pass
    except:
        pass
    
    # 추가 정리: 모든 자식 프로세스 강제 종료
    try:
        import psutil
        current_process = psutil.Process()
        children = current_process.children(recursive=True)
        for child in children:
            try:
                child.terminate()
                child.wait(timeout=0.5)
            except:
                try:
                    child.kill()
                except:
                    pass
    except ImportError:
        pass
    except Exception as e:
        print(f"자식 프로세스 정리 오류: {e}")
    
    # 즉시 강제 종료 실행
    print("강제 종료 실행 중...")
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
    import time
    start_time = time.time()
    max_runtime = 3600  # 1시간 최대 실행 시간
    
    try:
        while MAINAPP_RUNSTATUS:
            # 최대 실행 시간 체크
            if time.time() - start_time > max_runtime:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, "Maximum runtime reached, terminating FSW")
                break
                
            try:
                # Recv Message from queue with timeout
                recv_msg = Main_Queue.get(timeout=0.1)  # 0.1초로 단축하여 더 빠른 응답

                # 메시지 유효성 검사
                if not isinstance(recv_msg, str):
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Invalid message type: {type(recv_msg)}")
                    continue

                # Unpack the message to Check receiver
                unpacked_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(unpacked_msg, recv_msg):
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to unpack message: {recv_msg}")
                    continue
                
                if unpacked_msg.receiver_app in app_dict:
                    try:
                        # 파이프 유효성 검사
                        if app_dict[unpacked_msg.receiver_app].pipe is None:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Pipe is None for {unpacked_msg.receiver_app}")
                            continue
                        app_dict[unpacked_msg.receiver_app].pipe.send(recv_msg)
                    except Exception as e:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send message to {unpacked_msg.receiver_app}: {e}")
                else:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Unknown receiver app: {unpacked_msg.receiver_app}")
                    continue
            except Exception as e:
                # Handle queue timeout and other exceptions gracefully
                if "Empty" not in str(e):  # Not a timeout
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error: {e}")

    except KeyboardInterrupt:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "KeyboardInterrupt Detected, Terminating FSW")
        MAINAPP_RUNSTATUS = False
        print("KeyboardInterrupt 감지됨. 강제 종료합니다.")
        
        # 모든 프로세스 강제 종료
        try:
            for appID in app_dict:
                if app_dict[appID].process and app_dict[appID].process.is_alive():
                    print(f"강제 종료: {appID}")
                    app_dict[appID].process.kill()
        except:
            pass
        
        os._exit(0)
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical error in main loop: {e}")
        MAINAPP_RUNSTATUS = False
        print("치명적 오류 발생. 강제 종료합니다.")
        os._exit(0)

    # 정상 종료 시
    print("정상 종료 완료.")
    return


# Cleanup function for atexit
def cleanup_on_exit():
    """프로그램 종료 시 정리 작업"""
    print("\n프로그램 종료 시 정리 작업 실행...")
    try:
        terminate_FSW()
    except:
        pass

# Watchdog function to ensure termination
def watchdog_termination():
    """워치독 함수 - 일정 시간 후 강제 종료"""
    global MAINAPP_RUNSTATUS
    time.sleep(10)  # 10초로 단축
    if MAINAPP_RUNSTATUS:
        print("\n워치독: 10초 경과, 강제 종료 실행...")
        os._exit(0)

# Operation starts HERE
if __name__ == '__main__':

    # 시스템 리소스 한계 확인
    try:
        if not check_system_limits():
            print("시스템 리소스 한계에 도달했습니다. 프로그램을 종료합니다.")
            os._exit(1)
    except Exception as e:
        print(f"System limits check failed: {e}")

    # 시스템 안전성 검사
    try:
        system_safety_check()
    except Exception as e:
        print(f"Safety check failed: {e}")

    # 이중 로깅 시스템 초기화
    try:
        from lib import logging
        logging.init_dual_logging_system()
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "이중 로깅 시스템 초기화 완료")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"이중 로깅 시스템 초기화 실패: {e}")

    # Register cleanup function
    atexit.register(cleanup_on_exit)

    # Watchdog 스레드 제거 (스레드 수 줄이기)
    # import threading
    # watchdog_thread = threading.Thread(target=watchdog_termination, daemon=True)
    # watchdog_thread.start()

    # 프로세스 시작 전 검증 (순차적 시작으로 리소스 부하 줄이기)
    try:
        # Start each app's process sequentially
        for appID in app_dict:
            if app_dict[appID].process is None:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Process for {appID} is None")
                continue
            app_dict[appID].process.start()
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Started process for {appID}")
            time.sleep(0.1)  # 각 프로세스 시작 사이에 짧은 대기
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Error starting processes: {e}")
        os._exit(1)

    # Main app runloop
    runloop(main_queue)
