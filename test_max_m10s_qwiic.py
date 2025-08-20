#!/usr/bin/env python3
"""
MAX-M10S Qwiic GPS Module Test Script
CANSAT HEPHAESTUS 2025 - I2C Connection Test

This script tests the MAX-M10S GPS module connected via Qwiic I2C interface.
"""

import time
import board
import busio
from adafruit_gps import GPS_GtopI2C

def test_max_m10s_qwiic():
    """Test MAX-M10S Qwiic GPS module"""
    
    print("=== MAX-M10S Qwiic GPS Module Test ===")
    print("Connecting via I2C...")
    
    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C bus initialized")
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c)
        print("✓ MAX-M10S GPS module initialized")
        
        # Configure GPS settings
        gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        gps.send_command(b'PMTK220,1000')  # Update rate: 1Hz
        print("✓ GPS settings configured")
        
        # Test GPS data reading
        print("\n=== GPS Data Test ===")
        print("Waiting for GPS fix... (this may take a few minutes)")
        
        fix_count = 0
        timeout = 300  # 5 minutes timeout
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Update GPS data
            gps.update()
            
            # Check if we have a fix
            if gps.has_fix:
                fix_count += 1
                
                print(f"\n--- GPS Fix #{fix_count} ---")
                print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"Latitude: {gps.latitude:.6f}°")
                print(f"Longitude: {gps.longitude:.6f}°")
                print(f"Altitude: {gps.altitude_m:.1f}m")
                print(f"Speed: {gps.speed_knots:.1f} knots")
                print(f"Course: {gps.track_angle_deg:.1f}°")
                print(f"Satellites: {gps.satellites}")
                print(f"Fix Quality: {gps.fix_quality}")
                
                # Test for 10 fixes
                if fix_count >= 10:
                    print("\n✓ GPS test completed successfully!")
                    break
                    
            else:
                print(".", end="", flush=True)
                time.sleep(1)
        
        if fix_count == 0:
            print(f"\n⚠️ No GPS fix obtained within {timeout} seconds")
            print("Check antenna connection and clear sky view")
        
        # Test GPS module information
        print("\n=== GPS Module Information ===")
        print(f"GPS Module: MAX-M10S (Qwiic)")
        print(f"Connection: I2C")
        print(f"Update Rate: 1Hz")
        print(f"Fix Quality: {gps.fix_quality}")
        print(f"Satellites Visible: {gps.satellites}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nTroubleshooting:")
        print("1. Check I2C connection (VCC, GND, SDA, SCL)")
        print("2. Verify I2C is enabled: sudo raspi-config")
        print("3. Check I2C devices: i2cdetect -y 1")
        print("4. Ensure GPS antenna is connected")
        return False

def test_i2c_scan():
    """Scan I2C bus for devices"""
    print("=== I2C Bus Scan ===")
    
    try:
        import subprocess
        
        # Run i2cdetect
        result = subprocess.run(['i2cdetect', '-y', '1'], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("I2C devices found:")
            print(result.stdout)
        else:
            print("Error running i2cdetect")
            
    except Exception as e:
        print(f"Error scanning I2C: {e}")

def test_gps_commands():
    """Test GPS module commands"""
    print("=== GPS Commands Test ===")
    
    try:
        i2c = busio.I2C(board.SCL, board.SDA)
        gps = GPS_GtopI2C(i2c)
        
        # Test various GPS commands
        commands = [
            (b'PMTK605', 'Version Query'),
            (b'PMTK000', 'Hot Start'),
            (b'PMTK001', 'Warm Start'),
            (b'PMTK010', 'Cold Start'),
        ]
        
        for cmd, desc in commands:
            try:
                print(f"Testing {desc}...")
                gps.send_command(cmd)
                time.sleep(0.1)
                print(f"✓ {desc} command sent")
            except Exception as e:
                print(f"✗ {desc} failed: {e}")
                
    except Exception as e:
        print(f"Error testing GPS commands: {e}")

if __name__ == "__main__":
    print("MAX-M10S Qwiic GPS Module Test")
    print("=" * 40)
    
    # Test I2C scan first
    test_i2c_scan()
    print()
    
    # Test GPS module
    success = test_max_m10s_qwiic()
    
    if success:
        print("\n=== Additional Tests ===")
        test_gps_commands()
    
    print("\nTest completed!")
