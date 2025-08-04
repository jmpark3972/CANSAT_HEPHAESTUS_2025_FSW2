#!/bin/bash
# Camera App Installation Script
# Author : Hyeon Lee  (HEPHAESTUS)

echo "=== Camera App Installation Script ==="
echo "Installing dependencies for Raspberry Pi Camera Module v3 Wide..."

# 시스템 업데이트
echo "Updating system packages..."
sudo apt update

# 필수 패키지 설치
echo "Installing required packages..."
sudo apt install -y ffmpeg v4l2-utils python3-pip

# 카메라 활성화 확인
echo "Checking camera hardware..."
if vcgencmd get_camera | grep -q "detected=1"; then
    echo "✓ Camera hardware detected"
else
    echo "⚠️  Camera hardware not detected"
    echo "Please check camera connection and enable in raspi-config"
fi

# 카메라 드라이버 확인
echo "Checking camera driver..."
if [ -e /dev/video0 ]; then
    echo "✓ Camera driver available (/dev/video0)"
else
    echo "⚠️  Camera driver not found"
    echo "Please enable camera in raspi-config:"
    echo "sudo raspi-config -> Interface Options -> Camera -> Enable"
fi

# 디렉토리 생성
echo "Creating directories..."
mkdir -p /home/pi/cansat_videos
mkdir -p /tmp/camera_temp

# 권한 설정
echo "Setting permissions..."
sudo chmod 666 /dev/video0 2>/dev/null || echo "Warning: Could not set video0 permissions"
chmod 755 /home/pi/cansat_videos
chmod 755 /tmp/camera_temp

# ffmpeg 테스트
echo "Testing ffmpeg..."
if ffmpeg -version >/dev/null 2>&1; then
    echo "✓ ffmpeg is working"
else
    echo "✗ ffmpeg test failed"
    exit 1
fi

# 카메라 테스트 (선택적)
echo ""
echo "Do you want to test the camera? (y/n): "
read -r test_camera

if [ "$test_camera" = "y" ] || [ "$test_camera" = "Y" ]; then
    echo "Testing camera with ffmpeg..."
    echo "This will record a 5-second test video..."
    
    # 5초 테스트 녹화
    ffmpeg -f v4l2 -video_size 1920x1080 -framerate 30 -i /dev/video0 -t 5 -y /tmp/camera_test.h264 2>/dev/null
    
    if [ -f /tmp/camera_test.h264 ]; then
        echo "✓ Camera test successful - test video created"
        echo "Test video location: /tmp/camera_test.h264"
        echo "To play: ffplay /tmp/camera_test.h264"
    else
        echo "✗ Camera test failed"
        echo "Please check camera connection and permissions"
    fi
fi

echo ""
echo "=== Installation Complete ==="
echo "Camera app is ready to use!"
echo ""
echo "Next steps:"
echo "1. Run the camera test: python3 test_camera.py"
echo "2. Start the main FSW: python3 main.py"
echo ""
echo "Camera settings can be modified in camera/camera.py" 