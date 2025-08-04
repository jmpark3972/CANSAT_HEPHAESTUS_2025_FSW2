# Main Flight Software Code for Cansat Mission
# Author : Hyeon Lee

# Sys library is needed to exit app
import sys
import os
import signal
import atexit
import time
from datetime import datetime

MAINAPP_RUNSTATUS = True
_termination_in_progress = False

# Custom libraries
from lib import appargs
from lib import msgstructure
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



from lib import prevstate

main_queue = Queue()

class app_elements:
    process : Process = None
    pipe : connection.Connection = None

app_dict: dict[types.AppID, app_elements] = {}

def terminate_FSW():
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        return  # Already terminating
    _termination_in_progress = True
    print(f"\nFSW 종료 프로세스 시작...")
    
    MAINAPP_RUNSTATUS = False

    try:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "로깅 시스템 정리 완료")
    except Exception as e:
        print(f"로깅 시스템 정리 실패: {e}")

    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)

    # 종료 메시지 전송
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID}")
            try:
                app_dict[appID].pipe.send(termination_message_to_send)
            except Exception as e:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send termination to {appID}: {e}")
    
    time.sleep(0.5)

    # 프로세스 종료
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Joining AppID {appID}")
            try:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force terminating AppID {appID}")
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1)
                if app_dict[appID].process.is_alive():
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Force killing AppID {appID}")
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=0.5)
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Terminating AppID {appID} complete")
            except Exception as e:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Error joining {appID}: {e}")
                try:
                    app_dict[appID].process.kill()
                except Exception as kill_error:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"프로세스 강제 종료 중 오류: {kill_error}")

    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Manual termination! Resetting prev state file")
    prevstate.reset_prevstate()
    
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"All Termination Process complete, terminating FSW")
    
    try:
        pass
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Child process cleanup error: {e}")
    
    print("FSW 종료 완료. 프로그램을 종료합니다.")
    os._exit(0)

# Flag to prevent multiple termination calls
_termination_in_progress = False

def signal_handler(signum, frame):
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        print("이미 종료 중입니다. 강제 종료 실행...")
        os._exit(0)
        return
    
    print(f"\n시그널 {signum} 수신, FSW 종료 중...")
    _termination_in_progress = True
    MAINAPP_RUNSTATUS = False
    
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
                except Exception as e:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"시그널 핸들러에서 프로세스 종료 오류: {e}")
                    try:
                        app_dict[appID].process.kill()
                    except Exception as kill_error:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"시그널 핸들러에서 강제 종료 오류: {kill_error}")
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"시그널 핸들러에서 전체 프로세스 정리 오류: {e}")
    
    try:
        pass
    except Exception as e:
        print(f"자식 프로세스 정리 오류: {e}")
    
    print("강제 종료 실행 중...")
    os._exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# HK APP
try:
    from hk import hkapp
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    hkapp_elements = app_elements()
    hkapp_elements.process = Process(target = hkapp.hkapp_main, args = (main_queue, child_pipe, ))
    hkapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.HkAppArg.AppID] = hkapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "HK 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"HK 앱 로드 실패: {e}")

# BarometerApp
try:
    from barometer import barometerapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    barometerapp_elements = app_elements()
    barometerapp_elements.process = Process(target = barometerapp.barometerapp_main, args = (main_queue, child_pipe, ))
    barometerapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.BarometerAppArg.AppID] = barometerapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Barometer 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Barometer 앱 로드 실패: {e}")

# GpsApp
try:
    from gps import gpsapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    gpsapp_elements = app_elements()
    gpsapp_elements.process = Process(target = gpsapp.gpsapp_main, args = (main_queue, child_pipe, ))
    gpsapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.GpsAppArg.AppID] = gpsapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "GPS 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"GPS 앱 로드 실패: {e}")

# ImuApp
try:
    from imu import imuapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    imuapp_elements = app_elements()
    imuapp_elements.process = Process(target = imuapp.imuapp_main, args = (main_queue, child_pipe, ))
    imuapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.ImuAppArg.AppID] = imuapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "IMU 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"IMU 앱 로드 실패: {e}")

# FlightlogicApp
try:
    from flight_logic import flightlogicapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    flightlogicapp_elements = app_elements()
    flightlogicapp_elements.process = Process(target = flightlogicapp.flightlogicapp_main, args = (main_queue, child_pipe, ))
    flightlogicapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.FlightlogicAppArg.AppID] = flightlogicapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "FlightLogic 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"FlightLogic 앱 로드 실패: {e}")

# CommApp
try:
    from comm import commapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    commapp_elements = app_elements()
    commapp_elements.process = Process(target = commapp.commapp_main, args = (main_queue, child_pipe, ))
    commapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.CommAppArg.AppID] = commapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Comm 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Comm 앱 로드 실패: {e}")

# Motorapp
try:
    from motor import motorapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    motorapp_elements = app_elements()
    motorapp_elements.process = Process(target = motorapp.motorapp_main, args = (main_queue, child_pipe, ))
    motorapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.MotorAppArg.AppID] = motorapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Motor 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Motor 앱 로드 실패: {e}")

# FIR1App (MLX90614 Channel 0)
try:
    from fir1 import firapp1
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    firapp1_elements = app_elements()
    firapp1_elements.process = Process(target = firapp1.firapp1_main, args = (main_queue, child_pipe, ))
    firapp1_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.FirApp1Arg.AppID] = firapp1_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "FIR1 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"FIR1 앱 로드 실패: {e}")

# THERMISApp
try:
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
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Thermis 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Thermis 앱 로드 실패: {e}")

# TMP007App
try:
    from tmp007 import tmp007app
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    tmp007app_elements = app_elements()
    tmp007app_elements.process = Process(target = tmp007app.tmp007app_main, args = (main_queue, child_pipe, ))
    tmp007app_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.Tmp007AppArg.AppID] = tmp007app_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "TMP007 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"TMP007 앱 로드 실패: {e}")

# CameraApp
try:
    from thermal_camera import thermo_cameraapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    thermo_cameraapp_elements = app_elements()
    thermo_cameraapp_elements.process = Process(target = thermo_cameraapp.thermocamapp_main, args = (main_queue, child_pipe, ))
    thermo_cameraapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.ThermalcameraAppArg.AppID] = thermo_cameraapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Thermal Camera 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Thermal Camera 앱 로드 실패: {e}")

# THERMOApp
try:
    from thermo import thermoapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    thermoapp_elements = app_elements()
    thermoapp_elements.process = Process(target = thermoapp.thermoapp_main, args = (main_queue, child_pipe, ))
    thermoapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.ThermoAppArg.AppID] = thermoapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Thermo 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Thermo 앱 로드 실패: {e}")

# PitotApp
try:
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    pitotapp_elements = app_elements()
    pitotapp_elements.process = Process(target = pitotapp.pitotapp_main, args = (main_queue, child_pipe, ))
    pitotapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.PitotAppArg.AppID] = pitotapp_elements
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "Pitot 앱 로드 완료")
except Exception as e:
    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Pitot 앱 로드 실패: {e}")






# Main Runloop
def runloop(Main_Queue : Queue):
    global MAINAPP_RUNSTATUS
    import time
    start_time = time.time()
    max_runtime = 3600  # 1시간 최대 실행 시간
    
    # 프로세스 상태 모니터링
    last_health_check = time.time()
    
    try:
        while MAINAPP_RUNSTATUS:
            if time.time() - start_time > max_runtime:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, "Maximum runtime reached, terminating FSW")
                break
            
            # 주기적 프로세스 상태 체크 (10초마다)
            if time.time() - last_health_check > 10:
                last_health_check = time.time()
                
                # 시스템 상태 리포트 생성 (1분마다)
                if int(time.time()) % 60 < 10:  # 매분 처음 10초 동안
                    generate_system_status_report()
                
                for appID in app_dict:
                    if app_dict[appID].process and not app_dict[appID].process.is_alive():
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Process {appID} is dead, attempting restart")
                        try:
                            app_dict[appID].pipe.close()
                        except Exception as e:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Pipe close error for dead process {appID}: {e}")
                        
                        # 중요도별 앱 분류
                        critical_apps = [
                            appargs.HkAppArg.AppID,
                            appargs.CommAppArg.AppID,
                            appargs.FlightlogicAppArg.AppID
                        ]
                        
                        non_critical_apps = [
                            appargs.FirApp1Arg.AppID,
                            appargs.FirApp2Arg.AppID,
                            appargs.ThermalcameraAppArg.AppID,
                            appargs.Tmp007AppArg.AppID
                        ]
                        
                        if appID in non_critical_apps:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Non-critical process {appID} is dead, continuing without restart")
                        elif appID in critical_apps:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical process {appID} is dead, system may be unstable but continuing")
                        else:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Process {appID} is dead, continuing")
                
            try:
                recv_msg = Main_Queue.get(timeout=0.5)

                if not isinstance(recv_msg, str):
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Invalid message type: {type(recv_msg)}")
                    continue

                unpacked_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(unpacked_msg, recv_msg):
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to unpack message: {recv_msg}")
                    continue
                
                if unpacked_msg.receiver_app in app_dict:
                    try:
                        if app_dict[unpacked_msg.receiver_app].pipe is None:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Pipe is None for {unpacked_msg.receiver_app}")
                            continue
                        
                        if not app_dict[unpacked_msg.receiver_app].process.is_alive():
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Process {unpacked_msg.receiver_app} is dead, skipping message")
                            continue
                            
                        app_dict[unpacked_msg.receiver_app].pipe.send(recv_msg)
                    except BrokenPipeError:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Broken pipe for {unpacked_msg.receiver_app}, but continuing")
                        try:
                            app_dict[unpacked_msg.receiver_app].pipe.close()
                        except:
                            pass
                    except Exception as e:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send message to {unpacked_msg.receiver_app}: {e}")
                else:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Unknown receiver app: {unpacked_msg.receiver_app}")
                    continue
            except Exception as e:
                if "Empty" not in str(e):
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error: {e}")

    except KeyboardInterrupt:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "KeyboardInterrupt Detected, Terminating FSW")
        MAINAPP_RUNSTATUS = False
        print("KeyboardInterrupt 감지됨. 강제 종료합니다.")
        
        try:
            for appID in app_dict:
                if app_dict[appID].process and app_dict[appID].process.is_alive():
                    print(f"강제 종료: {appID}")
                    app_dict[appID].process.kill()
        except Exception as e:
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"KeyboardInterrupt에서 프로세스 강제 종료 오류: {e}")
        
        os._exit(0)
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical error in main loop: {e}")
        MAINAPP_RUNSTATUS = False
        print("치명적 오류 발생. 강제 종료합니다.")
        os._exit(0)

    print("정상 종료 완료.")
    return


def cleanup_on_exit():
    print("\n프로그램 종료 시 정리 작업 실행...")
    try:
        terminate_FSW()
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Cleanup on exit 오류: {e}")


def generate_system_status_report():
    """시스템 상태 리포트 생성"""
    try:
        report = {
            'timestamp': datetime.now().isoformat(sep=' ', timespec='milliseconds'),
            'processes': {},
            'memory_usage': {},
            'disk_usage': {},
            'transmission_stats': {}
        }
        
        # 프로세스 상태
        for appID in app_dict:
            if app_dict[appID].process:
                report['processes'][appID] = {
                    'alive': app_dict[appID].process.is_alive(),
                    'pid': app_dict[appID].process.pid if app_dict[appID].process.is_alive() else None,
                    'exitcode': app_dict[appID].process.exitcode if not app_dict[appID].process.is_alive() else None
                }
        
        # 메모리 사용량 (간단한 추정)
        import psutil
        process = psutil.Process()
        report['memory_usage'] = {
            'rss_mb': process.memory_info().rss / 1024 / 1024,
            'vms_mb': process.memory_info().vms / 1024 / 1024,
            'percent': process.memory_percent()
        }
        
        # 디스크 사용량
        try:
            disk_usage = psutil.disk_usage('.')
            report['disk_usage'] = {
                'total_gb': disk_usage.total / 1024 / 1024 / 1024,
                'used_gb': disk_usage.used / 1024 / 1024 / 1024,
                'free_gb': disk_usage.free / 1024 / 1024 / 1024,
                'percent': disk_usage.percent
            }
        except Exception as e:
            report['disk_usage'] = {'error': str(e)}
        
        # 전송 통계 (CommApp에서 가져오기)
        try:
            from comm import commapp
            report['transmission_stats'] = commapp.get_transmission_stats()
        except Exception as e:
            report['transmission_stats'] = {'error': str(e)}
        
        # 리포트를 로그 파일에 저장
        import json
        report_file = "logs/system_status_report.json"
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # 간단한 상태 출력
        alive_count = sum(1 for p in report['processes'].values() if p['alive'])
        total_count = len(report['processes'])
        
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, 
                       f"System Status: {alive_count}/{total_count} processes alive, "
                       f"Memory: {report['memory_usage']['rss_mb']:.1f}MB, "
                       f"Disk: {report['disk_usage'].get('percent', 0):.1f}% used")
        
        return report
        
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"System status report generation failed: {e}")
        return None


if __name__ == '__main__':

    try:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "로깅 시스템 초기화 완료")
    except Exception as e:
        print(f"로깅 시스템 초기화 실패: {e}")

    atexit.register(cleanup_on_exit)



    try:
        # 핵심 앱들을 우선순위에 따라 시작
        core_apps = [
            appargs.HkAppArg.AppID,      # HK 앱은 항상 먼저
            appargs.BarometerAppArg.AppID,  # 센서 앱들
            appargs.GpsAppArg.AppID,
            appargs.ImuAppArg.AppID,
            appargs.ThermisAppArg.AppID,
            appargs.FirApp1Arg.AppID,
            appargs.FirApp2Arg.AppID,
            appargs.ThermoAppArg.AppID,
            appargs.Tmp007AppArg.AppID,  # TMP007 센서 앱
            appargs.PitotAppArg.AppID,
            appargs.ThermalcameraAppArg.AppID,
            appargs.CommAppArg.AppID,    # 통신 앱
            appargs.MotorAppArg.AppID,   # 모터 앱
            appargs.FlightlogicAppArg.AppID,  # 비행 로직 앱
        ]
        
        # 중요도별 앱 분류
        critical_apps = [
            appargs.HkAppArg.AppID,
            appargs.CommAppArg.AppID,
            appargs.FlightlogicAppArg.AppID
        ]
        
        non_critical_apps = [
            appargs.FirApp1Arg.AppID,
            appargs.FirApp2Arg.AppID,
            appargs.ThermalcameraAppArg.AppID,
            appargs.Tmp007AppArg.AppID
        ]
        
        # 핵심 앱들 시작
        for appID in core_apps:
            if appID in app_dict and app_dict[appID].process is not None:
                try:
                    app_dict[appID].process.start()
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Started core process for {appID}")
                    time.sleep(0.3)  # 더 긴 대기로 안정성 향상
                except Exception as e:
                    if appID in critical_apps:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical app {appID} failed to start: {e}")
                        # 중요 앱 실패 시에도 계속 진행 (시스템 안정성 우선)
                    else:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Non-critical app {appID} failed to start: {e}")
                    continue
        
        # 나머지 앱들 시작
        for appID in app_dict:
            if appID not in core_apps and app_dict[appID].process is not None:
                try:
                    app_dict[appID].process.start()
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Started process for {appID}")
                    time.sleep(0.2)
                except Exception as e:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Failed to start {appID}: {e}")
                    continue
                    
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Error starting processes: {e}")
        # 프로세스 시작 실패 시에도 메인 루프는 계속 실행
        pass

    runloop(main_queue)
