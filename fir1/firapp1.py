#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 HEPHAESTUS
# SPDX-License-Identifier: MIT
"""firapp1.py – MLX90614 FIR temperature application for FSW V2 (Channel 0)

* Sensor: MLX90614 (infra‑red thermometer) on Qwiic Mux Channel 0
* Publishes ambient & object temperature to Flightlogic (10 Hz) and COMM (1 Hz)
* Supports CAL command: "<ambient_offset>,<object_offset>"
"""
import board, busio
from lib import appargs, msgstructure, events, prevstate
import signal, threading, time
from multiprocessing import Queue, connection

from fir1 import fir1  # helper module for channel 0


# ──────────────────────────────────────────────
# Globals & Locks
# ──────────────────────────────────────────────
FIRAPP1_RUNSTATUS = True

OFFSET_MUTEX = threading.Lock()  # protect offset update & sensor access

AMB_OFFSET = 0.0  # °C
OBJ_OFFSET = 0.0  # °C

AMB_TEMP = 0.0
OBJ_TEMP = 0.0

# ──────────────────────────────────────────────
# Command handler
# ──────────────────────────────────────────────

def command_handler(Main_Queue: Queue, recv: msgstructure.MsgStructure):
    """Handle SB messages addressed to FirApp1."""
    global FIRAPP1_RUNSTATUS, AMB_OFFSET, OBJ_OFFSET

    # Terminate process
    if recv.MsgID == appargs.MainAppArg.MID_TerminateProcess:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        "FIRAPP1 termination detected")
        FIRAPP1_RUNSTATUS = False
        return

    # Calibration: data == "<amb_off>,<obj_off>"
    if recv.MsgID == appargs.CommAppArg.MID_RouteCmd_CAL:
        try:
            amb_off, obj_off = map(float, recv.data.split(","))
        except Exception:
            events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                            "CAL cmd parse error")
            return

        with OFFSET_MUTEX:
            AMB_OFFSET, OBJ_OFFSET = amb_off, obj_off
        prevstate.update_fir1cal(AMB_OFFSET, OBJ_OFFSET)  # must exist in prevstate
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        f"FIR1 offsets set to amb={AMB_OFFSET}, obj={OBJ_OFFSET}")
        return

    events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                    f"Unhandled MID {recv.MsgID}")

# ──────────────────────────────────────────────
# HK thread
# ──────────────────────────────────────────────

def send_hk(main_q: Queue):
    while FIRAPP1_RUNSTATUS:
        hk = msgstructure.MsgStructure()
        msgstructure.send_msg(main_q, hk,
                              appargs.FirApp1Arg.AppID,
                              appargs.HkAppArg.AppID,
                              appargs.FirApp1Arg.MID_SendHK,
                              str(FIRAPP1_RUNSTATUS))
        time.sleep(1)

# ──────────────────────────────────────────────
# Sensor threads
# ──────────────────────────────────────────────

def read_fir1_data(mux, sensor):
    """Read FIR1 sensor data continuously."""
    global FIRAPP1_RUNSTATUS, FIR1_AMB, FIR1_OBJ
    while FIRAPP1_RUNSTATUS:
        try:
            amb, obj = fir1.read_fir1(mux, sensor)
            FIR1_AMB = amb
            FIR1_OBJ = obj
        except Exception as e:
            events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                            f"FIR1 read error: {e}")
        time.sleep(0.1)  # 10 Hz


def send_fir1_data(main_q: Queue):
    cnt = 0
    fl_msg = msgstructure.MsgStructure()
    tlm_msg = msgstructure.MsgStructure()

    while FIRAPP1_RUNSTATUS:
        # Flightlogic 10 Hz
        msgstructure.fill_msg(fl_msg,
                              appargs.FirApp1Arg.AppID,
                              appargs.FlightlogicAppArg.AppID,
                              appargs.FirApp1Arg.MID_SendFIR1Data,
                              f"{AMB_TEMP:.2f},{OBJ_TEMP:.2f}")
        main_q.put(msgstructure.pack_msg(fl_msg))

        # COMM 1 Hz
        if cnt % 10 == 0:
            msgstructure.fill_msg(tlm_msg,
                                  appargs.FirApp1Arg.AppID,
                                  appargs.CommAppArg.AppID,
                                  appargs.FirApp1Arg.MID_SendFIR1Data,
                                  f"{AMB_TEMP:.2f},{OBJ_TEMP:.2f}")
            main_q.put(msgstructure.pack_msg(tlm_msg))

        cnt += 1
        time.sleep(0.1)  # 10 Hz

# ──────────────────────────────────────────────
# Main functions
# ──────────────────────────────────────────────

def firapp1_init():
    """Initialize FIR1 sensor and start threads."""
    global FIRAPP1_RUNSTATUS
    FIRAPP1_RUNSTATUS = True

    try:
        mux, sensor = fir1.init_fir1()
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        "FIR1 sensor initialized successfully")

        # Start threads
        threads = [
            threading.Thread(target=resilient_thread, args=(send_hk, (main_queue,), "HK"), daemon=True),
            threading.Thread(target=resilient_thread, args=(read_fir1_data, (mux, sensor), "READ"), daemon=True),
            threading.Thread(target=resilient_thread, args=(send_fir1_data, (main_queue,), "SEND"), daemon=True)
        ]

        for t in threads:
            t.start()

        return mux

    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                        f"FIR1 initialization failed: {e}")
        raise

def firapp1_terminate(mux):
    """Terminate FIR1 sensor and cleanup."""
    global FIRAPP1_RUNSTATUS
    FIRAPP1_RUNSTATUS = False

    try:
        fir1.terminate_fir1(mux)
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        "FIR1 sensor terminated")
    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                        f"FIR1 termination error: {e}")

def resilient_thread(target, args=(), name=None):
    """Thread wrapper with error handling."""
    try:
        target(*args)
    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                        f"Thread {name} error: {e}")

def firapp1_main(main_q: Queue, main_pipe: connection.Connection):
    """Main FIR1 application loop."""
    global main_queue
    main_queue = main_q

    # Load previous calibration
    try:
        amb_off, obj_off = prevstate.get_fir1cal()
        global AMB_OFFSET, OBJ_OFFSET
        AMB_OFFSET, OBJ_OFFSET = amb_off, obj_off
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        f"Loaded FIR1 calibration: amb={AMB_OFFSET}, obj={OBJ_OFFSET}")
    except Exception as e:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.warning,
                        f"Could not load FIR1 calibration: {e}")

    # Initialize sensor
    mux = firapp1_init()

    # Main message loop
    try:
        while FIRAPP1_RUNSTATUS:
            # Non-blocking receive with timeout
            if main_pipe.poll(1.0):  # 1초 타임아웃
                try:
                    recv_msg = main_pipe.recv()
                    unpacked_msg = msgstructure.MsgStructure()
                    msgstructure.unpack_msg(unpacked_msg, recv_msg)
                    command_handler(main_q, unpacked_msg)
                except Exception as e:
                    events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.error,
                                    f"Message handling error: {e}")
                    time.sleep(0.1)
            else:
                # 타임아웃 시 루프 계속
                continue

    except KeyboardInterrupt:
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        "FIRAPP1 interrupted by user")

    finally:
        firapp1_terminate(mux)
        events.LogEvent(appargs.FirApp1Arg.AppName, events.EventType.info,
                        "FIRAPP1 terminated") 