# Python FSW V2 Thermo-Camera App
# Author : Hyeon Lee  (HEPHAESTUS)

from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수 - lib/logging.py 사용"""
    try:
        formatted_message = f"[ThermalCamera] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        # 로깅 실패 시에도 최소한 콘솔에 출력
        print(f"[ThermalCamera] 로깅 실패: {e}")
        print(f"[ThermalCamera] 원본 메시지: {message}")

from lib import appargs, msgstructure, logging, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from thermal_camera import thermo_camera as tcam

# ──────────────────────────────
# 0. 글로벌 플래그
# ──────────────────────────────
THERMOCAMAPP_RUNSTATUS = True

# Thermal camera data
THERMAL_AVG = 0.0
THERMAL_MIN = 0.0
THERMAL_MAX = 0.0

# ──────────────────────────────
# 1. 메시지 핸들러
# ──────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure):
    global THERMOCAMAPP_RUNSTATUS

    # (1) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        safe_log("THERMOCAMAPP TERMINATION DETECTED", "info".upper(), True)
        THERMOCAMAPP_RUNSTATUS = False
        return

    # (2) 기타 커맨드는 필요 시 확장
    safe_log(f"MID {recv_msg.MsgID} not handled", "error".upper(), True)

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

        safe_log("Initializing thermocamapp", "info".upper(), True)

        # MLX90640 start (기본 2 Hz)
        i2c, cam = tcam.init_thermal_camera()
        
        safe_log("Thermocamapp initialization complete", "info".upper(), True)
        return i2c, cam

    except Exception as e:
        safe_log(f"Init error: {e}", "error".upper(), True)
        return None, None

def thermocamapp_terminate(i2c):
    """스레드 합류 후 I²C 종료."""
    global THERMOCAMAPP_RUNSTATUS
    THERMOCAMAPP_RUNSTATUS = False

    safe_log("Terminating thermocamapp", "info".upper(), True)

    tcam.terminate_cam(i2c)

    for t in thread_dict.values():
        t.join()

    safe_log("Thermocamapp termination complete", "info".upper(), True)

# ──────────────────────────────
# 4. 센서 읽기 / 데이터 송신
# ──────────────────────────────
MIN_T, MAX_T, AVG_T = 0.0, 0.0, 0.0

def read_cam_data(cam):
    """MLX90640 데이터 읽기 스레드."""
    global THERMOCAMAPP_RUNSTATUS, THERMAL_AVG, THERMAL_MIN, THERMAL_MAX
    while THERMOCAMAPP_RUNSTATUS:
        try:
            # channel_guard를 사용하여 안전하게 센서 읽기
            data = tcam.read_cam(cam)
            if data:
                THERMAL_MIN, THERMAL_MAX, THERMAL_AVG = data  # min, max, avg 순서
        except Exception as e:
            safe_log(f"Thermal camera read error: {e}", "error".upper(), True)
        time.sleep(0.5)  # 2 Hz

def send_cam_data(Main_Queue: Queue):
    global THERMAL_AVG, THERMAL_MIN, THERMAL_MAX
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while THERMOCAMAPP_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.send_msg(Main_Queue, fl_msg,
                              appargs.ThermalcameraAppArg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.ThermalcameraAppArg.MID_SendCamFlightLogicData,
                              f"{THERMAL_AVG:.2f},{THERMAL_MIN:.2f},{THERMAL_MAX:.2f}")

        if cnt > 10:  # 1 Hz telemetry
            msgstructure.send_msg(Main_Queue, tlm_msg,
                                  appargs.ThermalcameraAppArg.AppID,
                                  appargs.CommAppArg.AppID,
                                  appargs.ThermalcameraAppArg.MID_SendCamTlmData,
                                  f"{THERMAL_AVG:.2f},{THERMAL_MIN:.2f},{THERMAL_MAX:.2f}")
            cnt = 0

        cnt += 1
        time.sleep(0.1)  # 10 Hz

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
        safe_log(f"Thread {name} error: {e}", "error".upper(), True)
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
                except Exception as e:
                    # 에러 시 루프 계속
                    safe_log(f"메시지 수신 오류: {e}", "WARNING")
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
                safe_log("Receiver MID mismatch", "error".upper(), True)

    except Exception as e:
        safe_log(f"thermocamapp error: {e}", "error".upper(), True)
        THERMOCAMAPP_RUNSTATUS = False

    thermocamapp_terminate(i2c)
