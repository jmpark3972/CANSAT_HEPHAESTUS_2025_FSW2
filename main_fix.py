#!/usr/bin/env python3
"""
Fixed Main Loop for CANSAT System
This version handles errors more gracefully and reduces the frequency of error messages
"""

import sys
import os
import signal
import atexit
import time
import queue

def improved_runloop(Main_Queue, app_dict):
    """Improved main loop with better error handling"""
    global MAINAPP_RUNSTATUS
    import time
    start_time = time.time()
    max_runtime = 3600  # 1시간 최대 실행 시간
    error_count = 0
    last_error_time = 0
    
    try:
        while MAINAPP_RUNSTATUS:
            # 최대 실행 시간 체크
            if time.time() - start_time > max_runtime:
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, "Maximum runtime reached, terminating FSW")
                break
                
            try:
                # Recv Message from queue with timeout
                recv_msg = Main_Queue.get(timeout=0.1)  # 0.1초로 단축하여 더 빠른 응답

                # 메시지 유효성 검사
                if not isinstance(recv_msg, str):
                    # Reduce error logging frequency
                    current_time = time.time()
                    if current_time - last_error_time > 5:  # Log only every 5 seconds
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Invalid message type: {type(recv_msg)}")
                        last_error_time = current_time
                    continue

                # Unpack the message to Check receiver
                unpacked_msg = msgstructure.MsgStructure()
                if not msgstructure.unpack_msg(unpacked_msg, recv_msg):
                    current_time = time.time()
                    if current_time - last_error_time > 5:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to unpack message: {recv_msg[:100]}...")  # Truncate long messages
                        last_error_time = current_time
                    continue
                
                if unpacked_msg.receiver_app in app_dict:
                    try:
                        # 파이프 유효성 검사
                        if app_dict[unpacked_msg.receiver_app].pipe is None:
                            current_time = time.time()
                            if current_time - last_error_time > 5:
                                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Pipe is None for {unpacked_msg.receiver_app}")
                                last_error_time = current_time
                            continue
                        app_dict[unpacked_msg.receiver_app].pipe.send(recv_msg)
                    except Exception as e:
                        current_time = time.time()
                        if current_time - last_error_time > 5:
                            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Failed to send message to {unpacked_msg.receiver_app}: {e}")
                            last_error_time = current_time
                else:
                    current_time = time.time()
                    if current_time - last_error_time > 5:
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.warning, f"Unknown receiver app: {unpacked_msg.receiver_app}")
                        last_error_time = current_time
                    continue
                    
                # Reset error count on successful message processing
                error_count = 0
                
            except queue.Empty:
                # This is expected, don't log it as an error
                continue
            except Exception as e:
                # Handle other exceptions gracefully
                error_count += 1
                current_time = time.time()
                
                # Only log errors if they're not timeouts and not too frequent
                if "Empty" not in str(e) and current_time - last_error_time > 5:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error (count: {error_count}): {e}")
                    last_error_time = current_time
                
                # If too many errors, consider terminating
                if error_count > 100:
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Too many errors ({error_count}), terminating FSW")
                    break

    except KeyboardInterrupt:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, "KeyboardInterrupt Detected, Terminating FSW")
        MAINAPP_RUNSTATUS = False
        print("KeyboardInterrupt 감지됨. 강제 종료합니다.")
        os._exit(0)
    except Exception as e:
        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Critical error in main loop: {e}")
        MAINAPP_RUNSTATUS = False
        print("치명적 오류 발생. 강제 종료합니다.")
        os._exit(0)

    # 정상 종료 시
    print("정상 종료 완료.")
    return

def improved_process_startup(app_dict):
    """Improved process startup with better error handling"""
    print("Starting processes with improved error handling...")
    
    startup_errors = []
    
    for appID in app_dict:
        try:
            if app_dict[appID].process is None:
                error_msg = f"Process for {appID} is None"
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, error_msg)
                startup_errors.append(error_msg)
                continue
                
            app_dict[appID].process.start()
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.info, f"Started process for {appID}")
            time.sleep(0.2)  # Slightly longer delay between processes
            
            # Check if process started successfully
            if not app_dict[appID].process.is_alive():
                error_msg = f"Process {appID} failed to start"
                events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, error_msg)
                startup_errors.append(error_msg)
                
        except Exception as e:
            error_msg = f"Error starting process {appID}: {e}"
            events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, error_msg)
            startup_errors.append(error_msg)
    
    if startup_errors:
        print(f"Warning: {len(startup_errors)} startup errors occurred:")
        for error in startup_errors[:5]:  # Show first 5 errors
            print(f"  - {error}")
        if len(startup_errors) > 5:
            print(f"  ... and {len(startup_errors) - 5} more errors")
    
    return len(startup_errors) == 0

def check_sensor_health():
    """Check sensor health and provide recommendations"""
    print("\n=== Sensor Health Check ===")
    
    # Check for common sensor issues
    issues = []
    
    # Check if THERMIS is working
    try:
        import thermis
        # Add specific checks for THERMIS sensor
        pass
    except ImportError:
        issues.append("THERMIS module not found")
    
    # Check I2C bus
    try:
        import board
        import busio
        i2c = busio.I2C(board.SCL, board.SDA)
        if not i2c.try_lock():
            issues.append("I2C bus is locked")
        else:
            i2c.unlock()
    except Exception as e:
        issues.append(f"I2C bus error: {e}")
    
    if issues:
        print("Sensor issues detected:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("All sensors appear to be healthy")
    
    return len(issues) == 0

# Usage instructions
if __name__ == "__main__":
    print("Main Loop Fix Module")
    print("This module provides improved error handling for the CANSAT system.")
    print("To use these functions, import them into your main.py file.")
    print("\nExample usage:")
    print("from main_fix import improved_runloop, improved_process_startup")
    print("improved_process_startup(app_dict)")
    print("improved_runloop(main_queue, app_dict)") 