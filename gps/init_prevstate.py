#!/usr/bin/env python3
"""
Initialize prevstate.txt file
prevstate.txt 파일을 초기화하는 스크립트
"""

import os
import sys

def init_prevstate():
    """Initialize prevstate.txt file"""
    try:
        # Get the project root directory (parent of gps directory)
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        prevstate_path = os.path.join(project_root, "lib", "prevstate.txt")
        
        # Create lib directory if it doesn't exist
        lib_dir = os.path.dirname(prevstate_path)
        os.makedirs(lib_dir, exist_ok=True)
        
        # Create prevstate.txt with default values
        with open(prevstate_path, "w") as f:
            f.write("PREV_STATE=0\n")
            f.write("PREV_ALT_CAL=0\n")
            f.write("PREV_MAX_ALT=0\n")
        
        print(f"✓ prevstate.txt initialized at: {prevstate_path}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to initialize prevstate.txt: {e}")
        return False

if __name__ == "__main__":
    print("Initializing prevstate.txt...")
    success = init_prevstate()
    
    if success:
        print("✓ prevstate.txt initialization successful!")
        print("You can now run gpsapp.py and hybrid_gpsapp.py")
    else:
        print("✗ prevstate.txt initialization failed!")
        sys.exit(1)
