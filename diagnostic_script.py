#!/usr/bin/env python3
"""
CANSAT Diagnostic Script
This script helps identify and fix issues with the CANSAT system
"""

import os
import sys
import time
import subprocess
import psutil
from pathlib import Path

def check_system_resources():
    """Check system resources"""
    print("=== System Resources Check ===")
    
    # Memory usage
    memory = psutil.virtual_memory()
    print(f"Memory Usage: {memory.percent}% ({memory.used // 1024 // 1024}MB / {memory.total // 1024 // 1024}MB)")
    
    # Disk usage
    disk = psutil.disk_usage('/')
    print(f"Disk Usage: {disk.percent}% ({disk.used // 1024 // 1024}MB / {disk.total // 1024 // 1024}MB)")
    
    # CPU usage
    cpu_percent = psutil.cpu_percent(interval=1)
    print(f"CPU Usage: {cpu_percent}%")
    
    # Process count
    process_count = len(psutil.pids())
    print(f"Active Processes: {process_count}")
    
    return memory.percent < 90 and disk.percent < 95

def check_python_processes():
    """Check for running Python processes"""
    print("\n=== Python Processes Check ===")
    python_processes = []
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            if 'python' in proc.info['name'].lower():
                cmdline = ' '.join(proc.info['cmdline']) if proc.info['cmdline'] else ''
                if 'main.py' in cmdline:
                    python_processes.append(proc.info)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    if python_processes:
        print("Found running Python processes:")
        for proc in python_processes:
            print(f"  PID {proc['pid']}: {proc['name']} - {proc['cmdline']}")
    else:
        print("No running Python processes found")
    
    return python_processes

def check_i2c_devices():
    """Check I2C devices"""
    print("\n=== I2C Devices Check ===")
    
    try:
        # Check if i2cdetect is available
        result = subprocess.run(['which', 'i2cdetect'], capture_output=True, text=True)
        if result.returncode != 0:
            print("i2cdetect not found. Install i2c-tools package.")
            return False
        
        # Scan I2C bus 1
        result = subprocess.run(['i2cdetect', '-y', '1'], capture_output=True, text=True)
        if result.returncode == 0:
            print("I2C Bus 1 devices:")
            print(result.stdout)
        else:
            print("Failed to scan I2C bus 1")
            
        # Scan I2C bus 0
        result = subprocess.run(['i2cdetect', '-y', '0'], capture_output=True, text=True)
        if result.returncode == 0:
            print("I2C Bus 0 devices:")
            print(result.stdout)
        else:
            print("Failed to scan I2C bus 0")
            
    except Exception as e:
        print(f"Error checking I2C devices: {e}")
        return False
    
    return True

def check_serial_ports():
    """Check available serial ports"""
    print("\n=== Serial Ports Check ===")
    
    try:
        # Check for common serial devices
        serial_devices = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1', 
                         '/dev/serial0', '/dev/serial1', '/dev/ttyAMA0', '/dev/ttyAMA1']
        
        for device in serial_devices:
            if os.path.exists(device):
                print(f"Found serial device: {device}")
                
                # Check permissions
                try:
                    stat = os.stat(device)
                    print(f"  Permissions: {oct(stat.st_mode)[-3:]}")
                    print(f"  Owner: {stat.st_uid}")
                except Exception as e:
                    print(f"  Error checking permissions: {e}")
            else:
                print(f"Serial device not found: {device}")
                
    except Exception as e:
        print(f"Error checking serial ports: {e}")
        return False
    
    return True

def check_gpio_access():
    """Check GPIO access"""
    print("\n=== GPIO Access Check ===")
    
    try:
        # Check if pigpiod is running
        result = subprocess.run(['pgrep', 'pigpiod'], capture_output=True, text=True)
        if result.returncode == 0:
            print("pigpiod is running")
        else:
            print("pigpiod is not running")
            
        # Check GPIO permissions
        gpio_path = '/sys/class/gpio'
        if os.path.exists(gpio_path):
            print(f"GPIO sysfs available: {gpio_path}")
        else:
            print("GPIO sysfs not available")
            
    except Exception as e:
        print(f"Error checking GPIO access: {e}")
        return False
    
    return True

def check_python_dependencies():
    """Check Python dependencies"""
    print("\n=== Python Dependencies Check ===")
    
    required_packages = [
        'board', 'busio', 'adafruit_blinka', 'psutil', 'multiprocessing',
        'signal', 'threading', 'time', 'serial', 'pigpio'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} - MISSING")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install missing packages with: pip install " + ' '.join(missing_packages))
        return False
    
    return True

def check_file_permissions():
    """Check file permissions"""
    print("\n=== File Permissions Check ===")
    
    current_dir = Path.cwd()
    print(f"Current directory: {current_dir}")
    
    # Check main.py
    main_py = current_dir / 'main.py'
    if main_py.exists():
        stat = main_py.stat()
        print(f"main.py permissions: {oct(stat.st_mode)[-3:]}")
        print(f"main.py executable: {os.access(main_py, os.X_OK)}")
    else:
        print("main.py not found")
    
    # Check logs directory
    logs_dir = current_dir / 'logs'
    if logs_dir.exists():
        print(f"logs directory exists: {logs_dir}")
        print(f"logs writable: {os.access(logs_dir, os.W_OK)}")
    else:
        print("logs directory not found")
    
    # Check lib directory
    lib_dir = current_dir / 'lib'
    if lib_dir.exists():
        print(f"lib directory exists: {lib_dir}")
        print(f"lib readable: {os.access(lib_dir, os.R_OK)}")
    else:
        print("lib directory not found")

def suggest_fixes():
    """Suggest fixes for common issues"""
    print("\n=== Suggested Fixes ===")
    
    print("1. If THERMIS sensor is not found:")
    print("   - Check I2C connections")
    print("   - Verify Qwiic Mux channel selection")
    print("   - Check ADS1115 address (0x48-0x4B)")
    
    print("\n2. If sensors return 0.0 values:")
    print("   - Check I2C bus connections")
    print("   - Verify sensor power supply")
    print("   - Check for I2C address conflicts")
    
    print("\n3. If XBee is not connected:")
    print("   - Connect XBee USB adapter")
    print("   - Check USB permissions")
    print("   - Verify XBee configuration")
    
    print("\n4. If main loop errors occur:")
    print("   - Check message queue handling")
    print("   - Verify process communication")
    print("   - Check for memory leaks")
    
    print("\n5. General troubleshooting:")
    print("   - Restart the system")
    print("   - Check all hardware connections")
    print("   - Verify power supply stability")
    print("   - Check for loose cables")

def main():
    """Main diagnostic function"""
    print("CANSAT Diagnostic Script")
    print("=" * 50)
    
    # Run all checks
    system_ok = check_system_resources()
    python_processes = check_python_processes()
    i2c_ok = check_i2c_devices()
    serial_ok = check_serial_ports()
    gpio_ok = check_gpio_access()
    deps_ok = check_python_dependencies()
    check_file_permissions()
    
    # Summary
    print("\n=== Summary ===")
    print(f"System Resources: {'✓' if system_ok else '✗'}")
    print(f"I2C Devices: {'✓' if i2c_ok else '✗'}")
    print(f"Serial Ports: {'✓' if serial_ok else '✗'}")
    print(f"GPIO Access: {'✓' if gpio_ok else '✗'}")
    print(f"Python Dependencies: {'✓' if deps_ok else '✗'}")
    
    if python_processes:
        print(f"Running Python Processes: {len(python_processes)}")
    
    # Suggest fixes
    suggest_fixes()
    
    print("\nDiagnostic complete!")

if __name__ == "__main__":
    main() 