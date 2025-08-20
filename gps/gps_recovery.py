#!/usr/bin/env python3
"""
GPS Module Recovery Script
GPS 모듈을 복구하고 재설정하는 스크립트
"""

import time
import board
import busio
from datetime import datetime

def reset_gps_module():
    """GPS 모듈을 완전히 리셋"""
    print("=== GPS Module Recovery ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C bus initialized")
        
        # Scan for devices
        scanned_devices = i2c.scan()
        print(f"I2C devices found: {[hex(addr) for addr in scanned_devices]}")
        
        if 0x42 not in scanned_devices:
            print("✗ MAX-M10S GPS module not found")
            return False
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c, address=0x42)
        print("✓ GPS module initialized")
        
        # Step 1: Hard reset
        print("\nStep 1: Performing hard reset...")
        try:
            gps.send_command(b'PMTK000')  # Reset to factory defaults
            time.sleep(3)
            print("✓ Hard reset completed")
        except Exception as e:
            print(f"⚠️ Hard reset warning: {e}")
        
        # Step 2: Wait for module to stabilize
        print("\nStep 2: Waiting for module to stabilize...")
        for i in range(10):
            try:
                gps.update()
                print(f"  Stabilization attempt {i+1}/10: OK")
                time.sleep(1)
            except Exception as e:
                print(f"  Stabilization attempt {i+1}/10: Error - {e}")
                time.sleep(1)
        
        # Step 3: Configure basic settings
        print("\nStep 3: Configuring basic settings...")
        try:
            # Set update rate to 1Hz
            gps.send_command(b'PMTK220,1000')
            time.sleep(1)
            print("✓ Update rate set to 1Hz")
            
            # Enable GGA and RMC sentences only
            gps.send_command(b'PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            time.sleep(1)
            print("✓ GGA and RMC sentences enabled")
            
        except Exception as e:
            print(f"⚠️ Configuration warning: {e}")
        
        # Step 4: Test reading
        print("\nStep 4: Testing GPS reading...")
        success_count = 0
        error_count = 0
        
        for i in range(10):
            try:
                gps.update()
                success_count += 1
                print(f"  Read {i+1}/10: OK")
            except Exception as e:
                error_count += 1
                print(f"  Read {i+1}/10: Error - {e}")
            time.sleep(1)
        
        print(f"\nRecovery Summary:")
        print(f"  Successful reads: {success_count}/10")
        print(f"  Errors: {error_count}/10")
        print(f"  Success rate: {success_count/10*100:.1f}%")
        
        # Cleanup
        i2c.deinit()
        
        if success_count >= 7:  # 70% success rate
            print("✓ GPS module recovery successful!")
            return True
        else:
            print("⚠️ GPS module partially recovered")
            return False
            
    except Exception as e:
        print(f"✗ GPS recovery failed: {e}")
        return False

def test_gps_after_recovery():
    """복구 후 GPS 테스트"""
    print("\n=== Post-Recovery GPS Test ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c, address=0x42)
        
        print("Testing GPS for 30 seconds...")
        start_time = time.time()
        fix_count = 0
        error_count = 0
        
        while time.time() - start_time < 30:
            try:
                gps.update()
                
                if gps.has_fix:
                    fix_count += 1
                    print(f"Fix #{fix_count}: Lat={gps.latitude:.6f}, Lon={gps.longitude:.6f}")
                    
                    if fix_count >= 3:
                        print("✓ GPS is working correctly!")
                        break
                else:
                    print(".", end="", flush=True)
                    
            except Exception as e:
                error_count += 1
                print(f"E", end="", flush=True)
                
                if error_count > 5:
                    print(f"\n⚠️ Too many errors, stopping test")
                    break
            
            time.sleep(1)
        
        # Cleanup
        i2c.deinit()
        
        if fix_count > 0:
            print(f"\n✓ GPS test successful! Got {fix_count} fixes")
            return True
        else:
            print(f"\n⚠️ No GPS fixes obtained")
            return False
            
    except Exception as e:
        print(f"✗ Post-recovery test failed: {e}")
        return False

def main():
    """메인 복구 함수"""
    print("GPS Module Recovery Tool")
    print("=" * 40)
    
    # Perform recovery
    recovery_success = reset_gps_module()
    
    if recovery_success:
        print("\n" + "=" * 40)
        print("Recovery completed successfully!")
        
        # Test after recovery
        test_success = test_gps_after_recovery()
        
        if test_success:
            print("\n✓ GPS module is fully operational!")
        else:
            print("\n⚠️ GPS module recovered but may need antenna/clear sky view")
    else:
        print("\n" + "=" * 40)
        print("Recovery partially successful")
        print("Try the following:")
        print("1. Check GPS antenna connection")
        print("2. Ensure clear sky view")
        print("3. Restart the system")
        print("4. Check power supply")

if __name__ == "__main__":
    main()
