#!/usr/bin/env python3
"""
Simple GPS Test Script
독립적으로 실행 가능한 GPS 테스트 스크립트
"""

import os
import sys
import time
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_max_m10s_gps():
    """MAX-M10S GPS 모듈 테스트"""
    print("=== MAX-M10S GPS Module Test ===")
    
    try:
        import board
        import busio
        from adafruit_gps import GPS_GtopI2C
        
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
            
            # Configure GPS settings
            gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            gps.send_command(b'PMTK220,1000')  # Update rate: 1Hz
            print("✓ GPS settings configured")
            
            # Test GPS reading with error handling
            print("Testing GPS data reading (30 seconds)...")
            start_time = time.time()
            fix_count = 0
            error_count = 0
            
            while time.time() - start_time < 30:
                try:
                    gps.update()
                    
                    if gps.has_fix:
                        fix_count += 1
                        print(f"Fix #{fix_count}: Lat={gps.latitude:.6f}, Lon={gps.longitude:.6f}, "
                              f"Alt={gps.altitude_m:.1f}m, Sats={gps.satellites}")
                        
                        if fix_count >= 3:
                            print("✓ GPS test successful!")
                            break
                    else:
                        print(".", end="", flush=True)
                        
                except Exception as e:
                    error_count += 1
                    print(f"E", end="", flush=True)  # Show error with 'E'
                    if error_count > 10:  # Stop if too many errors
                        print(f"\n⚠️ Too many errors ({error_count}), stopping test")
                        break
                
                time.sleep(1)
            
            if fix_count == 0:
                print("\n⚠️ No GPS fix obtained")
                print("Check antenna connection and clear sky view")
            
            # Cleanup
            i2c.deinit()
            return fix_count > 0
            
        else:
            print(f"✗ MAX-M10S GPS module not found at address 0x42")
            print(f"Available addresses: {[hex(addr) for addr in scanned_devices]}")
            print("Check connections:")
            print("1. Qwiic cable is properly connected")
            print("2. GPS module has power")
            print("3. I2C is enabled (sudo raspi-config)")
            return False
            
    except ImportError as e:
        print(f"✗ Import error: {e}")
        print("Install required packages: pip install adafruit-circuitpython-gps")
        return False
    except Exception as e:
        print(f"✗ GPS test failed: {e}")
        return False

def test_hybrid_gps():
    """하이브리드 GPS 시스템 테스트"""
    print("\n=== Hybrid GPS System Test ===")
    
    try:
        from hybrid_gps import init_hybrid_gps, read_hybrid_location, get_location_status, cleanup_hybrid_gps
        
        # Initialize hybrid GPS system
        gps_system = init_hybrid_gps()
        print("✓ Hybrid GPS system initialized")
        
        # Try to get location
        print("Attempting to get location...")
        location = read_hybrid_location()
        
        if location:
            print(f"✓ Location obtained!")
            print(f"  Latitude: {location.latitude:.6f}")
            print(f"  Longitude: {location.longitude:.6f}")
            print(f"  Altitude: {location.altitude:.1f}m" if location.altitude else "  Altitude: N/A")
            print(f"  Accuracy: {location.accuracy:.1f}m" if location.accuracy else "  Accuracy: N/A")
            print(f"  Source: {location.source.value}")
            print(f"  Timestamp: {location.timestamp}")
        else:
            print("✗ Failed to get location")
        
        # System status
        print("\nSystem Status:")
        status = get_location_status()
        for key, value in status.items():
            print(f"  {key}: {value}")
        
        # Cleanup
        cleanup_hybrid_gps()
        return location is not None
        
    except Exception as e:
        print(f"✗ Hybrid GPS test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """메인 테스트 함수"""
    print("GPS Module Test Suite")
    print("=" * 40)
    
    # Test MAX-M10S GPS
    max_m10s_success = test_max_m10s_gps()
    
    # Test Hybrid GPS
    hybrid_success = test_hybrid_gps()
    
    # Summary
    print("\n" + "=" * 40)
    print("TEST SUMMARY:")
    print(f"MAX-M10S GPS: {'✓ PASS' if max_m10s_success else '✗ FAIL'}")
    print(f"Hybrid GPS: {'✓ PASS' if hybrid_success else '✗ FAIL'}")
    
    if max_m10s_success or hybrid_success:
        print("\n✓ At least one GPS system is working!")
    else:
        print("\n✗ All GPS tests failed")
        print("Troubleshooting tips:")
        print("1. Check hardware connections")
        print("2. Ensure GPS antenna is connected and has clear sky view")
        print("3. Verify I2C is enabled: sudo raspi-config")
        print("4. Check power supply to GPS module")

if __name__ == "__main__":
    main()
