#!/bin/bash
# This is the startup script
# This script should be executed on startup
# configure the path to contain the python code you want to run first
# the path should be absolute

# Example) python_path = /home/hyunlee/Desktop/flight_code/Python_Cansat_FSW

python_path="/home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2"
venv_path="/home/SpaceY/Desktop/env"

if [ "${python_path}" == "not_configured" ]; then
    echo "Startup Script is not Configured! Please Edit the file"
else
    echo "Path > ${python_path}"
    echo "venv > ${venv_path}/bin/activate"
    
    # Activate virtual environment and run main.py
    source ${venv_path}/bin/activate
    cd ${python_path}
    python3 main.py
fi