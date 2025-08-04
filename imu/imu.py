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
    import board
    import busio
    import adafruit_bno055
    from lib.qwiic_mux import QwiicMux
    
    # I2C 버스 초기화
    i2c = busio.I2C(board.SCL, board.SDA, frequency=400_000)
    time.sleep(0.1)  # I2C 버스 안정화
    
    # Qwiic Mux 초기화 및 채널 5 선택 (IMU 위치 - 실제 연결된 채널)
    try:
        from lib.qwiic_mux import create_mux_instance
        mux = create_mux_instance(i2c_bus=i2c, mux_address=0x70)
        
        # channel_guard를 사용하여 안전하게 채널 선택 및 센서 초기화
        sensor = None
        with mux.channel_guard(5):  # 🔒 채널 5 점유
            print("Qwiic Mux 채널 5 선택 완료 (IMU)")
            
            # 여러 주소에서 IMU 찾기 시도
            imu_addresses = [0x28, 0x29]  # BNO055 일반적인 주소들
            
            for addr in imu_addresses:
                try:
                    print(f"IMU I2C 주소 0x{addr:02X} 시도 중...")
                    # I2C 버스 재초기화 시도
                    try:
                        i2c.unlock()
                    except:
                        pass
                    sensor = adafruit_bno055.BNO055_I2C(i2c, address=addr)
                    # 센서 상태 확인
                    if sensor.temperature is not None:
                        print(f"IMU 초기화 성공 (주소: 0x{addr:02X})")
                        break
                    else:
                        print(f"IMU 센서 응답 없음 (주소: 0x{addr:02X})")
                        sensor = None
                except Exception as e:
                    print(f"주소 0x{addr:02X} 실패: {e}")
                    time.sleep(0.3)  # 각 시도 사이 지연 증가
                    continue
        
        if sensor is None:
            raise Exception("IMU를 찾을 수 없습니다. I2C 연결을 확인하세요.")

        # Calibration results go HERE
        sensor.offsets_magnetometer = magneto_offset
        sensor.offsets_gyroscope = gyro_offset
        sensor.offsets_accelerometer = accel_offset
        
        # 센서 안정화를 위한 추가 지연
        time.sleep(1.0)
        
        return i2c, sensor, mux
        
    except Exception as e:
        print(f"Qwiic Mux 초기화 실패: {e}")
        raise Exception(f"Qwiic Mux 초기화 실패: {e}")

def read_sensor_data(sensor, mux):
    global angle_window

    # channel_guard를 사용하여 안전하게 센서 읽기
    with mux.channel_guard(5):  # 🔒 채널 5 점유
        q = sensor.quaternion

        # Pass this data when none is includued in quaternion
        if None in q:
            # In case that the angle window is empty, put 0
            if len(angle_window[0]) == 0: 
                angle_window[0].append(0)
            if len(angle_window[1]) == 0:
                angle_window[1].append(0)
            if len(angle_window[2]) == 0:
                angle_window[2].append(0)
        else:
            w, x, y, z = q

            w = round(w, 2)
            x = round(x, 2)
            y = round(y, 2)
            z = round(z, 2)
            # 쿼터니언으로부터 yaw (heading) 계산 (라디안 단위)
            yaw = math.atan2(2*(w*z + x*y), 1 - 2*(y**2 + z**2))
            yaw_deg = math.degrees(yaw)

            # 쿼터니언으로부터 pitch 계산 (라디안 단위)
            try: # arcsin 함수의 정의역 문제
                pitch_cal = 2*(w*y - z*x)
                if pitch_cal < -1:
                    pitch_cal = -1.00
                if pitch_cal > 1:
                    pitch_cal = 1.00
                pitch_cal = round(pitch_cal, 2)
                
                pitch = math.asin(pitch_cal)
                # 라디안을 도(degree)로 변환
                pitch_deg = math.degrees(pitch)
                
            except ValueError:
                # 정의역을 넘어버렸을 때 -> 직전 값을 가져와서 대체함.
                pitch_deg = angle_window[2][-1]     
                
            # 쿼터니언으로부터 roll 계산 (라디안 단위)
            roll = math.atan2(2*(w*x + y*z), 1 - 2*(x**2 + y**2))
            
            # 라디안을 도(degree)로 변환
            roll_deg = math.degrees(roll)
            
            # 음수 각도를 0~360도로 변환
            if yaw_deg < 0:
                yaw_deg += 360
            
            if roll_deg < 0:
                roll_deg += 360
            ''' 
            if pitch_deg < 0:
                pitch_deg += 360
            '''
            angle_window[0].append(yaw_deg)
            angle_window[1].append(roll_deg)
            angle_window[2].append(pitch_deg)

            # YAW 이동평균필터 리스트 최신화
            if len(angle_window[0]) > window_size:
                angle_window[0].pop(0)

            # ROLL 이동평균필터 리스트 최신화
            if len(angle_window[1]) > window_size:
                angle_window[1].pop(0)

            # PITCH 이동평균필터 리스트 최신화
            if len(angle_window[2]) > window_size:
                angle_window[2].pop(0)

        # Accelometer and Mag, gyro
        avg_yaw = sum(angle_window[0])/len(angle_window[0])
        avg_roll = sum(angle_window[1])/len(angle_window[1])
        avg_pitch = sum(angle_window[2])/len(angle_window[2])
        
        # Round all data to 2 digits

        avg_yaw = round(avg_yaw, 2)
        avg_roll = round(avg_roll, 2)
        avg_pitch = round(avg_pitch, 2)

        #sen_yaw, sen_roll, sen_pitch = sensor.euler 
        accX, accY, accZ = sensor.acceleration

        # Error Checking, if None is contained, set the value to 0
        if accX == None or accY == None or accZ == None:
            accX = 0
            accY = 0
            accZ = 0
        else:
            accX = round(accX, 2)
            accY = round(accY, 2)
            accZ = round(accZ, 2)

        magX, magY, magZ = sensor.magnetic
        if magX is None or magY is None or magZ is None:
            magX = 0
            magY = 0
            magZ = 0
        else:
            magX = round(magX, 4)
            magY = round(magY, 4)
            magZ = round(magZ, 4)

        gyrX, gyrY, gyrZ = sensor.gyro
        if gyrX is None or gyrY is None or gyrZ is None:
            gyrX = 0
            gyrY = 0
            gyrZ = 0
        else:
            gyrX = round(gyrX, 2)
            gyrY = round(gyrY, 2)
            gyrZ = round(gyrZ, 2)

        # Read temperature from BNO055
        temp = sensor.temperature
        if temp is None:
            temp = 0
        else:
            temp = round(temp, 2)

        # Log data
        log_imu(f"{avg_yaw},{avg_roll},{avg_pitch},{accX},{accY},{accZ},{magX},{magY},{magZ},{gyrX},{gyrY},{gyrZ},{temp}")

        # Return data as tuple
        return (avg_yaw, avg_roll, avg_pitch, accX, accY, accZ, magX, magY, magZ, gyrX, gyrY, gyrZ, temp)

    return False

def imu_terminate(i2c):
    i2c.deinit()
    return

if __name__ == "__main__":
    i2c, sensor, mux = init_imu()
    #print(f'Offset : {sensor.offsets_magnetometer}')
    try:
        while True:
            data = read_sensor_data(sensor, mux)
            print(data)
            time.sleep(0.1)
    
    except KeyboardInterrupt:
        imu_terminate(i2c)
