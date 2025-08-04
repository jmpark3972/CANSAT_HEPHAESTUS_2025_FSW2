#!/bin/bash

# Camera App Installation Script
# HEPHAESTUS CANSAT Team

echo "=== Camera App Installation Script ==="
echo "Installing dependencies for Raspberry Pi Camera Module v3 Wide..."

# Update package list
echo "Updating package list..."
sudo apt update

# Install required packages
echo "Installing ffmpeg and v4l2-utils..."
sudo apt install -y ffmpeg v4l2-utils

# Create necessary directories
echo "Creating directories..."
sudo mkdir -p /home/pi/cansat_videos
sudo mkdir -p /home/pi/cansat_logs
sudo mkdir -p /tmp/camera_temp

# Set permissions
echo "Setting permissions..."
sudo chown -R pi:pi /home/pi/cansat_videos
sudo chown -R pi:pi /home/pi/cansat_logs
sudo chmod 755 /home/pi/cansat_videos
sudo chmod 755 /home/pi/cansat_logs
sudo chmod 777 /tmp/camera_temp

# Enable camera interface (if not already enabled)
echo "Enabling camera interface..."
if ! grep -q "camera_auto_detect=1" /boot/config.txt; then
    echo "camera_auto_detect=1" | sudo tee -a /boot/config.txt
    echo "Camera interface enabled. Reboot required."
fi

# Test camera hardware
echo "Testing camera hardware..."
if vcgencmd get_camera | grep -q "detected=1"; then
    echo "✓ Camera hardware detected"
else
    echo "⚠ Camera hardware not detected. Please check CSI connection."
fi

# Test camera driver
echo "Testing camera driver..."
if [ -e /dev/video0 ]; then
    echo "✓ Camera driver available (/dev/video0)"
else
    echo "⚠ Camera driver not found. Please enable camera in raspi-config."
fi

# Test ffmpeg
echo "Testing ffmpeg installation..."
if command -v ffmpeg &> /dev/null; then
    echo "✓ FFmpeg installed successfully"
    ffmpeg -version | head -n 1
else
    echo "✗ FFmpeg installation failed"
    exit 1
fi

# Test v4l2-utils
echo "Testing v4l2-utils installation..."
if command -v v4l2-ctl &> /dev/null; then
    echo "✓ v4l2-utils installed successfully"
else
    echo "✗ v4l2-utils installation failed"
    exit 1
fi

# Create log rotation configuration
echo "Setting up log rotation..."
sudo tee /etc/logrotate.d/camera-app > /dev/null << EOF
/home/pi/cansat_logs/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 pi pi
    postrotate
        echo "Camera app logs rotated" >> /home/pi/cansat_logs/rotation.log
    endscript
}
EOF

# Test log directory permissions
echo "Testing log directory permissions..."
if [ -w /home/pi/cansat_logs ]; then
    echo "✓ Log directory is writable"
    echo "$(date): Installation completed successfully" >> /home/pi/cansat_logs/install.log
else
    echo "✗ Log directory is not writable"
    exit 1
fi

echo ""
echo "=== Installation Summary ==="
echo "✓ FFmpeg: $(ffmpeg -version | head -n 1 | cut -d' ' -f3)"
echo "✓ v4l2-utils: $(v4l2-ctl --version | head -n 1)"
echo "✓ Video directory: /home/pi/cansat_videos"
echo "✓ Log directory: /home/pi/cansat_logs"
echo "✓ Temp directory: /tmp/camera_temp"
echo "✓ Log rotation: Configured (7 days retention)"

echo ""
echo "=== Next Steps ==="
echo "1. If camera hardware was not detected, check CSI connection"
echo "2. If camera driver was not found, run: sudo raspi-config"
echo "3. Reboot if camera interface was enabled"
echo "4. Test camera functionality: python3 test/test_camera.py"

echo ""
echo "Installation completed successfully!" 