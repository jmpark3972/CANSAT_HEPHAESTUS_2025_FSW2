# Main Flight Software Code for Cansat Mission (Safe Version)
# Author : Hyeon Lee
# Modified for bus error prevention

# Sys library is needed to exit app
import sys
import os
import signal
import atexit
import time
import gc
import psutil
from datetime import datetime

MAINAPP_RUNSTATUS = True
_termination_in_progress = False

def safe_print(message: str):
    """Safe print function that won't cause issues"""
    try:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {message}")
        sys.stdout.flush()
    except:
        pass

def get_memory_usage():
    """Get current memory usage"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        return {
            'rss_mb': memory_info.rss / 1024 / 1024,
            'vms_mb': memory_info.vms / 1024 / 1024,
            'percent': process.memory_percent()
        }
    except Exception as e:
        safe_print(f"Memory check failed: {e}")
        return {}

def safe_import_module(module_name: str, import_path: str):
    """Safely import a module with error handling"""
    safe_print(f"Loading {module_name}...")
    
    initial_memory = get_memory_usage()
    if initial_memory:
        safe_print(f"Memory before {module_name}: {initial_memory['rss_mb']:.1f}MB")
    
    try:
        # Force garbage collection before import
        collected = gc.collect()
        if collected > 0:
            safe_print(f"Garbage collected: {collected} objects")
        
        # Import the module
        module = __import__(import_path, fromlist=['*'])
        safe_print(f"✓ {module_name} loaded successfully")
        
        # Check memory after import
        final_memory = get_memory_usage()
        if final_memory and initial_memory:
            memory_diff = final_memory['rss_mb'] - initial_memory['rss_mb']
            safe_print(f"Memory increase: {memory_diff:.2f}MB")
        
        return module, None
        
    except Exception as e:
        error_msg = f"✗ {module_name} failed to load: {e}"
        safe_print(error_msg)
        return None, str(e)

# Load core libraries first
safe_print("Loading core libraries...")

# Custom libraries - load one by one with error handling
core_modules = [
    ("lib.appargs", "appargs"),
    ("lib.msgstructure", "msgstructure"),
    ("lib.logging", "logging"),
    ("lib.types", "types"),
]

loaded_modules = {}
failed_modules = []

for import_path, module_name in core_modules:
    module, error = safe_import_module(module_name, import_path)
    if module:
        loaded_modules[module_name] = module
    else:
        failed_modules.append((module_name, error))
        safe_print(f"Critical module {module_name} failed to load - system may be unstable")

# Check if critical modules loaded
if 'appargs' not in loaded_modules or 'msgstructure' not in loaded_modules:
    safe_print("Critical modules failed to load. Exiting...")
    sys.exit(1)

# Import from loaded modules
appargs = loaded_modules['appargs']
msgstructure = loaded_modules['msgstructure']
logging = loaded_modules.get('logging')
types = loaded_modules.get('types')

# Multiprocessing Library is used on Python FSW V2
# Each application should have its own runloop
# Import the application and execute the runloop here.

from multiprocessing import Process, Queue, Pipe, connection

# Load configuration files with error handling
safe_print("Loading configuration...")

config_module, config_error = safe_import_module("config", "lib.config")
if config_module:
    config = config_module
    safe_print("✓ Configuration loaded")
else:
    safe_print(f"✗ Configuration failed to load: {config_error}")
    # Use default configuration
    config = None

# Load resource management modules
safe_print("Loading resource management...")

resource_manager_module, rm_error = safe_import_module("resource_manager", "lib.resource_manager")
memory_optimizer_module, mo_error = safe_import_module("memory_optimizer", "lib.memory_optimizer")
log_rotation_module, lr_error = safe_import_module("log_rotation", "lib.log_rotation")

# Initialize resource management if available
if resource_manager_module and hasattr(resource_manager_module, 'start_resource_monitoring'):
    try:
        resource_manager_module.start_resource_monitoring()
        safe_print("✓ Resource monitoring started")
    except Exception as e:
        safe_print(f"✗ Resource monitoring failed: {e}")

if memory_optimizer_module and hasattr(memory_optimizer_module, 'start_memory_optimization'):
    try:
        memory_optimizer_module.start_memory_optimization()
        safe_print("✓ Memory optimization started")
    except Exception as e:
        safe_print(f"✗ Memory optimization failed: {e}")

# Initialize log rotation if available
log_rotator = None
if log_rotation_module and hasattr(log_rotation_module, 'LogRotator'):
    try:
        log_rotator = log_rotation_module.LogRotator(max_size_mb=10, max_age_days=30)
        safe_print("✓ Log rotation initialized")
    except Exception as e:
        safe_print(f"✗ Log rotation failed: {e}")

# Check configuration
if config and hasattr(config, 'get_config'):
    fsw_mode = config.get_config("FSW_MODE")
    if fsw_mode == "NONE":
        safe_print("CONFIG IS SELECTED AS NONE, TERMINATING FSW")
        sys.exit(0)
else:
    safe_print("Using default FSW mode: PAYLOAD")

# Load previous state
prevstate_module, ps_error = safe_import_module("prevstate", "lib.prevstate")
if prevstate_module:
    try:
        prevstate = prevstate_module
        safe_print("✓ Previous state loaded")
    except Exception as e:
        safe_print(f"✗ Previous state failed: {e}")
        prevstate = None

main_queue = Queue()

class app_elements:
    process : Process = None
    pipe : connection.Connection = None

app_dict: dict = {}

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """Safe logging function"""
    try:
        if logging and hasattr(logging, 'log'):
            formatted_message = f"[{appargs.MainAppArg.AppName}] [{level}] {message}"
            logging.log(formatted_message, printlogs)
        else:
            safe_print(f"[{level}] {message}")
    except Exception as e:
        safe_print(f"Logging failed: {e}")
        safe_print(f"Original message: {message}")

def terminate_FSW():
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        return
    _termination_in_progress = True
    safe_print("FSW termination process starting...")
    
    MAINAPP_RUNSTATUS = False

    try:
        # Stop resource monitoring
        if resource_manager_module and hasattr(resource_manager_module, 'stop_resource_monitoring'):
            resource_manager_module.stop_resource_monitoring()
        if memory_optimizer_module and hasattr(memory_optimizer_module, 'stop_memory_optimization'):
            memory_optimizer_module.stop_memory_optimization()
        safe_log("Resource monitoring stopped", "INFO", True)
        
        # Rotate logs
        if log_rotator and hasattr(log_rotator, 'rotate_logs'):
            log_rotator.rotate_logs()
        safe_log("Log rotation completed", "INFO", True)
        
        # Close logging system
        if logging and hasattr(logging, 'close_dual_logging_system'):
            logging.close_dual_logging_system()
        safe_log("Logging system cleaned up", "INFO", True)
    except Exception as e:
        safe_print(f"System cleanup failed: {e}")

    # Create termination message
    if msgstructure and hasattr(msgstructure, 'MsgStructure'):
        termination_message = msgstructure.MsgStructure()
        msgstructure.fill_msg(termination_message, appargs.MainAppArg.AppID, appargs.MainAppArg.AppID, appargs.MainAppArg.MID_TerminateProcess, "")
        termination_message_to_send = msgstructure.pack_msg(termination_message)

        # Send termination message
        for appID in app_dict:
            if app_dict[appID].process and app_dict[appID].process.is_alive():
                safe_log(f"Terminating AppID {appID}", "INFO", True)
                try:
                    app_dict[appID].pipe.send(termination_message_to_send)
                except Exception as e:
                    safe_log(f"Failed to send termination to {appID}: {e}", "ERROR", True)
    
    time.sleep(0.5)

    # Terminate processes
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            safe_log(f"Joining AppID {appID}", "INFO", True)
            try:
                safe_log(f"Force terminating AppID {appID}", "WARNING", True)
                app_dict[appID].process.terminate()
                app_dict[appID].process.join(timeout=1)
                if app_dict[appID].process.is_alive():
                    safe_log(f"Force killing AppID {appID}", "WARNING", True)
                    app_dict[appID].process.kill()
                    app_dict[appID].process.join(timeout=0.5)
                safe_log(f"Terminating AppID {appID} complete", "INFO", True)
            except Exception as e:
                safe_log(f"Error joining {appID}: {e}", "ERROR", True)
                try:
                    app_dict[appID].process.kill()
                except Exception as kill_error:
                    safe_log(f"Process force kill error: {kill_error}", "ERROR", True)

    safe_log("Manual termination! Resetting prev state file", "INFO", True)
    if prevstate and hasattr(prevstate, 'reset_prevstate'):
        prevstate.reset_prevstate()
    
    safe_log("All termination process complete", "INFO", True)
    
    safe_print("FSW termination complete. Exiting program.")
    os._exit(0)

def signal_handler(signum, frame):
    global MAINAPP_RUNSTATUS, _termination_in_progress
    if _termination_in_progress:
        safe_print("Already terminating. Force exit...")
        os._exit(0)
        return
    
    safe_print(f"Signal {signum} received, terminating FSW...")
    _termination_in_progress = True
    MAINAPP_RUNSTATUS = False
    
    # Quick termination
    for appID in app_dict:
        if app_dict[appID].process and app_dict[appID].process.is_alive():
            try:
                app_dict[appID].process.kill()
            except:
                pass
    
    safe_print("Force termination complete. Exiting program.")
    os._exit(0)

# Setup signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load applications with error handling
safe_print("Loading applications...")

# Define applications to load
applications = [
    ("hk.hkapp", "hkapp", "hkapp_main", "HK"),
    ("barometer.barometerapp", "barometerapp", "barometerapp_main", "Barometer"),
    ("gps.gpsapp", "gpsapp", "gpsapp_main", "GPS"),
    ("imu.imuapp", "imuapp", "imuapp_main", "IMU"),
    ("flight_logic.flightlogicapp", "flightlogicapp", "flightlogicapp_main", "FlightLogic"),
    ("comm.commapp", "commapp", "commapp_main", "Comm"),
    ("motor.motorapp", "motorapp", "motorapp_main", "Motor"),
    ("fir1.firapp1", "firapp1", "firapp1_main", "FIR1"),
    ("thermis.thermisapp", "thermisapp", "thermisapp_main", "Thermis"),
    ("tmp007.tmp007app", "tmp007app", "tmp007app_main", "TMP007"),
    ("thermal_camera.thermo_cameraapp", "thermo_cameraapp", "thermocamapp_main", "Thermal Camera"),
    ("thermo.thermoapp", "thermoapp", "thermoapp_main", "Thermo"),
    ("camera.cameraapp", "cameraapp", "cameraapp_main", "Camera"),
]

# Load applications one by one
for import_path, module_name, main_func_name, app_name in applications:
    safe_print(f"Loading {app_name} app...")
    
    module, error = safe_import_module(module_name, import_path)
    if module and hasattr(module, main_func_name):
        try:
            parent_pipe, child_pipe = Pipe()
            
            app_elements_instance = app_elements()
            app_elements_instance.process = Process(target=getattr(module, main_func_name), args=(main_queue, child_pipe,))
            app_elements_instance.pipe = parent_pipe
            
            # Get AppID from appargs
            app_id = None
            for attr_name in dir(appargs):
                if attr_name.endswith('AppArg') and hasattr(getattr(appargs, attr_name), 'AppID'):
                    arg_obj = getattr(appargs, attr_name)
                    if hasattr(arg_obj, 'AppName') and app_name.lower() in arg_obj.AppName.lower():
                        app_id = arg_obj.AppID
                        break
            
            if app_id is not None:
                app_dict[app_id] = app_elements_instance
                safe_log(f"{app_name} app loaded successfully", "INFO", True)
            else:
                safe_print(f"Warning: Could not find AppID for {app_name}")
                
        except Exception as e:
            safe_log(f"{app_name} app load failed: {e}", "ERROR", True)
    else:
        safe_log(f"{app_name} app load failed: {error}", "ERROR", True)

# Main Runloop
def runloop(Main_Queue : Queue):
    global MAINAPP_RUNSTATUS
    start_time = time.time()
    max_runtime = 3600  # 1 hour max runtime
    
    # Process status monitoring
    last_health_check = time.time()
    
    try:
        while MAINAPP_RUNSTATUS:
            if time.time() - start_time > max_runtime:
                safe_log("Maximum runtime reached, terminating FSW", "WARNING", True)
                break
            
            # Periodic process status check (every 10 seconds)
            if time.time() - last_health_check > 10:
                last_health_check = time.time()
                
                for appID in app_dict:
                    if app_dict[appID].process and not app_dict[appID].process.is_alive():
                        safe_log(f"Process {appID} is dead, continuing", "WARNING", True)
            
            try:
                recv_msg = Main_Queue.get(timeout=0.5)

                if not isinstance(recv_msg, str):
                    safe_log(f"Invalid message type: {type(recv_msg)}", "ERROR", True)
                    continue

                if msgstructure and hasattr(msgstructure, 'MsgStructure'):
                    unpacked_msg = msgstructure.MsgStructure()
                    if not msgstructure.unpack_msg(unpacked_msg, recv_msg):
                        safe_log(f"Failed to unpack message: {recv_msg}", "ERROR", True)
                        continue
                    
                    # Handle messages
                    if unpacked_msg.receiver_app == appargs.MainAppArg.AppID:
                        safe_log(f"Main app received message: {unpacked_msg.MsgID} from {unpacked_msg.sender_app}", "DEBUG", True)
                        continue
                    
                    elif unpacked_msg.receiver_app in app_dict:
                        try:
                            if app_dict[unpacked_msg.receiver_app].pipe is None:
                                safe_log(f"Pipe is None for {unpacked_msg.receiver_app}", "ERROR", True)
                                continue
                            
                            if not app_dict[unpacked_msg.receiver_app].process.is_alive():
                                safe_log(f"Process {unpacked_msg.receiver_app} is dead, skipping message", "WARNING", True)
                                continue
                                
                            app_dict[unpacked_msg.receiver_app].pipe.send(unpacked_msg)
                        except BrokenPipeError:
                            safe_log(f"Broken pipe for {unpacked_msg.receiver_app}, but continuing", "WARNING", True)
                        except Exception as e:
                            safe_log(f"Failed to send message to {unpacked_msg.receiver_app}: {e}", "ERROR", True)
                    else:
                        safe_log(f"Unknown receiver app: {unpacked_msg.receiver_app}", "WARNING", True)
                        continue
                        
            except Exception as e:
                if "Empty" not in str(e):
                    safe_log(f"Main loop error: {e}", "ERROR", True)

    except KeyboardInterrupt:
        safe_log("KeyboardInterrupt Detected, Terminating FSW", "INFO", True)
        MAINAPP_RUNSTATUS = False
        safe_print("KeyboardInterrupt detected. Force terminating...")
        
        try:
            for appID in app_dict:
                if app_dict[appID].process and app_dict[appID].process.is_alive():
                    safe_print(f"Force terminating: {appID}")
                    app_dict[appID].process.kill()
        except Exception as e:
            safe_log(f"KeyboardInterrupt process force termination error: {e}", "ERROR", True)
        
        os._exit(0)
    except Exception as e:
        safe_log(f"Critical error in main loop: {e}", "ERROR", True)
        MAINAPP_RUNSTATUS = False
        safe_print("Critical error occurred. Force terminating...")
        os._exit(0)

    safe_print("Normal termination complete.")
    return

def cleanup_on_exit():
    safe_print("Program exit cleanup...")
    try:
        terminate_FSW()
    except Exception as e:
        safe_log(f"Cleanup on exit error: {e}", "ERROR", True)

if __name__ == '__main__':
    try:
        safe_log("Logging system initialization complete", "INFO", True)
    except Exception as e:
        safe_print(f"Logging system initialization failed: {e}")

    atexit.register(cleanup_on_exit)

    try:
        # Start processes
        core_apps = list(app_dict.keys())
        
        for appID in core_apps:
            if app_dict[appID].process is not None:
                try:
                    app_dict[appID].process.start()
                    safe_log(f"Started process for {appID}", "INFO", True)
                    time.sleep(0.3)  # Longer wait for stability
                except Exception as e:
                    safe_log(f"Failed to start {appID}: {e}", "WARNING", True)
                    continue
                    
    except Exception as e:
        safe_log(f"Error starting processes: {e}", "ERROR", True)
        pass

    runloop(main_queue) 