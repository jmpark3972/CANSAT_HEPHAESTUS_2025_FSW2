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

try:
    offsetfile = open(os.path.join('./imu/offset.txt'),mode='r')
    magneto_offset = tuple(map(int,offsetfile.readline().strip().split(sep=',')))
    gyro_offset = tuple(map(int,offsetfile.readline().strip().split(sep=',')))
    accel_offset = tuple(map(int,offsetfile.readline().strip().split(sep=',')))
    offsetfile.close()
except: 
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
        print("IMU 센서 초기화 완료 (직접 I2C 연결)")
        return i2c, sensor
    except Exception as e:
        print(f"IMU 초기화 실패: {e}")
        raise Exception(f"IMU 초기화 실패: {e}")

def read_sensor_data(sensor):
    """IMU 센서 데이터 읽기"""
    global angle_window
    if not hasattr(read_sensor_data, "none_count"): read_sensor_data.none_count = 0
    try:
        # 센서에서 데이터 읽기
        q = sensor.quaternion
        gyro = sensor.gyro  # 공식 속성명
        accel = sensor.acceleration  # 공식 속성명 (기존 accelerometer → acceleration)
        mag = sensor.magnetic  # 공식 속성명
        temp = sensor.temperature  # 공식 속성명
        
        # 디버그 로그 추가
        print(f"IMU Raw Data - Quaternion: {q}, Gyro: {gyro}, Accel: {accel}, Mag: {mag}, Temp: {temp}")
        
        # 유효성 검사
        if q is None or gyro is None or accel is None or mag is None:
            read_sensor_data.none_count += 1
            if read_sensor_data.none_count >= 5:
                print("[경고] IMU 데이터 5회 연속 None 발생 (하드웨어/배선 점검 필요)")
                read_sensor_data.none_count = 0
            return None, None, None, None, None
        else:
            read_sensor_data.none_count = 0
        
        # 오일러 각도 계산
        import math
        roll = math.atan2(2 * (q[0] * q[1] + q[2] * q[3]), 1 - 2 * (q[1] * q[1] + q[2] * q[2]))
        pitch = math.asin(2 * (q[0] * q[2] - q[3] * q[1]))
        yaw = math.atan2(2 * (q[0] * q[3] + q[1] * q[2]), 1 - 2 * (q[2] * q[2] + q[3] * q[3]))
        
        # 라디안을 도로 변환
        roll_deg = math.degrees(roll)
        pitch_deg = math.degrees(pitch)
        yaw_deg = math.degrees(yaw)
        
        print(f"IMU Processed - Roll: {roll_deg:.2f}°, Pitch: {pitch_deg:.2f}°, Yaw: {yaw_deg:.2f}°")
        
        return (gyro, accel, mag, (roll_deg, pitch_deg, yaw_deg), temp)
        
    except Exception as e:
        print(f"IMU 읽기 오류: {e}")
        log_imu(f"READ_ERROR,{e}")
        return None, None, None, None, None

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
