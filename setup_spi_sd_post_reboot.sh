#!/bin/bash
# CANSAT HEPHAESTUS 2025 FSW2 - SPI SD 카드 재부팅 후 설정
# 이중 로깅을 위한 서브 SD 카드 마운트 설정

set -e  # 오류 시 스크립트 중단

echo "🚀 CANSAT HEPHAESTUS 2025 FSW2 - SPI SD 카드 재부팅 후 설정"
echo "=================================================="

# 1. SPI SD 카드 확인
echo "🔍 SPI SD 카드 확인 중..."
lsblk | grep mmcblk

echo ""
echo "위 출력에서 mmcblk2가 보이는지 확인하세요."
echo "mmcblk2가 보이지 않으면 SPI 설정에 문제가 있을 수 있습니다."
echo ""

# 2. 기존 마운트 해제
echo "🔓 기존 마운트 해제 중..."
sudo umount /dev/mmcblk2* 2>/dev/null || true

# 3. 파티션 확인
echo "📋 파티션 확인 중..."
sudo fdisk -l /dev/mmcblk2 || {
    echo "❌ /dev/mmcblk2를 찾을 수 없습니다."
    echo "SPI 설정을 다시 확인해주세요."
    exit 1
}

# 4. 포맷 확인
echo "💾 포맷 확인 중..."
if sudo blkid /dev/mmcblk2p1 | grep -q "ext4"; then
    echo "✅ 이미 ext4로 포맷되어 있습니다."
else
    echo "🔄 ext4로 포맷 중..."
    echo "⚠️ 경고: 이 작업은 카드의 모든 데이터를 삭제합니다!"
    echo "계속하시겠습니까? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        sudo mkfs.ext4 /dev/mmcblk2p1 -L LOGSD
        echo "✅ 포맷 완료"
    else
        echo "❌ 포맷이 취소되었습니다."
        exit 1
    fi
fi

# 5. 마운트 포인트 생성
echo "📁 마운트 포인트 생성 중..."
sudo mkdir -p /mnt/log_sd

# 6. fstab 설정
echo "⚙️ fstab 설정 중..."
if ! grep -q "/dev/mmcblk2p1 /mnt/log_sd" /etc/fstab; then
    echo '/dev/mmcblk2p1 /mnt/log_sd ext4 defaults,noatime 0 2' | sudo tee -a /etc/fstab
    echo "✅ fstab에 마운트 설정 추가됨"
else
    echo "✅ fstab에 이미 마운트 설정이 있습니다."
fi

# 7. 마운트
echo "🔗 마운트 중..."
sudo mount -a

# 8. 마운트 확인
echo "✅ 마운트 확인 중..."
if mountpoint -q /mnt/log_sd; then
    echo "✅ SPI SD 카드가 성공적으로 마운트되었습니다!"
    echo "마운트 위치: /mnt/log_sd"
    
    # 용량 확인
    df -h /mnt/log_sd
    
    # 테스트 파일 생성
    echo "🧪 테스트 파일 생성 중..."
    echo "CANSAT HEPHAESTUS 2025 FSW2 - SPI SD 카드 테스트" > /mnt/log_sd/test.txt
    if [ -f /mnt/log_sd/test.txt ]; then
        echo "✅ 쓰기 테스트 성공"
        rm /mnt/log_sd/test.txt
        echo "✅ 읽기/삭제 테스트 성공"
    else
        echo "❌ 쓰기 테스트 실패"
    fi
    
else
    echo "❌ 마운트 실패"
    exit 1
fi

# 9. 이중 로깅 디렉토리 생성
echo "📂 이중 로깅 디렉토리 생성 중..."
sudo mkdir -p /mnt/log_sd/cansat_logs
sudo mkdir -p /mnt/log_sd/cansat_videos
sudo mkdir -p /mnt/log_sd/cansat_camera_temp
sudo mkdir -p /mnt/log_sd/cansat_camera_logs
sudo mkdir -p /mnt/log_sd/thermal_videos

# 권한 설정
sudo chown -R $USER:$USER /mnt/log_sd/cansat_*
sudo chmod -R 755 /mnt/log_sd/cansat_*

echo "✅ 이중 로깅 디렉토리 생성 완료"

# 10. 설정 완료
echo ""
echo "🎉 SPI SD 카드 설정 완료!"
echo "=================================================="
echo "📋 설정 요약:"
echo "- 마운트 위치: /mnt/log_sd"
echo "- 파일 시스템: ext4"
echo "- 자동 마운트: 활성화 (재부팅 시 자동 마운트)"
echo "- 이중 로깅: 활성화"
echo ""
echo "📁 생성된 디렉토리:"
echo "- /mnt/log_sd/cansat_logs"
echo "- /mnt/log_sd/cansat_videos"
echo "- /mnt/log_sd/cansat_camera_temp"
echo "- /mnt/log_sd/cansat_camera_logs"
echo "- /mnt/log_sd/thermal_videos"
echo ""
echo "🚀 이제 CANSAT FSW를 실행하면 이중 로깅이 활성화됩니다!" 