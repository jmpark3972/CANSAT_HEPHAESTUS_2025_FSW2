# This is the startup script
# This script should be executed on startup
# configure the path to contain the python code you want to run first
# the path should be absolute

python_path="home/SpaceY/Desktop/CANSAT_HEPHAESTUS_2025_FSW2"
venv_path="home/SpaceY/Desktop/env/bin"

if [ "${python_path}" == "not_configured" ]; then
echo "Startup Script is not Configured! Please Edit the file"

else
echo "Path > ${python_path}"
echo "venv > ${venv_path}/activate"
. ${venv_path}/activate;
cd ${python_path};python3 main.py

fi