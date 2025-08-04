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
    
    try:
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
    except Exception as e:
        print(f"Error checking system resources: {e}")
        return False

def check_python_processes():
    """Check for running Python processes"""
    print("\n=== Python Processes Check ===")
    python_processes = []
    
    try:
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
    except Exception as e:
        print(f"Error checking Python processes: {e}")
        return []

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
            
        return True
    except Exception as e:
        print(f"Error checking I2C devices: {e}")
        return False

def check_serial_ports():
    """Check available serial ports"""
    print("\n=== Serial Ports Check ===")
    
    try:
        # Check for common serial devices
        serial_devices = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1', 
                         '/dev/serial0', '/dev/serial1', '/dev/ttyAMA0', '/dev/ttyAMA1']
        
        found_devices = []
        for device in serial_devices:
            if os.path.exists(device):
                found_devices.append(device)
        
        if found_devices:
            print("Found serial devices:")
            for device in found_devices:
                print(f"  {device}")
        else:
            print("No serial devices found")
        
        return len(found_devices) > 0
    except Exception as e:
        print(f"Error checking serial ports: {e}")
        return False

def check_gpio_access():
    """Check GPIO access"""
    print("\n=== GPIO Access Check ===")
    
    try:
        # Check if GPIO is accessible
        if os.path.exists('/sys/class/gpio'):
            print("GPIO sysfs interface available")
            
            # Check if user is in gpio group
            result = subprocess.run(['groups'], capture_output=True, text=True)
            if result.returncode == 0 and 'gpio' in result.stdout:
                print("User is in gpio group ✓")
                return True
            else:
                print("User is not in gpio group ✗")
                return False
        else:
            print("GPIO sysfs interface not available")
            return False
    except Exception as e:
        print(f"Error checking GPIO access: {e}")
        return False

def check_python_dependencies():
    """Check Python dependencies"""
    print("\n=== Python Dependencies Check ===")
    
    required_modules = [
        'board', 'busio', 'adafruit_mlx90614', 'adafruit_mlx90640',
        'smbus2', 'serial', 'threading', 'multiprocessing', 'psutil'
    ]
    
    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✓ {module}")
        except ImportError:
            print(f"  ✗ {module}")
            missing_modules.append(module)
    
    return len(missing_modules) == 0

def check_file_permissions():
    """Check file permissions"""
    print("\n=== File Permissions Check ===")
    
    try:
        # Check log directory
        log_dir = './logs'
        if os.path.exists(log_dir):
            if os.access(log_dir, os.W_OK):
                print(f"Log directory writable: {log_dir} ✓")
            else:
                print(f"Log directory not writable: {log_dir} ✗")
        else:
            print(f"Log directory not found: {log_dir}")
        
        # Check main.py
        if os.path.exists('main.py'):
            if os.access('main.py', os.R_OK):
                print("main.py readable ✓")
            else:
                print("main.py not readable ✗")
        else:
            print("main.py not found")
        
        return True
    except Exception as e:
        print(f"Error checking file permissions: {e}")
        return False

def suggest_fixes():
    """Suggest fixes for common issues"""
    print("\n=== Suggested Fixes ===")
    
    print("1. If I2C devices not found:")
    print("   - Check physical connections")
    print("   - Run: sudo apt install i2c-tools")
    print("   - Enable I2C in raspi-config")
    
    print("\n2. If GPIO access denied:")
    print("   - Run: sudo usermod -a -G gpio $USER")
    print("   - Reboot the system")
    
    print("\3. If Python modules missing:")
    print("   - Run: pip3 install adafruit-circuitpython-mlx90614")
    print("   - Run: pip3 install adafruit-circuitpython-mlx90640")
    print("   - Run: pip3 install smbus2 pyserial psutil")
    
    print("\n4. If serial ports not found:")
    print("   - Check USB connections")
    print("   - Run: sudo usermod -a -G dialout $USER")
    print("   - Reboot the system")

def main():
    """Main diagnostic function"""
    print("=== CANSAT System Diagnostic ===")
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run all checks
    system_ok = check_system_resources()
    python_processes = check_python_processes()
    i2c_ok = check_i2c_devices()
    serial_ok = check_serial_ports()
    gpio_ok = check_gpio_access()
    deps_ok = check_python_dependencies()
    perms_ok = check_file_permissions()
    
    # Summary
    print("\n=== Diagnostic Summary ===")
    print(f"System Resources: {'✓' if system_ok else '✗'}")
    print(f"Python Processes: {len(python_processes)} found")
    print(f"I2C Devices: {'✓' if i2c_ok else '✗'}")
    print(f"Serial Ports: {'✓' if serial_ok else '✗'}")
    print(f"GPIO Access: {'✓' if gpio_ok else '✗'}")
    print(f"Dependencies: {'✓' if deps_ok else '✗'}")
    print(f"File Permissions: {'✓' if perms_ok else '✗'}")
    
    # Suggest fixes if issues found
    if not all([system_ok, i2c_ok, serial_ok, gpio_ok, deps_ok, perms_ok]):
        suggest_fixes()
    else:
        print("\n✓ All checks passed! System appears to be healthy.")

if __name__ == "__main__":
    main() 