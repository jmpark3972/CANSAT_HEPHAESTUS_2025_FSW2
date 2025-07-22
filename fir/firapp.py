#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""firapp.py – MLX90614 FIR temperature application for FSW V2

* Sensor: MLX90614 (infra‑red thermometer)
* Publishes ambient & object temperature to Flightlogic (10 Hz) and COMM (1 Hz)
* Supports CAL command: "<ambient_offset>,<object_offset>"
"""
import board, busio
from lib import appargs, msgstructure, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from fir import fir  # helper module created earlier


# ──────────────────────────────────────────────
# Globals & Locks
# ──────────────────────────────────────────────
FIRAPP_RUNSTATUS = True

OFFSET_MUTEX = threading.Lock()  # protect offset update & sensor access

AMB_OFFSET = 0.0  # °C
OBJ_OFFSET = 0.0  # °C

AMB_TEMP = 0.0
OBJ_TEMP = 0.0

# ──────────────────────────────────────────────
# Command handler
# ──────────────────────────────────────────────

def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    """Handle SB messages addressed to FirApp."""
    global FIRAPP_RUNSTATUS, AMB_OFFSET, OBJ_OFFSET

    # Terminate process
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                        "FIRAPP termination detected")
        FIRAPP_RUNSTATUS = False
        return

    # Calibration: data == "<amb_off>,<obj_off>"
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            amb_off, obj_off = map(float, recv.data.split(","))
        except Exception:
            events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                            "CAL cmd parse error")
            return

        with OFFSET_MUTEX:
            AMB_OFFSET, OBJ_OFFSET = amb_off, obj_off
        prevstate.update_fircal(AMB_OFFSET, OBJ_OFFSET)  # must exist in prevstate
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                        f"FIR offsets set to amb={AMB_OFFSET}, obj={OBJ_OFFSET}")
        return

    events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# ──────────────────────────────────────────────
# HK thread
# ──────────────────────────────────────────────

def send_hk(main_q: Queue):
    while FIRAPP_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(main_q, hk,
                              appargs.FirAppArg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.FirAppArg.MID_SendHK,
                              str(FIRAPP_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────────────────────
# Sensor threads
# ──────────────────────────────────────────────

def read_fir_data(sensor):
    global AMB_TEMP, OBJ_TEMP
    while FIRAPP_RUNSTATUS:
        with OFFSET_MUTEX:
            amb, obj = fir.read_fir(sensor)  # returns None,None on error
            if amb is not None:
                AMB_TEMP = round(amb - AMB_OFFSET, 2)
                OBJ_TEMP = round(obj - OBJ_OFFSET, 2)
        time.sleep(0.2)  # MLX90614 ~2Hz default


def send_fir_data(main_q: Queue):
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while FIRAPP_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.send_msg(main_q, fl_msg,
                              appargs.FirAppArg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.FirAppArg.MID_SendFirFlightLogicData,
                              f"{AMB_TEMP},{OBJ_TEMP}")

        # COMM 1 Hz
        if cnt >= 10:
            status = msgstructure.send_msg(main_q, tlm_msg,
                                           appargs.FirAppArg.AppID,
                                           appargs.CommAppArg.AppID,
                                           appargs.FirAppArg.MID_SendFirTlmData,
                                           f"{AMB_TEMP},{OBJ_TEMP}")
            if not status:
                events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                                "Error sending Fir TLM")
            cnt = 0
        cnt += 1
        time.sleep(0.1)

# ──────────────────────────────────────────────
# Init / Terminate
# ──────────────────────────────────────────────

def firapp_init():
    global AMB_OFFSET, OBJ_OFFSET
    try:
        signal.signal(signal.SIGINT, signal.SIG_IGN)
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                        "Initializing firapp")

        i2c, sensor = fir.init_fir()

        # previous calibration (if any)
        AMB_OFFSET = float(getattr(prevstate, "PREV_FIR_AOFF", 0.0))
        OBJ_OFFSET = float(getattr(prevstate, "PREV_FIR_OOFF", 0.0))

        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                        "Firapp initialization complete")
        return i2c, sensor

    except Exception as e:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                        f"Init error: {e}")
        return None, None


def firapp_terminate(i2c):
    global FIRAPP_RUNSTATUS
    FIRAPP_RUNSTATUS = False
    events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                    "Terminating firapp")
    fir.terminate_fir(i2c)
    for t in thread_dict.values():
        t.join()
    events.LogEvent(appargs.FirAppArg.AppName, events.EventType.info,
                    "Firapp termination complete")

# ──────────────────────────────────────────────
# Main entry
# ──────────────────────────────────────────────
thread_dict: dict[str, threading.Thread] = {}

def resilient_thread(target, args=(), name=None):
    def wrapper():
        while FIRAPP_RUNSTATUS:
            try:
                target(*args)
            except Exception:
                pass
            time.sleep(1)
    t = threading.Thread(target=wrapper, name=name)
    t.daemon = True
    t.start()
    return t

def firapp_main(main_q: Queue, main_pipe: connection.Connection):
    global FIRAPP_RUNSTATUS
    FIRAPP_RUNSTATUS = True

    i2c, sensor = firapp_init()
    if sensor is None:
        return

    # spawn threads
    thread_dict["HK"] = threading.Thread(target=send_hk, args=(main_q,), name="HK")
    thread_dict["READ"] = resilient_thread(read_fir_data, args=(sensor,), name="READ")
    thread_dict["SEND"] = threading.Thread(target=send_fir_data, args=(main_q,), name="SEND")
    for t in thread_dict.values():
        t.start()

    try:
        while FIRAPP_RUNSTATUS:
            raw = main_pipe.recv()
            m = msgstructure.MsgStructure()
            if not msgstructure.unpack_msg(m, raw):
                continue
            if m.receiver_app in (appargs.FirAppArg.AppID, appargs.MainAppArg.AppID):
                command_handler(main_q, m)
            else:
                events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                                "Receiver MID mismatch")
    except Exception as e:
        events.LogEvent(appargs.FirAppArg.AppName, events.EventType.error,
                        f"firapp error: {e}")
        FIRAPP_RUNSTATUS = False

    firapp_terminate(i2c)
