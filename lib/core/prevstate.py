import os
from ..logging import safe_log

# Previous state variables
PREV_STATE = "0"
PREV_ALT_CAL = "0"
PREV_MAX_ALT = "0"

def update_prevstate(state: str):
    """Update previous state"""
    global PREV_STATE
    PREV_STATE = state
    try:
        with open("lib/prevstate.txt", "w") as f:
            f.write(f"PREV_STATE={state}\n")
            f.write(f"PREV_ALT_CAL={PREV_ALT_CAL}\n")
            f.write(f"PREV_MAX_ALT={PREV_MAX_ALT}\n")
    except Exception as e:
        safe_log(f"Failed to update prevstate: {e}", True)

def update_alt_cal(alt_cal: str):
    """Update altitude calibration"""
    global PREV_ALT_CAL
    PREV_ALT_CAL = alt_cal
    try:
        with open("lib/prevstate.txt", "w") as f:
            f.write(f"PREV_STATE={PREV_STATE}\n")
            f.write(f"PREV_ALT_CAL={alt_cal}\n")
            f.write(f"PREV_MAX_ALT={PREV_MAX_ALT}\n")
    except Exception as e:
        safe_log(f"Failed to update alt_cal: {e}", True)

def update_maxalt(max_alt: str):
    """Update maximum altitude"""
    global PREV_MAX_ALT
    PREV_MAX_ALT = max_alt
    try:
        with open("lib/prevstate.txt", "w") as f:
            f.write(f"PREV_STATE={PREV_STATE}\n")
            f.write(f"PREV_ALT_CAL={PREV_ALT_CAL}\n")
            f.write(f"PREV_MAX_ALT={max_alt}\n")
    except Exception as e:
        safe_log(f"Failed to update max_alt: {e}", True)

def reset_prevstate():
    """Reset previous state"""
    global PREV_STATE, PREV_ALT_CAL, PREV_MAX_ALT
    PREV_STATE = "0"
    PREV_ALT_CAL = "0"
    PREV_MAX_ALT = "0"
    try:
        with open("lib/prevstate.txt", "w") as f:
            f.write(f"PREV_STATE=0\n")
            f.write(f"PREV_ALT_CAL=0\n")
            f.write(f"PREV_MAX_ALT=0\n")
        safe_log("Previous state reset", True)
    except Exception as e:
        safe_log(f"Failed to reset prevstate: {e}", True)

def load_prevstate():
    """Load previous state from file"""
    global PREV_STATE, PREV_ALT_CAL, PREV_MAX_ALT
    try:
        with open("lib/prevstate.txt", "r") as f:
            for line in f:
                if line.startswith("PREV_STATE="):
                    PREV_STATE = line.split("=")[1].strip()
                elif line.startswith("PREV_ALT_CAL="):
                    PREV_ALT_CAL = line.split("=")[1].strip()
                elif line.startswith("PREV_MAX_ALT="):
                    PREV_MAX_ALT = line.split("=")[1].strip()
        safe_log(f"Loaded previous state: {PREV_STATE}, {PREV_ALT_CAL}, {PREV_MAX_ALT}", True)
    except Exception as e:
        safe_log(f"Failed to load prevstate: {e}", True)

# Load previous state on import
load_prevstate()