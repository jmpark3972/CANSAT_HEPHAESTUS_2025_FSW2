#!/usr/bin/env python3
"""
Quick Fix Script for CANSAT System Issues
Run this script to address common problems
"""

import os
import sys
import subprocess
import time

def fix_main_loop_errors():
    """Fix the main loop error handling"""
    print("Fixing main loop error handling...")
    
    # Read the current main.py
    try:
        with open('main.py', 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading main.py: {e}")
        return False
    
    # Replace the problematic error handling section
    old_pattern = """            except Exception as e:
                # Handle queue timeout and other exceptions gracefully
                if "Empty" not in str(e):  # Not a timeout
                    events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error: {e}")"""
    
    new_pattern = """            except Exception as e:
                # Handle queue timeout and other exceptions gracefully
                if "Empty" not in str(e):  # Not a timeout
                    # Reduce error logging frequency to avoid spam
                    import time
                    current_time = time.time()
                    if not hasattr(fix_main_loop_errors, 'last_error_time'):
                        fix_main_loop_errors.last_error_time = 0
                    if current_time - fix_main_loop_errors.last_error_time > 5:  # Log only every 5 seconds
                        events.LogEvent(appargs.MainAppArg.AppName, events.EventType.error, f"Main loop error: {e}")
                        fix_main_loop_errors.last_error_time = current_time"""
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        
        # Write the fixed content back
        try:
            with open('main.py', 'w', encoding='utf-8') as f:
                f.write(content)
            print("✓ Main loop error handling fixed")
            return True
        except Exception as e:
            print(f"Error writing main.py: {e}")
            return False
    else:
        print("Main loop error pattern not found - may already be fixed")
        return True

def check_and_fix_i2c():
    """Check and fix I2C issues"""
    print("Checking I2C configuration...")
    
    # Check if i2c-tools is installed
    try:
        result = subprocess.run(['which', 'i2cdetect'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Installing i2c-tools...")
            subprocess.run(['sudo', 'apt-get', 'update'], check=True)
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 'i2c-tools'], check=True)
            print("✓ i2c-tools installed")
        else:
            print("✓ i2c-tools already installed")
    except Exception as e:
        print(f"Error installing i2c-tools: {e}")
    
    # Enable I2C if not already enabled
    try:
        # Check if I2C is enabled in config
        if os.path.exists('/boot/config.txt'):
            with open('/boot/config.txt', 'r') as f:
                config_content = f.read()
            
            if 'dtparam=i2c_arm=on' not in config_content:
                print("Enabling I2C in config.txt...")
                with open('/boot/config.txt', 'a') as f:
                    f.write('\ndtparam=i2c_arm=on\n')
                print("✓ I2C enabled in config.txt (reboot required)")
            else:
                print("✓ I2C already enabled in config.txt")
    except Exception as e:
        print(f"Error checking I2C config: {e}")

def check_and_fix_serial():
    """Check and fix serial port issues"""
    print("Checking serial port configuration...")
    
    # Check if user is in dialout group
    try:
        result = subprocess.run(['groups'], capture_output=True, text=True)
        if result.returncode == 0 and 'dialout' not in result.stdout:
            print("Adding user to dialout group...")
            subprocess.run(['sudo', 'usermod', '-a', '-G', 'dialout', os.getenv('USER')], check=True)
            print("✓ User added to dialout group (logout/login required)")
        else:
            print("✓ User already in dialout group")
    except Exception as e:
        print(f"Error checking serial permissions: {e}")

def check_and_fix_gpio():
    """Check and fix GPIO issues"""
    print("Checking GPIO configuration...")
    
    # Check if pigpiod is running
    try:
        result = subprocess.run(['pgrep', 'pigpiod'], capture_output=True, text=True)
        if result.returncode != 0:
            print("Starting pigpiod...")
            subprocess.run(['sudo', 'systemctl', 'start', 'pigpiod'], check=True)
            subprocess.run(['sudo', 'systemctl', 'enable', 'pigpiod'], check=True)
            print("✓ pigpiod started and enabled")
        else:
            print("✓ pigpiod already running")
    except Exception as e:
        print(f"Error starting pigpiod: {e}")

def create_sensor_test_script():
    """Create a sensor test script"""
    print("Creating sensor test script...")
    
    test_script = '''#!/usr/bin/env python3
"""
Sensor Test Script
Test individual sensors to identify issues
"""

import time
import board
import busio

def test_i2c_bus():
    """Test I2C bus"""
    print("Testing I2C bus...")
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        if i2c.try_lock():
            print("✓ I2C bus is working")
            i2c.unlock()
            return True
        else:
            print("✗ I2C bus is locked")
            return False
    except Exception as e:
        print(f"✗ I2C bus error: {e}")
        return False

def test_barometer():
    """Test barometer sensor"""
    print("Testing barometer...")
    try:
        from barometer import barometer
        # Add specific barometer test
        print("✓ Barometer module imported")
        return True
    except Exception as e:
        print(f"✗ Barometer error: {e}")
        return False

def test_thermis():
    """Test THERMIS sensor"""
    print("Testing THERMIS...")
    try:
        from thermis import thermis
        # Add specific THERMIS test
        print("✓ THERMIS module imported")
        return True
    except Exception as e:
        print(f"✗ THERMIS error: {e}")
        return False

def main():
    """Run all tests"""
    print("CANSAT Sensor Test")
    print("=" * 30)
    
    tests = [
        test_i2c_bus,
        test_barometer,
        test_thermis
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"Test failed with exception: {e}")
            results.append(False)
        time.sleep(1)
    
    print("\nTest Results:")
    print(f"Passed: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed. Check hardware connections.")

if __name__ == "__main__":
    main()
'''
    
    try:
        with open('sensor_test.py', 'w') as f:
            f.write(test_script)
        os.chmod('sensor_test.py', 0o755)
        print("✓ Sensor test script created: sensor_test.py")
        return True
    except Exception as e:
        print(f"Error creating sensor test script: {e}")
        return False

def main():
    """Run all fixes"""
    print("CANSAT Quick Fix Script")
    print("=" * 40)
    
    fixes = [
        ("Main Loop Errors", fix_main_loop_errors),
        ("I2C Configuration", check_and_fix_i2c),
        ("Serial Port Configuration", check_and_fix_serial),
        ("GPIO Configuration", check_and_fix_gpio),
        ("Sensor Test Script", create_sensor_test_script)
    ]
    
    results = []
    for name, fix_func in fixes:
        print(f"\n--- {name} ---")
        try:
            result = fix_func()
            results.append(result if result is not None else False)
        except Exception as e:
            print(f"Error in {name}: {e}")
            results.append(False)
    
    print("\n" + "=" * 40)
    print("Fix Summary:")
    print(f"Successful: {sum(results)}/{len(results)}")
    
    if all(results):
        print("✓ All fixes applied successfully!")
    else:
        print("✗ Some fixes failed. Check the output above.")
    
    print("\nNext steps:")
    print("1. Reboot the system if I2C was enabled")
    print("2. Logout and login if serial permissions were changed")
    print("3. Run: python3 sensor_test.py")
    print("4. Run: python3 diagnostic_script.py")
    print("5. Try running main.py again")

if __name__ == "__main__":
    main() 