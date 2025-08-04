# Python FSW V2 Thermo-Camera App
# Author : Hyeon Lee  (HEPHAESTUS)

from lib import appargs, msgstructure, logging, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from thermal_camera import thermo_camera as tcam

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
THERMOCAMAPP_RUNSTATUS = True
# MLX90640 는 별도 오프셋 필요 없음 → 락도 생략
THERMOCAM_MUX = None  # MUX instance for channel 4

# ──────────────────────────────
# 1. 메시지 핸들러
# ──────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure):
    global THERMOCAMAPP_RUNSTATUS

    # (1) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.info,
                        "THERMOCAMAPP TERMINATION DETECTED")
        THERMOCAMAPP_RUNSTATUS = False
        return

    # (2) 기타 커맨드는 필요 시 확장
    events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                    events.EventType.error,
                    f"MID {recv_msg.MsgID} not handled")

# ──────────────────────────────
# 2. HK 송신 스레드
# ──────────────────────────────
def send_hk(Main_Queue: Queue):
    while THERMOCAMAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, hk,
                              appargs.ThermalcameraAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermalcameraAppArg.MID_SendHK,
                              str(THERMOCAMAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────
# 3. 초기화 / 종료
# ──────────────────────────────
def thermocamapp_init():
    """센서 초기화·시리얼 확인."""
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.info,
                        "Initializing thermocamapp")

        # MLX90640 start (기본 2 Hz)
        i2c, cam, mux = tcam.init_cam(refresh_hz=2)
        
        # Store MUX instance globally for proper channel management
        global THERMOCAM_MUX
        THERMOCAM_MUX = mux

        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.info,
                        "Thermocamapp initialization complete")
        return i2c, cam

    except Exception as e:
        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.error,
                        f"Init error: {e}")
        return None, None

def thermocamapp_terminate(i2c):
    """스레드 합류 후 I²C 종료."""
    global THERMOCAMAPP_RUNSTATUS, THERMOCAM_MUX
    THERMOCAMAPP_RUNSTATUS = False

    events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                    events.EventType.info,
                    "Terminating thermocamapp")

    # Close MUX connection
    if THERMOCAM_MUX:
        try:
            THERMOCAM_MUX.close()
        except Exception as e:
            events.LogEvent(appargs.ThermalcameraAppArg.AppName, events.EventType.error, f"MUX 종료 오류: {e}")

    tcam.terminate_cam(i2c)

    for t in thread_dict.values():
        t.join()

    events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                    events.EventType.info,
                    "Thermocamapp termination complete")

# ──────────────────────────────
# 4. 센서 읽기 / 데이터 송신
# ──────────────────────────────
MIN_T, MAX_T, AVG_T = 0.0, 0.0, 0.0

def read_cam_data(cam):
    """MLX90640 데이터 읽기 스레드."""
    global THERMOCAMAPP_RUNSTATUS, THERMOCAM_MUX
    while THERMOCAMAPP_RUNSTATUS:
        try:
            # channel_guard를 사용하여 안전하게 센서 읽기
            with THERMOCAM_MUX.channel_guard(5):  # 🔒 채널 5 점유
                data = tcam.read_cam(cam)
                if data:
                    global THERMAL_AVG, THERMAL_MIN, THERMAL_MAX
                    THERMAL_AVG, THERMAL_MIN, THERMAL_MAX = data
        except Exception as e:
            events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                            events.EventType.error,
                            f"Thermal camera read error: {e}")
        time.sleep(0.5)  # 2 Hz

def send_cam_data(Main_Queue: Queue):
    global MIN_T, MAX_T, AVG_T

    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()
    cnt = 0
    while THERMOCAMAPP_RUNSTATUS:
        # ① FlightLogic (10 Hz): "avg,min,max"
        # msgstructure.send_msg(Main_Queue, fl_msg,
        #                       appargs.ThermalcameraAppArg.AppID,
        #                       appargs.FlightlogicAppArg.AppID,
        #                       appargs.ThermalcameraAppArg.MID_SendCamFlightLogicData,
        #                       f"{AVG_T},{MIN_T},{MAX_T}")

        # ② COMM (1 Hz)
        status = msgstructure.send_msg(Main_Queue, tlm_msg,
                                           appargs.ThermalcameraAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.ThermalcameraAppArg.MID_SendCamTlmData,
                                           f"{AVG_T},{MIN_T},{MAX_T}")
        if not status:
            events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                            events.EventType.error,
                            "Error sending ThermoCam TLM")

        time.sleep(0.1)

# ──────────────────────────────
# 5. 메인 엔트리
# ──────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

# 스레드 자동 재시작 래퍼
import threading

def resilient_thread(target, args=(), name=None):
    try:
        target(*args)
    except Exception as e:
        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.error,
                        f"Thread {name} error: {e}")
    return None

def thermocamapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global THERMOCAMAPP_RUNSTATUS
    THERMOCAMAPP_RUNSTATUS = True

    i2c, cam = thermocamapp_init()
    if cam is None:
        return  # 초기화 실패 시 바로 종료

    # 스레드 생성
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(Main_Queue,),
                                         name="HKSender_Thread", daemon=True)
    thread_dict["READ"] = threading.Thread(target=read_cam_data, args=(cam,),
                                           name="ReadCamData_Thread", daemon=True)
    thread_dict["SEND"] = threading.Thread(target=send_cam_data, args=(Main_Queue,),
                                           name="SendCamData_Thread", daemon=True)

    for t in thread_dict.values():
        t.start()

    try:
        while THERMOCAMAPP_RUNSTATUS:
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

            target_apps = (appargs.ThermalcameraAppArg.AppID, appargs.MainAppArg.AppID)
            if m.receiver_app in target_apps:
                command_handler(Main_Queue, m)
            else:
                events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                                events.EventType.error,
                                "Receiver MID mismatch")

    except Exception as e:
        events.LogEvent(appargs.ThermalcameraAppArg.AppName,
                        events.EventType.error,
                        f"thermocamapp error: {e}")
        THERMOCAMAPP_RUNSTATUS = False

    thermocamapp_terminate(i2c)
