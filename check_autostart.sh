#!/bin/bash

# CANSAT HEPHAESTUS 2025 FSW2 - Auto-Start Verification Script
# 이 스크립트는 auto-start 설정이 올바르게 되어 있는지 확인합니다.

echo "🔍 CANSAT HEPHAESTUS 2025 FSW2 Auto-Start Verification"
echo "====================================================="

# 1. 서비스 파일 존재 확인
echo "1️⃣ 서비스 파일 확인..."
if [ -f "/etc/systemd/system/cansat-hephaestus.service" ]; then
    echo "   ✅ 서비스 파일 존재: /etc/systemd/system/cansat-hephaestus.service"
else
    echo "   ❌ 서비스 파일 없음: /etc/systemd/system/cansat-hephaestus.service"
    echo "   💡 해결방법: sudo cp cansat-hephaestus.service /etc/systemd/system/"
fi

# 2. 서비스 활성화 상태 확인
echo ""
echo "2️⃣ 서비스 활성화 상태 확인..."
if systemctl is-enabled cansat-hephaestus.service >/dev/null 2>&1; then
    echo "   ✅ 서비스 활성화됨"
else
    echo "   ❌ 서비스 비활성화됨"
    echo "   💡 해결방법: sudo systemctl enable cansat-hephaestus.service"
fi

# 3. 서비스 실행 상태 확인
echo ""
echo "3️⃣ 서비스 실행 상태 확인..."
if systemctl is-active cansat-hephaestus.service >/dev/null 2>&1; then
    echo "   ✅ 서비스 실행 중"
else
    echo "   ❌ 서비스 중지됨"
    echo "   💡 해결방법: sudo systemctl start cansat-hephaestus.service"
fi

# 4. main.py 파일 존재 확인
echo ""
echo "4️⃣ main.py 파일 확인..."
if [ -f "/home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py" ]; then
    echo "   ✅ main.py 파일 존재"
else
    echo "   ❌ main.py 파일 없음"
    echo "   💡 경로 확인: /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py"
fi

# 5. Python 가상환경 확인
echo ""
echo "5️⃣ Python 가상환경 확인..."
if [ -f "/home/pi/env/bin/python3" ]; then
    echo "   ✅ Python 가상환경 존재"
else
    echo "   ❌ Python 가상환경 없음"
    echo "   💡 경로 확인: /home/pi/env/bin/python3"
fi

# 6. 최근 로그 확인
echo ""
echo "6️⃣ 최근 서비스 로그 확인..."
echo "   📋 최근 10줄 로그:"
sudo journalctl -u cansat-hephaestus.service -n 10 --no-pager

# 7. 서비스 상세 상태
echo ""
echo "7️⃣ 서비스 상세 상태:"
sudo systemctl status cansat-hephaestus.service --no-pager

echo ""
echo "🎯 설정 완료 확인 사항:"
echo "   - 서비스 파일이 /etc/systemd/system/에 존재"
echo "   - 서비스가 enabled 상태"
echo "   - main.py 파일이 올바른 경로에 존재"
echo "   - Python 가상환경이 올바른 경로에 존재"
echo ""
echo "💡 문제가 있다면 AUTO_START_SETUP.md 파일을 참조하세요." 