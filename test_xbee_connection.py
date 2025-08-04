#!/usr/bin/env python3
"""
XBee 연결 상태 테스트 스크립트
"""

import sys
import os

# 프로젝트 루트 디렉토리를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from comm.uartserial import find_serial_ports, detect_xbee_port, init_serial, send_serial_data, receive_serial_data, terminate_serial
import time

def test_xbee_connection():
    """XBee 연결 상태 테스트"""
    print("=" * 60)
    print("🔧 XBee 연결 상태 테스트")
    print("=" * 60)
    
    # 1. 사용 가능한 시리얼 포트 확인
    print("\n1. 사용 가능한 시리얼 포트 확인...")
    available_ports = find_serial_ports()
    
    if not available_ports:
        print("❌ 사용 가능한 시리얼 포트가 없습니다.")
        print("XBee USB 연결을 확인하세요.")
        return False
    
    print(f"✅ 발견된 시리얼 포트: {available_ports}")
    
    # 2. XBee 포트 감지
    print("\n2. XBee 포트 감지...")
    xbee_port = detect_xbee_port()
    
    if xbee_port is None:
        print("❌ XBee 연결을 찾을 수 없습니다.")
        print("USB 케이블 연결을 확인하세요.")
        return False
    
    print(f"✅ XBee 포트 감지: {xbee_port}")
    
    # 3. 시리얼 연결 초기화
    print("\n3. 시리얼 연결 초기화...")
    serial_instance = init_serial()
    
    if serial_instance is None:
        print("❌ 시리얼 연결 초기화 실패")
        return False
    
    print("✅ 시리얼 연결 초기화 성공")
    
    # 4. 데이터 전송 테스트
    print("\n4. 데이터 전송 테스트...")
    test_messages = [
        "Hello XBee!",
        "CANSAT Test Message",
        "Telemetry Data Test"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"📤 전송 {i}/{len(test_messages)}: {message}")
        success = send_serial_data(serial_instance, message + "\n")
        
        if success:
            print(f"✅ 전송 성공: {message}")
        else:
            print(f"❌ 전송 실패: {message}")
        
        time.sleep(0.5)  # 500ms 대기
    
    # 5. 데이터 수신 테스트
    print("\n5. 데이터 수신 테스트 (10초간)...")
    print("XBee에서 데이터를 전송해보세요...")
    
    start_time = time.time()
    timeout = 10  # 10초 타임아웃
    
    while time.time() - start_time < timeout:
        received_data = receive_serial_data(serial_instance)
        
        if received_data:
            print(f"📨 수신: {received_data}")
        else:
            remaining = int(timeout - (time.time() - start_time))
            print(f"⏰ 수신 대기 중... ({remaining}초 남음)")
        
        time.sleep(1)
    
    # 6. 연결 종료
    print("\n6. 연결 종료...")
    terminate_serial(serial_instance)
    
    print("\n" + "=" * 60)
    print("✅ XBee 연결 테스트 완료")
    print("=" * 60)
    
    return True

def show_connection_guide():
    """XBee 연결 가이드 표시"""
    print("\n" + "=" * 60)
    print("📋 XBee 연결 가이드")
    print("=" * 60)
    print("1. XBee 모듈을 USB 케이블로 연결")
    print("2. 연결 후 다음 명령으로 테스트:")
    print("   python3 test_xbee_connection.py")
    print("3. 연결이 확인되면 메인 시스템 실행:")
    print("   python3 main.py")
    print("=" * 60)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--guide":
        show_connection_guide()
    else:
        success = test_xbee_connection()
        if not success:
            show_connection_guide()
        sys.exit(0 if success else 1) 