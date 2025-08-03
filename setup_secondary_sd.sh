#!/bin/bash
# Secondary SD Card Setup Script for CANSAT
# 추가 SD카드 설정 스크립트

echo "=== CANSAT 이중 로깅 시스템 설정 ==="
echo "추가 SD카드를 SPI를 통해 연결하여 로그를 이중 저장합니다."
echo ""

# 1. 시스템 업데이트 및 필요한 패키지 설치
echo "1. 시스템 업데이트 및 패키지 설치..."
sudo apt update
sudo apt install -y device-tree-compiler git

# 2. Device Tree Overlay 생성
echo ""
echo "2. Device Tree Overlay 생성..."
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

# 3. Device Tree Overlay 컴파일
echo ""
echo "3. Device Tree Overlay 컴파일..."
dtc -@ -I dts -O dtb -o spi_sd1.dtbo spi_sd1.dts

# 4. Overlay 파일 복사
echo ""
echo "4. Overlay 파일 복사..."
sudo cp spi_sd1.dtbo /boot/firmware/overlays/

# 5. config.txt 설정
echo ""
echo "5. config.txt 설정..."
# 기존 설정 백업
sudo cp /boot/firmware/config.txt /boot/firmware/config.txt.backup.$(date +%Y%m%d_%H%M%S)

# 새로운 설정 추가
cat >> /boot/firmware/config.txt <<'EOF'

# Secondary SD Card Configuration
[all]
dtparam=spi=on
disable_spidev=1
dtoverlay=spi_sd1
EOF

echo ""
echo "6. 시스템 재부팅이 필요합니다."
echo "재부팅 후 다음 명령어로 SD카드 상태를 확인하세요:"
echo "  lsblk | grep mmcblk"
echo ""
echo "SD카드가 인식되면 다음 명령어로 포맷하세요:"
echo "  sudo umount /dev/mmcblk2* 2>/dev/null"
echo "  sudo mkfs.ext4 /dev/mmcblk2p1 -L LOGSD"
echo ""
echo "마운트 설정:"
echo "  sudo mkdir -p /mnt/log_sd"
echo "  echo '/dev/mmcblk2p1 /mnt/log_sd ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab"
echo "  sudo mount -a"
echo ""

read -p "지금 재부팅하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "시스템을 재부팅합니다..."
    sudo reboot
else
    echo "나중에 수동으로 재부팅하세요."
fi 