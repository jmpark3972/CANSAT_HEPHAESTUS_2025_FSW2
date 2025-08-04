# Events.py
# Author : Hyeon Lee
# Print, save Event logs
import os
from lib import logging
from datetime import datetime

# Create log directory if it doesn't exist
log_dir = './eventlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

# Open the log files depending on error types
infologfile = open(os.path.join(log_dir, 'info_event.txt'), 'a')
errorlogfile = open(os.path.join(log_dir, 'error_event.txt'), 'a') 
debuglogfile = open(os.path.join(log_dir, 'debug_event.txt'), 'a') 

# Write the log file generation message
logging.logdata(infologfile, "Log file generated")
logging.logdata(errorlogfile, "Log file generated")
logging.logdata(errorlogfile, "Log file generated")

class EventType:
    error = 0
    info = 1
    debug = 2
    warning = 3

def LogEvent(app_name : str ,event_type : int, event_msg : str, print_event=True):

    event_type_str_arr = ["ERROR", "INFO","DEBUG","WARNING"]
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    data_to_log = f"{event_type_str_arr[event_type]} | {app_name} : {event_msg}"

    log_to_write = f"[{t}] {data_to_log}\n"

    # Save the logs into separate file by event type
    if event_type == EventType.info:
        infologfile.write(log_to_write)
        infologfile.flush()
    elif event_type == EventType.error:
        errorlogfile.write(log_to_write)
        errorlogfile.flush()
    elif event_type == EventType.debug:
        debuglogfile.write(log_to_write)
        debuglogfile.flush()
    elif event_type == EventType.warning:
        errorlogfile.write(log_to_write)  # Write warnings to error log
        errorlogfile.flush()

    if print_event:
        print(log_to_write, end="")
    return