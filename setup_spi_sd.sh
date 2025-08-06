#!/bin/bash
# CANSAT HEPHAESTUS 2025 FSW2 - SPI SD 카드 설정 스크립트
# 이중 로깅을 위한 서브 SD 카드 설정

set -e  # 오류 시 스크립트 중단

echo "🚀 CANSAT HEPHAESTUS 2025 FSW2 - SPI SD 카드 설정 시작"
echo "=================================================="

# 1. 필요한 패키지 설치
echo "📦 필요한 패키지 설치 중..."
sudo apt update
sudo apt install -y device-tree-compiler git

# 2. SPI SD 카드 오버레이 생성
echo "🔧 SPI SD 카드 오버레이 생성 중..."
cat > ~/spi_sd1.dts <<'EOF'
/dts-v1/;
/plugin/;

fragment@0 {
    target = <&spi0>;
    __overlay__ {
        status = "okay";
        #address-cells = <1>;
        #size-cells   = <0>;

        sd1: mmc@1 {                // CS1 (GPIO 7)
            compatible        = "mmc-spi-slot";
            reg               = <1>;
            spi-max-frequency = <12000000>;   // 필요하면 4000000 으로 낮춰도 됨
            voltage-ranges    = <3300 3300>;
            broken-cd;                     // 카드-감지 핀 없음
        };
    };
};
EOF

# 3. 오버레이 컴파일
echo "🔨 오버레이 컴파일 중..."
dtc -@ -I dts -O dtb -o spi_sd1.dtbo spi_sd1.dts

# 4. 오버레이 설치
echo "📁 오버레이 설치 중..."
sudo cp spi_sd1.dtbo /boot/firmware/overlays/

# 5. config.txt 백업 및 수정
echo "⚙️ config.txt 설정 중..."
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d_%H%M%S)

# config.txt에 SPI 설정 추가
if ! grep -q "dtparam=spi=on" /boot/firmware/config.txt; then
    echo "dtparam=spi=on" | sudo tee -a /boot/firmware/config.txt
fi

if ! grep -q "disable_spidev=1" /boot/firmware/config.txt; then
    echo "disable_spidev=1" | sudo tee -a /boot/firmware/config.txt
fi

if ! grep -q "dtoverlay=spi_sd1" /boot/firmware/config.txt; then
    echo "dtoverlay=spi_sd1" | sudo tee -a /boot/firmware/config.txt
fi

echo "✅ config.txt 설정 완료"

# 6. 재부팅 안내
echo ""
echo "🔄 재부팅이 필요합니다."
echo "재부팅 후 다음 명령어로 설정을 확인하세요:"
echo "  lsblk | grep mmcblk"
echo ""
echo "재부팅하시겠습니까? (y/n)"
read -r response
if [[ "$response" =~ ^[Yy]$ ]]; then
    echo "🔄 재부팅 중..."
    sudo reboot
else
    echo "⚠️ 수동으로 재부팅해주세요."
fi

echo ""
echo "📋 재부팅 후 실행할 명령어:"
echo "1. lsblk | grep mmcblk  # SPI SD 카드 확인"
echo "2. sudo umount /dev/mmcblk2* 2>/dev/null  # 기존 마운트 해제"
echo "3. sudo mkfs.ext4 /dev/mmcblk2p1 -L LOGSD  # 포맷"
echo "4. sudo mkdir -p /mnt/log_sd  # 마운트 포인트 생성"
echo "5. echo '/dev/mmcblk2p1 /mnt/log_sd ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab"
echo "6. sudo mount -a  # 마운트"
echo ""
echo "🎉 SPI SD 카드 설정 완료!" 