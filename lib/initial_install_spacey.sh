#!/bin/bash
# CANSAT HEPHAESTUS 2025 FSW2 - SpaceY 사용자용 초기 설치 스크립트
# HEPHAESTUS CANSAT Team

set -e  # 오류 시 스크립트 중단

echo "🚀 CANSAT HEPHAESTUS 2025 FSW2 - SpaceY 사용자용 설치 스크립트"
echo "================================================================"
echo ""

# 1. 시스템 업데이트
echo "📦 1. 시스템 업데이트 및 업그레이드..."
sudo apt-get update
yes | sudo apt-get -y upgrade
sudo apt-get install python3-pip

# 2. Python 환경 설정
echo ""
echo "🐍 2. Python 환경 설정..."
sudo apt install --upgrade python3-setuptools
sudo apt install python3-venv

# 가상환경 생성
cd ~
if [ ! -d "env" ]; then
    echo "가상환경 생성 중..."
    python3 -m venv env --system-site-packages
else
    echo "기존 가상환경 발견"
fi

source ~/env/bin/activate

# 3. GPIO 및 하드웨어 라이브러리 설치
echo ""
echo "🔌 3. GPIO 및 하드웨어 라이브러리 설치..."
pip3 install pigpio
sudo systemctl enable pigpiod
sudo systemctl start pigpiod

# Adafruit Blinka 설치
pip3 install --upgrade adafruit-python-shell
wget https://raw.githubusercontent.com/adafruit/Raspberry-Pi-Installer-Scripts/master/raspi-blinka.py
yes n | sudo -E env PATH=$PATH python3 raspi-blinka.py

# 4. 센서 라이브러리 설치
echo ""
echo "📡 4. 센서 라이브러리 설치..."
pip3 install adafruit-circuitpython-bmp3xx
pip3 install adafruit-circuitpython-gps
pip3 install adafruit-circuitpython-bno055
pip3 install adafruit-circuitpython-ads1x15
pip3 install adafruit-circuitpython-motor
pip3 install adafruit-circuitpython-mlx90614

# 6. 기본 모듈 설치
echo ""
echo "📚 6. 기본 모듈 설치..."
pip3 install numpy==1.26.4
pip3 install psutil
pip3 install pyserial

# 7. I2C 도구 설치
echo ""
echo "🔧 7. I2C 도구 설치..."
sudo apt install -y i2c-tools

# 8. 권한 설정 (SpaceY 사용자용)
echo ""
echo "🔐 8. 권한 설정 (SpaceY 사용자용)..."
sudo usermod -a -G gpio SpaceY
sudo usermod -a -G video SpaceY
sudo usermod -a -G dialout SpaceY
sudo usermod -a -G i2c SpaceY

# 9. 추가 SD카드 설정 (선택사항)
echo ""
echo "💾 9. 추가 SD카드 설정..."
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
    
    # SPI 설정 추가
    if ! grep -q "dtparam=spi=on" /boot/firmware/config.txt; then
        echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
    fi
    
    if ! grep -q "disable_spidev=1" /boot/firmware/config.txt; then
        echo "disable_spidev=1" | sudo tee -a /boot/firmware/config.txt
    fi
    
    if ! grep -q "dtoverlay=spi_sd1" /boot/firmware/config.txt; then
        echo "dtoverlay=spi_sd1" | sudo tee -a /boot/firmware/config.txt
    fi
    
    echo "✅ 추가 SD카드 설정 완료"
    echo "재부팅 후 /mnt/log_sd 디렉토리를 생성하세요"
else
    echo "추가 SD카드 설정을 건너뜁니다"
fi

# 10. 프로젝트 디렉토리 설정
echo ""
echo "📁 10. 프로젝트 디렉토리 설정..."
cd ~/Desktop
if [ ! -d "hepa" ]; then
    mkdir hepa
    echo "hepa 디렉토리 생성됨"
fi

# 11. 로그 디렉토리 생성
echo ""
echo "📝 11. 로그 디렉토리 생성..."
cd ~/Desktop/hepa
mkdir -p logs
mkdir -p eventlogs
mkdir -p logs/cansat_videos
mkdir -p logs/cansat_camera_temp
mkdir -p logs/cansat_camera_logs
mkdir -p logs/thermal_videos

# 12. 설치 완료
echo ""
echo "🎉 설치 완료!"
echo "================================================================"
echo "📋 다음 단계:"
echo "1. 재부팅: sudo reboot"
echo "2. 가상환경 활성화: source ~/env/bin/activate"
echo "3. 프로젝트 디렉토리로 이동: cd ~/Desktop/hepa"
echo "4. CANSAT FSW 실행: python3 main.py"
echo ""
echo "🔧 추가 설정:"
echo "- 카메라 활성화: sudo raspi-config"
echo "- I2C 활성화: sudo raspi-config"
echo "- SPI 활성화: sudo raspi-config"
echo ""
echo "📞 문제가 발생하면:"
echo "python3 lib/diagnostic_script.py"
echo ""

# 13. 재부팅 안내
read -p "지금 재부팅하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🔄 재부팅 중..."
    sudo reboot
else
    echo "⚠️ 수동으로 재부팅해주세요"
fi 