# CANSAT FSW2 Fixes Summary

## Issues Identified and Fixed

### 1. FSW_CONF Configuration Issue
**Problem**: The comm app was failing with error `module 'lib.config' has no attribute 'FSW_CONF'`

**Root Cause**: The `lib/config.py` file was missing the FSW configuration constants that other modules expected.

**Fix Applied**:
- Added missing FSW configuration constants to `lib/config.py`:
  - `CONF_NONE = 0`
  - `CONF_PAYLOAD = 1` 
  - `CONF_CONTAINER = 2`
  - `CONF_ROCKET = 3`
- Added `FSW_CONF_MAPPING` dictionary to map string modes to integer constants
- Added `FSW_CONF` variable that maps the current FSW mode to the appropriate constant

**Files Modified**:
- `lib/config.py` - Added missing FSW configuration constants

### 2. Camera Permission Issue
**Problem**: Camera app was failing with `Permission denied: '/home/pi'` error

**Root Cause**: The camera module was trying to create directories in `/home/pi` which requires root permissions.

**Fix Applied**:
- Changed hardcoded absolute paths to relative paths in the project directory:
  - `VIDEO_DIR` from `/home/pi/cansat_videos` to `logs/cansat_videos`
  - `TEMP_DIR` from `/tmp/cansat_camera` to `logs/cansat_camera_temp`
  - `LOG_DIR` from `/home/pi/cansat_logs` to `logs/cansat_camera_logs`

**Files Modified**:
- `camera/camera.py` - Updated directory paths
- `camera/camera_config.py` - Updated video directory path

### 3. Message Structure Issue
**Problem**: FlightLogic was failing with `'MsgStructure' object has no attribute 'MsgData'` errors

**Root Cause**: FlightLogic was trying to access `recv_msg.MsgData` but the `MsgStructure` class only has a `data` attribute.

**Fix Applied**:
- Updated all `recv_msg.MsgData` references to `recv_msg.data` in FlightLogic
- Added handlers for previously unknown message IDs (2503, 2603, 1203)
- Added missing `MID_RocketMotorStandby` to `FlightlogicAppArg`

**Files Modified**:
- `flight_logic/flightlogicapp.py` - Fixed MsgData references and added message handlers
- `lib/appargs.py` - Added missing MID_RocketMotorStandby

### 4. IMU Sensor Error Handling
**Problem**: IMU was failing with `unsupported operand type(s) for *: 'NoneType' and 'NoneType'` errors

**Root Cause**: IMU sensor was returning None values that weren't properly handled before mathematical operations.

**Fix Applied**:
- Added additional None value checks for quaternion data
- Added try-catch blocks around mathematical calculations
- Improved error logging for debugging

**Files Modified**:
- `imu/imu.py` - Enhanced None value handling and error checking

### 5. Process Management Issue
**Problem**: Process 16 (Comm app) was dead and causing repeated warnings

**Root Cause**: The comm app was failing during initialization due to the FSW_CONF issue, causing the process to terminate.

**Fix Applied**:
- The FSW_CONF fix should resolve this issue as the comm app will now be able to initialize properly.

### 6. Thermal Camera Format Error
**Problem**: Thermal camera was failing with `TypeError: unsupported format string passed to NoneType.__format__`

**Root Cause**: Thermal camera variables (THERMAL_AVG, THERMAL_MIN, THERMAL_MAX) were None when trying to format them.

**Fix Applied**:
- Added None value checks before formatting thermal camera data
- Added try-catch blocks around the send_cam_data function
- Provided default values (0.0) when thermal data is None

**Files Modified**:
- `thermal_camera/thermo_cameraapp.py` - Added None value handling for thermal data formatting

### 7. Camera Hardware Detection Issue
**Problem**: Camera app was failing with "카메라 하드웨어 감지되지 않음" error

**Root Cause**: Camera hardware detection was too strict and would fail the entire camera initialization.

**Fix Applied**:
- Enhanced camera hardware detection with multiple methods:
  - vcgencmd get_camera
  - /proc/device-tree/soc/csi1 check
  - dmesg camera/CSI message check
  - libcamera-hello --list-cameras test
- Made camera initialization more robust - continues even if hardware detection fails
- Added detailed troubleshooting information in error messages
- Changed camera status to "LIMITED" mode when hardware/driver issues exist

**Files Modified**:
- `camera/camera.py` - Enhanced hardware detection and made initialization more robust
- `camera/cameraapp.py` - Made camera app continue even if camera initialization fails

### 8. Pi Camera Standalone Testing
**Problem**: No independent way to test Pi Camera functionality outside of the main CANSAT system

**Root Cause**: Camera testing was only possible through the main system, making debugging difficult.

**Fix Applied**:
- Created standalone camera testing scripts for independent testing and debugging
- Added comprehensive camera installation and setup scripts
- Created detailed documentation for camera usage and troubleshooting

**Files Created**:
- `camera/standalone_camera.py` - Independent camera test script with interactive interface
- `camera/simple_camera_test.py` - Quick camera functionality test script
- `camera/install_camera.sh` - Automated camera installation script
- `camera/CAMERA_README.md` - Comprehensive camera usage guide

## Testing the Fixes

### 1. Run the Test Scripts
```bash
# Test configuration and camera fixes
python test_fixes.py

# Test message structure fixes
python test_message_fixes.py

# Test camera functionality (after installation)
python camera/simple_camera_test.py

# Test standalone camera
python camera/standalone_camera.py
```

These scripts will verify:
- ✅ Config module imports successfully
- ✅ FSW_CONF constants are available
- ✅ Camera directories can be created without permission issues
- ✅ Comm app can import config without errors
- ✅ Message structure works correctly
- ✅ FlightLogic can import without errors
- ✅ All required message IDs exist
- ✅ Motor app can import without errors
- ✅ Camera hardware is detected (with multiple methods)
- ✅ Camera drivers are working
- ✅ FFmpeg is properly installed
- ✅ Video recording functionality works
- ✅ Thermal camera handles None values properly

### 2. Install Camera (if needed)
```bash
# Run the camera installation script
chmod +x camera/install_camera.sh
./camera/install_camera.sh
```

This will:
- Install all required camera packages
- Enable camera interfaces
- Set up proper permissions
- Create necessary directories
- Configure system settings

### 3. Test the Main Application
```bash
python main.py
```

Expected behavior after fixes:
- ✅ All apps should load successfully
- ✅ No FSW_CONF errors in comm app
- ✅ No permission errors in camera app
- ✅ No "Process 16 is dead" warnings
- ✅ No "MsgData" attribute errors in FlightLogic
- ✅ No "MID_RocketMotorStandby" missing errors in motor app
- ✅ Reduced IMU sensor errors
- ✅ Proper handling of all message types
- ✅ Camera functionality works (even in LIMITED mode)
- ✅ No thermal camera format errors
- ✅ Better error handling and logging

### 4. Verify Individual Components
```bash
# Test config module
python -c "from lib import config; print(f'FSW_CONF: {config.FSW_CONF}')"

# Test camera module
python -c "from camera import camera; print('Camera module imports successfully')"

# Test comm module
python -c "from comm import commapp; print('Comm module imports successfully')"

# Test message structure
python -c "from lib import msgstructure; msg = msgstructure.MsgStructure(); print('Message structure works')"

# Test flight logic
python -c "from flight_logic import flightlogicapp; print('FlightLogic imports successfully')"

# Test camera hardware
vcgencmd get_camera

# Test video devices
ls -la /dev/video*

# Test thermal camera
python -c "from thermal_camera import thermo_cameraapp; print('Thermal camera imports successfully')"
```

## Additional Recommendations

### 1. Error Handling
Consider adding better error handling in the main process to gracefully handle app initialization failures without causing the entire system to become unstable.

### 2. Logging
The logging system appears to be working well. Consider adding more detailed error messages to help diagnose future issues.

### 3. Configuration Management
The new configuration system in `lib/config.py` provides better structure. Consider migrating all hardcoded values to use this centralized configuration system.

### 4. Directory Structure
The relative path approach for camera directories is more portable. Consider applying this pattern to other modules that might have similar permission issues.

### 5. Sensor Robustness
Consider implementing retry mechanisms and fallback values for sensor readings to improve system stability during hardware issues.

### 6. Camera Testing
Use the new standalone camera scripts for:
- Initial camera setup verification
- Troubleshooting camera issues
- Testing camera functionality independently
- Performance optimization
- Quality testing

### 7. Hardware Diagnostics
For persistent hardware issues:
- Check I2C bus connections and addresses
- Verify sensor power supply
- Monitor system temperature
- Check for electromagnetic interference
- Consider adding hardware watchdog timers

## Files Created/Modified

### Modified Files:
- `lib/config.py` - Added FSW configuration constants
- `camera/camera.py` - Updated directory paths and enhanced hardware detection
- `camera/camera_config.py` - Updated video directory path
- `flight_logic/flightlogicapp.py` - Fixed MsgData references and added message handlers
- `lib/appargs.py` - Added missing MID_RocketMotorStandby
- `imu/imu.py` - Enhanced error handling for None values
- `thermal_camera/thermo_cameraapp.py` - Added None value handling for thermal data
- `camera/cameraapp.py` - Made camera app more robust to initialization failures

### Created Files:
- `test_fixes.py` - Test script to verify configuration and camera fixes
- `test_message_fixes.py` - Test script to verify message structure fixes
- `camera/standalone_camera.py` - Independent camera test script
- `camera/simple_camera_test.py` - Quick camera functionality test
- `camera/install_camera.sh` - Automated camera installation script
- `camera/CAMERA_README.md` - Comprehensive camera usage guide
- `FIXES_SUMMARY.md` - This summary document

## Next Steps

1. **Test the fixes** using the provided test scripts
2. **Install camera components** if needed using the installation script
3. **Run the main application** to verify all issues are resolved
4. **Test camera functionality** using the standalone scripts
5. **Monitor the system** for any new issues that might arise
6. **Consider implementing** the additional recommendations for better robustness
7. **Test sensor functionality** under various conditions to ensure stability
8. **Optimize camera settings** based on your specific requirements
9. **Set up hardware diagnostics** for persistent sensor issues
10. **Implement monitoring** for system health and performance 