import threading
import time
import serial
import os
import glob

# 시리얼 포트 자동 감지
def find_serial_ports():
    """사용 가능한 시리얼 포트 목록 반환"""
    ports = []
    
    # Linux에서 USB 시리얼 포트 찾기
    if os.name == 'posix':
        # USB 시리얼 포트 패턴
        usb_patterns = [
            '/dev/ttyUSB*',
            '/dev/ttyACM*',
            '/dev/serial/by-id/*',
            '/dev/serial/by-path/*'
        ]
        
        for pattern in usb_patterns:
            try:
                found_ports = glob.glob(pattern)
                ports.extend(found_ports)
            except Exception:
                continue
    
    # 중복 제거 및 정렬
    ports = list(set(ports))
    ports.sort()
    
    return ports

def detect_xbee_port():
    """XBee가 연결된 시리얼 포트 감지"""
    available_ports = find_serial_ports()
    
    if not available_ports:
        print("❌ 사용 가능한 시리얼 포트가 없습니다.")
        print("XBee USB 연결을 확인하세요.")
        return None
    
    print(f"🔍 발견된 시리얼 포트: {available_ports}")
    
    # XBee 연결 테스트
    for port in available_ports:
        try:
            print(f"🔌 {port} 연결 테스트 중...")
            test_ser = serial.Serial(port, 9600, timeout=1)
            test_ser.close()
            print(f"✅ XBee 연결 확인: {port}")
            return port
        except Exception as e:
            print(f"❌ {port} 연결 실패: {e}")
            continue
    
    print("❌ XBee 연결을 찾을 수 없습니다.")
    print("USB 케이블 연결을 확인하세요.")
    return None

# 기본 설정
SERIAL_PORT = None  # 자동 감지로 설정
SERIAL_BAUD = 9600
SERIAL_TIMEOUT = 1

def init_serial():
    """시리얼 포트 초기화 - XBee 자동 감지"""
    global SERIAL_PORT
    
    # XBee 포트 자동 감지
    if SERIAL_PORT is None:
        SERIAL_PORT = detect_xbee_port()
    
    if SERIAL_PORT is None:
        print("⚠️ XBee가 연결되지 않았습니다. 시뮬레이션 모드로 실행됩니다.")
        return None
    
    try:
        # 시리얼 포트 열기
        ser = serial.Serial(SERIAL_PORT, SERIAL_BAUD, timeout=SERIAL_TIMEOUT)
        print(f"✅ XBee 연결 성공: {SERIAL_PORT}")
        return ser
    except Exception as e:
        print(f"❌ XBee 연결 실패: {e}")
        print("USB 케이블과 포트를 확인하세요.")
        return None

def send_serial_data(ser, string_to_write:str):
    """시리얼 데이터 전송"""
    if ser is None:
        print("⚠️ XBee가 연결되지 않아 데이터 전송을 건너뜁니다.")
        return False
    
    try:
        ser.write(string_to_write.encode())
        return True
    except Exception as e:
        print(f"❌ 시리얼 데이터 전송 오류: {e}")
        return False

def receive_serial_data(ser) -> str:
    """시리얼 데이터 수신"""
    if ser is None:
        return ""
    
    try:
        read_data = ser.readline().decode().strip()
        return read_data
    except serial.SerialException as e:
        print(f"❌ 시리얼 통신 오류: {e}")
        return ""
    except UnicodeDecodeError as e:
        print(f"❌ 데이터 디코딩 오류: {e}")
        return ""
    except Exception as e:
        print(f"❌ 시리얼 읽기 예상치 못한 오류: {e}")
        return ""

def terminate_serial(ser):
    """시리얼 포트 종료"""
    if ser is None:
        print("⚠️ XBee가 연결되지 않아 종료를 건너뜁니다.")
        return
    
    try:
        ser.close()
        print("✅ XBee 연결 종료 완료")
    except Exception as e:
        print(f"❌ XBee 연결 종료 오류: {e}")

DEBUG_RUNSTATUS = True

def debug_send_tlm_thread(ser):
    """디버그 텔레메트리 전송 스레드"""
    global DEBUG_RUNSTATUS
    while DEBUG_RUNSTATUS:
        if ser is not None:
            send_serial_data(ser, "Hello World!")
        else:
            print("⚠️ XBee 미연결 - 텔레메트리 전송 건너뜀")
        time.sleep(1)
    return

if __name__ == "__main__":
    print("🔧 XBee 디버그 모드 시작")
    print("=" * 50)
    
    serial_instance = init_serial()
    
    if serial_instance is None:
        print("⚠️ XBee가 연결되지 않아 시뮬레이션 모드로 실행됩니다.")
        print("USB 케이블을 연결하고 다시 실행하세요.")
    else:
        print("✅ XBee 연결 확인 - 정상 모드로 실행됩니다.")

    try:
        threading.Thread(target=debug_send_tlm_thread, args=(serial_instance,), daemon=True).start()

        while DEBUG_RUNSTATUS:
            if serial_instance is not None:
                rcv_data = receive_serial_data(serial_instance)
                if rcv_data == "":
                    print("⏰ 타임아웃")
                else:
                    print(f"📨 수신: {rcv_data}")
            else:
                print("⚠️ XBee 미연결 - 수신 대기 건너뜀")
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 키보드 인터럽트 감지!")
        
    finally:
        DEBUG_RUNSTATUS = False
        terminate_serial(serial_instance)
        print("�� XBee 디버그 모드 종료")
