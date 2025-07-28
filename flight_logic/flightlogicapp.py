# Python FSW V2 Flightlogic App
# Author : Hyeon Lee

from lib import appargs
from lib import msgstructure
from lib import logging
from lib import events
from lib import types
from lib import prevstate
from lib import config

import signal
from multiprocessing import Queue, connection
import threading
import time
import os
import csv
from datetime import datetime

# Runstatus of application. Application is terminated when false
FLIGHTLOGICAPP_RUNSTATUS = True

# <NEW/> 현재 환경 측정값
CURRENT_TEMP: float = 0.0  # DHT11 temperature (°C)
#CURRENT_ALT:  float = 0.0  # Barometer altitude (m)
# <NEW/> 마지막으로 실제 서보에 지시한 각도 (스팸 방지용). –1이면 미전송 상태
MOTOR_TARGET_PULSE: int = -1  # mg996r: 500=open, 2500=close

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

# 로그 파일 경로
GPS_LOG_PATH = os.path.join(LOG_DIR, "gps_log.csv")
IMU_LOG_PATH = os.path.join(LOG_DIR, "imu_log.csv")
BAROMETER_LOG_PATH = os.path.join(LOG_DIR, "barometer_log.csv")
DHT11_LOG_PATH = os.path.join(LOG_DIR, "dht11_log.csv")
FIR_LOG_PATH = os.path.join(LOG_DIR, "fir_log.csv")
THERMIS_LOG_PATH = os.path.join(LOG_DIR, "thermis_log.csv")
PITOT_LOG_PATH = os.path.join(LOG_DIR, "pitot_log.csv")
NIR_LOG_PATH = os.path.join(LOG_DIR, "nir_log.csv")
THERMAL_LOG_PATH = os.path.join(LOG_DIR, "thermal_log.csv")
HK_LOG_PATH = os.path.join(LOG_DIR, "hk_log.csv")
ERROR_LOG_PATH = os.path.join(LOG_DIR, "error_log.csv")

# 공통 로그 함수
def log_csv(path, header, row):
    file_exists = os.path.exists(path)
    with open(path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row)

def now_epoch():
    return time.time()

def now_iso():
    return datetime.now().isoformat()

def safe(val):
    return "NA" if val is None else val

######################################################
## FUNDEMENTAL METHODS                              ##
######################################################

# SB Methods
# Methods for sending/receiving/handling SB messages

# Handles received message
def command_handler (recv_msg : msgstructure.MsgStructure, Main_Queue:Queue):
    global SIMULATION_ACTIVATE, MAX_ALT, recent_alt, FLIGHTLOGICAPP_RUNSTATUS
    global SIMULATION_ENABLE, CURRENT_TEMP, LAST_IMU_ROLL, LAST_IMU_PITCH, LAST_GPS, LAST_FIR, LAST_THERMIS, LAST_NIR, LAST_THERMAL
    try:
        if recv_msg.MsgID == appargs.MainAppArg.MID_TerminateProcess:
            # Change Runstatus to false to start termination process
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"FLIGHTLOGICAPP TERMINATION DETECTED")
            FLIGHTLOGICAPP_RUNSTATUS = False

        elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SIM:
            # When simulation command is input
            option = recv_msg.data
            if option == "ENABLE":
                SIMULATION_ENABLE = True
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Enabled")
            if option == "ACTIVATE":
                SIMULATION_ACTIVATE = True
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Activated")
            if option == "DISABLE":
                SIMULATION_ACTIVATE = False
                SIMULATION_ENABLE = False
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Simulation Disabled")
                
            check_simulation_status(Main_Queue)

        # Simulation pressure data
        elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SIMP:
            if SIMULATION_ACTIVATE and SIMULATION_ENABLE:

                simulated_altitude = float(recv_msg.data)
                
                barometer_logic(Main_Queue, simulated_altitude)
            else:
                return

        # Receive Sensor data
        # Barometer Data input at 10Hz
        elif recv_msg.MsgID == appargs.BarometerAppArg.MID_SendBarometerFlightLogicData:
            # Ignore the barometer data when simulation is activated
            if SIMULATION_ENABLE and SIMULATION_ACTIVATE:
                return
            
            try:
                log_barometer_data(recv_msg.data)
                recv_altitude = float(recv_msg.data)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"Barometer data parse error: {type(e).__name__}: {e}")
                return

            # Perform barometer logic
            barometer_logic(Main_Queue, recv_altitude)

        elif recv_msg.MsgID == getattr(appargs, "ThermoAppArg").MID_SendThermoFlightLogicData:
            try:
                log_dht11_data(recv_msg.data)
                temp_str, _ = recv_msg.data.split(",")
                CURRENT_TEMP = float(temp_str)
            except Exception:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                "Thermo data parse error")
                return
            update_motor_logic(Main_Queue)
            return

        elif recv_msg.MsgID == appargs.FirAppArg.MID_SendFirFlightLogicData:
            try:
                # 예: "amb,obj,rawdata..." 형태로 온다고 가정
                parts = recv_msg.data.split(",")
                amb, obj = map(float, parts[:2])
                raw_fir = ",".join(parts[2:]) if len(parts) > 2 else None
                LAST_FIR = (amb, obj)
                if raw_fir:
                    log_fir_data(raw_fir)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"FIR data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return

        elif recv_msg.MsgID == appargs.ThermisAppArg.MID_SendThermisFlightLogicData:
            try:
                # 예: "temp,rawdata..." 형태로 온다고 가정
                parts = recv_msg.data.split(",")
                temp = float(parts[0])
                raw_thermis = ",".join(parts[1:]) if len(parts) > 1 else None
                LAST_THERMIS = temp
                if raw_thermis:
                    log_thermis_data(raw_thermis)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"THERMIS data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return
        elif recv_msg.MsgID == appargs.PitotAppArg.MID_SendPitotFlightLogicData:
            try:
                # 예: "pressure,temp,rawdata..." 형태로 온다고 가정
                parts = recv_msg.data.split(",")
                pressure, temp = map(float, parts[:2])
                raw_pitot = ",".join(parts[2:]) if len(parts) > 2 else None
                LAST_PITOT_PRESSURE = pressure
                LAST_PITOT_TEMP = temp
                if raw_pitot:
                    log_pitot_data(raw_pitot)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"Pitot data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return
        elif recv_msg.MsgID == appargs.NirAppArg.MID_SendNirFlightLogicData:
            try:
                # 예: "voltage,temp,rawdata..." 형태로 온다고 가정
                parts = recv_msg.data.split(",")
                voltage, temp = map(float, parts[:2])
                raw_nir = ",".join(parts[2:]) if len(parts) > 2 else None
                LAST_NIR = (voltage, temp)
                if raw_nir:
                    log_nir_data(raw_nir)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"NIR data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return
        elif recv_msg.MsgID == appargs.ThermalcameraAppArg.MID_SendCamFlightLogicData:
            try:
                # 예: "avg,min,max,p0,p1,...,p767" 형태로 온다고 가정
                parts = recv_msg.data.split(",")
                avg, min_t, max_t = map(float, parts[:3])
                frame = list(map(float, parts[3:]))
                LAST_THERMAL = (avg, min_t, max_t)
                log_thermal_frame(frame, avg, min_t, max_t)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"ThermalCam data parse error: {type(e).__name__}: {e}")
            return

        elif recv_msg.MsgID == appargs.CommAppArg.MID_RouteCmd_SS:
            # When received Set State command
            recv_state = int(recv_msg.data)

            # LAUNCHPAD
            if recv_state == 0:
                launchpad_state_transition(Main_Queue)

            # ASCENT
            elif recv_state == 1:
                ascent_state_transition(Main_Queue)

            # APOGEE
            elif recv_state == 2:
                apogee_state_transition(Main_Queue)

            # DESCENT
            elif recv_state == 3:
                descent_state_transition(Main_Queue)

            # PROBE RELEASE
            elif recv_state == 4:
                probe_release_state_transition(Main_Queue)

            # LANDED
            elif recv_state == 5:
                landed_state_transition(Main_Queue)
                
            # Received State out of state range
            else: 
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"Error receiving SS message, Expected state value of 0 ~ {len(STATE_LIST) - 1}, received {recv_state}")

        # When reset message from barometer app is received, set the max alt to 0
        elif recv_msg.MsgID == appargs.BarometerAppArg.MID_ResetBarometerMaxAlt:
            MAX_ALT = 0
            recent_alt.clear()

        elif recv_msg.MsgID == appargs.GpsAppArg.MID_SendGpsFlightLogicData:
            try:
                log_gps_data(recv_msg.data)
                lat, lon, alt, *_ = map(float, recv_msg.data.split(","))
                LAST_GPS = (lat, lon, alt)
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"GPS data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return

        elif recv_msg.MsgID == appargs.ImuAppArg.MID_SendImuFlightLogicData:
            try:
                log_imu_data(recv_msg.data)
                roll, pitch, *_ = map(float, recv_msg.data.split(","))
                LAST_IMU_ROLL = roll
                LAST_IMU_PITCH = pitch
            except Exception as e:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                                f"IMU data parse error: {type(e).__name__}: {e}")
                return
            update_motor_logic(Main_Queue)
            return

        else:
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"MID {recv_msg.MsgID} not handled")
    except Exception as e:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                        f"Exception in command_handler: {type(e).__name__}: {e}")
        raise
    return

def send_hk(Main_Queue : Queue):
    global FLIGHTLOGICAPP_RUNSTATUS, CURRENT_STATE, CURRENT_TEMP, recent_alt
    global LAST_IMU_ROLL, LAST_IMU_PITCH, LAST_GPS, LAST_FIR, LAST_THERMIS, LAST_NIR, MOTOR_TARGET_PULSE
    while FLIGHTLOGICAPP_RUNSTATUS:
        flightlogicHK = msgstructure.MsgStructure()
        hk_payload = (
            f"run={FLIGHTLOGICAPP_RUNSTATUS},state={CURRENT_STATE},temp={CURRENT_TEMP},alt={recent_alt[-1] if recent_alt else 'NA'},"
            f"imu_roll={LAST_IMU_ROLL},imu_pitch={LAST_IMU_PITCH},gps={LAST_GPS},fir={LAST_FIR},thermis={LAST_THERMIS},nir={LAST_NIR},motor={MOTOR_TARGET_PULSE}"
        )
        msgstructure.send_msg(Main_Queue, flightlogicHK, appargs.FlightlogicAppArg.AppID, appargs.HkAppArg.AppID, appargs.FlightlogicAppArg.MID_SendHK, hk_payload)
        hk_row = [now_epoch(), now_iso(), FLIGHTLOGICAPP_RUNSTATUS, CURRENT_STATE, safe(CURRENT_TEMP),
                  safe(recent_alt[-1] if recent_alt else None), safe(LAST_IMU_ROLL), safe(LAST_IMU_PITCH),
                  safe(LAST_GPS), safe(LAST_FIR), safe(LAST_THERMIS), safe(LAST_PITOT_PRESSURE), safe(LAST_PITOT_TEMP), safe(LAST_NIR), safe(MOTOR_TARGET_PULSE)]
        log_csv(HK_LOG_PATH, ["epoch","iso","run","state","temp","alt","imu_roll","imu_pitch","gps","fir","thermis","pitot_pressure","pitot_temp","nir","motor"], hk_row)
        time.sleep(1)
    return

######################################################
# Motor‑control helpers <NEW/>
######################################################

def set_motor_pulse(Main_Queue: Queue, pulse: int) -> None:
    """MG996R 모터에 펄스 명령 전송송"""
    global MOTOR_TARGET_PULSE, IMU_ROLL_THRESHOLD, IMU_PITCH_THRESHOLD, CLOSE_EVENT_LOGGED, LAST_BAROMETER
    if pulse == MOTOR_TARGET_PULSE:
        return  # 이미 같은 펄스로 지시함
    MOTOR_TARGET_PULSE = pulse
    msg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, msg,
                          appargs.FlightlogicAppArg.AppID,
                          appargs.MotorAppArg.AppID,
                          appargs.FlightlogicAppArg.MID_SetServoAngle,
                          str(pulse))
    if pulse == 500:
        state = "열림"
        CLOSE_EVENT_LOGGED = False
    elif pulse == 2500:
        state = "닫힘"
        # 완전히 닫힘 시점에 센서 데이터 저장 및 로그
        if not CLOSE_EVENT_LOGGED:
            # IMU, GPS, Barometer, 온도 등 실제 데이터로 대입 필요
            IMU_ROLL_THRESHOLD = get_current_imu_roll()  # 함수 구현 필요
            IMU_PITCH_THRESHOLD = get_current_imu_pitch()  # 함수 구현 필요
            LAST_GPS = get_current_gps()  # 함수 구현 필요
            LAST_BAROMETER = recent_alt[-1] if recent_alt else None
            log_msg = (
                f"[CLOSE_EVENT] time={time.time()}, "
                f"GPS={LAST_GPS}, IMU_roll={IMU_ROLL_THRESHOLD}, IMU_pitch={IMU_PITCH_THRESHOLD}, "
                f"Barometer={LAST_BAROMETER}, TEMP={CURRENT_TEMP}, "
                f"FIR={LAST_FIR}, NIR={LAST_NIR}, THERMAL={LAST_THERMAL}"
            )
            events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, log_msg)
            CLOSE_EVENT_LOGGED = True
    else:
        state = None
    if state:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info,
                        f"Motor pulse cmd → {pulse} ({state})")
    else:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info,
                        f"Motor pulse cmd → {pulse}")

# 최근 0.5초(5회) 동안 고도가 모두 70m 이하인지 체크
RECENT_ALT_CHECK_LEN = 5  # 0.5초(10Hz)

# IMU 관련 변수(닫힘 시점 값 저장용)
IMU_ROLL_THRESHOLD = None
IMU_PITCH_THRESHOLD = None
CLOSE_EVENT_LOGGED = False  # 중복 저장 방지

# 센서 데이터 저장용(예시)
LAST_GPS = None  # 실제 GPS 데이터 구조에 맞게 할당 필요
LAST_IMU = None  # 실제 IMU 데이터 구조에 맞게 할당 필요
LAST_BAROMETER = None  # 최근 고도값 등

def update_motor_logic(Main_Queue: Queue):
    """고도/온도 조건에 따라 MG996R 모터 제어 (500=open, 2500=close)"""
    # recent_alt의 최신값이 최근 5개 모두 PAYLOAD_SEP_ALT_THRESHOLD 이하라면 닫힘
    if len(recent_alt) >= RECENT_ALT_CHECK_LEN and all(alt <= PAYLOAD_SEP_ALT_THRESHOLD for alt in recent_alt[-RECENT_ALT_CHECK_LEN:]):
        set_motor_pulse(Main_Queue, 2500)  # 닫힘
        return
    # 온도 조건
    if CURRENT_TEMP >= 40:
        set_motor_pulse(Main_Queue, 500)  # 열림
    else:
        set_motor_pulse(Main_Queue, 2500)  # 닫힘

######################################################
## INITIALIZATION, TERMINATION                      ##
######################################################

# Initialization
def flightlogicapp_init(Main_Queue : Queue):
    try:
        global FLIGHTLOGICAPP_RUNSTATUS, CURRENT_STATE, MAX_ALT, PAYLOAD_SEP_ALT_THRESHOLD
        # Disable Keyboardinterrupt since Termination is handled by parent process
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Initializating flightlogicapp")
        ## User Defined Initialization goes HERE

        # For recovery, set the prev state as the current state.
        CURRENT_STATE = int(prevstate.PREV_STATE)

        # Perform state transition according to state
        if CURRENT_STATE == 0:
            launchpad_state_transition(Main_Queue)
        elif CURRENT_STATE == 1:
            ascent_state_transition(Main_Queue)
        elif CURRENT_STATE == 2 :
            descent_state_transition(Main_Queue)
        elif CURRENT_STATE == 3 :
            apogee_state_transition(Main_Queue)
        elif CURRENT_STATE == 4 :
            probe_release_state_transition(Main_Queue)
        elif CURRENT_STATE == 5:
            landed_state_transition(Main_Queue)
            
        # For recovery set the max altitude
        MAX_ALT = float(prevstate.PREV_MAX_ALT)
        PAYLOAD_SEP_ALT_THRESHOLD = 70  # 초기값(예: 70m)

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Setting Current state to {CURRENT_STATE}")

        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Flightlogicapp Initialization Complete")
    except Exception as e:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error,
                        f"Error during initialization: {type(e).__name__}: {e}")
        FLIGHTLOGICAPP_RUNSTATUS = False

# Termination
def flightlogicapp_terminate():
    global FLIGHTLOGICAPP_RUNSTATUS

    FLIGHTLOGICAPP_RUNSTATUS = False
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Terminating flightlogicapp")
    # Termination Process Comes Here

    # Join Each Thread to make sure all threads terminates
    for thread_name in thread_dict:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name}")
        thread_dict[thread_name].join()
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, f"Terminating thread {thread_name} Complete")

    # The termination flag should switch to false AFTER ALL TERMINATION PROCESS HAS ENDED
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, "Terminating flightlogicapp complete")
    return

######################################################
## USER METHOD                                      ##
######################################################

STATE_LIST = ["LAUNCH_PAD",
              "ASCENT",
              "APOGEE",
              "DESCENT",
              "PROBE_RELEASE",
              "LANDED"]

CURRENT_STATE = 0

# Simulation Mode Flags, both ENABLE and ACTIVATE should be true to use simulation mode
SIMULATION_ENABLE = False
SIMULATION_ACTIVATE = False

# Variable used in state determination
MAX_ALT = 0
# PAYLOAD_SEP_ALT_THRESHOLD: 모터를 무조건 닫는 고도 임계값
PAYLOAD_SEP_ALT_THRESHOLD = 70  # 초기값(예: 70m), 이후 barometer_logic에서 갱신

# counters for each state transition. State will change when counter > 3,
# counter + 1 when state transition condition satisfies, counter - 2 when not
BAROMETER_ASCENT_COUNTER = 0
BAROMETER_APOGEE_COUNTER = 0
BAROMETER_DESCENT_COUNTER = 0
BAROMETER_PROBE_RELEASE_COUNTER = 0
BAROMETER_LANDED_COUNTER = 0

# IMU 관련 상수(실제 사용처 없으면 삭제, 전역 변수로만 유지)
IMU_ROLL_THRESHOLD = 70
IMU_PITCH_THRESHOLD = 70

recent_alt = []

def barometer_logic(Main_Queue:Queue, altitude:float):
    # 최대 고도 찍고 감소하면 -> Descening State
    # Descending State에서 75% 고도 되면 Payload Release State
    # 이렇게 하면 될듯?
    global MAX_ALT, PAYLOAD_SEP_ALT_THRESHOLD, CURRENT_STATE
    global BAROMETER_ASCENT_COUNTER, BAROMETER_DESCENT_COUNTER
    global BAROMETER_APOGEE_COUNTER, BAROMETER_PROBE_RELEASE_COUNTER, BAROMETER_LANDED_COUNTER
    global recent_alt

    # recent_alt 길이 5로 유지
    recent_alt.append(altitude)
    if len(recent_alt) > 5:
        recent_alt.pop(0)

    if len(recent_alt) > 2:
        sorted_alts = sorted(recent_alt, reverse=True)
        second_max = sorted_alts[1]

        if sorted_alts[1] > MAX_ALT:
            MAX_ALT = second_max
            prevstate.update_maxalt(second_max)

    PAYLOAD_SEP_ALT_THRESHOLD = MAX_ALT * 0.75  # 최대고도의 75%로 계속 갱신
    #print(f"alt : {altitude} , max : {MAX_ALT}")
    if len(recent_alt) < 3:
        # Do not perform any logic before filter is enabled
        return

    if BAROMETER_ASCENT_COUNTER <= 0 :
        BAROMETER_ASCENT_COUNTER = 0

    if BAROMETER_APOGEE_COUNTER <= 0 :
        BAROMETER_APOGEE_COUNTER = 0

    if BAROMETER_DESCENT_COUNTER <= 0 :
        BAROMETER_DESCENT_COUNTER = 0
    
    if BAROMETER_PROBE_RELEASE_COUNTER <= 0:
        BAROMETER_PROBE_RELEASE_COUNTER = 0

    if BAROMETER_LANDED_COUNTER <= 0 :
        BAROMETER_LANDED_COUNTER = 0
        
    # At Standby State
    if CURRENT_STATE == 0:

        # When Altitude is higher than 75 meters
        if (altitude > 75):
            BAROMETER_ASCENT_COUNTER += 1
        else:
            BAROMETER_ASCENT_COUNTER -= 2
        
        # When the counter is larger than 3 ; when the altitude is higher than 50 meter 3 times in a row
        if BAROMETER_ASCENT_COUNTER >= 3:
            ascent_state_transition(Main_Queue)
    
    # At Ascent State
    if CURRENT_STATE == 1:

        # When Altitude is 20 meter lower than max altitude

        if (altitude <= MAX_ALT - 20):
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2
        
        # 0.25 meter is the resolution of BMP390
        if (altitude < MAX_ALT - 0.25 and altitude > MAX_ALT - 20):
            BAROMETER_APOGEE_COUNTER += 1
        else:
            BAROMETER_APOGEE_COUNTER -= 2

        # When the counter is larger than 2; When the altitude is 2 meter lower than max altitude 2 times in a row
        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

        if BAROMETER_APOGEE_COUNTER >= 2:
            apogee_state_transition(Main_Queue)

    # At Apogee State
    if CURRENT_STATE == 2:
        
        # Check for descent
        if (altitude <= MAX_ALT - 20):
            BAROMETER_DESCENT_COUNTER += 1
        else:
            BAROMETER_DESCENT_COUNTER -= 2

        # When the counter is larger than 3; When the altitude is 2 meter lower than max altitude 3 times in a row
        if BAROMETER_DESCENT_COUNTER >= 2:
            descent_state_transition(Main_Queue)

    # At Descent State
    if CURRENT_STATE == 3:
        # When Altitude is 75% of max altitude

        if (altitude <= MAX_ALT * 0.75):
            BAROMETER_PROBE_RELEASE_COUNTER += 1
        else:
            BAROMETER_PROBE_RELEASE_COUNTER -= 2

        # When the counter is larger than 3; When the altitude is 75% of max altitude 2 times in a row
        if BAROMETER_PROBE_RELEASE_COUNTER >= 2:
            probe_release_state_transition(Main_Queue)
    
    # At Probe Release State

    if CURRENT_STATE == 4:
        # When altitude is almost zero

        if altitude <= 15:
            BAROMETER_LANDED_COUNTER += 1
        else:
            BAROMETER_LANDED_COUNTER -= 2

        if BAROMETER_LANDED_COUNTER >= 3:
            landed_state_transition(Main_Queue)
        

    return

def log_and_update_state(state: int, log_msg: str):
    global CURRENT_STATE
    CURRENT_STATE = state
    events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, log_msg)
    prevstate.update_prevstate(CURRENT_STATE)

def launchpad_state_transition(Main_Queue : Queue):
    global MAX_ALT
    global recent_alt
    log_and_update_state(0, "CHANGED STATE TO STANDBY")
    MAX_ALT = 0
    recent_alt.clear()
    return

def ascent_state_transition(Main_Queue : Queue):
    log_and_update_state(1, "CHANGED STATE TO ASCENT")
    return

def apogee_state_transition(Main_Queue : Queue):
    log_and_update_state(2, "CHANGED STATE TO APOGEE")
    return

# 낙하(Descent) 상태 진입 시점 이벤트 로깅
DESCENT_EVENT_LOGGED = False

def descent_state_transition(Main_Queue:Queue):
    global DESCENT_EVENT_LOGGED, LAST_BAROMETER
    log_and_update_state(3, "CHANGED STATE TO DESCENT")
    if not DESCENT_EVENT_LOGGED:
        LAST_BAROMETER = recent_alt[-1] if recent_alt else None
        log_msg = (
            f"[DESCENT_EVENT] epoch={now_epoch()}, iso={now_iso()}, "
            f"GPS={safe(LAST_GPS)}, IMU_roll={safe(LAST_IMU_ROLL)}, IMU_pitch={safe(LAST_IMU_PITCH)}, "
            f"Barometer={safe(LAST_BAROMETER)}, TEMP={safe(CURRENT_TEMP)}, "
            f"FIR={safe(LAST_FIR)}, NIR={safe(LAST_NIR)}, THERMAL={safe(LAST_THERMAL)}"
        )
        log_error(log_msg)
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.info, log_msg)
        DESCENT_EVENT_LOGGED = True
    return

def probe_release_state_transition(Main_Queue:Queue):
    log_and_update_state(4, "CHANGED STATE TO PROBE RELEASE")
    return

def landed_state_transition(Main_Queue : Queue):
    log_and_update_state(5, "CHANGED STATE TO LANDED")
    return

def check_simulation_status(Main_Queue:Queue):
    simulation_status = "F"

    if SIMULATION_ENABLE and SIMULATION_ACTIVATE:
        simulation_status = "S"
        
    SimulationStatusToTlmMsg = msgstructure.MsgStructure()
    msgstructure.send_msg(Main_Queue, SimulationStatusToTlmMsg, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.MID_SendSimulationStatustoTlm, simulation_status)   

# Put user-defined methods here!

def send_current_state(Main_Queue:Queue):
    global FLIGHTLOGICAPP_RUNSTATUS
    global CURRENT_STATE

    SendCurrentStateMsg = msgstructure.MsgStructure()
    while FLIGHTLOGICAPP_RUNSTATUS:
        msgstructure.send_msg(Main_Queue, SendCurrentStateMsg, appargs.FlightlogicAppArg.AppID, appargs.CommAppArg.AppID, appargs.FlightlogicAppArg.MID_SendCurrentStateToTlm, STATE_LIST[CURRENT_STATE])
        time.sleep(1)
    
    return
######################################################
## MAIN METHOD                                      ##
######################################################

thread_dict = dict[str, threading.Thread]()

# This method is called from main app. Initialization, runloop process
def flightlogicapp_main(Main_Queue : Queue, Main_Pipe : connection.Connection):
    global FLIGHTLOGICAPP_RUNSTATUS
    FLIGHTLOGICAPP_RUNSTATUS = True

    # Initialization Process
    flightlogicapp_init(Main_Queue)

    # Spawn SB Message Listner Thread
    thread_dict["HKSender_Thread"] = threading.Thread(target=send_hk, args=(Main_Queue, ), name="HKSender_Thread")
    thread_dict["SendCurrentState_Thread"] = threading.Thread(target=send_current_state, args=(Main_Queue, ), name="SendCurrentState_Thread")

    # Spawn Each Threads
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while FLIGHTLOGICAPP_RUNSTATUS:
            # Receive Message From Pipe
            message = Main_Pipe.recv()
            recv_msg = msgstructure.MsgStructure()

            # Unpack Message, Skip this message if unpacked message is not valid
            if msgstructure.unpack_msg(recv_msg, message) == False:
                continue
            
            # Validate Message, Skip this message if target AppID different from flightlogicapp's AppID
            # Exception when the message is from main app
            if recv_msg.receiver_app == appargs.FlightlogicAppArg.AppID or recv_msg.receiver_app == appargs.MainAppArg.AppID:
                # Handle Command According to Message ID
                command_handler(recv_msg, Main_Queue)
            else:
                events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, "Receiver MID does not match with flightlogicapp MID")

    # If error occurs, terminate app
    except Exception as e:
        events.LogEvent(appargs.FlightlogicAppArg.AppName, events.EventType.error, f"flightlogicapp error : {e}")
        FLIGHTLOGICAPP_RUNSTATUS = False

    # Termination Process after runloop
    flightlogicapp_terminate()

    return

# 파일 최상단
LAST_IMU_ROLL = None
LAST_IMU_PITCH = None
LAST_GPS = None
LAST_FIR = None
LAST_THERMIS = None
LAST_PITOT_PRESSURE = None
LAST_PITOT_TEMP = None
LAST_NIR = None
LAST_THERMAL = None
LAST_BAROMETER = None

def get_current_imu_roll():
    return LAST_IMU_ROLL

def get_current_imu_pitch():
    return LAST_IMU_PITCH

def get_current_gps():
    return LAST_GPS

# Thermal Camera(mlx90640) 전체 프레임 로그
THERMAL_FRAME_SIZE = 24*32

def log_thermal_frame(frame, avg, min_t, max_t):
    header = ["epoch","iso","avg","min","max"] + [f"pix_{i}" for i in range(THERMAL_FRAME_SIZE)]
    row = [now_epoch(), now_iso(), safe(avg), safe(min_t), safe(max_t)] + [safe(p) for p in frame]
    log_csv(THERMAL_LOG_PATH, header, row)

def log_fir_data(raw_data):
    log_csv(FIR_LOG_PATH, ["epoch","iso","raw_fir"], [now_epoch(), now_iso(), safe(raw_data)])

def log_thermis_data(raw_data):
    log_csv(THERMIS_LOG_PATH, ["epoch","iso","raw_thermis"], [now_epoch(), now_iso(), safe(raw_data)])

def log_pitot_data(raw_data):
    log_csv(PITOT_LOG_PATH, ["epoch","iso","raw_pitot"], [now_epoch(), now_iso(), safe(raw_data)])

def log_nir_data(raw_data):
    log_csv(NIR_LOG_PATH, ["epoch","iso","raw_nir"], [now_epoch(), now_iso(), safe(raw_data)])

def log_gps_data(raw_data):
    log_csv(GPS_LOG_PATH, ["epoch","iso","raw_gps"], [now_epoch(), now_iso(), safe(raw_data)])

def log_imu_data(raw_data):
    log_csv(IMU_LOG_PATH, ["epoch","iso","raw_imu"], [now_epoch(), now_iso(), safe(raw_data)])

def log_barometer_data(raw_data):
    log_csv(BAROMETER_LOG_PATH, ["epoch","iso","raw_barometer"], [now_epoch(), now_iso(), safe(raw_data)])

def log_dht11_data(raw_data):
    log_csv(DHT11_LOG_PATH, ["epoch","iso","raw_dht11"], [now_epoch(), now_iso(), safe(raw_data)])

def log_error(msg):
    log_csv(ERROR_LOG_PATH, ["epoch","iso","error_msg"], [now_epoch(), now_iso(), msg])

