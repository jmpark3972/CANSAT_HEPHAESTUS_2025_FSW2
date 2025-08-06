#!/usr/bin/env python3
"""
Hardware Access Test Script
Tests I2C, GPIO, and other hardware access that might cause bus errors
"""

import sys
import os
import time
import subprocess
from datetime import datetime

def safe_print(message: str):
    """Safe print function"""
    try:
        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
        print(f"[{timestamp}] {message}")
        sys.stdout.flush()
    except Exception as e:
        print(f"[SAFE_PRINT_ERROR] {message} (Error: {e})")

def test_i2c_access():
    """Test I2C bus access"""
    safe_print("Testing I2C bus access...")
    
    try:
        # Test I2C bus 1
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            safe_print("✓ I2C bus 1 accessible")
            safe_print(f"I2C devices found:\n{result.stdout}")
        else:
            safe_print(f"✗ I2C bus 1 failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        safe_print("✗ I2C bus 1 timeout")
    except FileNotFoundError:
        safe_print("✗ i2cdetect command not found")
    except Exception as e:
        safe_print(f"✗ I2C bus 1 error: {e}")

def test_gpio_access():
    """Test GPIO access"""
    safe_print("Testing GPIO access...")
    
    try:
        # Test GPIO export
        result = subprocess.run(['gpio', 'readall'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            safe_print("✓ GPIO access successful")
        else:
            safe_print(f"✗ GPIO access failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        safe_print("✗ GPIO access timeout")
    except FileNotFoundError:
        safe_print("✗ gpio command not found")
    except Exception as e:
        safe_print(f"✗ GPIO access error: {e}")

def test_camera_access():
    """Test camera access"""
    safe_print("Testing camera access...")
    
    try:
        # Test camera hardware detection
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            safe_print(f"✓ Camera hardware: {result.stdout.strip()}")
        else:
            safe_print(f"✗ Camera hardware check failed: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        safe_print("✗ Camera hardware check timeout")
    except FileNotFoundError:
        safe_print("✗ vcgencmd command not found")
    except Exception as e:
        safe_print(f"✗ Camera hardware check error: {e}")

def test_serial_access():
    """Test serial port access"""
    safe_print("Testing serial port access...")
    
    serial_ports = ['/dev/serial0', '/dev/serial1', '/dev/ttyAMA0', '/dev/ttyS0']
    
    for port in serial_ports:
        try:
            if os.path.exists(port):
                safe_print(f"✓ Serial port {port} exists")
                # Test if we can open it
                try:
                    with open(port, 'r') as f:
                        pass
                    safe_print(f"✓ Serial port {port} is readable")
                except PermissionError:
                    safe_print(f"⚠ Serial port {port} exists but not readable (permission denied)")
                except Exception as e:
                    safe_print(f"✗ Serial port {port} error: {e}")
            else:
                safe_print(f"✗ Serial port {port} does not exist")
        except Exception as e:
            safe_print(f"✗ Serial port {port} check error: {e}")

def test_memory_pressure():
    """Test memory pressure"""
    safe_print("Testing memory pressure...")
    
    try:
        # Read memory info
        with open('/proc/meminfo', 'r') as f:
            meminfo = f.read()
        
        # Parse memory info
        lines = meminfo.split('\n')
        mem_total = 0
        mem_available = 0
        
        for line in lines:
            if line.startswith('MemTotal:'):
                mem_total = int(line.split()[1]) * 1024  # Convert KB to bytes
            elif line.startswith('MemAvailable:'):
                mem_available = int(line.split()[1]) * 1024  # Convert KB to bytes
        
        if mem_total > 0 and mem_available > 0:
            mem_used = mem_total - mem_available
            mem_percent = (mem_used / mem_total) * 100
            
            safe_print(f"✓ Total memory: {mem_total / 1024 / 1024 / 1024:.2f} GB")
            safe_print(f"✓ Available memory: {mem_available / 1024 / 1024 / 1024:.2f} GB")
            safe_print(f"✓ Memory usage: {mem_percent:.1f}%")
            
            if mem_percent > 80:
                safe_print("⚠ High memory usage detected")
            elif mem_percent > 90:
                safe_print("✗ Critical memory usage detected")
        else:
            safe_print("✗ Could not read memory information")
            
    except Exception as e:
        safe_print(f"✗ Memory pressure test error: {e}")

def test_python_imports():
    """Test Python module imports that might cause issues"""
    safe_print("Testing Python module imports...")
    
    modules_to_test = [
        ('board', 'board'),
        ('busio', 'busio'),
        ('adafruit_mlx90640', 'adafruit_mlx90640'),
        ('picamera', 'picamera'),
        ('RPi.GPIO', 'RPi.GPIO'),
        ('smbus2', 'smbus2'),
        ('serial', 'serial'),
    ]
    
    for module_name, import_name in modules_to_test:
        try:
            module = __import__(import_name)
            safe_print(f"✓ {module_name} imported successfully")
        except ImportError as e:
            safe_print(f"✗ {module_name} import failed: {e}")
        except Exception as e:
            safe_print(f"✗ {module_name} error: {e}")

def main():
    """Main test function"""
    safe_print("=" * 60)
    safe_print("Hardware Access Test")
    safe_print("=" * 60)
    
    # Test system resources
    safe_print("\n1. Testing system resources...")
    test_memory_pressure()
    
    # Test hardware access
    safe_print("\n2. Testing hardware access...")
    test_i2c_access()
    test_gpio_access()
    test_camera_access()
    test_serial_access()
    
    # Test Python modules
    safe_print("\n3. Testing Python module imports...")
    test_python_imports()
    
    safe_print("\n" + "=" * 60)
    safe_print("Hardware access test complete!")
    safe_print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        safe_print("\nTest interrupted by user")
    except Exception as e:
        safe_print(f"\nTest failed with error: {e}")
        import traceback
        safe_print(f"Traceback: {traceback.format_exc()}") 