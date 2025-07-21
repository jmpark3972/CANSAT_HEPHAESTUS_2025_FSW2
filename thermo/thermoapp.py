# Python FSW V2 Thermo App
# Author : Hyeon Lee  (HEPHAESTUS)
import board, busio
from lib import appargs, msgstructure, logging, events, types, prevstate
import signal
from multiprocessing import Queue, connection
import threading, time

from thermo import thermo   # ★ 앞서 만든 thermo.py 모듈

# ────────────────────────────────────────────────
# 0) 전역 스위치 & 락
# ────────────────────────────────────────────────
THERMOAPP_RUNSTATUS = True

# 센서 보정(Offset) 갱신 시 동시 접근 방지
OFFSET_MUTEX = threading.Lock()

# 보정 직후 잘못된 데이터 송신 방지
RESET_MUTEX = threading.Lock()
THERMO_OFFSET = getattr(prevstate, "PREV_THERMO_TOFF", 0.0)
# ────────────────────────────────────────────────
# 1) 기본 메시지 핸들러
# ────────────────────────────────────────────────
def command_handler(Main_Queue: Queue,
                    recv_msg: msgstructure.MsgStructure,
                    dht_device):
    global THERMOAPP_RUNSTATUS, TEMP_OFFSET, HUMI_OFFSET

    # 1-A) 프로세스 종료
    if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                        "THERMOAPP TERMINATION DETECTED")
        THERMOAPP_RUNSTATUS = False
        return

    # 1-B) 센서 보정(CAL) : “tempOffset,humOffset” 두 실수
    if recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            temp_off, hum_off = map(float, recv_msg.data.split(","))
        except Exception:
            events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                            "CAL cmd parsing error")
            return

        with OFFSET_MUTEX:
            TEMP_OFFSET, HUMI_OFFSET = temp_off, hum_off

        # FLIGHTLOGIC 쪽에 “리셋됐음” 알리기(Optional)
        with RESET_MUTEX:
            ResetThermoCmd = msgstructure.MsgStructure()
            msgstructure.send_msg(Main_Queue, ResetThermoCmd,
                                  appargs.ThermoAppArg.AppID,
                                  appargs.FlightlogicAppArg.AppID,
                                  appargs.ThermoAppArg.MID_ResetThermoCal, "")
            time.sleep(0.5)

        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                        f"Thermo offset set to T={TEMP_OFFSET}, H={HUMI_OFFSET}")
        prevstate.update_thermocal(TEMP_OFFSET, HUMI_OFFSET)
        return

    events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                    f"MID {recv_msg.MsgID} not handled")

# ────────────────────────────────────────────────
# 2) HK 송신 스레드
# ────────────────────────────────────────────────
def send_hk(Main_Queue: Queue):
    global THERMOAPP_RUNSTATUS
    while THERMOAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(Main_Queue, hk,
                              appargs.ThermoAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermoAppArg.MID_SendHK,
                              str(THERMOAPP_RUNSTATUS))
        time.sleep(1)

# ────────────────────────────────────────────────
# 3) 초기화 · 종료
# ────────────────────────────────────────────────
def thermoapp_init():
    global TEMP_OFFSET, HUMI_OFFSET

    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                        "Initializing thermoapp")

        # DHT11 초기화
        dht_device = thermo.init_dht()

        # 이전 보정값 로드
        TEMP_OFFSET = float(prevstate.PREV_THERMO_TOFF)
        HUMI_OFFSET = float(prevstate.PREV_THERMO_HOFF)

        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                        "Thermoapp initialization complete")
        return dht_device

    except Exception as e:
        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                        f"Init error: {e}")
        return None

def thermoapp_terminate(dht_device):
    global THERMOAPP_RUNSTATUS
    THERMOAPP_RUNSTATUS = False
    events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                    "Terminating thermoapp")

    thermo.terminate_dht(dht_device)

    for t in thread_dict.values():
        t.join()

    events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.info,
                    "Thermoapp termination complete")

# ────────────────────────────────────────────────
# 4) 센서 읽기 / 메시지 송신 스레드
# ────────────────────────────────────────────────
TEMP_C, HUMI = 0.0, 0.0
TEMP_OFFSET, HUMI_OFFSET = 0.0, 0.0   # 보정값

def read_thermo_data(dht_device):
    global TEMP_C, HUMI, TEMP_OFFSET, HUMI_OFFSET, THERMOAPP_RUNSTATUS

    while THERMOAPP_RUNSTATUS:
	
    	if dht_device is None:
        	time.sleep(2)
        	continue            # 초기화 실패 → 재시도만 하고 루프 유지

    	t, h = thermo.read_dht(dht_device)
    	if t is None and h is None:
        	time.sleep(2)
        	continue     

def send_thermo_data(Main_Queue: Queue):
    global TEMP_C, HUMI, THERMOAPP_RUNSTATUS

    # 10 Hz로 FLIGHTLOGIC·1 Hz로 텔레메트리
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()
    cnt = 0

    while THERMOAPP_RUNSTATUS:
        with RESET_MUTEX:
            # FlightLogic 전송 (10 Hz)
            msgstructure.send_msg(Main_Queue, fl_msg,
                                  appargs.ThermoAppArg.AppID,
                                  appargs.FlightlogicAppArg.AppID,
                                  appargs.ThermoAppArg.MID_SendThermoFlightLogicData,
                                  f"{TEMP_C},{HUMI}")

        if cnt >= 10:  # 1 Hz
            status = msgstructure.send_msg(Main_Queue, tlm_msg,
                                           appargs.ThermoAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.ThermoAppArg.MID_SendThermoTlmData,
                                           f"{TEMP_C},{HUMI}")
            if not status:
                events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                                "Error sending Thermo TLM")
            cnt = 0

        cnt += 1
        time.sleep(0.1)

# ────────────────────────────────────────────────
# 5) 메인 엔트리
# ────────────────────────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

def thermoapp_main(Main_Queue: Queue, Main_Pipe: connection.Connection):
    global THERMOAPP_RUNSTATUS
    dht = thermoapp_init()

    # 스레드 생성
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(Main_Queue,))
    thread_dict["SEND"] = threading.Thread(target=send_thermo_data, args=(Main_Queue,))
    thread_dict["READ"] = threading.Thread(target=read_thermo_data, args=(dht,))

    for t in thread_dict.values():
        t.start()

    try:
        while THERMOAPP_RUNSTATUS:
            raw = Main_Pipe.recv()
            m = msgstructure.MsgStructure()
            if not msgstructure.unpack_msg(m, raw):
                continue

            if m.receiver_app in (appargs.ThermoAppArg.AppID, appargs.MainAppArg.AppID):
                command_handler(Main_Queue, m, dht)
            else:
                events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                                "Receiver MID mismatch")

    except Exception as e:
        events.LogEvent(appargs.ThermoAppArg.AppName, events.EventType.error,
                        f"thermoapp error: {e}")
        THERMOAPP_RUNSTATUS = False

    thermoapp_terminate(dht)
