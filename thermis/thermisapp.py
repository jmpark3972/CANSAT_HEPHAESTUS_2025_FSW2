#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""thermisapp.py – ADS1115 thermistor temperature application for FSW V2

* Sensor: ADS1115 with thermistor
* Publishes temperature to Flightlogic (10 Hz) and COMM (1 Hz)
* Supports CAL command: "<temperature_offset>"
"""
import board, busio
from lib import appargs, msgstructure, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from thermis import thermis  # helper module created earlier


# ──────────────────────────────────────────────
# Globals & Locks
# ──────────────────────────────────────────────
THERMISAPP_RUNSTATUS = True

OFFSET_MUTEX = threading.Lock()  # protect offset update & sensor access

TEMP_OFFSET = 0.0  # °C

TEMP = 0.0

THERMIS_MUX = None  # MUX instance for channel 4

# ──────────────────────────────────────────────
# Command handler
# ──────────────────────────────────────────────

def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    """Handle SB messages addressed to ThermisApp."""
    global THERMISAPP_RUNSTATUS, TEMP_OFFSET

    # Terminate process
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                        "THERMISAPP termination detected")
        THERMISAPP_RUNSTATUS = False
        return

    # Calibration: data == "<temp_off>"
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            temp_off = float(recv.data)
        except Exception:
            events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                            "CAL cmd parse error")
            return

        with OFFSET_MUTEX:
            TEMP_OFFSET = temp_off
        prevstate.update_thermiscal(TEMP_OFFSET)  # must exist in prevstate
        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                        f"THERMIS offset set to temp={TEMP_OFFSET}")
        return

    events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# ──────────────────────────────────────────────
# HK thread
# ──────────────────────────────────────────────

def send_hk(main_q: Queue):
    while THERMISAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(main_q, hk,
                              appargs.ThermisAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.ThermisAppArg.MID_SendHK,
                              str(THERMISAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────────────────────
# Sensor threads
# ──────────────────────────────────────────────

def read_thermis_data(chan):
    global TEMP
    while THERMISAPP_RUNSTATUS:
        with OFFSET_MUTEX:
            temp = thermis.read_thermis(chan)  # returns None on error
            if temp is not None:
                TEMP = round(temp - TEMP_OFFSET, 2)
        time.sleep(0.2)  # ADS1115 ~2Hz default


def send_thermis_data(main_q: Queue):
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while THERMISAPP_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.send_msg(main_q, fl_msg,
                              appargs.ThermisAppArg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.ThermisAppArg.MID_SendThermisFlightLogicData,
                              f"{TEMP}")

        # COMM 1 Hz
        if cnt >= 10:
            status = msgstructure.send_msg(main_q, tlm_msg,
                                           appargs.ThermisAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.ThermisAppArg.MID_SendThermisTlmData,
                                           f"{TEMP}")
            if not status:
                events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                                "Error sending Thermis TLM")
            cnt = 0
        cnt += 1
        time.sleep(0.1)

# ──────────────────────────────────────────────
# Init / Terminate
# ──────────────────────────────────────────────

def thermisapp_init():
    global TEMP_OFFSET
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                        "Initializing thermisapp")

        i2c, ads, chan, mux = thermis.init_thermis()

        # Store MUX instance globally for proper channel management
        global THERMIS_MUX
        THERMIS_MUX = mux

        # previous calibration (if any)
        TEMP_OFFSET = float(getattr(prevstate, "PREV_THERMIS_OFF", 0.0))

        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                        "Thermisapp initialization complete")
        return i2c, ads, chan

    except Exception as e:
        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                        f"Init error: {e}")
        return None, None, None


def thermisapp_terminate(i2c):
    global THERMISAPP_RUNSTATUS, THERMIS_MUX
    THERMISAPP_RUNSTATUS = False
    events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                    "Terminating thermisapp")
    
    # Close MUX connection
    if THERMIS_MUX:
        try:
            THERMIS_MUX.close()
        except Exception as e:
            events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error, f"MUX 종료 오류: {e}")
    
    thermis.terminate_thermis(i2c)
    for t in thread_dict.values():
        t.join()
    events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.info,
                    "Thermisapp termination complete")

# ──────────────────────────────────────────────
# Main entry
# ──────────────────────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while THERMISAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            time.sleep(1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t._is_resilient = True
    t.start()
    return t

def thermisapp_main(main_q: Queue, main_pipe: connection.Connection):
    global THERMISAPP_RUNSTATUS
    THERMISAPP_RUNSTATUS = True

    i2c, ads, chan = thermisapp_init()
    if chan is None:
        return

    # spawn threads
    thread_dict["HK"] = resilient_thread(send_hk, args=(main_q,), name="HK")
    thread_dict["READ"] = resilient_thread(read_thermis_data, args=(chan,), name="READ")
    thread_dict["SEND"] = threading.Thread(target=send_thermis_data, args=(main_q,), name="SEND")
    for t in thread_dict.values():
        if not hasattr(t, '_is_resilient') or not t._is_resilient:
            t.start()

    try:
        while THERMISAPP_RUNSTATUS:
            # Non-blocking receive with timeout
            if main_pipe.poll(1.0):  # 1초 타임아웃
                try:
                    raw = main_pipe.recv()
                except:
                    # 에러 시 루프 계속
                    continue
            else:
                # 타임아웃 시 루프 계속
                continue
            m = msgstructure.MsgStructure()
            if not msgstructure.unpack_msg(m, raw):
                continue
            if m.receiver_app in (appargs.ThermisAppArg.AppID, appargs.MainAppArg.AppID):
                command_handler(main_q, m)
            else:
                events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                                "Receiver MID mismatch")
    except Exception as e:
        events.LogEvent(appargs.ThermisAppArg.AppName, events.EventType.error,
                        f"thermisapp error: {e}")
        THERMISAPP_RUNSTATUS = False

    thermisapp_terminate(i2c) 