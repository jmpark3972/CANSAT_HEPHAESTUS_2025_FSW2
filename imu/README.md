IMU code for CANSAT AAS 2025

I2C Stretch 필요함

Library
pip3 install adafruit-circuitpython-bno055

Function
imu.py

cal_imu : imu를 calibration 함.
1차 (Mag) : 8자 그리기. (수평이든 수직이든)

2차 (Acc) : roll 방향으로 45도씩 돌리고 기다렸다 반복.

3차 (Gyr) : 그냥 두면 됨.

단!!! init_imu가 먼저 시작되어야 함!

init_imu : imu를 초기 설정함.
read_sensor_data : yaw, roll, pitch를 계산하며, 이동평균을 토대로 출력한다. (motor의 급격한 운동 방지)
