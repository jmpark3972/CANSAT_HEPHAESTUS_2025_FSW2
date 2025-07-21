echo "Performing apt update, upgrade"

sudo apt-get update
yes | sudo apt-get -y upgrade
sudo apt-get install python3-pip

echo "installing python setup tools"

sudo apt install --upgrade python3-setuptools

echo "Creating virtual envinorment"

cd ~
sudo apt install python3-venv
python3 -m venv env --system-site-packages

echo "Activating virtual envinorment"

source ~/env/bin/activate

echo "Installing pigpio"

pip3 install pigpio
sudo systemctl enable pigpiod

echo "Installing adafruit blinka, do not reboot!"

cd ~
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
yes n | sudo -E env PATH=$PATH python3 raspi-blinka.py

echo "Installing adafruit sensor libraries"

pip3 install adafruit-circuitpython-bmp3xx
pip3 install adafruit-circuitpython-gps
pip3 install adafruit-circuitpython-bno055
pip3 install adafruit-circuitpython-ads1x15
pip3 install adafruit-circuitpython-motor

echo "Installing video libraires"

yes | sudo apt install ffmpeg
yes | pip install opencv-python
yes | sudo apt install python3-picamera2

echo "Installing basic modules"
pip3 install numpy==1.26.4

echo "Setting up crontab"
(crontab -l 2>/dev/null; echo "@reboot /home/pi/CANSAT_AAS_2025_FSW/startup.sh") | crontab -

echo "Rebooting"
sudo systemctl reboot