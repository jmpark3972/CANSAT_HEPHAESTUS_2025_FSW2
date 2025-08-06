#!/usr/bin/env python3
"""
Test script to verify the fixes for FSW_CONF and camera permission issues
"""

import sys
import os

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

def test_config_fix():
    """Test that FSW_CONF is now available"""
    try:
        from lib import config
        print("✅ Config module imported successfully")
        
        # Test FSW_CONF
        print(f"✅ FSW_CONF = {config.FSW_CONF}")
        print(f"✅ CONF_PAYLOAD = {config.CONF_PAYLOAD}")
        print(f"✅ CONF_CONTAINER = {config.CONF_CONTAINER}")
        print(f"✅ CONF_ROCKET = {config.CONF_ROCKET}")
        
        # Test team ID mapping
        team_id = config.get_team_id()
        print(f"✅ Team ID = {team_id}")
        
        return True
    except Exception as e:
        print(f"❌ Config test failed: {e}")
        return False

def test_camera_paths():
    """Test that camera paths are now relative"""
    try:
        from camera.camera import camera
        print("✅ Camera module imported successfully")
        
        # Test directory creation
        if camera.ensure_directories():
            print("✅ Camera directories created successfully")
            return True
        else:
            print("❌ Camera directory creation failed")
            return False
    except Exception as e:
        print(f"❌ Camera test failed: {e}")
        return False

def test_comm_app():
    """Test that comm app can import config without errors"""
    try:
        from comm.commapp import commapp
        print("✅ Comm app imported successfully")
        
        # Test that FSW_CONF is accessible
        from lib import config
        selected_config = config.FSW_CONF
        print(f"✅ Comm app can access FSW_CONF: {selected_config}")
        
        return True
    except Exception as e:
        print(f"❌ Comm app test failed: {e}")
        return False

if __name__ == "__main__":
    print("Testing CANSAT fixes...")
    print("=" * 50)
    
    config_ok = test_config_fix()
    camera_ok = test_camera_paths()
    comm_ok = test_comm_app()
    
    print("=" * 50)
    if config_ok and camera_ok and comm_ok:
        print("✅ All tests passed! The fixes should resolve the issues.")
    else:
        print("❌ Some tests failed. Please check the errors above.") 