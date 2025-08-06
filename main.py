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
from lib import logging
from lib import types

# Multiprocessing Library is used on Python FSW V2
# Each application should have its own runloop
# Import the application and execute the runloop here.

from multiprocessing import Process, Queue, Pipe, connection

# Load configuration files
from lib import config
from lib import resource_manager
from lib import memory_optimizer
from lib import LogRotator

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        logging.safe_log(message, level, printlogs, appargs.MainAppArg.AppName)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        pass  # [MAIN] 로깅 실패: {e}
        pass  # [MAIN] 원본 메시지: {message}

# 리소스 모니터링 및 메모리 최적화 시작
resource_manager.start_resource_monitoring()
memory_optimizer.start_memory_optimization()

# 로그 로테이션 초기화
log_rotator = LogRotator(max_size_mb=10, max_age_days=30)

if config.get_config("FSW_MODE") == "NONE":
    safe_log("CONFIG IS SELECTED AS NONE, TERMINATING FSW", "ERROR", True)
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
    # FSW 종료 프로세스 시작...
    
    MAINAPP_RUNSTATUS = False

    try:
        # 리소스 모니터링 및 메모리 최적화 중지
        resource_manager.stop_resource_monitoring()
        memory_optimizer.stop_memory_optimization()
        safe_log("리소스 모니터링 및 메모리 최적화 중지 완료", "INFO", True)
        
        # 로그 로테이션 실행
        log_rotator.rotate_logs()
        safe_log("로그 로테이션 완료", "INFO", True)
        
        # 로깅 시스템 정리
        # 통합 로깅 시스템은 자동으로 정리됨
        safe_log("로깅 시스템 정리 완료", "INFO", True)
    except Exception as e:
        pass  # 시스템 정리 실패: {e}

    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)

    # 종료 메시지 전송
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            safe_log(f"Terminating AppID {appID}", "INFO", True)
            try:
                app_dict[appID].pipe.send(termination_message_to_send)
            except Exception as e:
                safe_log(f"Failed to send termination to {appID}: {e}", "ERROR", True)
    
    time.sleep(0.5)

    # 프로세스 종료
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            safe_log(f"Joining AppID {appID}", "INFO", True)
            try:
                safe_log(f"Force terminating AppID {appID}", "WARNING", True)
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1)
                if app_dict[appID].process.is_alive():
                    safe_log(f"Force killing AppID {appID}", "WARNING", True)
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=0.5)
                safe_log(f"Terminating AppID {appID} complete", "INFO", True)
            except Exception as e:
                safe_log(f"Error joining {appID}: {e}", "ERROR", True)
                try:
                    app_dict[appID].process.kill()
                except Exception as kill_error:
                    safe_log(f"프로세스 강제 종료 중 오류: {kill_error}", "ERROR", True)

    safe_log(f"Manual termination! Resetting prev state file", "INFO", True)
    prevstate.reset_prevstate()
    
    safe_log(f"All Termination Process complete, terminating FSW", "INFO", True)
    
    try:
        pass
    except Exception as e:
        safe_log(f"Child process cleanup error: {e}", "ERROR", True)
    
    # FSW 종료 완료. 프로그램을 종료합니다.
    os._exit(0)

# Flag to prevent multiple termination calls
_termination_in_progress = False

def signal_handler(signum, frame):
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        # 이미 종료 중입니다. 강제 종료 실행...
        os._exit(0)
        return
    
    # 시그널 {signum} 수신, FSW 종료 중...
    _termination_in_progress = True
    MAINAPP_RUNSTATUS = False
    
    # 종료 메시지 생성
    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)
    
    # 1단계: 정상 종료 메시지 전송
    # 1단계: 정상 종료 메시지 전송 중...
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            try:
                app_dict[appID].pipe.send(termination_message_to_send)
                # - {appID}: 종료 메시지 전송 완료
            except Exception as e:
                pass  # - {appID}: 종료 메시지 전송 실패: {e}
    
    # 2단계: 프로세스 종료 대기 (3초)
    # 2단계: 프로세스 정상 종료 대기 중... (3초)
    time.sleep(3.0)
    
    # 3단계: 강제 종료
    # 3단계: 강제 종료 실행...
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            # - {appID}: 강제 종료 실행
            try:
                # 먼저 terminate 시도
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1.0)
                
                # 여전히 살아있으면 kill
                if app_dict[appID].process.is_alive():
                    # {appID}: kill 실행
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=1.0)
                    
                    # 최후의 수단으로 강제 종료
                    if app_dict[appID].process.is_alive():
                        # {appID}: 최후 강제 종료
                        try:
                            import psutil
                            parent = psutil.Process(app_dict[appID].process.pid)
                            for child in parent.children(recursive=True):
                                child.kill()
                            parent.kill()
                        except Exception as e:
                            safe_log(f"자식 프로세스 종료 실패: {e}", "WARNING", False)
            except Exception as e:
                pass  # {appID}: 종료 오류: {e}
    
    # 4단계: 시스템 정리
    # 4단계: 시스템 정리 중...
    try:
        # 리소스 모니터링 중지
        resource_manager.stop_resource_monitoring()
        # - 리소스 모니터링 중지 완료
        
        # 로깅 시스템 정리
        # 통합 로깅 시스템은 자동으로 정리됨
        # - 로깅 시스템 정리 완료
        
        # 큐 정리
        try:
            while not main_queue.empty():
                main_queue.get_nowait()
        except Exception as e:
            safe_log(f"큐 정리 실패: {e}", "WARNING", False)
        # - 메시지 큐 정리 완료
        
    except Exception as e:
        pass  # - 시스템 정리 오류: {e}
    
    # 강제 종료 완료. 프로그램을 종료합니다.
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
    safe_log("HK 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"HK 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("Barometer 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Barometer 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("GPS 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"GPS 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("IMU 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"IMU 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("FlightLogic 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"FlightLogic 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("Comm 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Comm 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("Motor 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Motor 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("FIR1 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"FIR1 앱 로드 실패: {e}", "ERROR", True)

# THERMISApp
try:
    from thermis import thermisapp
    
    parent_pipe, child_pipe = Pipe()
    
    # Add Process, pipe to elements dictionary
    thermisapp_elements = app_elements()
    thermisapp_elements.process = Process(target = thermisapp.thermisapp_main, args = (main_queue, child_pipe, ))
    thermisapp_elements.pipe = parent_pipe
    
    # Add the process to dictionary
    app_dict[appargs.ThermisAppArg.AppID] = thermisapp_elements
    safe_log("Thermis 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Thermis 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("TMP007 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"TMP007 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("Thermal Camera 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Thermal Camera 앱 로드 실패: {e}", "ERROR", True)

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
    safe_log("Thermo 앱 로드 완료", "INFO", True)
except Exception as e:
    safe_log(f"Thermo 앱 로드 실패: {e}", "ERROR", True)




# Main Runloop
def runloop(Main_Queue : Queue):
    global MAINAPP_RUNSTATUS
    import time
    start_time = time.time()
    max_runtime = 3600  # 1시간 최대 실행 시간
    
    # 프로세스 상태 모니터링
    last_health_check = time.time()
    last_restart_attempt = {}  # 앱별 마지막 재시작 시도 시간
    
    # 중요도별 앱 분류
    critical_apps = [
        appargs.HkAppArg.AppID,
        appargs.CommAppArg.AppID,
        appargs.FlightlogicAppArg.AppID
    ]
    
    non_critical_apps = [
        appargs.FirApp1Arg.AppID,
        appargs.ThermalcameraAppArg.AppID,
        appargs.Tmp007AppArg.AppID
    ]
    
    # 센서 앱들 (중간 중요도)
    sensor_apps = [
        appargs.BarometerAppArg.AppID,
        appargs.GpsAppArg.AppID,
        appargs.ImuAppArg.AppID,
        appargs.ThermisAppArg.AppID,
        appargs.ThermoAppArg.AppID,
        appargs.MotorAppArg.AppID
    ]
    
    def restart_app(appID):
        """앱 재시작 함수"""
        try:
            if appID not in last_restart_attempt:
                last_restart_attempt[appID] = 0
            
            # 재시작 간격 제한 (30초)
            if time.time() - last_restart_attempt[appID] < 30:
                return False
                
            last_restart_attempt[appID] = time.time()
            
            # 기존 프로세스 정리
            if app_dict[appID].process and app_dict[appID].process.is_alive():
                try:
                    app_dict[appID].process.terminate()
                    app_dict[appID].process.join(timeout=5)
                    if app_dict[appID].process.is_alive():
                        app_dict[appID].process.kill()
                except Exception as e:
                    safe_log(f"Failed to terminate {appID}: {e}", "WARNING", True)
            
            # 파이프 정리
            try:
                app_dict[appID].pipe.close()
            except Exception as e:
                safe_log(f"Pipe close error for {appID}: {e}", "WARNING", True)
            
            # 새 파이프 생성
            parent_pipe, child_pipe = Pipe()
            app_dict[appID].pipe = parent_pipe
            
            # 앱별 프로세스 재생성
            if appID == appargs.HkAppArg.AppID:
                from hk import hkapp
                app_dict[appID].process = Process(target=hkapp.hkapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.CommAppArg.AppID:
                from comm import commapp
                app_dict[appID].process = Process(target=commapp.commapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.FlightlogicAppArg.AppID:
                from flight_logic import flightlogicapp
                app_dict[appID].process = Process(target=flightlogicapp.flightlogicapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.BarometerAppArg.AppID:
                from barometer import barometerapp
                app_dict[appID].process = Process(target=barometerapp.barometerapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.GpsAppArg.AppID:
                from gps import gpsapp
                app_dict[appID].process = Process(target=gpsapp.gpsapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.ImuAppArg.AppID:
                from imu import imuapp
                app_dict[appID].process = Process(target=imuapp.imuapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.ThermisAppArg.AppID:
                from thermis import thermisapp
                app_dict[appID].process = Process(target=thermisapp.thermisapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.FirApp1Arg.AppID:
                from fir1 import firapp1
                app_dict[appID].process = Process(target=firapp1.firapp1_main, args=(main_queue, child_pipe))
            elif appID == appargs.ThermoAppArg.AppID:
                from thermo import thermoapp
                app_dict[appID].process = Process(target=thermoapp.thermoapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.Tmp007AppArg.AppID:
                from tmp007 import tmp007app
                app_dict[appID].process = Process(target=tmp007app.tmp007app_main, args=(main_queue, child_pipe))
            elif appID == appargs.ThermalcameraAppArg.AppID:
                from thermal_camera import thermo_cameraapp
                app_dict[appID].process = Process(target=thermo_cameraapp.thermo_cameraapp_main, args=(main_queue, child_pipe))
            elif appID == appargs.MotorAppArg.AppID:
                from motor import motorapp
                app_dict[appID].process = Process(target=motorapp.motorapp_main, args=(main_queue, child_pipe))
            
            # 프로세스 시작
            if app_dict[appID].process:
                app_dict[appID].process.start()
                safe_log(f"Successfully restarted {appID}", "INFO", True)
                return True
            else:
                safe_log(f"Failed to create process for {appID}", "ERROR", True)
                return False
                
        except Exception as e:
            safe_log(f"Restart failed for {appID}: {e}", "ERROR", True)
            return False
    
    try:
        while MAINAPP_RUNSTATUS:
            if time.time() - start_time > max_runtime:
                safe_log("Maximum runtime reached, terminating FSW", "WARNING", True)
                break
            
            # 주기적 프로세스 상태 체크 (10초마다)
            if time.time() - last_health_check > 10:
                last_health_check = time.time()
                
                # 시스템 상태 리포트 생성 (1분마다)
                if int(time.time()) % 60 < 10:  # 매분 처음 10초 동안
                    generate_system_status_report()
                
                # 프로세스 상태 확인 및 재시작
                for appID in app_dict:
                    if app_dict[appID].process and not app_dict[appID].process.is_alive():
                        safe_log(f"Process {appID} is dead, checking restart policy", "WARNING", True)
                        
                        # 중요도별 재시작 정책
                        if appID in critical_apps:
                            safe_log(f"Critical app {appID} is dead, attempting restart", "ERROR", True)
                            if restart_app(appID):
                                safe_log(f"Critical app {appID} restarted successfully", "INFO", True)
                            else:
                                safe_log(f"Critical app {appID} restart failed, system may be unstable", "ERROR", True)
                        elif appID in sensor_apps:
                            safe_log(f"Sensor app {appID} is dead, attempting restart", "WARNING", True)
                            if restart_app(appID):
                                safe_log(f"Sensor app {appID} restarted successfully", "INFO", True)
                            else:
                                safe_log(f"Sensor app {appID} restart failed, continuing without sensor", "WARNING", True)
                        elif appID in non_critical_apps:
                            safe_log(f"Non-critical app {appID} is dead, continuing without restart", "INFO", True)
                        else:
                            safe_log(f"Unknown app {appID} is dead, attempting restart", "WARNING", True)
                            if restart_app(appID):
                                safe_log(f"Unknown app {appID} restarted successfully", "INFO", True)
                            else:
                                safe_log(f"Unknown app {appID} restart failed, continuing", "WARNING", True)
                
            try:
                recv_msg = Main_Queue.get(timeout=0.5)

                if not isinstance(recv_msg, str):
                    safe_log(f"Invalid message type: {type(recv_msg)}", "ERROR", True)
                    continue

                unpacked_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(unpacked_msg, recv_msg):
                    safe_log(f"Failed to unpack message: {recv_msg}", "ERROR", True)
                    continue
                
                # 메인 앱에서 직접 처리할 메시지들
                if unpacked_msg.receiver_app == appargs.MainAppArg.AppID:
                    # 메인 앱으로 직접 전송된 메시지 처리
                    safe_log(f"Main app received message: {unpacked_msg.MsgID} from {unpacked_msg.sender_app}", "DEBUG", True)
                    continue
                
                # 텔레메트리 앱으로의 메시지 (AppID: 3)
                elif unpacked_msg.receiver_app == 3:  # TelemetryAppArg.AppID
                    # 텔레메트리 메시지는 Comm 앱으로 리다이렉트
                    if appargs.CommAppArg.AppID in app_dict:
                        try:
                            if app_dict[appargs.CommAppArg.AppID].pipe and app_dict[appargs.CommAppArg.AppID].process.is_alive():
                                app_dict[appargs.CommAppArg.AppID].pipe.send(unpacked_msg)
                                safe_log(f"Telemetry message redirected to Comm app: {unpacked_msg.MsgID}", "DEBUG", True)
                            else:
                                safe_log(f"Comm app not available for telemetry message: {unpacked_msg.MsgID}", "WARNING", True)
                        except Exception as e:
                            safe_log(f"Failed to redirect telemetry message to Comm app: {e}", "ERROR", True)
                    else:
                        safe_log(f"Comm app not found for telemetry message: {unpacked_msg.MsgID}", "WARNING", True)
                    continue
                
                # 알려진 앱으로의 메시지
                elif unpacked_msg.receiver_app in app_dict:
                    try:
                        if app_dict[unpacked_msg.receiver_app].pipe is None:
                            safe_log(f"Pipe is None for {unpacked_msg.receiver_app}", "ERROR", True)
                            continue
                        
                        if not app_dict[unpacked_msg.receiver_app].process.is_alive():
                            safe_log(f"Process {unpacked_msg.receiver_app} is dead, skipping message", "WARNING", True)
                            continue
                            
                        app_dict[unpacked_msg.receiver_app].pipe.send(unpacked_msg)
                    except BrokenPipeError:
                        safe_log(f"Broken pipe for {unpacked_msg.receiver_app}, attempting restart", "WARNING", True)
                        # 파이프 오류 시 재시작 시도
                        if unpacked_msg.receiver_app in critical_apps or unpacked_msg.receiver_app in sensor_apps:
                            restart_app(unpacked_msg.receiver_app)
                        try:
                            app_dict[unpacked_msg.receiver_app].pipe.close()
                        except Exception as e:
                            safe_log(f"파이프 닫기 오류: {e}", "WARNING")
                    except Exception as e:
                        safe_log(f"Failed to send message to {unpacked_msg.receiver_app}: {e}", "ERROR", True)
                else:
                    # 알 수 없는 receiver app에 대한 처리
                    safe_log(f"Unknown receiver app: {unpacked_msg.receiver_app} (MsgID: {unpacked_msg.MsgID}, Sender: {unpacked_msg.sender_app})", "WARNING", True)
                    
                    # 특정 메시지 타입에 대한 기본 처리
                    if unpacked_msg.MsgID in [appargs.MainAppArg.MID_TerminateProcess]:
                        safe_log(f"Termination message received, but receiver app {unpacked_msg.receiver_app} not found", "WARNING", True)
                    elif unpacked_msg.MsgID in [appargs.HkAppArg.MID_SendHK]:
                        safe_log(f"HK message received, but receiver app {unpacked_msg.receiver_app} not found", "WARNING", True)
                    else:
                        safe_log(f"Unhandled message type {unpacked_msg.MsgID} for unknown receiver {unpacked_msg.receiver_app}", "WARNING", True)
                    continue
            except Exception as e:
                if "Empty" not in str(e):
                    safe_log(f"Main loop error: {e}", "ERROR", True)

    except KeyboardInterrupt:
        safe_log("KeyboardInterrupt Detected, Terminating FSW", "INFO", True)
        MAINAPP_RUNSTATUS = False
        # KeyboardInterrupt 감지됨. 강제 종료합니다.
        
        try:
            for appID in app_dict:
                if app_dict[appID].process and app_dict[appID].process.is_alive():
                    # 강제 종료: {appID}
                    app_dict[appID].process.kill()
        except Exception as e:
            safe_log(f"KeyboardInterrupt에서 프로세스 강제 종료 오류: {e}", "ERROR", True)
        
        os._exit(0)
    except Exception as e:
        safe_log(f"Critical error in main loop: {e}", "ERROR", True)
        MAINAPP_RUNSTATUS = False
        # 치명적 오류 발생. 강제 종료합니다.
        os._exit(0)

    # 정상 종료 완료.
    return


def cleanup_on_exit():
    # 프로그램 종료 시 정리 작업 실행...
    try:
        terminate_FSW()
    except Exception as e:
        safe_log(f"Cleanup on exit 오류: {e}", "ERROR", True)


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
        
        safe_log(
                       f"System Status: {alive_count}/{total_count} processes alive, "
                       f"Memory: {report['memory_usage']['rss_mb']:.1f}MB, "
                       f"Disk: {report['disk_usage'].get('percent', 0):.1f}% used", "INFO", True)
        
        return report
        
    except Exception as e:
        safe_log(f"System status report generation failed: {e}", "ERROR", True)
        return None


if __name__ == '__main__':

    try:
        safe_log("로깅 시스템 초기화 완료", "INFO", True)
    except Exception as e:
        pass  # 로깅 시스템 초기화 실패: {e}

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
            appargs.ThermoAppArg.AppID,
            appargs.Tmp007AppArg.AppID,  # TMP007 센서 앱
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
            appargs.ThermalcameraAppArg.AppID,
            appargs.Tmp007AppArg.AppID
        ]
        
        # 핵심 앱들 시작
        for appID in core_apps:
            if appID in app_dict and app_dict[appID].process is not None:
                try:
                    app_dict[appID].process.start()
                    safe_log(f"Started core process for {appID}", "INFO", True)
                    time.sleep(0.3)  # 더 긴 대기로 안정성 향상
                except Exception as e:
                    if appID in critical_apps:
                        safe_log(f"Critical app {appID} failed to start: {e}", "ERROR", True)
                        # 중요 앱 실패 시에도 계속 진행 (시스템 안정성 우선)
                    else:
                        safe_log(f"Non-critical app {appID} failed to start: {e}", "WARNING", True)
                    continue
        
        # 나머지 앱들 시작
        for appID in app_dict:
            if appID not in core_apps and app_dict[appID].process is not None:
                try:
                    app_dict[appID].process.start()
                    safe_log(f"Started process for {appID}", "INFO", True)
                    time.sleep(0.2)
                except Exception as e:
                    safe_log(f"Failed to start {appID}: {e}", "WARNING", True)
                    continue
                    
    except Exception as e:
        safe_log(f"Error starting processes: {e}", "ERROR", True)
        # 프로세스 시작 실패 시에도 메인 루프는 계속 실행
        pass

    runloop(main_queue)
