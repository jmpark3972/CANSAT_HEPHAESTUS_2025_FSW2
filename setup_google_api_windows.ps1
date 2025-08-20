# Google Maps API 키 설정 스크립트 (Windows PowerShell)
Write-Host "🔑 Google Maps API 키 설정 스크립트" -ForegroundColor Green
Write-Host "==================================" -ForegroundColor Green

# 현재 API 키 확인
$CURRENT_KEY = $env:GOOGLE_MAPS_API_KEY
if ($CURRENT_KEY -eq "your_api_key_here" -or -not $CURRENT_KEY) {
    Write-Host "❌ API 키가 설정되지 않았거나 더미 키입니다." -ForegroundColor Red
    Write-Host ""
    Write-Host "📋 Google Cloud Console에서 API 키를 생성하세요:" -ForegroundColor Yellow
    Write-Host "1. https://console.cloud.google.com/ 접속" -ForegroundColor White
    Write-Host "2. 새 프로젝트 생성: 'CANSAT-Hybrid-GPS'" -ForegroundColor White
    Write-Host "3. Geolocation API 활성화" -ForegroundColor White
    Write-Host "4. API 키 생성 (APIs & Services > Credentials)" -ForegroundColor White
    Write-Host ""
    
    $API_KEY = Read-Host "🔑 생성된 API 키를 입력하세요"
    
    if ($API_KEY) {
        # 환경변수 설정
        $env:GOOGLE_MAPS_API_KEY = $API_KEY
        Write-Host "✅ API 키가 설정되었습니다." -ForegroundColor Green
        
        # 영구 설정을 위한 시스템 환경변수 설정
        Write-Host ""
        $SAVE_PERMANENT = Read-Host "💾 시스템 환경변수에 영구 저장하시겠습니까? (y/n)"
        
        if ($SAVE_PERMANENT -eq "y" -or $SAVE_PERMANENT -eq "Y") {
            try {
                [Environment]::SetEnvironmentVariable("GOOGLE_MAPS_API_KEY", $API_KEY, "User")
                Write-Host "✅ 시스템 환경변수에 API 키가 저장되었습니다." -ForegroundColor Green
                Write-Host "   다음 터미널 세션부터 자동으로 로드됩니다." -ForegroundColor White
            }
            catch {
                Write-Host "❌ 시스템 환경변수 설정 실패: $_" -ForegroundColor Red
            }
        }
        
        # 테스트 실행
        Write-Host ""
        Write-Host "🧪 API 키 테스트를 실행합니다..." -ForegroundColor Yellow
        python google_api_setup.py
        
    }
    else {
        Write-Host "❌ API 키가 입력되지 않았습니다." -ForegroundColor Red
    }
}
else {
    Write-Host "✅ API 키가 이미 설정되어 있습니다: $($CURRENT_KEY.Substring(0,10))..." -ForegroundColor Green
    Write-Host ""
    Write-Host "🧪 API 키 테스트를 실행합니다..." -ForegroundColor Yellow
    python google_api_setup.py
}
