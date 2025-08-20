#!/usr/bin/env python3
"""
MAX-M10S Qwiic GPS Module for CANSAT HEPHAESTUS 2025
I2C Connection Implementation

This module provides GPS functionality using MAX-M10S Qwiic module
via I2C interface, compatible with existing CANSAT project structure.
"""

import time
import os
import board
import busio
from datetime import datetime
from adafruit_gps import GPS_GtopI2C

# Log directory setup
log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)
gpslogfile = open(os.path.join(log_dir, 'gps_max_m10s.txt'), 'a')

def log_gps(text):
    """Log GPS data to file"""
    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    gpslogfile.write(f'{t},{text}\n')
    gpslogfile.flush()

def init_gps():
    """Initialize MAX-M10S GPS module via I2C"""
    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C bus initialized")
        
        # Scan for I2C devices
        scanned_devices = i2c.scan()
        print(f"I2C devices found: {[hex(addr) for addr in scanned_devices]}")
        
        # MAX-M10S GPS module uses address 0x42
        if 0x42 in scanned_devices:
            gps = GPS_GtopI2C(i2c, address=0x42)
            print("✓ MAX-M10S GPS module initialized (address 0x42)")
        else:
            print(f"✗ MAX-M10S GPS module not found at address 0x42")
            print(f"Available addresses: {[hex(addr) for addr in scanned_devices]}")
            return None, None
        
        # Configure GPS settings for optimal performance
        gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
        gps.send_command(b'PMTK220,1000')  # Update rate: 1Hz
        gps.send_command(b'PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0')  # Enable all data
        
        print("✓ GPS settings configured")
        log_gps("MAX-M10S GPS module initialized successfully")
        
        return i2c, gps
        
    except Exception as e:
        print(f"✗ GPS initialization failed: {e}")
        log_gps(f"GPS initialization failed: {e}")
        return None, None

def read_gps(gps, timeout=2.0):
    """Read GPS data from MAX-M10S module"""
    if not gps:
        return None
    
    try:
        # Update GPS data
        gps.update()
        
        # Check if we have a fix
        if gps.has_fix:
            gps_data = {
                'latitude': gps.latitude,
                'longitude': gps.longitude,
                'altitude': gps.altitude_m,
                'speed': gps.speed_knots,
                'course': gps.track_angle_deg,
                'satellites': gps.satellites,
                'fix_quality': gps.fix_quality,
                'timestamp': datetime.now().isoformat(),
                'has_fix': True
            }
            
            # Log GPS data
            log_gps(f"FIX,{gps_data['latitude']:.6f},{gps_data['longitude']:.6f},"
                   f"{gps_data['altitude']:.1f},{gps_data['speed']:.1f},"
                   f"{gps_data['satellites']},{gps_data['fix_quality']}")
            
            return gps_data
        else:
            # No fix available
            log_gps("NO_FIX")
            return {
                'has_fix': False,
                'satellites': gps.satellites,
                'timestamp': datetime.now().isoformat()
            }
            
    except Exception as e:
        print(f"GPS read error: {e}")
        log_gps(f"READ_ERROR,{e}")
        return None

def parse_gps_data(gps_data):
    """Parse GPS data into standard format"""
    if not gps_data or not gps_data.get('has_fix'):
        return None, None, None, None, None
    
    try:
        # Extract data
        lat = gps_data['latitude']
        lon = gps_data['longitude']
        alt = gps_data['altitude']
        speed = gps_data['speed']
        satellites = gps_data['satellites']
        
        # Format for compatibility with existing code
        gga_data = {
            'latitude': lat,
            'longitude': lon,
            'altitude': alt,
            'satellites': satellites,
            'fix_quality': gps_data['fix_quality']
        }
        
        rmc_data = {
            'latitude': lat,
            'longitude': lon,
            'speed': speed,
            'course': gps_data['course'],
            'timestamp': gps_data['timestamp']
        }
        
        return gga_data, rmc_data, lat, lon, alt
        
    except Exception as e:
        print(f"GPS data parsing error: {e}")
        log_gps(f"PARSE_ERROR,{e}")
        return None, None, None, None, None

def get_gps_status(gps):
    """Get GPS module status"""
    if not gps:
        return "Not initialized"
    
    try:
        gps.update()
        
        status = {
            'has_fix': gps.has_fix,
            'satellites': gps.satellites,
            'fix_quality': gps.fix_quality,
            'timestamp': datetime.now().isoformat()
        }
        
        return status
        
    except Exception as e:
        return f"Error: {e}"

def terminate_gps(i2c):
    """Cleanup GPS resources"""
    try:
        if hasattr(i2c, "deinit"):
            i2c.deinit()
        gpslogfile.close()
        print("GPS resources cleaned up")
    except Exception as e:
        print(f"GPS cleanup error: {e}")

# Compatibility functions for existing code
def read_gps_simple(gps):
    """Simple GPS read function for compatibility"""
    data = read_gps(gps)
    if data and data.get('has_fix'):
        return (data['latitude'], data['longitude'], data['altitude'])
    return (None, None, None)

def test_gps_connection():
    """Test GPS connection and functionality"""
    print("=== MAX-M10S GPS Connection Test ===")
    
    i2c, gps = init_gps()
    if not gps:
        print("✗ GPS initialization failed")
        return False
    
    print("Testing GPS data reading...")
    
    # Test for 30 seconds
    start_time = time.time()
    fix_count = 0
    
    while time.time() - start_time < 30:
        data = read_gps(gps)
        
        if data and data.get('has_fix'):
            fix_count += 1
            print(f"Fix #{fix_count}: Lat={data['latitude']:.6f}, Lon={data['longitude']:.6f}")
            
            if fix_count >= 3:
                print("✓ GPS test successful!")
                break
        else:
            print(".", end="", flush=True)
        
        time.sleep(1)
    
    if fix_count == 0:
        print("\n⚠️ No GPS fix obtained")
        print("Check antenna connection and clear sky view")
    
    terminate_gps(i2c)
    return fix_count > 0

if __name__ == "__main__":
    print("MAX-M10S GPS Module Test")
    print("=" * 30)
    
    # Test GPS connection
    success = test_gps_connection()
    
    if success:
        print("\n✓ MAX-M10S GPS module is working correctly!")
    else:
        print("\n✗ GPS module test failed")
        print("Check connections and antenna")
