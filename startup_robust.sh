#!/bin/bash
# Robust startup script for CANSAT HEPHAESTUS 2025 FSW2
# This script includes error handling, logging, and automatic recovery

# Configuration
python_path="/home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2"
venv_path="/home/SpaceY/Desktop/env"
log_dir="/home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2/logs"
startup_log="${log_dir}/startup.log"

# Create log directory if it doesn't exist
mkdir -p "${log_dir}"

# Logging function
log_message() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] $1" | tee -a "${startup_log}"
}

# Error handling function
handle_error() {
    local exit_code=$?
    log_message "ERROR: Startup script failed with exit code ${exit_code}"
    log_message "ERROR: Last command: $BASH_COMMAND"
    exit ${exit_code}
}

# Set error handling
set -e
trap handle_error ERR

# Main startup sequence
log_message "=== CANSAT HEPHAESTUS 2025 FSW2 Startup Script ==="

# Check if paths are configured
if [ "${python_path}" == "not_configured" ]; then
    log_message "ERROR: Startup Script is not Configured! Please Edit the file"
    exit 1
fi

# Validate paths
log_message "Validating paths..."
if [ ! -d "${python_path}" ]; then
    log_message "ERROR: Python path does not exist: ${python_path}"
    exit 1
fi

if [ ! -d "${venv_path}" ]; then
    log_message "ERROR: Virtual environment path does not exist: ${venv_path}"
    exit 1
fi

if [ ! -f "${venv_path}/bin/activate" ]; then
    log_message "ERROR: Virtual environment activate script not found: ${venv_path}/bin/activate"
    exit 1
fi

if [ ! -f "${python_path}/main.py" ]; then
    log_message "ERROR: main.py not found in: ${python_path}"
    exit 1
fi

log_message "Path validation successful"
log_message "Python path: ${python_path}"
log_message "Virtual environment: ${venv_path}"

# Change to project directory
log_message "Changing to project directory..."
cd "${python_path}"
log_message "Current directory: $(pwd)"

# Activate virtual environment
log_message "Activating virtual environment..."
source "${venv_path}/bin/activate"
log_message "Virtual environment activated"

# Check Python version and dependencies
log_message "Checking Python environment..."
python3 --version
pip list | grep -E "(numpy|adafruit|pyserial)" || log_message "WARNING: Some dependencies may be missing"

# Create necessary directories
log_message "Creating necessary directories..."
mkdir -p "${python_path}/logs/imu"
mkdir -p "${python_path}/logs"
mkdir -p "${python_path}/eventlogs"

# Set environment variables
export PYTHONPATH="${python_path}:${PYTHONPATH}"
log_message "PYTHONPATH set to: ${PYTHONPATH}"

# Start the main application
log_message "Starting CANSAT HEPHAESTUS 2025 FSW2..."
log_message "=== Application Starting ==="

# Run main.py with error handling
python3 main.py

# If we reach here, the application has exited
log_message "=== Application Exited ==="
log_message "Startup script completed" 