# This is the startup script
# This script should be executed on startup
# configure the path to contain the python code you want to run first
# the path should be absolute

# Example) python_path = /home/hyunlee/Desktop/flight_code/Python_Cansat_FSW

python_path="/home/SpaceY/Desktop/CANSAT_AAS_2025_FSW"
venv_path="/home/SpaceY/Desktop/env/bin"

if [ "${python_path}" == "not_configured" ]; then
echo "Startup Script is not Configured! Please Edit the file"

else
echo "Path > ${python_path}"
echo "venv > ${venv_path}/activate"
. ${venv_path}/activate;
cd ${python_path};python3 main.py

fi