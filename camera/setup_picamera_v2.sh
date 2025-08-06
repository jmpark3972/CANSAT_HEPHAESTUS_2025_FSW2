#!/bin/bash
# Pi Camera v2 Quick Setup Script
# Pi Camera v2 전용 빠른 설정 스크립트

echo "=========================================="
echo "Pi Camera v2 Quick Setup"
echo "=========================================="

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 현재 설정 확인
log_info "현재 /boot/config.txt 설정 확인 중..."

if [ -f /boot/config.txt ]; then
    echo "현재 설정:"
    grep -E "(camera|ov5647|i2c)" /boot/config.txt || echo "카메라 관련 설정 없음"
else
    log_error "/boot/config.txt 파일을 찾을 수 없음"
    exit 1
fi

echo ""

# Pi Camera v2 설정 추가
log_info "Pi Camera v2 설정 추가 중..."

# 백업 생성
cp /boot/config.txt /boot/config.txt.backup.$(date +%Y%m%d_%H%M%S)
log_success "설정 파일 백업 생성됨"

# 카메라 자동 감지 설정
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    log_success "카메라 자동 감지 설정 추가"
else
    log_info "카메라 자동 감지 설정이 이미 존재함"
fi

# OV5647 센서 오버레이 설정 (Pi Camera v2)
if ! grep -q "dtoverlay=ov5647" /boot/config.txt; then
    echo "dtoverlay=ov5647" | sudo tee -a /boot/config.txt
    log_success "OV5647 센서 오버레이 설정 추가"
else
    log_info "OV5647 센서 오버레이 설정이 이미 존재함"
fi

# I2C 활성화
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    log_success "I2C 활성화 설정 추가"
else
    log_info "I2C 활성화 설정이 이미 존재함"
fi

echo ""

# 설정 확인
log_info "업데이트된 설정 확인:"
echo "카메라 관련 설정:"
grep -E "(camera|ov5647|i2c)" /boot/config.txt

echo ""

# 하드웨어 확인
log_info "하드웨어 확인 중..."

# vcgencmd 확인
if command -v vcgencmd &> /dev/null; then
    result=$(vcgencmd get_camera 2>/dev/null)
    if [[ $result == *"detected=1"* ]]; then
        log_success "카메라 하드웨어 감지됨: $result"
    else
        log_warning "카메라 하드웨어 감지되지 않음: $result"
    fi
else
    log_warning "vcgencmd 명령어를 찾을 수 없음"
fi

# 비디오 디바이스 확인
if ls /dev/video* 1> /dev/null 2>&1; then
    log_success "비디오 디바이스 발견:"
    ls -la /dev/video*
else
    log_warning "비디오 디바이스 없음"
fi

echo ""

# 패키지 설치 확인
log_info "필요한 패키지 확인 중..."

packages=("raspistill" "raspivid" "libcamera-hello")

for pkg in "${packages[@]}"; do
    if command -v $pkg &> /dev/null; then
        log_success "$pkg 설치됨"
    else
        log_warning "$pkg 설치되지 않음"
    fi
done

echo ""

# 설정 완료 메시지
log_success "Pi Camera v2 설정 완료!"
echo ""
echo "다음 단계:"
echo "1. 시스템을 재부팅하세요: sudo reboot"
echo "2. 재부팅 후 카메라 테스트를 실행하세요:"
echo "   python3 camera/test_picamera_v2.py"
echo "3. 또는 간단한 테스트:"
echo "   raspistill -o test.jpg -t 1000"
echo ""
echo "문제가 발생하면 다음을 확인하세요:"
echo "- Pi Camera v2가 올바르게 연결되었는지"
echo "- CSI 케이블이 제대로 연결되었는지"
echo "- 백업된 설정 파일: /boot/config.txt.backup.*"
echo ""

# 재부팅 권장
read -p "지금 시스템을 재부팅하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "시스템 재부팅 중..."
    sudo reboot
else
    log_info "수동으로 재부팅하세요: sudo reboot"
fi 