#!/bin/bash
# Secondary SD Card Setup After Reboot
# 재부팅 후 추가 SD카드 설정 완료

echo "=== 재부팅 후 SD카드 설정 완료 ==="
echo ""

# 1. SD카드 상태 확인
echo "1. SD카드 상태 확인..."
echo "현재 인식된 블록 디바이스:"
lsblk | grep mmcblk
echo ""

# 2. 추가 SD카드 확인
echo "2. 추가 SD카드 확인..."
if lsblk | grep -q "mmcblk2"; then
    echo "✓ 추가 SD카드가 인식되었습니다: mmcblk2"
    SD_DEVICE="mmcblk2"
elif lsblk | grep -q "mmcblk1"; then
    echo "✓ 추가 SD카드가 인식되었습니다: mmcblk1"
    SD_DEVICE="mmcblk1"
else
    echo "✗ 추가 SD카드가 인식되지 않았습니다."
    echo "SPI 연결을 확인하고 다시 시도하세요."
    exit 1
fi

# 3. 파티션 확인
echo ""
echo "3. 파티션 확인..."
if lsblk | grep -q "${SD_DEVICE}p1"; then
    echo "✓ 파티션이 존재합니다: ${SD_DEVICE}p1"
    PARTITION="${SD_DEVICE}p1"
else
    echo "✗ 파티션이 없습니다. 파티션을 생성해야 합니다."
    echo "다음 명령어로 파티션을 생성하세요:"
    echo "  sudo fdisk /dev/${SD_DEVICE}"
    echo "  (n, p, 1, Enter, Enter, w)"
    exit 1
fi

# 4. 기존 마운트 해제
echo ""
echo "4. 기존 마운트 해제..."
sudo umount /dev/${PARTITION} 2>/dev/null
echo "마운트 해제 완료"

# 5. 파일시스템 포맷
echo ""
echo "5. 파일시스템 포맷..."
read -p "SD카드를 ext4로 포맷하시겠습니까? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "포맷 중... (시간이 걸릴 수 있습니다)"
    sudo mkfs.ext4 /dev/${PARTITION} -L LOGSD
    echo "포맷 완료"
else
    echo "포맷을 건너뜁니다."
fi

# 6. 마운트 디렉토리 생성
echo ""
echo "6. 마운트 디렉토리 생성..."
sudo mkdir -p /mnt/log_sd
echo "마운트 디렉토리 생성 완료"

# 7. fstab에 마운트 설정 추가
echo ""
echo "7. fstab에 마운트 설정 추가..."
# 기존 설정이 있는지 확인
if ! grep -q "/mnt/log_sd" /etc/fstab; then
    echo "/dev/${PARTITION} /mnt/log_sd ext4 defaults,noatime 0 2" | sudo tee -a /etc/fstab
    echo "fstab 설정 추가 완료"
else
    echo "fstab에 이미 설정이 있습니다."
fi

# 8. 마운트
echo ""
echo "8. 마운트..."
sudo mount -a
if [ $? -eq 0 ]; then
    echo "✓ 마운트 성공"
else
    echo "✗ 마운트 실패"
    exit 1
fi

# 9. 권한 설정
echo ""
echo "9. 권한 설정..."
sudo chown -R pi:pi /mnt/log_sd
sudo chmod 755 /mnt/log_sd
echo "권한 설정 완료"

# 10. 테스트
echo ""
echo "10. 쓰기 테스트..."
TEST_FILE="/mnt/log_sd/test_write.txt"
if echo "test" | sudo tee "$TEST_FILE" > /dev/null; then
    echo "✓ 쓰기 테스트 성공"
    sudo rm "$TEST_FILE"
else
    echo "✗ 쓰기 테스트 실패"
    exit 1
fi

# 11. 로그 디렉토리 생성
echo ""
echo "11. 로그 디렉토리 생성..."
mkdir -p /mnt/log_sd/logs
mkdir -p /mnt/log_sd/sensorlogs
echo "로그 디렉토리 생성 완료"

# 12. 최종 확인
echo ""
echo "12. 최종 확인..."
echo "마운트 상태:"
df -h | grep log_sd
echo ""
echo "디렉토리 내용:"
ls -la /mnt/log_sd/
echo ""

echo "=== 설정 완료 ==="
echo "이제 CANSAT 시스템이 추가 SD카드에 로그를 이중 저장할 수 있습니다."
echo "메인 로그: /home/pi/logs"
echo "보조 로그: /mnt/log_sd/logs"
echo ""
echo "시스템을 시작하려면 다음 명령어를 실행하세요:"
echo "  python3 main.py" 