# CANSAT FSW Bus Error Fix Guide

## Problem Description
Your CANSAT application is experiencing a "Bus error" after loading all modules but before starting the main loop. This is a serious memory-related error that typically occurs when there's a memory access violation.

## Root Causes
Bus errors in this context are usually caused by:

1. **Memory Pressure**: Too many modules loaded simultaneously causing memory exhaustion
2. **Hardware Access Issues**: I2C, GPIO, or camera hardware access problems
3. **Multiprocessing Issues**: Problems with process creation and inter-process communication
4. **Library Conflicts**: Incompatible or corrupted Python libraries
5. **System Resource Limitations**: Insufficient RAM or disk space

## Diagnostic Steps

### Step 1: Run the Diagnostic Script
```bash
python3 debug_bus_error.py
```
This script will:
- Test each module import individually
- Monitor memory usage during loading
- Identify which module causes the failure
- Provide detailed error information

### Step 2: Test Hardware Access
```bash
python3 test_hardware_access.py
```
This script will:
- Test I2C bus access
- Test GPIO access
- Test camera hardware
- Test serial port access
- Check memory pressure
- Test critical Python module imports

### Step 3: Check System Resources
```bash
# Check available memory
free -h

# Check disk space
df -h

# Check running processes
ps aux | grep python

# Check system logs
dmesg | tail -20
```

## Solutions

### Solution 1: Use the Safe Main Script
Replace your current `main.py` with the safer version:

```bash
# Backup original
cp main.py main_original.py

# Use safe version
cp main_safe.py main.py

# Test the safe version
python3 main.py
```

The safe version includes:
- Gradual module loading with error handling
- Memory monitoring and garbage collection
- Better error recovery
- Graceful degradation when modules fail

### Solution 2: Reduce Memory Usage

#### Option A: Disable Non-Critical Modules
Edit `main.py` and comment out non-critical modules:

```python
# Comment out these lines to reduce memory usage
# from thermal_camera import thermo_cameraapp
# from camera import cameraapp
# from tmp007 import tmp007app
```

#### Option B: Increase Swap Space
```bash
# Check current swap
swapon --show

# Create additional swap file
sudo fallocate -l 1G /swapfile2
sudo chmod 600 /swapfile2
sudo mkswap /swapfile2
sudo swapon /swapfile2
```

### Solution 3: Fix Hardware Issues

#### I2C Issues
```bash
# Enable I2C
sudo raspi-config nonint do_i2c 0

# Check I2C devices
i2cdetect -y 1

# Restart I2C service
sudo systemctl restart i2c-dev
```

#### Camera Issues
```bash
# Enable camera
sudo raspi-config nonint do_camera 0

# Check camera hardware
vcgencmd get_camera

# Restart camera service
sudo systemctl restart camera
```

#### GPIO Issues
```bash
# Check GPIO permissions
ls -la /dev/gpiomem

# Fix GPIO permissions if needed
sudo chmod 666 /dev/gpiomem
```

### Solution 4: Update Dependencies
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python packages
pip3 install --upgrade pip
pip3 install --upgrade -r requirements.txt

# Clean Python cache
find . -name "*.pyc" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### Solution 5: System Optimization

#### Increase Memory Limits
Edit `/etc/security/limits.conf`:
```
pi soft memlock unlimited
pi hard memlock unlimited
```

#### Optimize Python Memory
Add to your script:
```python
import gc
import sys

# Enable garbage collection
gc.enable()

# Set memory limit (adjust as needed)
import resource
resource.setrlimit(resource.RLIMIT_AS, (1024 * 1024 * 1024, -1))  # 1GB limit
```

## Testing Strategy

### Phase 1: Minimal Configuration
1. Start with only core modules (HK, GPS, IMU)
2. Test basic functionality
3. Gradually add modules one by one

### Phase 2: Hardware Testing
1. Test each hardware component individually
2. Verify I2C communication
3. Test camera functionality
4. Check serial communication

### Phase 3: Full System Test
1. Load all modules with safe version
2. Monitor memory usage
3. Test complete mission cycle

## Monitoring and Debugging

### Memory Monitoring
```bash
# Monitor memory usage in real-time
watch -n 1 'free -h'

# Monitor Python process memory
ps aux | grep python | grep -v grep
```

### Log Analysis
```bash
# Check application logs
tail -f logs/*.log

# Check system logs
tail -f /var/log/syslog | grep -i python
```

### Performance Profiling
```bash
# Install memory profiler
pip3 install memory_profiler

# Profile memory usage
python3 -m memory_profiler main.py
```

## Emergency Recovery

### If System Becomes Unresponsive
1. **Hard Reset**: Power cycle the Raspberry Pi
2. **Safe Mode**: Boot with minimal services
3. **Recovery Mode**: Use backup configuration

### Data Recovery
```bash
# Check for corrupted files
find . -name "*.py" -exec python3 -m py_compile {} \;

# Restore from backup
cp -r backup/* .
```

## Prevention Measures

### Regular Maintenance
1. **Weekly**: Check system resources
2. **Monthly**: Update dependencies
3. **Before Missions**: Full system test

### Monitoring Setup
1. **Memory Alerts**: Set up memory usage monitoring
2. **Error Logging**: Implement comprehensive error logging
3. **Health Checks**: Regular system health checks

### Backup Strategy
1. **Code Backup**: Version control with Git
2. **Configuration Backup**: Regular config backups
3. **System Backup**: Full system image backup

## Contact and Support

If you continue to experience issues:

1. **Check Logs**: Review all error logs
2. **Document Steps**: Record exact steps to reproduce
3. **System Info**: Collect system information
4. **Contact Team**: Reach out to the development team

## Quick Fix Checklist

- [ ] Run diagnostic scripts
- [ ] Check system resources
- [ ] Test hardware access
- [ ] Use safe main script
- [ ] Reduce memory usage
- [ ] Fix hardware issues
- [ ] Update dependencies
- [ ] Test minimal configuration
- [ ] Monitor performance
- [ ] Document changes

## Success Criteria

The system is considered fixed when:
- [ ] All modules load without bus errors
- [ ] Memory usage stays below 80%
- [ ] All hardware components function correctly
- [ ] System runs stable for extended periods
- [ ] No critical errors in logs 