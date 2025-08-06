#!/bin/bash
# Pi Camera Installation Script
# CANSAT Pi Camera 설정을 위한 설치 스크립트

echo "=========================================="
echo "Pi Camera Installation Script"
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

# 시스템 업데이트
log_info "시스템 패키지 업데이트 중..."
sudo apt update && sudo apt upgrade -y
if [ $? -eq 0 ]; then
    log_success "시스템 업데이트 완료"
else
    log_error "시스템 업데이트 실패"
    exit 1
fi

# 카메라 관련 패키지 설치
log_info "카메라 관련 패키지 설치 중..."
sudo apt install -y \
    python3-picamera2 \
    python3-picamera2-doc \
    ffmpeg \
    v4l-utils \
    libcamera-tools \
    libcamera-apps

if [ $? -eq 0 ]; then
    log_success "카메라 패키지 설치 완료"
else
    log_error "카메라 패키지 설치 실패"
    exit 1
fi

# Python 패키지 설치
log_info "Python 패키지 설치 중..."
pip3 install --upgrade pip
pip3 install \
    opencv-python \
    opencv-python-headless \
    numpy \
    pillow

if [ $? -eq 0 ]; then
    log_success "Python 패키지 설치 완료"
else
    log_warning "일부 Python 패키지 설치 실패 (계속 진행)"
fi

# 카메라 활성화
log_info "카메라 인터페이스 활성화 중..."
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    log_success "카메라 자동 감지 설정 추가"
else
    log_info "카메라 자동 감지 설정이 이미 존재함"
fi

# Pi Camera v2 전용 설정 (OV5647 센서)
if ! grep -q "dtoverlay=ov5647" /boot/config.txt; then
    echo "dtoverlay=ov5647" | sudo tee -a /boot/config.txt
    log_success "Pi Camera v2 (OV5647) 오버레이 설정 추가"
else
    log_info "Pi Camera v2 오버레이 설정이 이미 존재함"
fi

# I2C 활성화 (센서 통신용)
log_info "I2C 인터페이스 활성화 중..."
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
    log_success "I2C 설정 추가"
else
    log_info "I2C 설정이 이미 존재함"
fi

# SPI 활성화 (필요한 경우)
log_info "SPI 인터페이스 활성화 중..."
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    log_success "SPI 설정 추가"
else
    log_info "SPI 설정이 이미 존재함"
fi

# 카메라 하드웨어 확인
log_info "카메라 하드웨어 확인 중..."
if vcgencmd get_camera | grep -q "detected=1"; then
    log_success "카메라 하드웨어 감지됨"
else
    log_warning "카메라 하드웨어가 감지되지 않음"
    log_info "다음을 확인하세요:"
    echo "  1. Pi Camera가 올바르게 연결되었는지 확인"
    echo "  2. 카메라 케이블이 제대로 연결되었는지 확인"
    echo "  3. 시스템을 재부팅한 후 다시 시도"
fi

# 비디오 디바이스 확인
log_info "비디오 디바이스 확인 중..."
if ls /dev/video* 1> /dev/null 2>&1; then
    log_success "비디오 디바이스 발견:"
    ls -la /dev/video*
else
    log_warning "비디오 디바이스가 발견되지 않음"
fi

# FFmpeg 확인
log_info "FFmpeg 설치 확인 중..."
if command -v ffmpeg &> /dev/null; then
    log_success "FFmpeg 설치됨: $(ffmpeg -version | head -n1)"
else
    log_error "FFmpeg가 설치되지 않음"
fi

# 디렉토리 생성
log_info "로그 디렉토리 생성 중..."
mkdir -p logs/cansat_videos
mkdir -p logs/cansat_camera_temp
mkdir -p logs/cansat_camera_logs

if [ $? -eq 0 ]; then
    log_success "로그 디렉토리 생성 완료"
else
    log_error "로그 디렉토리 생성 실패"
fi

# 권한 설정
log_info "권한 설정 중..."
sudo usermod -a -G video $USER
sudo chmod 755 logs/cansat_videos
sudo chmod 755 logs/cansat_camera_temp
sudo chmod 755 logs/cansat_camera_logs

if [ $? -eq 0 ]; then
    log_success "권한 설정 완료"
else
    log_warning "권한 설정 중 일부 실패"
fi

# 테스트 스크립트 실행 권한 부여
log_info "테스트 스크립트 권한 설정 중..."
chmod +x camera/standalone_camera.py
chmod +x camera/simple_camera_test.py

if [ $? -eq 0 ]; then
    log_success "스크립트 권한 설정 완료"
else
    log_warning "스크립트 권한 설정 실패"
fi

# 설치 완료 메시지
echo ""
echo "=========================================="
echo "설치 완료!"
echo "=========================================="
log_success "Pi Camera 설치가 완료되었습니다."
echo ""
echo "다음 단계:"
echo "1. 시스템을 재부팅하세요: sudo reboot"
echo "2. 재부팅 후 카메라 테스트를 실행하세요:"
echo "   python3 camera/simple_camera_test.py"
echo "3. 또는 독립 실행 카메라를 테스트하세요:"
echo "   python3 camera/standalone_camera.py"
echo ""
echo "문제가 발생하면 다음을 확인하세요:"
echo "- Pi Camera가 올바르게 연결되었는지"
echo "- 카메라 케이블이 제대로 연결되었는지"
echo "- /boot/config.txt 파일의 설정"
echo "- 시스템 로그: dmesg | grep camera"
echo ""

# 시스템 재부팅 권장
read -p "시스템을 지금 재부팅하시겠습니까? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "시스템 재부팅 중..."
    sudo reboot
else
    log_info "수동으로 재부팅하세요: sudo reboot"
fi 