#!/bin/bash
# CANSAT FSW Initial Installation Script
# HEPHAESTUS CANSAT Team

echo "=== CANSAT FSW 초기 설치 스크립트 ==="
echo ""

# 1. 시스템 업데이트
echo "1. 시스템 업데이트 및 업그레이드..."
sudo apt-get update
yes | sudo apt-get -y upgrade
sudo apt-get install python3-pip

# 2. Python 환경 설정
echo ""
echo "2. Python 환경 설정..."
sudo apt install --upgrade python3-setuptools
sudo apt install python3-venv

# 가상환경 생성
cd ~
python3 -m venv env --system-site-packages
source ~/env/bin/activate

# 3. GPIO 및 하드웨어 라이브러리 설치
echo ""
echo "3. GPIO 및 하드웨어 라이브러리 설치..."
pip3 install pigpio
sudo systemctl enable pigpiod

# Adafruit Blinka 설치
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
yes n | sudo -E env PATH=$PATH python3 raspi-blinka.py

# 4. 센서 라이브러리 설치
echo ""
echo "4. 센서 라이브러리 설치..."
pip3 install adafruit-circuitpython-bmp3xx
pip3 install adafruit-circuitpython-gps
pip3 install adafruit-circuitpython-bno055
pip3 install adafruit-circuitpython-ads1x15
pip3 install adafruit-circuitpython-motor

# 5. 비디오 라이브러리 설치
echo ""
echo "5. 비디오 라이브러리 설치..."
yes | sudo apt install ffmpeg
yes | pip install opencv-python
yes | sudo apt install python3-picamera2

# 6. 기본 모듈 설치
echo ""
echo "6. 기본 모듈 설치..."
pip3 install numpy==1.26.4

# 7. 추가 SD카드 설정 (선택사항)
echo ""
echo "7. 추가 SD카드 설정..."
read -p "추가 SD카드를 설정하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "추가 SD카드 설정을 시작합니다..."
    
    # 필요한 패키지 설치
    sudo apt install -y device-tree-compiler git
    
    # Device Tree Overlay 생성
    cat > ~/spi_sd1.dts <<'EOF'
/dts-v1/;
/plugin/;

fragment@0 {
    target = <&spi0>;
    __overlay__ {
        status = "okay";
        #address-cells = <1>;
        #size-cells   = <0>;

        sd1: mmc@1 {
            compatible        = "mmc-spi-slot";
            reg               = <1>;
            spi-max-frequency = <12000000>;
            voltage-ranges    = <3300 3300>;
            broken-cd;
        };
    };
};
EOF

    # Device Tree Overlay 컴파일 및 설치
    dtc -@ -I dts -O dtb -o spi_sd1.dtbo spi_sd1.dts
    sudo cp spi_sd1.dtbo /boot/firmware/overlays/
    
    # config.txt 설정
    sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d_%H%M%S)
    cat >> /boot/firmware/config.txt <<'EOF'

# Secondary SD Card Configuration
[all]
dtparam=spi=on
disable_spidev=1
dtoverlay=spi_sd1
EOF
    
    echo "✓ 추가 SD카드 설정 완료 (재부팅 후 활성화)"
else
    echo "추가 SD카드 설정을 건너뜁니다."
fi

# 8. 시작 스크립트 설정
echo ""
echo "8. 시작 스크립트 설정..."
(crontab -l 2>/dev/null; echo "@reboot /home/pi/CANSAT_AAS_2025_FSW/startup.sh") | crontab -
echo "✓ 시작 스크립트 설정 완료"

# 9. 설치 완료 메시지
echo ""
echo "=== 설치 완료 ==="
echo "✓ 기본 시스템 설치 완료"
echo "✓ 센서 라이브러리 설치 완료"
echo "✓ 비디오 라이브러리 설치 완료"
echo "✓ 시작 스크립트 설정 완료"

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "추가 SD카드 설정 후 다음 단계:"
    echo "1. 시스템 재부팅"
    echo "2. SD카드 인식 확인: lsblk | grep mmcblk"
    echo "3. SD카드 포맷: sudo mkfs.ext4 /dev/mmcblk2p1 -L LOGSD"
    echo "4. 마운트 설정: sudo mkdir -p /mnt/log_sd"
    echo "5. fstab 설정: echo '/dev/mmcblk2p1 /mnt/log_sd ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab"
    echo "6. 마운트: sudo mount -a"
fi

echo ""
read -p "지금 재부팅하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "시스템을 재부팅합니다..."
    sudo systemctl reboot
else
    echo "나중에 수동으로 재부팅하세요."
fi