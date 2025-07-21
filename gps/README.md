### GPS RX_PIN
GPIO 22번 핀 사용
### Daemon 부팅 때 자동으로 켜지도록 하기.
sudo systemctl enable pigpiod
### Install Library
pip3 install pigpio

time 모듈 사용
### Function
- GPS 데이터 수신

init_gps: gps pigpio로 연결

read_gps: gps의 NMEA lines 모두 읽어서 return

parse_gps_data: NMEA lines 중 gga, RMC 데이터만 뽑아서 리스트로 return

- GPS 데이터 파싱

unit_convert_deg: 위도, 경도 상용 단위로 변환

gps_readdata: pi handle을 통해 필요한 데이터 파싱
