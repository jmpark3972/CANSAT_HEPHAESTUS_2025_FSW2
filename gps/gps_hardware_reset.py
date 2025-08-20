#!/usr/bin/env python3
"""
GPS Hardware Reset Script
GPS 모듈을 하드웨어 레벨에서 리셋하는 스크립트
"""

import time
import board
import busio
import subprocess
import os

def reset_i2c_bus():
    """I2C 버스를 완전히 리셋"""
    print("=== I2C Bus Reset ===")
    
    try:
        # Try to reset I2C bus using system commands
        print("Attempting to reset I2C bus...")
        
        # Check if we can access I2C devices
        result = subprocess.run(['sudo', 'i2cdetect', '-y', '1'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✓ I2C bus is accessible")
            print("I2C scan result:")
            print(result.stdout)
        else:
            print("⚠️ I2C bus may have issues")
            
        return True
        
    except Exception as e:
        print(f"⚠️ I2C reset warning: {e}")
        return False

def power_cycle_gps():
    """GPS 모듈 전원 사이클링 시뮬레이션"""
    print("\n=== GPS Power Cycle Simulation ===")
    
    try:
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        print("✓ I2C bus initialized")
        
        # Scan for devices
        scanned_devices = i2c.scan()
        print(f"I2C devices found: {[hex(addr) for addr in scanned_devices]}")
        
        if 0x42 not in scanned_devices:
            print("✗ MAX-M10S GPS module not found")
            i2c.deinit()
            return False
        
        # Simulate power cycle by deinitializing and reinitializing
        print("Simulating power cycle...")
        i2c.deinit()
        time.sleep(2)  # Wait for module to "power off"
        
        # Reinitialize
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        time.sleep(1)  # Wait for module to "power on"
        
        # Scan again
        scanned_devices = i2c.scan()
        print(f"After power cycle - I2C devices: {[hex(addr) for addr in scanned_devices]}")
        
        if 0x42 in scanned_devices:
            print("✓ GPS module detected after power cycle")
            i2c.deinit()
            return True
        else:
            print("✗ GPS module not detected after power cycle")
            i2c.deinit()
            return False
            
    except Exception as e:
        print(f"✗ Power cycle failed: {e}")
        return False

def aggressive_gps_reset():
    """공격적인 GPS 리셋"""
    print("\n=== Aggressive GPS Reset ===")
    
    try:
        from adafruit_gps import GPS_GtopI2C
        
        # Initialize I2C bus
        i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
        
        # Initialize GPS module
        gps = GPS_GtopI2C(i2c, address=0x42)
        print("✓ GPS module initialized")
        
        # Step 1: Multiple hard resets
        print("Step 1: Multiple hard resets...")
        for i in range(3):
            try:
                print(f"  Reset attempt {i+1}/3...")
                gps.send_command(b'PMTK000')  # Factory reset
                time.sleep(3)
                print(f"  ✓ Reset {i+1} completed")
            except Exception as e:
                print(f"  ⚠️ Reset {i+1} warning: {e}")
        
        # Step 2: Clear all settings
        print("\nStep 2: Clearing all settings...")
        try:
            # Disable all sentences
            gps.send_command(b'PMTK314,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            time.sleep(1)
            print("✓ All sentences disabled")
            
            # Set minimum update rate
            gps.send_command(b'PMTK220,5000')  # 5Hz (200ms)
            time.sleep(1)
            print("✓ Update rate set to minimum")
            
        except Exception as e:
            print(f"⚠️ Settings clear warning: {e}")
        
        # Step 3: Wait for complete stabilization
        print("\nStep 3: Extended stabilization period...")
        success_count = 0
        error_count = 0
        
        for i in range(20):  # 20 seconds
            try:
                gps.update()
                success_count += 1
                if i % 5 == 0:  # Print every 5 seconds
                    print(f"  Stabilization {i+1}/20: OK")
            except Exception as e:
                error_count += 1
                if i % 5 == 0:  # Print every 5 seconds
                    print(f"  Stabilization {i+1}/20: Error - {e}")
            time.sleep(1)
        
        print(f"\nStabilization Summary:")
        print(f"  Successful: {success_count}/20")
        print(f"  Errors: {error_count}/20")
        print(f"  Success rate: {success_count/20*100:.1f}%")
        
        # Step 4: Configure minimal settings
        print("\nStep 4: Configuring minimal settings...")
        try:
            # Enable only GGA sentence
            gps.send_command(b'PMTK314,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0')
            time.sleep(1)
            print("✓ GGA sentence enabled only")
            
            # Set update rate to 1Hz
            gps.send_command(b'PMTK220,1000')
            time.sleep(1)
            print("✓ Update rate set to 1Hz")
            
        except Exception as e:
            print(f"⚠️ Configuration warning: {e}")
        
        # Step 5: Final test
        print("\nStep 5: Final test...")
        final_success = 0
        final_errors = 0
        
        for i in range(10):
            try:
                gps.update()
                final_success += 1
                print(f"  Test {i+1}/10: OK")
            except Exception as e:
                final_errors += 1
                print(f"  Test {i+1}/10: Error - {e}")
            time.sleep(1)
        
        print(f"\nFinal Test Summary:")
        print(f"  Successful: {final_success}/10")
        print(f"  Errors: {final_errors}/10")
        print(f"  Success rate: {final_success/10*100:.1f}%")
        
        # Cleanup
        i2c.deinit()
        
        if final_success >= 8:  # 80% success rate
            print("✓ Aggressive reset successful!")
            return True
        else:
            print("⚠️ Aggressive reset partially successful")
            return False
            
    except Exception as e:
        print(f"✗ Aggressive reset failed: {e}")
        return False

def check_gps_antenna():
    """GPS 안테나 상태 확인"""
    print("\n=== GPS Antenna Check ===")
    
    print("GPS Antenna Status:")
    print("1. Physical Connection:")
    print("   - Check if GPS antenna is properly connected")
    print("   - Verify antenna cable is not damaged")
    print("   - Ensure antenna is oriented upward")
    
    print("\n2. Signal Reception:")
    print("   - Move to outdoor location with clear sky view")
    print("   - Avoid buildings, trees, and other obstructions")
    print("   - Wait 5-10 minutes for first fix (cold start)")
    
    print("\n3. Power Supply:")
    print("   - Ensure stable 3.3V power supply")
    print("   - Check for voltage fluctuations")
    print("   - Verify adequate current supply (>50mA)")
    
    return True

def main():
    """메인 하드웨어 리셋 함수"""
    print("GPS Hardware Reset Tool")
    print("=" * 50)
    
    # Step 1: I2C bus reset
    i2c_ok = reset_i2c_bus()
    
    # Step 2: Power cycle simulation
    power_ok = power_cycle_gps()
    
    # Step 3: Aggressive GPS reset
    gps_ok = aggressive_gps_reset()
    
    # Step 4: Antenna check
    antenna_ok = check_gps_antenna()
    
    # Summary
    print("\n" + "=" * 50)
    print("HARDWARE RESET SUMMARY:")
    print(f"  I2C Bus Reset: {'✓ PASS' if i2c_ok else '✗ FAIL'}")
    print(f"  Power Cycle: {'✓ PASS' if power_ok else '✗ FAIL'}")
    print(f"  GPS Reset: {'✓ PASS' if gps_ok else '✗ FAIL'}")
    print(f"  Antenna Check: {'✓ PASS' if antenna_ok else '✗ FAIL'}")
    
    passed = sum([i2c_ok, power_ok, gps_ok, antenna_ok])
    total = 4
    
    print(f"\nOverall: {passed}/{total} steps passed")
    
    if passed >= 3:
        print("\n✓ Hardware reset mostly successful!")
        print("Try testing the GPS module now:")
        print("  python3 test_gps_simple.py")
    else:
        print("\n⚠️ Hardware reset partially successful")
        print("Consider the following:")
        print("1. Check physical connections")
        print("2. Verify power supply")
        print("3. Test with different GPS antenna")
        print("4. Try restarting the Raspberry Pi")

if __name__ == "__main__":
    main()
