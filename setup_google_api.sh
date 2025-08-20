#!/bin/bash

echo "🔑 Google Maps API 키 설정 스크립트"
echo "=================================="

# 현재 API 키 확인
CURRENT_KEY=$(echo $GOOGLE_MAPS_API_KEY)
if [ "$CURRENT_KEY" = "your_api_key_here" ] || [ -z "$CURRENT_KEY" ]; then
    echo "❌ API 키가 설정되지 않았거나 더미 키입니다."
    echo ""
    echo "📋 Google Cloud Console에서 API 키를 생성하세요:"
    echo "1. https://console.cloud.google.com/ 접속"
    echo "2. 새 프로젝트 생성: 'CANSAT-Hybrid-GPS'"
    echo "3. Geolocation API 활성화"
    echo "4. API 키 생성 (APIs & Services > Credentials)"
    echo ""
    echo "🔑 생성된 API 키를 입력하세요:"
    read -p "API 키: " API_KEY
    
    if [ -n "$API_KEY" ]; then
        # 환경변수 설정
        export GOOGLE_MAPS_API_KEY="$API_KEY"
        echo "✅ API 키가 설정되었습니다."
        
        # 영구 설정을 위한 .bashrc 업데이트
        echo ""
        echo "💾 영구 설정을 위해 .bashrc에 추가하시겠습니까? (y/n)"
        read -p "선택: " SAVE_PERMANENT
        
        if [ "$SAVE_PERMANENT" = "y" ] || [ "$SAVE_PERMANENT" = "Y" ]; then
            # 기존 설정 제거
            sed -i '/GOOGLE_MAPS_API_KEY/d' ~/.bashrc
            # 새 설정 추가
            echo "export GOOGLE_MAPS_API_KEY=\"$API_KEY\"" >> ~/.bashrc
            echo "✅ .bashrc에 API 키가 저장되었습니다."
            echo "   다음 터미널 세션부터 자동으로 로드됩니다."
        fi
        
        # 테스트 실행
        echo ""
        echo "🧪 API 키 테스트를 실행합니다..."
        python3 google_api_setup.py
        
    else
        echo "❌ API 키가 입력되지 않았습니다."
    fi
else
    echo "✅ API 키가 이미 설정되어 있습니다: ${CURRENT_KEY:0:10}..."
    echo ""
    echo "🧪 API 키 테스트를 실행합니다..."
    python3 google_api_setup.py
fi
