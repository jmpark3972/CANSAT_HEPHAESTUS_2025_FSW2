import time
import math
from datetime import datetime
import os

# Variables for moving window filter
angle_window = [[],[],[]] # (ROLL, PITCH, YAW)
window_size = 5

log_dir = './sensorlogs'
if not os.path.exists(log_dir): 
    os.makedirs(log_dir)

## Create sensor log file
imulogfile = open(os.path.join(log_dir, 'imu.txt'), 'a')

# 통합 오프셋 관리 시스템 사용
try:
    from lib.offsets import get_imu_offsets
    magneto_offset, gyro_offset, accel_offset = get_imu_offsets()
    print(f"IMU 오프셋 로드됨 - 자기계: {magneto_offset}, 자이로: {gyro_offset}, 가속도: {accel_offset}")
except Exception as e:
    print(f"IMU 오프셋 로드 실패, 기본값 사용: {e}")
    magneto_offset = (0,0,0)
    gyro_offset = (0,0,0)
    accel_offset = (0,0,0)

def log_imu(text):

    t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
    string_to_write = f'{t},{text}\n'
    imulogfile.write(string_to_write)
    imulogfile.flush()

def init_imu():
    """IMU 센서 초기화 (직접 I2C 연결)"""
    import board
    import busio
    import adafruit_bno055
    
    # I2C setup
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    
    try:
        # IMU 센서 직접 연결
        sensor = adafruit_bno055.BNO055_I2C(i2c)
        time.sleep(0.1)
        
        # 센서 모드 설정 (NDOF 모드로 설정하여 모든 센서 활성화)
        sensor.mode = adafruit_bno055.NDOF_MODE
        time.sleep(0.5)  # 모드 변경 후 안정화 대기
        
        print("IMU 센서 초기화 완료 (직접 I2C 연결)")
        return i2c, sensor
    except Exception as e:
        print(f"IMU 초기화 실패: {e}")
        raise Exception(f"IMU 초기화 실패: {e}")

def read_sensor_data(sensor):
    """IMU 센서 데이터 읽기"""
    global angle_window
    if not hasattr(read_sensor_data, "none_count"): read_sensor_data.none_count = 0
    if not hasattr(read_sensor_data, "last_valid_data"): 
        read_sensor_data.last_valid_data = {
            'gyro': (0.0, 0.0, 0.0),
            'accel': (0.0, 0.0, 0.0),
            'mag': (0.0, 0.0, 0.0),
            'euler': (0.0, 0.0, 0.0),
            'temp': 0.0,
            'quaternion': (1.0, 0.0, 0.0, 0.0),
            'linear_accel': (0.0, 0.0, 0.0),
            'gravity': (0.0, 0.0, 0.0),
            'calibration': (0, 0, 0, 0),
            'system_status': 0
        }
    
    try:
        # 센서에서 데이터 읽기
        q = sensor.quaternion
        gyro = sensor.gyro  # 공식 속성명
        accel = sensor.acceleration  # 공식 속성명 (기존 accelerometer → acceleration)
        mag = sensor.magnetic  # 공식 속성명
        temp = sensor.temperature  # 공식 속성명
        
        # 추가 데이터 읽기
        linear_accel = sensor.linear_acceleration  # 중력 제거된 순수 가속도
        gravity = sensor.gravity  # 중력 벡터
        calibration = sensor.calibration_status  # 보정 상태
        try:
            system_status = sensor.system_status  # 시스템 상태
        except AttributeError:
            system_status = 0  # system_status가 지원되지 않는 경우 기본값 사용
        
        # 오프셋 적용
        if gyro is not None and all(val is not None for val in gyro):
            gyro = tuple(g - o for g, o in zip(gyro, gyro_offset))
        if accel is not None and all(val is not None for val in accel):
            accel = tuple(a - o for a, o in zip(accel, accel_offset))
        if mag is not None and all(val is not None for val in mag):
            mag = tuple(m - o for m, o in zip(mag, magneto_offset))
        
        # 디버그 로그 (파일로만 기록, 화면 출력 안함)
        log_imu(f"RAW_DATA,{q},{gyro},{accel},{mag},{temp}")
        
        # 유효성 검사 - 각 데이터 타입별로 개별 검사
        data_valid = True
        
        # Gyro 데이터 검사
        if gyro is None or any(val is None for val in gyro):
            print("[경고] IMU gyro 데이터 None")
            gyro = read_sensor_data.last_valid_data['gyro']
            data_valid = False
        
        # Accel 데이터 검사
        if accel is None or any(val is None for val in accel):
            print("[경고] IMU accel 데이터 None")
            accel = read_sensor_data.last_valid_data['accel']
            data_valid = False
        
        # Mag 데이터 검사
        if mag is None or any(val is None for val in mag):
            print("[경고] IMU mag 데이터 None")
            mag = read_sensor_data.last_valid_data['mag']
            data_valid = False
        
        # Quaternion 데이터 검사
        if q is None or any(val is None for val in q):
            print("[경고] IMU quaternion 데이터 None")
            # 이전 유효한 오일러 각도 사용
            euler = read_sensor_data.last_valid_data['euler']
            data_valid = False
        else:
            # 오일러 각도 계산 (유효한 데이터가 있을 때만)
            import math
            try:
                roll = math.atan2(2 * (q[0] * q[1] + q[2] * q[3]), 1 - 2 * (q[1] * q[1] + q[2] * q[2]))
                pitch = math.asin(2 * (q[0] * q[2] - q[3] * q[1]))
                yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] * q[2] + q[3] * q[3]))
                
                # 라디안을 도로 변환
                roll_deg = math.degrees(roll)
                pitch_deg = math.degrees(pitch)
                yaw_deg = math.degrees(yaw)
                
                euler = (roll_deg, pitch_deg, yaw_deg)
                
                # 처리된 데이터 로그 (파일로만 기록)
                log_imu(f"PROCESSED,{roll_deg:.2f},{pitch_deg:.2f},{yaw_deg:.2f}")
                
            except (TypeError, ValueError) as e:
                print(f"IMU 각도 계산 오류: {e}")
                log_imu(f"ANGLE_CALC_ERROR,{e}")
                euler = read_sensor_data.last_valid_data['euler']
                data_valid = False
        
        # 온도 데이터 검사
        if temp is None:
            print("[경고] IMU 온도 데이터 None")
            temp = read_sensor_data.last_valid_data['temp']
            data_valid = False
        
        # 추가 데이터 검사
        if linear_accel is None or any(val is None for val in linear_accel):
            print("[경고] IMU linear_accel 데이터 None")
            linear_accel = read_sensor_data.last_valid_data['linear_accel']
            data_valid = False
        
        if gravity is None or any(val is None for val in gravity):
            print("[경고] IMU gravity 데이터 None")
            gravity = read_sensor_data.last_valid_data['gravity']
            data_valid = False
        
        if calibration is None or len(calibration) != 4:
            print("[경고] IMU calibration 데이터 None")
            calibration = read_sensor_data.last_valid_data['calibration']
            data_valid = False
        
        if system_status is None:
            print("[경고] IMU system_status 데이터 None")
            system_status = read_sensor_data.last_valid_data['system_status']
            data_valid = False
        
        # 데이터가 유효한 경우 마지막 유효 데이터 업데이트
        if data_valid:
            read_sensor_data.last_valid_data = {
                'gyro': gyro,
                'accel': accel,
                'mag': mag,
                'euler': euler,
                'temp': temp,
                'quaternion': q,
                'linear_accel': linear_accel,
                'gravity': gravity,
                'calibration': calibration,
                'system_status': system_status
            }
            read_sensor_data.none_count = 0
        else:
            read_sensor_data.none_count += 1
            if read_sensor_data.none_count >= 10:
                print(f"[경고] IMU 데이터 {read_sensor_data.none_count}회 연속 None 발생 (하드웨어/배선 점검 필요)")
                read_sensor_data.none_count = 0
        
        return (gyro, accel, mag, euler, temp, q, linear_accel, gravity, calibration, system_status)
        
    except Exception as e:
        # 에러 타입에 따라 다른 메시지 출력
        if "system_status" in str(e):
            print(f"IMU system_status 속성 오류 (정상 동작): {e}")
        else:
            print(f"IMU 읽기 오류: {e}")
        log_imu(f"READ_ERROR,{e}")
        # 오류 발생 시 마지막 유효 데이터 반환
        last_data = read_sensor_data.last_valid_data
        return (last_data['gyro'], last_data['accel'], last_data['mag'], last_data['euler'], last_data['temp'],
                last_data['quaternion'], last_data['linear_accel'], last_data['gravity'], 
                last_data['calibration'], last_data['system_status'])

def read_sensor_data_advanced(sensor):
    """
    IMU 센서 고급 데이터 읽기 - 모든 데이터 포함
    
    Returns:
        dict: 모든 IMU 데이터
    """
    try:
        # 기본 데이터 읽기
        gyro, accel, mag, euler, temp, q, linear_accel, gravity, calibration, system_status = read_sensor_data(sensor)
        
        # 고급 데이터 구성
        advanced_data = {
            'basic': {
                'gyro': gyro,
                'accel': accel,
                'mag': mag,
                'euler': euler,
                'temp': temp
            },
            'quaternion': q,
            'linear_acceleration': linear_accel,
            'gravity': gravity,
            'calibration': {
                'system': calibration[0],
                'gyro': calibration[1],
                'accel': calibration[2],
                'mag': calibration[3]
            },
            'system_status': system_status,
            'calibration_status': {
                'excellent': all(cal >= 3 for cal in calibration),
                'good': all(cal >= 2 for cal in calibration),
                'fair': all(cal >= 1 for cal in calibration),
                'poor': any(cal == 0 for cal in calibration)
            }
        }
        
        # 로그 기록
        log_imu(f"ADVANCED_DATA,QUAT:{q},LIN_ACC:{linear_accel},GRAV:{gravity},"
                f"CAL:{calibration},STATUS:{system_status}")
        
        return advanced_data
        
    except Exception as e:
        print(f"IMU 고급 데이터 읽기 오류: {e}")
        log_imu(f"ADVANCED_READ_ERROR,{e}")
        return None

def imu_terminate(i2c):
    i2c.deinit()
    return

if __name__ == "__main__":
    i2c, sensor = init_imu()
    #print(f'Offset : {sensor.offsets_magnetometer}')
    try:
        while True:
            data = read_sensor_data(sensor)
            print(data)
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        imu_terminate(i2c)
