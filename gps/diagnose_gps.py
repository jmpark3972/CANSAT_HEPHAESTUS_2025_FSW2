#!/usr/bin/env python3
"""
GPS Module Diagnostic Script
GPS 모듈을 단계별로 진단하는 스크립트
"""

import time
import board
import busio
from datetime import datetime

def test_i2c_communication():
    """I2C 통신 테스트"""
    print("=== I2C Communication Test ===")
    
    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C bus initialized")
        
        # Scan for devices
        scanned_devices = i2c.scan()
        print(f"I2C devices found: {[hex(addr) for addr in scanned_devices]}")
        
        # Check for GPS module
        if 0x42 in scanned_devices:
            print("✓ MAX-M10S GPS module found at address 0x42")
            
            # Try to read from GPS module
            try:
                # Read a few bytes from the GPS module
                result = i2c.readfrom(0x42, 10)
                print(f"✓ Raw data from GPS: {result}")
                print(f"✓ Data as hex: {result.hex()}")
            except Exception as read_error:
                print(f"✗ Error reading from GPS: {read_error}")
            
            return i2c, True
        else:
            print("✗ MAX-M10S GPS module not found at address 0x42")
            return i2c, False
            
    except Exception as e:
        print(f"✗ I2C initialization failed: {e}")
        return None, False

def test_gps_library():
    """GPS 라이브러리 테스트"""
    print("\n=== GPS Library Test ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Get I2C bus
        i2c, found = test_i2c_communication()
        if not found:
            return False
        
        # Initialize GPS module
        print("Initializing GPS module...")
        gps = GPS_GtopI2C(i2c, address=0x42)
        print("✓ GPS module object created")
        
        # Test basic properties
        print("Testing GPS properties...")
        try:
            print(f"  has_fix: {gps.has_fix}")
        except Exception as e:
            print(f"  has_fix error: {e}")
        
        try:
            print(f"  satellites: {gps.satellites}")
        except Exception as e:
            print(f"  satellites error: {e}")
        
        try:
            print(f"  latitude: {gps.latitude}")
        except Exception as e:
            print(f"  latitude error: {e}")
        
        try:
            print(f"  longitude: {gps.longitude}")
        except Exception as e:
            print(f"  longitude error: {e}")
        
        # Test update method
        print("Testing GPS update method...")
        for i in range(5):
            try:
                gps.update()
                print(f"  Update {i+1}: OK")
                time.sleep(1)
            except Exception as e:
                print(f"  Update {i+1} error: {e}")
        
        # Cleanup
        i2c.deinit()
        return True
        
    except ImportError as e:
        print(f"✗ GPS library import error: {e}")
        return False
    except Exception as e:
        print(f"✗ GPS library test failed: {e}")
        return False

def test_gps_commands():
    """GPS 명령어 테스트"""
    print("\n=== GPS Commands Test ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Get I2C bus
        i2c, found = test_i2c_communication()
        if not found:
            return False
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c, address=0x42)
        
        # Test basic commands
        commands = [
            (b'PMTK000', 'Reset'),
            (b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0', 'Basic config'),
            (b'PMTK220,1000', 'Update rate 1Hz'),
        ]
        
        for cmd, desc in commands:
            try:
                print(f"Testing {desc}...")
                gps.send_command(cmd)
                time.sleep(0.5)
                print(f"  ✓ {desc} command sent successfully")
            except Exception as e:
                print(f"  ✗ {desc} command failed: {e}")
        
        # Cleanup
        i2c.deinit()
        return True
        
    except Exception as e:
        print(f"✗ GPS commands test failed: {e}")
        return False

def test_gps_data_reading():
    """GPS 데이터 읽기 테스트"""
    print("\n=== GPS Data Reading Test ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Get I2C bus
        i2c, found = test_i2c_communication()
        if not found:
            return False
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c, address=0x42)
        
        print("Reading GPS data for 10 seconds...")
        start_time = time.time()
        read_count = 0
        error_count = 0
        
        while time.time() - start_time < 10:
            try:
                gps.update()
                read_count += 1
                
                if gps.has_fix:
                    print(f"  Fix #{read_count}: Lat={gps.latitude:.6f}, Lon={gps.longitude:.6f}")
                else:
                    print(f"  Read #{read_count}: No fix, Sats={gps.satellites}")
                    
            except Exception as e:
                error_count += 1
                print(f"  Error #{error_count}: {e}")
            
            time.sleep(1)
        
        print(f"\nSummary:")
        print(f"  Successful reads: {read_count}")
        print(f"  Errors: {error_count}")
        print(f"  Success rate: {read_count/(read_count+error_count)*100:.1f}%")
        
        # Cleanup
        i2c.deinit()
        return error_count == 0
        
    except Exception as e:
        print(f"✗ GPS data reading test failed: {e}")
        return False

def main():
    """메인 진단 함수"""
    print("GPS Module Diagnostic Tool")
    print("=" * 40)
    
    # Run all tests
    tests = [
        ("I2C Communication", test_i2c_communication),
        ("GPS Library", test_gps_library),
        ("GPS Commands", test_gps_commands),
        ("GPS Data Reading", test_gps_data_reading),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            if test_name == "I2C Communication":
                i2c, result = test_func()
                results.append((test_name, result))
            else:
                result = test_func()
                results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} test crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 40)
    print("DIAGNOSTIC SUMMARY:")
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ All tests passed! GPS module should work correctly.")
    else:
        print("✗ Some tests failed. Check the issues above.")
        print("\nTroubleshooting tips:")
        print("1. Check hardware connections")
        print("2. Verify GPS antenna is connected")
        print("3. Ensure clear sky view")
        print("4. Check power supply")
        print("5. Try restarting the system")

if __name__ == "__main__":
    main()
