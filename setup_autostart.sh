#!/bin/bash

# CANSAT HEPHAESTUS 2025 FSW2 - Auto-Start Setup Script
# 이 스크립트는 라즈베리파이 부팅 시 자동으로 main.py를 실행하도록 설정합니다.

echo "🚀 CANSAT HEPHAESTUS 2025 FSW2 Auto-Start Setup"
echo "================================================"

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "📁 현재 디렉토리: $SCRIPT_DIR"

# 서비스 파일 경로 확인
SERVICE_FILE="$SCRIPT_DIR/cansat-hephaestus.service"
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ 서비스 파일을 찾을 수 없습니다: $SERVICE_FILE"
    exit 1
fi

echo "✅ 서비스 파일 발견: $SERVICE_FILE"

# 시스템 서비스 디렉토리에 복사
echo "📋 서비스 파일을 시스템에 복사 중..."
sudo cp "$SERVICE_FILE" /etc/systemd/system/

if [ $? -eq 0 ]; then
    echo "✅ 서비스 파일 복사 완료"
else
    echo "❌ 서비스 파일 복사 실패"
    exit 1
fi

# systemd 데몬 리로드
echo "🔄 systemd 데몬 리로드 중..."
sudo systemctl daemon-reload

if [ $? -eq 0 ]; then
    echo "✅ systemd 데몬 리로드 완료"
else
    echo "❌ systemd 데몬 리로드 실패"
    exit 1
fi

# 서비스 활성화
echo "🔧 서비스 활성화 중..."
sudo systemctl enable cansat-hephaestus.service

if [ $? -eq 0 ]; then
    echo "✅ 서비스 활성화 완료"
else
    echo "❌ 서비스 활성화 실패"
    exit 1
fi

# 서비스 상태 확인
echo "📊 서비스 상태 확인 중..."
sudo systemctl status cansat-hephaestus.service --no-pager

echo ""
echo "🎉 Auto-Start 설정이 완료되었습니다!"
echo ""
echo "📋 사용 가능한 명령어:"
echo "   서비스 시작:   sudo systemctl start cansat-hephaestus.service"
echo "   서비스 중지:   sudo systemctl stop cansat-hephaestus.service"
echo "   서비스 재시작: sudo systemctl restart cansat-hephaestus.service"
echo "   로그 확인:     sudo journalctl -u cansat-hephaestus.service -f"
echo "   상태 확인:     sudo systemctl status cansat-hephaestus.service"
echo ""
echo "🔄 다음 부팅부터 main.py가 자동으로 실행됩니다."
echo "💡 지금 바로 테스트하려면: sudo systemctl start cansat-hephaestus.service" 