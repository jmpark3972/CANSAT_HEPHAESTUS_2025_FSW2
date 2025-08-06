#!/bin/bash
# CANSAT HEPHAESTUS 2025 FSW2 - 모듈 업데이트 스크립트
# 모든 모듈을 최신 버전으로 업데이트합니다

set -e  # 오류 시 스크립트 중단

echo "🔄 CANSAT HEPHAESTUS 2025 FSW2 - 모듈 업데이트"
echo "=============================================="

# 1. 메인 저장소 업데이트
echo "📦 1. 메인 저장소 업데이트..."
git pull

# 2. 서브모듈 업데이트
echo ""
echo "📦 2. 서브모듈 업데이트..."
git submodule foreach "git checkout main || :"
git submodule foreach "git pull || :"

# 3. Python 패키지 업데이트
echo ""
echo "🐍 3. Python 패키지 업데이트..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt --upgrade
else
    echo "⚠️ requirements.txt 파일이 없습니다"
fi

# 4. 시스템 패키지 업데이트
echo ""
echo "🔧 4. 시스템 패키지 업데이트..."
sudo apt update
sudo apt upgrade -y

# 5. 업데이트 완료
echo ""
echo "🎉 모듈 업데이트 완료!"
echo "=============================================="
echo "📋 업데이트된 항목:"
echo "- 메인 저장소"
echo "- 서브모듈"
echo "- Python 패키지"
echo "- 시스템 패키지"
echo ""
echo "🚀 CANSAT FSW를 다시 실행하세요:"
echo "python3 main.py" 