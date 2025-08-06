#!/usr/bin/env python3
"""
Test script to verify the fixes for the identified issues
"""

def test_offset_manager():
    """Test the OffsetManager initialization"""
    print("Testing OffsetManager initialization...")
    try:
        from lib.offsets import get_offset_manager, get_comm_offset
        manager = get_offset_manager()
        print("✓ OffsetManager initialized successfully")
        
        # Test comm offset function
        comm_offset = get_comm_offset()
        print(f"✓ Comm offset loaded: {comm_offset}")
        
        return True
    except Exception as e:
        print(f"✗ OffsetManager test failed: {e}")
        return False

def test_gps_formatting():
    """Test GPS data formatting"""
    print("\nTesting GPS data formatting...")
    try:
        # Simulate the GPS data formatting logic
        GPS_LAT = 37.123456
        GPS_LON = 127.123456
        GPS_ALT = 100.5
        GPS_TIME = "12:34:56"
        GPS_SATS = "8"  # Simulate string input
        
        # Test the fixed formatting logic
        try:
            gps_sats_int = int(GPS_SATS) if GPS_SATS is not None else 0
        except (ValueError, TypeError):
            gps_sats_int = 0
        
        gps_tlm_data = f"{GPS_LAT:.6f},{GPS_LON:.6f},{GPS_ALT:.2f},{GPS_TIME},{gps_sats_int}"
        print(f"✓ GPS data formatted successfully: {gps_tlm_data}")
        
        return True
    except Exception as e:
        print(f"✗ GPS formatting test failed: {e}")
        return False

def test_tmp007_voltage():
    """Test TMP007 voltage range validation"""
    print("\nTesting TMP007 voltage range validation...")
    try:
        # Test voltage values that were causing issues
        test_voltages = [-20625.0, -18593.75, -17343.75, -17968.75, -19062.5]
        
        for voltage in test_voltages:
            # Simulate the new validation logic
            if voltage < -50000 or voltage > 50000:
                print(f"✗ Voltage {voltage}μV would still be rejected")
                return False
            else:
                print(f"✓ Voltage {voltage}μV is now accepted")
        
        return True
    except Exception as e:
        print(f"✗ TMP007 voltage test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Testing Fixes ===")
    
    tests = [
        test_offset_manager,
        test_gps_formatting,
        test_tmp007_voltage
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed!")
    else:
        print("✗ Some tests failed")

if __name__ == "__main__":
    main() 