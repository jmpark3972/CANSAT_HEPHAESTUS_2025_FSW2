#!/usr/bin/env python3
"""
Test script to verify the message structure fixes
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_msg_structure():
    """Test that MsgStructure works correctly with data attribute"""
    try:
        from lib import msgstructure
        from lib import appargs
        
        # Create a test message
        msg = msgstructure.MsgStructure()
        
        # Fill the message
        success = msgstructure.fill_msg(msg, 10, 14, 1003, "86.65,25.37,1002.88")
        
        if not success:
            print("❌ Message filling failed")
            return False
            
        # Test that data attribute exists and works
        if not hasattr(msg, 'data'):
            print("❌ MsgStructure missing 'data' attribute")
            return False
            
        if msg.data != "86.65,25.37,1002.88":
            print(f"❌ Data attribute incorrect: {msg.data}")
            return False
            
        # Test packing and unpacking
        packed = msgstructure.pack_msg(msg)
        if packed == "ERROR":
            print("❌ Message packing failed")
            return False
            
        # Unpack the message
        new_msg = msgstructure.MsgStructure()
        if not msgstructure.unpack_msg(new_msg, packed):
            print("❌ Message unpacking failed")
            return False
            
        if new_msg.data != msg.data:
            print(f"❌ Unpacked data doesn't match: {new_msg.data} vs {msg.data}")
            return False
            
        print("✅ Message structure test passed")
        return True
        
    except Exception as e:
        print(f"❌ Message structure test failed: {e}")
        return False

def test_flight_logic_import():
    """Test that FlightLogic can import without errors"""
    try:
        from flight_logic import flightlogicapp
        print("✅ FlightLogic import successful")
        return True
    except Exception as e:
        print(f"❌ FlightLogic import failed: {e}")
        return False

def test_app_args():
    """Test that all required message IDs exist"""
    try:
        from lib import appargs
        
        # Test that MID_RocketMotorStandby exists
        if not hasattr(appargs.FlightlogicAppArg, 'MID_RocketMotorStandby'):
            print("❌ MID_RocketMotorStandby missing")
            return False
            
        print(f"✅ MID_RocketMotorStandby = {appargs.FlightlogicAppArg.MID_RocketMotorStandby}")
        
        # Test other message IDs
        required_mids = [
            'MID_SendThermoFlightLogicData',
            'MID_SendThermisFlightLogicData', 
            'MID_SendImuFlightLogicData',
            'MID_SendGpsTlmData',
            'MID_SendBarometerFlightLogicData',
            'MID_SendFIR1Data',
            'MID_SendCamFlightLogicData',
            'MID_SendCameraFlightLogicData',
            'MID_SendPitotFlightLogicData',
            'MID_SendTmp007FlightLogicData',
            'MID_SendGpsFlightLogicData'
        ]
        
        for mid_name in required_mids:
            if not hasattr(appargs.ThermoAppArg, mid_name) and \
               not hasattr(appargs.ThermisAppArg, mid_name) and \
               not hasattr(appargs.ImuAppArg, mid_name) and \
               not hasattr(appargs.GpsAppArg, mid_name) and \
               not hasattr(appargs.BarometerAppArg, mid_name) and \
               not hasattr(appargs.FirApp1Arg, mid_name) and \
               not hasattr(appargs.ThermalcameraAppArg, mid_name) and \
               not hasattr(appargs.CameraAppArg, mid_name) and \
               not hasattr(appargs.PitotAppArg, mid_name) and \
               not hasattr(appargs.Tmp007AppArg, mid_name):
                print(f"❌ Missing message ID: {mid_name}")
                return False
                
        print("✅ All required message IDs found")
        return True
        
    except Exception as e:
        print(f"❌ App args test failed: {e}")
        return False

def test_motor_app_import():
    """Test that Motor app can import without errors"""
    try:
        from motor import motorapp
        print("✅ Motor app import successful")
        return True
    except Exception as e:
        print(f"❌ Motor app import failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing message structure fixes...")
    print("=" * 50)
    
    msg_ok = test_msg_structure()
    flight_logic_ok = test_flight_logic_import()
    app_args_ok = test_app_args()
    motor_ok = test_motor_app_import()
    
    print("=" * 50)
    if msg_ok and flight_logic_ok and app_args_ok and motor_ok:
        print("✅ All tests passed! The message structure fixes should resolve the issues.")
    else:
        print("❌ Some tests failed. Please check the errors above.") 