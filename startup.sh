#!/bin/bash
# This is the startup script
# This script should be executed on startup
# configure the path to contain the python code you want to run first
# the path should be absolute

# Example) python_path = /home/hyunlee/Desktop/flight_code/Python_Cansat_FSW

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_path="${SCRIPT_DIR}"
venv_path="/home/SpaceY/Desktop/env"

echo "Script directory: ${SCRIPT_DIR}"
echo "Python path: ${python_path}"
echo "Virtual environment: ${venv_path}"

# Check if virtual environment exists
if [ ! -d "${venv_path}" ]; then
    echo "ERROR: Virtual environment not found at ${venv_path}"
    echo "Please check the venv_path in the script"
    exit 1
fi

# Check if main.py exists
if [ ! -f "${python_path}/main.py" ]; then
    echo "ERROR: main.py not found in ${python_path}"
    echo "Please check the python_path in the script"
    exit 1
fi

echo "Path > ${python_path}"
echo "venv > ${venv_path}/bin/activate"

# Activate virtual environment and run main.py
source "${venv_path}/bin/activate"
cd "${python_path}"
echo "Current directory: $(pwd)"
echo "Starting main.py..."
python3 main.py