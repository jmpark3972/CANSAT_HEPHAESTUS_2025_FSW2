#!/usr/bin/env python3
"""
CANSAT FSW Bus Error Diagnostic Script
This script helps identify which module is causing the bus error by testing them individually.
"""

import sys
import os
import time
import psutil
import gc
import signal
import traceback
from datetime import datetime

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def safe_print(message: str):
    """Safe print function that won't cause issues"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S.%f')[:-3]}] {message}")
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

def test_module_import(module_name: str, import_path: str):
    """Test importing a specific module"""
    safe_print(f"Testing import: {module_name}")
    
    initial_memory = get_memory_usage()
    safe_print(f"Initial memory: {initial_memory}")
    
    try:
        # Force garbage collection before import
        collected = gc.collect()
        safe_print(f"Garbage collected: {collected} objects")
        
        # Import the module
        module = __import__(import_path, fromlist=['*'])
        safe_print(f"✓ {module_name} imported successfully")
        
        # Check memory after import
        final_memory = get_memory_usage()
        safe_print(f"Final memory: {final_memory}")
        
        if initial_memory and final_memory:
            memory_diff = final_memory['rss_mb'] - initial_memory['rss_mb']
            safe_print(f"Memory increase: {memory_diff:.2f} MB")
        
        return True, None
        
    except Exception as e:
        error_msg = f"✗ {module_name} import failed: {e}"
        safe_print(error_msg)
        safe_print(f"Error type: {type(e).__name__}")
        safe_print(f"Traceback: {traceback.format_exc()}")
        return False, str(e)

def test_module_initialization(module_name: str, init_function: str):
    """Test module initialization"""
    safe_print(f"Testing initialization: {module_name}.{init_function}")
    
    try:
        # Get the module
        module = sys.modules.get(module_name)
        if not module:
            safe_print(f"Module {module_name} not found in sys.modules")
            return False, "Module not imported"
        
        # Get the initialization function
        if hasattr(module, init_function):
            init_func = getattr(module, init_function)
            if callable(init_func):
                # Test the initialization function
                result = init_func()
                safe_print(f"✓ {module_name}.{init_function} completed successfully")
                return True, None
            else:
                safe_print(f"✗ {init_function} is not callable")
                return False, f"{init_function} is not callable"
        else:
            safe_print(f"✗ {init_function} not found in {module_name}")
            return False, f"{init_function} not found"
            
    except Exception as e:
        error_msg = f"✗ {module_name}.{init_function} failed: {e}"
        safe_print(error_msg)
        safe_print(f"Error type: {type(e).__name__}")
        safe_print(f"Traceback: {traceback.format_exc()}")
        return False, str(e)

def test_system_resources():
    """Test system resource availability"""
    safe_print("Testing system resources...")
    
    try:
        # Check available memory
        memory = psutil.virtual_memory()
        safe_print(f"Total memory: {memory.total / 1024 / 1024 / 1024:.2f} GB")
        safe_print(f"Available memory: {memory.available / 1024 / 1024 / 1024:.2f} GB")
        safe_print(f"Memory usage: {memory.percent:.1f}%")
        
        # Check disk space
        disk = psutil.disk_usage('/')
        safe_print(f"Disk usage: {disk.percent:.1f}%")
        safe_print(f"Free disk space: {disk.free / 1024 / 1024 / 1024:.2f} GB")
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        safe_print(f"CPU usage: {cpu_percent:.1f}%")
        
        return True
        
    except Exception as e:
        safe_print(f"System resource check failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    safe_print("=" * 60)
    safe_print("CANSAT FSW Bus Error Diagnostic")
    safe_print("=" * 60)
    
    # Test system resources first
    safe_print("\n1. Testing system resources...")
    test_system_resources()
    
    # Define modules to test (in order of loading)
    modules_to_test = [
        ("lib.logging", "logging"),
        ("lib.config", "config"),
        ("lib.resource_manager", "resource_manager"),
        ("lib.memory_optimizer", "memory_optimizer"),
        ("lib.log_rotation", "log_rotation"),
        ("lib.prevstate", "prevstate"),
        ("lib.appargs", "appargs"),
        ("lib.msgstructure", "msgstructure"),
        ("lib.types", "types"),
        ("hk.hkapp", "hkapp"),
        ("barometer.barometerapp", "barometerapp"),
        ("gps.gpsapp", "gpsapp"),
        ("imu.imuapp", "imuapp"),
        ("flight_logic.flightlogicapp", "flightlogicapp"),
        ("comm.commapp", "commapp"),
        ("motor.motorapp", "motorapp"),
        ("fir1.firapp1", "firapp1"),
        ("thermis.thermisapp", "thermisapp"),
        ("tmp007.tmp007app", "tmp007app"),
        ("thermal_camera.thermo_cameraapp", "thermo_cameraapp"),
        ("thermo.thermoapp", "thermoapp"),
        ("camera.cameraapp", "cameraapp"),
    ]
    
    safe_print(f"\n2. Testing {len(modules_to_test)} modules...")
    
    failed_modules = []
    
    for i, (import_path, module_name) in enumerate(modules_to_test, 1):
        safe_print(f"\n--- Test {i}/{len(modules_to_test)}: {module_name} ---")
        
        # Test import
        success, error = test_module_import(module_name, import_path)
        
        if not success:
            failed_modules.append((module_name, error))
            safe_print(f"❌ {module_name} failed - stopping here")
            break
        
        # Small delay between modules
        time.sleep(0.1)
        
        # Force garbage collection
        collected = gc.collect()
        if collected > 0:
            safe_print(f"Garbage collected: {collected} objects")
    
    # Summary
    safe_print("\n" + "=" * 60)
    safe_print("DIAGNOSTIC SUMMARY")
    safe_print("=" * 60)
    
    if failed_modules:
        safe_print("❌ FAILED MODULES:")
        for module_name, error in failed_modules:
            safe_print(f"  - {module_name}: {error}")
        safe_print(f"\nThe bus error is likely caused by: {failed_modules[0][0]}")
    else:
        safe_print("✅ All modules imported successfully")
        safe_print("The bus error might be caused by:")
        safe_print("  1. Memory pressure during multiprocessing")
        safe_print("  2. Hardware access issues (I2C, GPIO, etc.)")
        safe_print("  3. System resource limitations")
    
    # Final memory check
    final_memory = get_memory_usage()
    safe_print(f"\nFinal memory usage: {final_memory}")
    
    safe_print("\nDiagnostic complete!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print("\nDiagnostic interrupted by user")
    except Exception as e:
        safe_print(f"\nDiagnostic failed with error: {e}")
        safe_print(f"Traceback: {traceback.format_exc()}") 