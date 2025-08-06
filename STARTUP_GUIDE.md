# CANSAT HEPHAESTUS 2025 FSW2 Startup Guide

## Overview
This guide explains how to use the startup scripts to run the CANSAT FSW2 system.

## Available Scripts

### 1. `startup.sh` - Basic Startup Script
Simple startup script that activates the virtual environment and runs main.py.

### 2. `startup_robust.sh` - Robust Startup Script
Advanced startup script with error handling, logging, and validation.

### 3. `test_startup.sh` - Startup Test Script
Test script to verify the startup configuration without running the full application.

## Usage

### Basic Usage
```bash
# Make scripts executable (if not already done)
chmod +x startup.sh startup_robust.sh test_startup.sh

# Test the configuration first
./test_startup.sh

# Run the basic startup script
./startup.sh

# Or run the robust startup script
./startup_robust.sh
```

### From Different Directory
```bash
# Run from any directory
/path/to/CANSAT_HEPHAESTUS_2025_FSW2/startup.sh
```

## Configuration

### Virtual Environment Path
The scripts are configured to use the virtual environment at:
```
/home/SpaceY/Desktop/env
```

If your virtual environment is in a different location, edit the `venv_path` variable in the startup scripts.

### Project Path
The scripts automatically detect the project directory, so no manual configuration is needed.

## Troubleshooting

### Common Issues

#### 1. "Permission denied" Error
```bash
# Solution: Make script executable
chmod +x startup.sh
```

#### 2. "required file not found" Error
```bash
# Solution: Check if you're in the correct directory
pwd
ls -la startup.sh

# If the file doesn't exist, you might be in the wrong directory
cd /path/to/CANSAT_HEPHAESTUS_2025_FSW2
```

#### 3. Virtual Environment Not Found
```bash
# Check if virtual environment exists
ls -la /home/SpaceY/Desktop/env

# If it doesn't exist, create it
python3 -m venv /home/SpaceY/Desktop/env
source /home/SpaceY/Desktop/env/bin/activate
pip install -r requirements.txt
```

#### 4. Python Dependencies Missing
```bash
# Activate virtual environment and install dependencies
source /home/SpaceY/Desktop/env/bin/activate
pip install -r requirements.txt
```

#### 5. Line Ending Issues (Windows)
If you see errors like `$'\r': command not found`, the script has Windows line endings.

```bash
# Fix line endings
dos2unix startup.sh
# Or manually edit the file and ensure it uses Unix line endings
```

### Testing Your Setup

1. **Run the test script first:**
   ```bash
   ./test_startup.sh
   ```

2. **Check the output for any errors**

3. **If all tests pass, run the startup script:**
   ```bash
   ./startup.sh
   ```

## Log Files

### Robust Startup Script Logs
The robust startup script creates logs in:
```
logs/startup.log
```

### Application Logs
The main application creates logs in:
```
logs/imu/high_freq_imu_log.csv
logs/imu/hk_log.csv
logs/imu/error_log.csv
```

## Automatic Startup

### Systemd Service (Recommended)
Create a systemd service for automatic startup:

1. **Create service file:**
   ```bash
   sudo nano /etc/systemd/system/cansat-hephaestus.service
   ```

2. **Add service configuration:**
   ```ini
   [Unit]
   Description=CANSAT HEPHAESTUS 2025 FSW2
   After=network.target

   [Service]
   Type=simple
   User=SpaceY
   WorkingDirectory=/home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2
   ExecStart=/home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2/startup_robust.sh
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start the service:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable cansat-hephaestus
   sudo systemctl start cansat-hephaestus
   ```

4. **Check service status:**
   ```bash
   sudo systemctl status cansat-hephaestus
   ```

### Cron Job (Alternative)
Add to crontab for startup:
```bash
crontab -e
# Add this line to start on boot:
@reboot /home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2/startup_robust.sh
```

## Monitoring

### Check if Application is Running
```bash
# Check for Python processes
ps aux | grep python3

# Check for main.py process
ps aux | grep main.py
```

### View Logs
```bash
# View startup logs
tail -f logs/startup.log

# View application logs
tail -f logs/imu/high_freq_imu_log.csv
```

### Stop the Application
```bash
# If running manually
Ctrl+C

# If running as systemd service
sudo systemctl stop cansat-hephaestus

# Kill all Python processes (use with caution)
pkill -f main.py
```

## Security Considerations

1. **File Permissions**: Ensure startup scripts are only executable by authorized users
2. **Virtual Environment**: Keep virtual environment secure and up to date
3. **Log Files**: Monitor log files for security-related events
4. **Network Access**: Consider firewall rules if the application uses network communication

## Support

If you encounter issues:

1. **Check the logs**: Look at startup and application logs for error messages
2. **Run the test script**: Use `test_startup.sh` to verify configuration
3. **Check file permissions**: Ensure scripts are executable
4. **Verify paths**: Confirm virtual environment and project paths are correct
5. **Check dependencies**: Ensure all Python packages are installed

For additional help, refer to the main project documentation or contact the development team. 