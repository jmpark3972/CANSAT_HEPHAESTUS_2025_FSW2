# Main Flight Software Code for Cansat Mission
# Author : Hyeon Lee

print("=== MAIN.PY IS RUNNING ===")

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
from lib import appargs, msgstructure, types, config, prevstate
from lib import safe_log, LogRotator

# Multiprocessing Library is used on Python FSW V2
# Each application should have its own runloop
# Import the application and execute the runloop here.

from multiprocessing import Process, Queue, Pipe, connection

# Load configuration files
from lib import resource_manager

def main_safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        safe_log(message, level, printlogs, appargs.MainAppArg.AppName)
    except Exception as e:
        print(f"[MAIN] 로깅 실패: {e}")
        print(f"[MAIN] 원본 메시지: {message}")

# 리소스 모니터링 시작
resource_manager.start_resource_monitoring()

# 로그 로테이션 초기화
log_rotator = LogRotator(max_size_mb=10, max_age_days=30)

if config.get_config("FSW_MODE") == "NONE":
    main_safe_log("CONFIG IS SELECTED AS NONE, TERMINATING FSW", "ERROR", True)
    sys.exit(0)

main_queue = Queue()

class app_elements:
    process : Process = None
    pipe : connection.Connection = None
    last_heartbeat : float = 0.0
    failure_count : int = 0
    is_healthy : bool = True
    restart_attempts : int = 0
    max_restart_attempts : int = 3

app_dict: dict[types.AppID, app_elements] = {}

# 앱 상태 모니터링
app_health_status = {}
app_failure_threshold = 5  # 5초 동안 응답 없으면 비정상으로 간주
app_restart_cooldown = 30  # 재시작 후 30초 대기

def monitor_app_health(): """앱 상태 모니터링 및 로깅"""
    
    global app_health_status
    
    current_time = time.time()
    
    for app_id, app_elem in app_dict.items():
        try:
            # 프로세스 상태 확인
            if app_elem.process and app_elem.process.is_alive():
                app_elem.is_healthy = True
                app_elem.last_heartbeat = current_time
                app_elem.failure_count = 0
            else:
                app_elem.is_healthy = False
                app_elem.failure_count += 1
                
                # 실패 로그 (빈도 제한)
                if app_elem.failure_count == 1 or app_elem.failure_count % 10 == 0:
                    main_safe_log(f"App {app_id} is not responding (failure count: {app_elem.failure_count})", "WARNING", True)
            
            # 앱 상태 업데이트
            app_health_status[app_id] = {
                'healthy': app_elem.is_healthy,
                'failure_count': app_elem.failure_count,
                'last_heartbeat': app_elem.last_heartbeat,
                'restart_attempts': app_elem.restart_attempts
            }
            
        except Exception as e:
            main_safe_log(f"App health monitoring error for {app_id}: {e}", "ERROR", True)

def log_system_status(): """시스템 상태 로깅"""
   
    try:
        healthy_apps = sum(1 for app_elem in app_dict.values() if app_elem.is_healthy)
        total_apps = len(app_dict)
        
        status_msg = f"System Status - Healthy: {healthy_apps}/{total_apps} apps"
        
        # 비정상 앱 목록
        unhealthy_apps = [app_id for app_id, app_elem in app_dict.items() if not app_elem.is_healthy]
        if unhealthy_apps:
            status_msg += f", Unhealthy: {unhealthy_apps}"
        
        main_safe_log(status_msg, "INFO", True)
        
        # 개별 앱 상태 로깅 (디버그 레벨)
        for app_id, app_elem in app_dict.items():
            if not app_elem.is_healthy:
                main_safe_log(f"App {app_id}: failures={app_elem.failure_count}, restart_attempts={app_elem.restart_attempts}", "DEBUG", True)
                
    except Exception as e:
        main_safe_log(f"System status logging error: {e}", "ERROR", True)

def terminate_FSW(): # FSW 종료
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        return  # Already terminating
    _termination_in_progress = True
    
    MAINAPP_RUNSTATUS = False

    try:
        # 리소스 모니터링 중지
        resource_manager.stop_resource_monitoring()
        main_safe_log("리소스 모니터링 중지 완료", "INFO", True)
        
        # 로그 로테이션 실행
        log_rotator.rotate_logs()
        main_safe_log("로그 로테이션 완료", "INFO", True)
        
        # 로깅 시스템 정리
        # 통합 로깅 시스템은 자동으로 정리됨
        main_safe_log("로깅 시스템 정리 완료", "INFO", True)
    except Exception as e:
        main_safe_log(f"시스템 정리 실패: {e}", "ERROR", True)

    termination_message = msgstructure.MsgStructure()
    msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
    termination_message_to_send = msgstructure.pack_msg(termination_message)

    # 종료 메시지 전송
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            main_safe_log(f"Terminating AppID {appID}", "INFO", True)
            try:
                app_dict[appID].pipe.send(termination_message_to_send)
            except Exception as e:
                main_safe_log(f"Failed to send termination to {appID}: {e}", "ERROR", True)
    
    time.sleep(0.5)

    # 프로세스 종료
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            main_safe_log(f"Joining AppID {appID}", "INFO", True)
            try:
                main_safe_log(f"Force terminating AppID {appID}", "WARNING", True)
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1)
                if app_dict[appID].process.is_alive():
                    main_safe_log(f"Force killing AppID {appID}", "WARNING", True)
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=0.5)
                main_safe_log(f"Terminating AppID {appID} complete", "INFO", True)
            except Exception as e:
                main_safe_log(f"Error joining {appID}: {e}", "ERROR", True)
                try:
                    app_dict[appID].process.kill()
                except Exception as kill_error:
                    main_safe_log(f"프로세스 강제 종료 중 오류: {kill_error}", "ERROR", True)

    main_safe_log(f"Manual termination! Resetting prev state file", "INFO", True)
    prevstate.reset_prevstate()
    
    main_safe_log(f"All Termination Process complete, terminating FSW", "INFO", True)
    
    try:
        # 추가 정리 작업
        pass
    except Exception as e:
        main_safe_log(f"Child process cleanup error: {e}", "ERROR", True)

def signal_handler(signum, frame):
    """시그널 핸들러"""
    main_safe_log(f"Signal {signum} received, terminating FSW", "INFO", True)
    terminate_FSW()
    sys.exit(0)

# 시그널 핸들러 등록
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# 종료 시 정리 함수 등록
atexit.register(terminate_FSW)

def cleanup_child_processes():  """자식 프로세스 정리"""
   
    try:
        for appID in app_dict:
            if app_dict[appID].process and app_dict[appID].process.is_alive():
                try:
                    app_dict[appID].process.terminate()
                    app_dict[appID].process.join(timeout=1)
                    if app_dict[appID].process.is_alive():
                        app_dict[appID].process.kill()
                        app_dict[appID].process.join(timeout=0.5)
                except Exception as e:
                    main_safe_log(f"자식 프로세스 종료 실패: {e}", "WARNING", False)
    except Exception as e:
        main_safe_log(f"자식 프로세스 정리 실패: {e}", "ERROR", True)

def cleanup_queues():
    """큐 정리"""
    try:
        # 메인 큐 정리
        while not main_queue.empty():
            try:
                main_queue.get_nowait()
            except:
                break
        main_safe_log("큐 정리 완료", "INFO", False)
    except Exception as e:
        main_safe_log(f"큐 정리 실패: {e}", "WARNING", False)

def restart_app(appID): # 강제 종료 시 앱 재시작
    try:
        app_elem = app_dict[appID]
        
        # 재시작 시도 횟수 체크
        if app_elem.restart_attempts >= app_elem.max_restart_attempts:
            main_safe_log(f"App {appID} exceeded max restart attempts ({app_elem.max_restart_attempts}), skipping restart", "WARNING", True)
            return False
        
        # 재시작 쿨다운 체크
        current_time = time.time()
        if hasattr(app_elem, 'last_restart_time') and current_time - app_elem.last_restart_time < app_restart_cooldown:
            main_safe_log(f"App {appID} in restart cooldown, skipping restart", "DEBUG", True)
            return False
        
        main_safe_log(f"Attempting to restart app {appID} (attempt {app_elem.restart_attempts + 1}/{app_elem.max_restart_attempts})", "INFO", True)
        
        # 기존 프로세스 종료
        if app_elem.process and app_elem.process.is_alive():
            try:
                app_elem.process.terminate()
                app_elem.process.join(timeout=1)
                if app_elem.process.is_alive():
                    app_elem.process.kill()
                    app_elem.process.join(timeout=0.5)
            except Exception as e:
                main_safe_log(f"Failed to terminate {appID}: {e}", "WARNING", True)
        
        # 파이프 정리
        try:
            if app_elem.pipe:
                app_elem.pipe.close()
        except Exception as e:
            main_safe_log(f"Pipe close error for {appID}: {e}", "WARNING", True)
        
        # 앱 재시작 로직 (load_apps에서 사용하는 것과 동일)
        try:
            # 앱 정의에서 해당 앱 찾기
            apps_to_load = [
                ("hk.hkapp", "HKApp", appargs.HkAppArg.AppID),
                ("barometer.barometerapp", "BarometerApp", appargs.BarometerAppArg.AppID),
                ("gps.gpsapp", "GpsApp", appargs.GpsAppArg.AppID),
                ("imu.imuapp", "ImuApp", appargs.ImuAppArg.AppID),
                ("flight_logic.flightlogicapp", "FlightLogicApp", appargs.FlightlogicAppArg.AppID),
                ("comm.commapp", "CommApp", appargs.CommAppArg.AppID),
                ("motor.motorapp", "MotorApp", appargs.MotorAppArg.AppID),
                ("fir1.firapp1", "FirApp1", appargs.FirApp1Arg.AppID),
                ("thermis.thermisapp", "ThermisApp", appargs.ThermisAppArg.AppID),
                ("tmp007.tmp007app", "Tmp007App", appargs.Tmp007AppArg.AppID),
                ("thermo.thermoapp", "ThermoApp", appargs.ThermoAppArg.AppID),
            ]
            
            app_info = None
            for module_path, class_name, app_id in apps_to_load:
                if app_id == appID:
                    app_info = (module_path, class_name, app_id)
                    break
            
            if app_info:
                module_path, class_name, app_id = app_info
                
                # 모듈 동적 임포트
                module = __import__(module_path, fromlist=[class_name])
                app_class = getattr(module, class_name)
                
                # 앱 인스턴스 생성
                app_instance = app_class()
                
                # 프로세스 및 파이프 생성
                parent_pipe, child_pipe = Pipe()
                
                app_elem.process = Process(target=app_instance.start, args=(main_queue, child_pipe))
                app_elem.pipe = parent_pipe
                
                # 프로세스 시작
                app_elem.process.start()
                time.sleep(0.2)  # 프로세스 시작 대기
                
                # 재시작 정보 업데이트
                app_elem.restart_attempts += 1
                app_elem.last_restart_time = current_time
                app_elem.failure_count = 0
                app_elem.is_healthy = True
                app_elem.last_heartbeat = current_time
                
                main_safe_log(f"Successfully restarted {appID}", "INFO", True)
                return True
            else:
                main_safe_log(f"App {appID} not found in app definitions", "ERROR", True)
                return False
                
        except Exception as e:
            main_safe_log(f"Failed to restart {appID}: {e}", "ERROR", True)
            return False
            
    except Exception as e:
        main_safe_log(f"Restart failed for {appID}: {e}", "ERROR", True)
        return False

def load_apps(): # 앱 로드 및 프로세스 시작
    try:
        main_safe_log("load_apps() 함수 시작", "INFO", True)
        
        # 앱 정의 (모듈명, 클래스명, AppID)
        apps_to_load = [
            ("hk.hkapp", "HKApp", appargs.HkAppArg.AppID),
            ("barometer.barometerapp", "BarometerApp", appargs.BarometerAppArg.AppID),
            ("gps.gpsapp", "GpsApp", appargs.GpsAppArg.AppID),
            ("imu.imuapp", "ImuApp", appargs.ImuAppArg.AppID),
            ("flight_logic.flightlogicapp", "FlightLogicApp", appargs.FlightlogicAppArg.AppID),
            ("comm.commapp", "CommApp", appargs.CommAppArg.AppID),
            ("motor.motorapp", "MotorApp", appargs.MotorAppArg.AppID),
            ("fir1.firapp1", "FirApp1", appargs.FirApp1Arg.AppID),
            ("thermis.thermisapp", "ThermisApp", appargs.ThermisAppArg.AppID),
            ("tmp007.tmp007app", "Tmp007App", appargs.Tmp007AppArg.AppID),
            ("thermo.thermoapp", "ThermoApp", appargs.ThermoAppArg.AppID),
        ]

        main_safe_log(f"로드할 앱 수: {len(apps_to_load)}", "INFO", True)

        for module_path, class_name, app_id in apps_to_load:
            try:
                main_safe_log(f"{class_name} 앱 로드 시도 중...", "INFO", True)
                
                # 모듈 동적 임포트
                module = __import__(module_path, fromlist=[class_name])
                app_class = getattr(module, class_name)
                
                # 앱 인스턴스 생성
                app_instance = app_class()
                
                # 프로세스 및 파이프 생성
                parent_pipe, child_pipe = Pipe()
                
                app_elements_instance = app_elements()
                app_elements_instance.process = Process(target=app_instance.start, args=(main_queue, child_pipe))
                app_elements_instance.pipe = parent_pipe
                app_elements_instance.last_heartbeat = time.time()
                
                # 앱 딕셔너리에 추가
                app_dict[app_id] = app_elements_instance
                
                main_safe_log(f"{class_name} 앱 로드 완료", "INFO", True)
                
            except Exception as e:
                main_safe_log(f"{class_name} 앱 로드 실패: {e}", "ERROR", True)

        main_safe_log(f"앱 딕셔너리 크기: {len(app_dict)}", "INFO", True)

        # 모든 앱 프로세스 시작
        main_safe_log("모든 앱 프로세스 시작 중...", "INFO", True)
        for app_id, app_elem in app_dict.items():
            try:
                if app_elem.process and not app_elem.process.is_alive():
                    app_elem.process.start()
                    main_safe_log(f"{app_id} 프로세스 시작 완료", "INFO", True)
                    time.sleep(0.2)  # 프로세스 시작 간격
            except Exception as e:
                main_safe_log(f"{app_id} 프로세스 시작 실패: {e}", "ERROR", True)

        main_safe_log("모든 앱 로드 및 프로세스 시작 완료", "INFO", True)

    except Exception as e:
        main_safe_log(f"load_apps() 함수에서 예외 발생: {e}", "ERROR", True)
        import traceback
        main_safe_log(f"예외 상세: {traceback.format_exc()}", "ERROR", True)

def runloop(Main_Queue : Queue): # 메인 루프
    global MAINAPP_RUNSTATUS
    
    start_time = time.time()
    max_runtime = 3600  # 1시간
    last_health_check = time.time()
    last_status_log = time.time()
    health_check_interval = 5.0  # 5초마다 앱 상태 체크
    status_log_interval = 30.0   # 30초마다 시스템 상태 로깅
    
    while MAINAPP_RUNSTATUS:
        try:
            # 최대 실행 시간 체크
            if time.time() - start_time > max_runtime:
                main_safe_log("Maximum runtime reached, terminating FSW", "WARNING", True)
                break
            
            current_time = time.time()
            
            # 주기적 앱 상태 모니터링
            if current_time - last_health_check >= health_check_interval:
                monitor_app_health()
                last_health_check = current_time
            
            # 주기적 시스템 상태 로깅
            if current_time - last_status_log >= status_log_interval:
                log_system_status()
                last_status_log = current_time
            
            # 메시지 처리
            try:
                recv_msg = Main_Queue.get(timeout=0.1)
            except:
                continue
            
            # 메시지 타입 체크 및 변환
            if isinstance(recv_msg, str):
                # 문자열 메시지를 바이트로 변환
                try:
                    recv_msg = recv_msg.encode('utf-8')
                    main_safe_log(f"문자열 메시지를 바이트로 변환: {recv_msg[:50]}...", "DEBUG", True)
                except Exception as e:
                    main_safe_log(f"문자열을 바이트로 변환 실패: {e}", "ERROR", True)
                    continue
            elif not isinstance(recv_msg, bytes):
                main_safe_log(f"지원하지 않는 메시지 타입: {type(recv_msg)}", "ERROR", True)
                continue
            
            # 메시지 언패킹
            try:
                unpacked_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(unpacked_msg, recv_msg.decode('utf-8')):
                    main_safe_log(f"메시지 언패킹 실패: 잘못된 메시지 형식", "WARNING", True)
                    main_safe_log(f"메시지 내용: {recv_msg[:100]}...", "DEBUG", True)
                    continue
            except Exception as e:
                main_safe_log(f"메시지 언패킹 실패: {e}", "WARNING", True)
                main_safe_log(f"메시지 내용: {recv_msg[:100]}...", "DEBUG", True)
                continue
            
            main_safe_log(f"Main app received message: {unpacked_msg.MsgID} from {unpacked_msg.sender_app}", "DEBUG", True)
            
            # 메시지 라우팅
            if unpacked_msg.receiver_app == appargs.CommAppArg.AppID:
                # 텔레메트리 메시지를 Comm 앱으로 리다이렉트
                try:
                    if appargs.CommAppArg.AppID in app_dict and app_dict[appargs.CommAppArg.AppID].pipe:
                        app_dict[appargs.CommAppArg.AppID].pipe.send(recv_msg)
                        main_safe_log(f"Telemetry message redirected to Comm app: {unpacked_msg.MsgID}", "DEBUG", True)
                    else:
                        main_safe_log(f"Comm app not available for telemetry message: {unpacked_msg.MsgID}", "WARNING", True)
                except Exception as e:
                    main_safe_log(f"Failed to redirect telemetry message to Comm app: {e}", "ERROR", True)
                except:
                    main_safe_log(f"Comm app not found for telemetry message: {unpacked_msg.MsgID}", "WARNING", True)
            else:
                # 일반 메시지 처리
                if unpacked_msg.receiver_app in app_dict:
                    app_elem = app_dict[unpacked_msg.receiver_app]
                    
                    if app_elem.pipe is None:
                        main_safe_log(f"Pipe is None for {unpacked_msg.receiver_app}", "ERROR", True)
                        continue
                    
                    if not app_elem.process.is_alive():
                        # 앱이 죽어있으면 재시작 시도
                        main_safe_log(f"Process {unpacked_msg.receiver_app} is dead, attempting restart", "WARNING", True)
                        if restart_app(unpacked_msg.receiver_app):
                            # 재시작 성공 시 메시지 전송 재시도
                            try:
                                app_elem.pipe.send(recv_msg)
                                main_safe_log(f"Message sent to restarted app {unpacked_msg.receiver_app}", "INFO", True)
                            except Exception as e:
                                main_safe_log(f"Failed to send message to restarted app {unpacked_msg.receiver_app}: {e}", "ERROR", True)
                        continue
                    
                    try:
                        app_elem.pipe.send(recv_msg)
                        # 성공적인 메시지 전송 시 앱 상태 업데이트
                        app_elem.last_heartbeat = current_time
                        app_elem.is_healthy = True
                        app_elem.failure_count = 0
                    except BrokenPipeError:
                        main_safe_log(f"Broken pipe for {unpacked_msg.receiver_app}, attempting restart", "WARNING", True)
                        restart_app(unpacked_msg.receiver_app)
                    except Exception as e:
                        try:
                            app_elem.pipe.close()
                        except:
                            pass
                        main_safe_log(f"파이프 닫기 오류: {e}", "WARNING")
                        main_safe_log(f"Failed to send message to {unpacked_msg.receiver_app}: {e}", "ERROR", True)
                        
                        # 메시지 전송 실패 시 앱 상태 업데이트
                        app_elem.failure_count += 1
                        if app_elem.failure_count >= app_failure_threshold:
                            app_elem.is_healthy = False
                else:
                    main_safe_log(f"Unknown receiver app: {unpacked_msg.receiver_app} (MsgID: {unpacked_msg.MsgID}, Sender: {unpacked_msg.sender_app})", "WARNING", True)
                    
                    # 특별한 메시지 타입 처리
                    if unpacked_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
                        main_safe_log(f"Termination message received, but receiver app {unpacked_msg.receiver_app} not found", "WARNING", True)
                    elif unpacked_msg.MsgID == appargs.HkAppArg.MID_Housekeeping:
                        main_safe_log(f"HK message received, but receiver app {unpacked_msg.receiver_app} not found", "WARNING", True)
                    elif unpacked_msg.MsgID == appargs.MainAppArg.MID_SendHK:
                        # CommApp에서 보낸 디버그 상태 메시지 처리
                        if unpacked_msg.data == "DEBUG_ON":
                            main_safe_log("🔍 DEBUG MODE ENABLED - CommApp debug output will be shown", "INFO", True)
                        elif unpacked_msg.data == "DEBUG_OFF":
                            main_safe_log("🔍 DEBUG MODE DISABLED - CommApp debug output hidden", "INFO", True)
                    else:
                        main_safe_log(f"Unhandled message type {unpacked_msg.MsgID} for unknown receiver {unpacked_msg.receiver_app}", "WARNING", True)
            
        except Exception as e:
            main_safe_log(f"Main loop error: {e}", "ERROR", True)
            time.sleep(0.1)
    
    main_safe_log("Main loop terminated", "INFO", True)

def main(): # 메인 함수
    try:
        main_safe_log("CANSAT HEPHAESTUS 2025 FSW2 시작", "INFO", True)
        
        # 앱 로드
        main_safe_log("load_apps() 호출 시작", "INFO", True)
        load_apps()
        main_safe_log("load_apps() 호출 완료", "INFO", True)
        
        # 메인 루프 실행
        main_safe_log("runloop() 호출 시작", "INFO", True)
        runloop(main_queue)
        main_safe_log("runloop() 호출 완료", "INFO", True)
        
    except KeyboardInterrupt:
        main_safe_log("KeyboardInterrupt Detected, Terminating FSW", "INFO", True)
    except Exception as e:
        main_safe_log(f"main() 함수에서 예외 발생: {e}", "ERROR", True)
        import traceback
        main_safe_log(f"예외 상세: {traceback.format_exc()}", "ERROR", True)
        try:
            cleanup_child_processes()
        except Exception as cleanup_error:
            main_safe_log(f"KeyboardInterrupt에서 프로세스 강제 종료 오류: {e}", "ERROR", True)
        main_safe_log(f"Critical error in main loop: {e}", "ERROR", True)
    finally:
        try:
            cleanup_queues()
            cleanup_child_processes()
        except Exception as e:
            main_safe_log(f"Cleanup on exit 오류: {e}", "ERROR", True)
        
        main_safe_log("CANSAT HEPHAESTUS 2025 FSW2 종료", "INFO", True)

if __name__ == "__main__":
    main()
