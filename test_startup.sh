#!/bin/bash
# Test script for startup.sh
# This script tests the startup configuration without running the full application

echo "=== Testing Startup Script Configuration ==="

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python_path="${SCRIPT_DIR}"
venv_path="/home/SpaceY/Desktop/env"

echo "Script directory: ${SCRIPT_DIR}"
echo "Python path: ${python_path}"
echo "Virtual environment: ${venv_path}"

# Test 1: Check if virtual environment exists
echo "Test 1: Checking virtual environment..."
if [ -d "${venv_path}" ]; then
    echo "✓ Virtual environment found at ${venv_path}"
else
    echo "✗ Virtual environment not found at ${venv_path}"
    exit 1
fi

# Test 2: Check if activate script exists
echo "Test 2: Checking activate script..."
if [ -f "${venv_path}/bin/activate" ]; then
    echo "✓ Activate script found"
else
    echo "✗ Activate script not found"
    exit 1
fi

# Test 3: Check if main.py exists
echo "Test 3: Checking main.py..."
if [ -f "${python_path}/main.py" ]; then
    echo "✓ main.py found"
else
    echo "✗ main.py not found"
    exit 1
fi

# Test 4: Test virtual environment activation
echo "Test 4: Testing virtual environment activation..."
source "${venv_path}/bin/activate"
if [ $? -eq 0 ]; then
    echo "✓ Virtual environment activated successfully"
    echo "Python version: $(python3 --version)"
    echo "Python path: $(which python3)"
else
    echo "✗ Failed to activate virtual environment"
    exit 1
fi

# Test 5: Check Python imports
echo "Test 5: Testing Python imports..."
python3 -c "
import sys
print('Python path:', sys.executable)
print('Python version:', sys.version)

# Test basic imports
try:
    import numpy
    print('✓ numpy imported successfully')
except ImportError as e:
    print('✗ numpy import failed:', e)

try:
    import adafruit_bno055
    print('✓ adafruit_bno055 imported successfully')
except ImportError as e:
    print('✗ adafruit_bno055 import failed:', e)

try:
    import serial
    print('✓ pyserial imported successfully')
except ImportError as e:
    print('✗ pyserial import failed:', e)
"

echo "=== Startup Test Completed ==="
echo "If all tests passed, the startup script should work correctly." 