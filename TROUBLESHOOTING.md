# CANSAT System Troubleshooting Guide

## Current Issues Identified

Based on the terminal output, your CANSAT system has several issues:

### 1. Main Loop Errors
- **Problem**: Repeated "Main loop error" messages flooding the logs
- **Cause**: Poor error handling in the main message processing loop
- **Solution**: Run the quick fix script to improve error handling

### 2. Sensor Initialization Issues
- **THERMIS Sensor**: ADS1115 not found on I2C bus
- **Barometer**: Working but returning 0.0 values initially
- **Other Sensors**: Some returning 0.0 values

### 3. XBee Communication
- **Problem**: XBee not connected, running in simulation mode
- **Solution**: Connect XBee USB adapter and check permissions

### 4. Watchdog Timer
- **Problem**: 10-second watchdog forcing termination
- **Solution**: Disabled in current version

## Quick Fix Instructions

### Step 1: Run the Quick Fix Script
```bash
python3 quick_fix.py
```

This script will:
- Fix main loop error handling
- Check and configure I2C
- Check and configure serial ports
- Check and configure GPIO
- Create a sensor test script

### Step 2: Run Diagnostics
```bash
python3 diagnostic_script.py
```

This will provide detailed information about:
- System resources
- I2C devices
- Serial ports
- GPIO access
- Python dependencies

### Step 3: Test Sensors
```bash
python3 sensor_test.py
```

This will test individual sensors to identify hardware issues.

## Detailed Troubleshooting

### THERMIS Sensor Issues

The THERMIS sensor (ADS1115) is not being detected. This could be due to:

1. **I2C Address Issues**: ADS1115 can be at addresses 0x48-0x4B
2. **Qwiic Mux Channel**: Check if the correct channel is selected
3. **Hardware Connection**: Verify wiring and power supply

**Debug Steps**:
```bash
# Check I2C devices
i2cdetect -y 1
i2cdetect -y 0

# Check Qwiic Mux
python3 -c "
from lib.qwiic_mux import QwiicMux
mux = QwiicMux()
print('Mux initialized')
"
```

### Sensor Zero Values

Sensors returning 0.0 values could indicate:

1. **Initialization Timing**: Some sensors need time to warm up
2. **I2C Bus Issues**: Check for bus conflicts or timing issues
3. **Power Supply**: Verify stable power to sensors

**Debug Steps**:
```bash
# Check I2C bus status
python3 -c "
import board
import busio
i2c = busio.I2C(board.SCL, board.SDA)
print('I2C bus available')
"
```

### XBee Communication

**To fix XBee issues**:

1. **Connect XBee**: Plug in XBee USB adapter
2. **Check Permissions**: Ensure user is in dialout group
3. **Check Device**: Verify device appears in `/dev/ttyUSB*`

```bash
# Check serial devices
ls -la /dev/ttyUSB*
ls -la /dev/ttyACM*

# Check user groups
groups

# Add to dialout if needed
sudo usermod -a -G dialout $USER
```

### Main Loop Error Reduction

The main loop errors are being reduced by:

1. **Error Rate Limiting**: Only log errors every 5 seconds
2. **Better Exception Handling**: Distinguish between timeouts and real errors
3. **Queue Empty Handling**: Don't log expected queue timeouts

## Hardware Checklist

### Required Connections
- [ ] Qwiic Mux properly connected to I2C bus
- [ ] THERMIS sensor connected to correct Mux channel
- [ ] Barometer sensor connected and powered
- [ ] XBee USB adapter connected
- [ ] All sensors have stable power supply

### I2C Addresses
- Qwiic Mux: 0x70
- THERMIS (ADS1115): 0x48-0x4B (check all)
- Barometer: 0x76 or 0x77
- IMU: 0x28
- Thermal Camera: 0x33

## System Requirements

### Software Dependencies
- Python 3.7+
- i2c-tools
- pigpiod
- adafruit_blinka
- psutil

### Hardware Requirements
- Raspberry Pi (tested on Pi 4)
- I2C enabled in config.txt
- User in dialout group
- Stable power supply

## Recovery Procedures

### If System Crashes
1. Check logs in `logs/` directory
2. Restart pigpiod: `sudo systemctl restart pigpiod`
3. Check for zombie processes: `ps aux | grep python`
4. Kill any stuck processes: `pkill -f main.py`

### If Sensors Don't Work
1. Run `i2cdetect -y 1` to check I2C devices
2. Check physical connections
3. Verify power supply
4. Test individual sensors with `sensor_test.py`

### If Communication Fails
1. Check XBee connection
2. Verify serial port permissions
3. Test with simple serial communication
4. Check XBee configuration

## Performance Optimization

### Reduce Error Spam
- Error logging is now rate-limited
- Queue timeouts are not logged as errors
- Better exception handling

### Memory Management
- Processes are started sequentially
- Resource limits are checked
- Watchdog timer is disabled

### Sensor Timing
- Sensors are given time to initialize
- I2C bus is properly managed
- Qwiic Mux channel switching is handled

## Contact and Support

If issues persist after following this guide:

1. Check the logs in `logs/` directory
2. Run `python3 diagnostic_script.py` and save output
3. Test individual sensors with `python3 sensor_test.py`
4. Document any error messages or unexpected behavior

## Common Error Messages

### "THERMIS ADS1115를 찾을 수 없습니다"
- Check I2C connections
- Verify Qwiic Mux channel
- Test with `i2cdetect -y 1`

### "XBee가 연결되지 않았습니다"
- Connect XBee USB adapter
- Check user permissions
- Verify device appears in `/dev/ttyUSB*`

### "Main loop error"
- This is now rate-limited to reduce spam
- Check message queue handling
- Verify process communication

### "워치독: 10초 경과"
- Watchdog timer is now disabled
- System should run continuously
- Check for other termination conditions 