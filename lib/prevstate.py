import os
from lib import events

# Prevstate.py, store and restore prev state

PREV_ALT_CAL = 0
PREV_STATE  = 0
PREV_MAX_ALT = 0
PREV_THERMO_TOFF = 0.0
PREV_THERMO_HOFF = 0.0

prevstate_file_path = 'lib/prevstate.txt'

def write_prevstate_file():
    global PREV_ALT_CAL
    global PREV_STATE
    global PREV_MAX_ALT
    global PREV_THERMO_TOFF
    global PREV_THERMO_HOFF

    content = f"""# Prevstate.txt
# The Config below stores the prev flight data
# DO NOT EDIT MANUALLY
STATE={PREV_STATE}
ALTCAL={PREV_ALT_CAL}
MAXALT={PREV_MAX_ALT}
THERMO_TOFF={PREV_THERMO_TOFF}
THERMO_HOFF={PREV_THERMO_HOFF}"""

    with open(prevstate_file_path, 'w') as file:
        file.write(content)

def reset_prevstate():
    global PREV_STATE
    global PREV_ALT_CAL
    global PREV_MAX_ALT

    PREV_STATE = "NONE"
    PREV_ALT_CAL = "NONE"
    PREV_MAX_ALT = "NONE"
    write_prevstate_file()
    return

def update_prevstate(state:int):
    global PREV_STATE
    PREV_STATE = state
    write_prevstate_file()
    return

def update_altcal(alt:float):
    global PREV_ALT_CAL
    PREV_ALT_CAL = alt
    write_prevstate_file()
    return

def update_maxalt(alt:float):
    global PREV_MAX_ALT
    PREV_MAX_ALT = alt
    write_prevstate_file()

def update_thermocal(temp_off: float, humi_off: float):
    global PREV_THERMO_TOFF, PREV_THERMO_HOFF
    PREV_THERMO_TOFF = temp_off
    PREV_THERMO_HOFF = humi_off
    write_prevstate_file()
    return

def init_prevstate():

    global PREV_STATE
    global PREV_ALT_CAL
    global PREV_MAX_ALT
    global PREV_THERMO_TOFF
    global PREV_THERMO_HOFF
    if not os.path.exists(prevstate_file_path):
        print(f"#################################################################\n\nPrevstate file does not exist, Using initial state\n\n#################################################################")
        write_prevstate_file()

    else:
        with open(prevstate_file_path, 'r') as file:
            lines = file.readlines()

        prevstate_lines = [line.strip() for line in lines if not line.strip().startswith('#')]
        for prevstate_line in prevstate_lines:
            prevstate_line = prevstate_line.strip().replace(" ", "").replace("\t", "")

            if "STATE=" in prevstate_line:
                prev_state = prevstate_line.split("=")[1].strip()
                if prev_state == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev state is NONE")
                    PREV_STATE = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev state is {prev_state}")
                    PREV_STATE = int(prev_state)

            elif "ALTCAL=" in prevstate_line:
                prev_altcal = prevstate_line.split("=")[1].strip()
                if prev_altcal == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev calibration is NONE")
                    PREV_ALT_CAL = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev calibration is {prev_altcal}")
                    PREV_ALT_CAL = float(prev_altcal)

            elif "MAXALT=" in prevstate_line:
                prev_maxalt = prevstate_line.split("=")[1].strip()
                if prev_maxalt == "NONE":
                    events.LogEvent("RECOVERY", events.EventType.info, "Prev maxalt is NONE")
                    PREV_MAX_ALT = 0
                    continue
                else:
                    events.LogEvent("RECOVERY", events.EventType.info, f"Prev maxalt is {prev_maxalt}")
                    PREV_MAX_ALT = float(prev_maxalt)
            elif "THERMO_TOFF=" in prevstate_line:
                try:
                    PREV_THERMO_TOFF = float(prevstate_line.split("=")[1].strip())
                except Exception:
                    PREV_THERMO_TOFF = 0.0
            elif "THERMO_HOFF=" in prevstate_line:
                try:
                    PREV_THERMO_HOFF = float(prevstate_line.split("=")[1].strip())
                except Exception:
                    PREV_THERMO_HOFF = 0.0
    return