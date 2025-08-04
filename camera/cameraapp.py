# Python FSW V2 Camera App
# Author : Hyeon Lee  (HEPHAESTUS)
# Raspberry Pi Camera Module v3 Wide 지원

from lib import appargs, msgstructure, logging, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from camera import camera as cam

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
CAMERAAPP_RUNSTATUS = True

# 카메라 상태
CAMERA_STATUS = "IDLE"
VIDEO_COUNT = 0
DISK_USAGE = 0.0

# ──────────────────────────────
# 1. 메시지 핸들러
# ──────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure):
    global CAMERAAPP_RUNSTATUS, CAMERA_STATUS

    # (1) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.info,
                        "CAMERAAPP TERMINATION DETECTED")
        CAMERAAPP_RUNSTATUS = False
        return

    # (2) FlightLogic에서 카메라 활성화 명령
    elif recv_msg.MsgID == appargs.CameraAppArg.MID_CameraActivate:
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.info,
                        "Camera activation command received")
        if cam.start_recording():
            CAMERA_STATUS = "RECORDING"
        else:
            CAMERA_STATUS = "ERROR"
        return

    # (3) FlightLogic에서 카메라 비활성화 명령
    elif recv_msg.MsgID == appargs.CameraAppArg.MID_CameraDeactivate:
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.info,
                        "Camera deactivation command received")
        if cam.stop_recording():
            CAMERA_STATUS = "IDLE"
        else:
            CAMERA_STATUS = "ERROR"
        return

    # (4) 기타 커맨드는 필요 시 확장
    events.LogEvent(appargs.CameraAppArg.AppName,
                    events.EventType.error,
                    f"MID {recv_msg.MsgID} not handled")

# ──────────────────────────────
# 2. HK 송신 스레드
# ──────────────────────────────
def send_hk(Main_Queue: Queue):
    while CAMERAAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, hk,
                              appargs.CameraAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.CameraAppArg.MID_SendHK,
                              str(CAMERAAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────
# 3. 초기화 / 종료
# ──────────────────────────────
def cameraapp_init():
    """카메라 초기화."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.info,
                        "Initializing cameraapp")

        # 카메라 초기화
        if not cam.init_camera():
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           "Camera initialization failed")
            return False
        
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.info,
                        "Cameraapp initialization complete")
        return True

    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.error,
                        f"Init error: {e}")
        return False

def cameraapp_terminate():
    """카메라 종료."""
    global CAMERAAPP_RUNSTATUS
    CAMERAAPP_RUNSTATUS = False

    events.LogEvent(appargs.CameraAppArg.AppName,
                    events.EventType.info,
                    "Terminating cameraapp")

    # 카메라 종료
    cam.terminate_camera()

    # 스레드 종료 대기
    for t in thread_dict.values():
        t.join()

    events.LogEvent(appargs.CameraAppArg.AppName,
                    events.EventType.info,
                    "Cameraapp termination complete")

# ──────────────────────────────
# 4. 상태 모니터링 / 데이터 송신
# ──────────────────────────────
def update_camera_status():
    """카메라 상태 업데이트 스레드."""
    global CAMERA_STATUS, VIDEO_COUNT, DISK_USAGE
    
    while CAMERAAPP_RUNSTATUS:
        try:
            # 카메라 상태 가져오기
            status = cam.get_camera_status()
            disk_info = cam.get_disk_usage()
            
            # 상태 업데이트
            if status['active']:
                CAMERA_STATUS = "RECORDING"
            else:
                CAMERA_STATUS = "IDLE"
            
            VIDEO_COUNT = status['video_count']
            DISK_USAGE = disk_info['usage_percent']
            
        except Exception as e:
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           f"Status update error: {e}")
        
        time.sleep(1)  # 1초마다 업데이트

def send_camera_data(Main_Queue: Queue):
    """카메라 데이터 송신 스레드."""
    global CAMERA_STATUS, VIDEO_COUNT, DISK_USAGE
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while CAMERAAPP_RUNSTATUS:
        try:
            # FlightLogic 5 Hz
            msgstructure.send_msg(Main_Queue, fl_msg,
                                  appargs.CameraAppArg.AppID,
                                  appargs.FlightlogicAppArg.AppID,
                                  appargs.CameraAppArg.MID_SendCameraFlightLogicData,
                                  f"{CAMERA_STATUS},{VIDEO_COUNT},{DISK_USAGE:.1f}")

            if cnt >= 5:  # 1 Hz telemetry
                msgstructure.send_msg(Main_Queue, tlm_msg,
                                      appargs.CameraAppArg.AppID,
                                      appargs.CommAppArg.AppID,
                                      appargs.CameraAppArg.MID_SendCameraTlmData,
                                      f"{CAMERA_STATUS},{VIDEO_COUNT},{DISK_USAGE:.1f}")
                cnt = 0

            cnt += 1
            time.sleep(0.2)  # 5 Hz

        except Exception as e:
            events.LogEvent(appargs.CameraAppArg.AppName,
                           events.EventType.error,
                           f"Data send error: {e}")
            time.sleep(1)

# ──────────────────────────────
# 5. 메인 엔트리
# ──────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

def cameraapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global CAMERAAPP_RUNSTATUS
    CAMERAAPP_RUNSTATUS = True

    # 초기화
    if not cameraapp_init():
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.error,
                        "Cameraapp initialization failed")
        return

    # 스레드 생성
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(Main_Queue,),
                                         name="HKSender_Thread", daemon=True)
    thread_dict["STATUS"] = threading.Thread(target=update_camera_status,
                                             name="StatusUpdate_Thread", daemon=True)
    thread_dict["SEND"] = threading.Thread(target=send_camera_data, args=(Main_Queue,),
                                           name="SendCameraData_Thread", daemon=True)

    # 스레드 시작
    for t in thread_dict.values():
        t.start()

    try:
        while CAMERAAPP_RUNSTATUS:
            # Non-blocking receive with timeout
            if Main_Pipe.poll(1.0):  # 1초 타임아웃
                try:
                    raw = Main_Pipe.recv()
                except:
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            
            m = msgstructure.MsgStructure()
            if not msgstructure.unpack_msg(m, raw):
                continue

            target_apps = (appargs.CameraAppArg.AppID, appargs.MainAppArg.AppID)
            if m.receiver_app in target_apps:
                command_handler(Main_Queue, m)
            else:
                events.LogEvent(appargs.CameraAppArg.AppName,
                                events.EventType.error,
                                "Receiver MID mismatch")

    except Exception as e:
        events.LogEvent(appargs.CameraAppArg.AppName,
                        events.EventType.error,
                        f"cameraapp error: {e}")
        CAMERAAPP_RUNSTATUS = False

    cameraapp_terminate() 