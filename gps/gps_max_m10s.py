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
        
        # Configure GPS settings for optimal performance with error handling
        try:
            # Reset GPS module first
            gps.send_command(b'PMTK000')
            time.sleep(2)  # Longer wait for reset
            
            # Wait for GPS to stabilize
            print("Waiting for GPS module to stabilize...")
            for i in range(5):
                try:
                    gps.update()
                    time.sleep(1)
                except:
                    pass
            
            # Configure basic settings with longer delays
            gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            time.sleep(1)
            gps.send_command(b'PMTK220,1000')  # Update rate: 1Hz
            time.sleep(1)
            
            # Enable all data
            gps.send_command(b'PMTK314,1,1,1,1,1,1,0,0,0,0,0,0,0,0,0,0,0,1,0')
            time.sleep(1)
            
            print("✓ GPS settings configured")
            log_gps("MAX-M10S GPS module initialized successfully")
            
        except Exception as config_error:
            print(f"⚠️ GPS configuration warning: {config_error}")
            log_gps(f"CONFIG_WARNING,{config_error}")
            # Continue anyway - GPS might still work with default settings
        
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
        # Update GPS data with error handling and retry logic
        update_success = False
        retry_count = 0
        max_retries = 3
        
        while not update_success and retry_count < max_retries:
            try:
                gps.update()
                update_success = True
            except Exception as update_error:
                retry_count += 1
                error_msg = str(update_error)
                
                # Log the specific error
                if "invalid literal for int()" in error_msg:
                    log_gps(f"HEX_PARSE_ERROR,{error_msg}")
                    print(f"GPS hex parse error (attempt {retry_count}/{max_retries})")
                else:
                    log_gps(f"UPDATE_ERROR,{error_msg}")
                    print(f"GPS update error: {error_msg}")
                
                # Wait before retry
                time.sleep(0.5)
        
        if not update_success:
            return {
                'has_fix': False,
                'satellites': 0,
                'timestamp': datetime.now().isoformat(),
                'error': f"Failed after {max_retries} attempts"
            }
        
        # Check if we have a fix with safe data access
        try:
            has_fix = gps.has_fix
            satellites = gps.satellites if hasattr(gps, 'satellites') else 0
            fix_quality = gps.fix_quality if hasattr(gps, 'fix_quality') else 0
            
            if has_fix:
                # Safely extract GPS data with validation
                try:
                    lat = gps.latitude
                    lon = gps.longitude
                    alt = gps.altitude_m if hasattr(gps, 'altitude_m') else 0
                    speed = gps.speed_knots if hasattr(gps, 'speed_knots') else 0
                    course = gps.track_angle_deg if hasattr(gps, 'track_angle_deg') else 0
                    
                    # Validate coordinates
                    if lat is None or lon is None or not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
                        print("Invalid GPS coordinates received")
                        log_gps("INVALID_COORDINATES")
                        return {
                            'has_fix': False,
                            'satellites': satellites,
                            'timestamp': datetime.now().isoformat()
                        }
                    
                    gps_data = {
                        'latitude': lat,
                        'longitude': lon,
                        'altitude': alt,
                        'speed': speed,
                        'course': course,
                        'satellites': satellites,
                        'fix_quality': fix_quality,
                        'timestamp': datetime.now().isoformat(),
                        'has_fix': True
                    }
                    
                    # Log GPS data
                    log_gps(f"FIX,{gps_data['latitude']:.6f},{gps_data['longitude']:.6f},"
                           f"{gps_data['altitude']:.1f},{gps_data['speed']:.1f},"
                           f"{gps_data['satellites']},{gps_data['fix_quality']}")
                    
                    return gps_data
                    
                except Exception as data_error:
                    print(f"GPS data extraction error: {data_error}")
                    log_gps(f"DATA_ERROR,{data_error}")
                    return {
                        'has_fix': False,
                        'satellites': satellites,
                        'timestamp': datetime.now().isoformat(),
                        'error': str(data_error)
                    }
            else:
                # No fix available
                log_gps("NO_FIX")
                return {
                    'has_fix': False,
                    'satellites': satellites,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as fix_error:
            print(f"GPS fix check error: {fix_error}")
            log_gps(f"FIX_ERROR,{fix_error}")
            return {
                'has_fix': False,
                'satellites': 0,
                'timestamp': datetime.now().isoformat(),
                'error': str(fix_error)
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
