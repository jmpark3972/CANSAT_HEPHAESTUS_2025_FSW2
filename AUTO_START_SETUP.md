# CANSAT HEPHAESTUS 2025 FSW2 - Auto-Start Setup Guide

## 개요
라즈베리파이가 부팅될 때 자동으로 `main.py`를 실행하도록 설정하는 방법입니다.

## 방법 1: Systemd Service (권장)

### 1. 서비스 파일 확인
`cansat-hephaestus.service` 파일이 이미 프로젝트에 포함되어 있습니다.

### 2. 서비스 파일을 시스템에 복사
```bash
sudo cp cansat-hephaestus.service /etc/systemd/system/
```

### 3. 서비스 활성화
```bash
sudo systemctl daemon-reload
sudo systemctl enable cansat-hephaestus.service
```

### 4. 서비스 상태 확인
```bash
sudo systemctl status cansat-hephaestus.service
```

### 5. 서비스 시작/중지/재시작
```bash
# 서비스 시작
sudo systemctl start cansat-hephaestus.service

# 서비스 중지
sudo systemctl stop cansat-hephaestus.service

# 서비스 재시작
sudo systemctl restart cansat-hephaestus.service
```

### 6. 로그 확인
```bash
# 실시간 로그 확인
sudo journalctl -u cansat-hephaestus.service -f

# 최근 로그 확인
sudo journalctl -u cansat-hephaestus.service -n 50
```

## 방법 2: rc.local 사용 (대안)

### 1. rc.local 편집
```bash
sudo nano /etc/rc.local
```

### 2. 다음 내용 추가 (exit 0 앞에)
```bash
# CANSAT HEPHAESTUS 2025 FSW2 Auto-Start
cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2
source /home/pi/env/bin/activate
python3 main.py &
```

### 3. rc.local 실행 권한 부여
```bash
sudo chmod +x /etc/rc.local
```

## 방법 3: Crontab 사용 (대안)

### 1. crontab 편집
```bash
crontab -e
```

### 2. 다음 내용 추가
```bash
@reboot cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2 && /home/pi/env/bin/python3 main.py
```

## 권장 설정: Systemd Service

Systemd 서비스를 사용하는 것을 권장합니다. 이유:

1. **자동 재시작**: 프로그램이 충돌하면 자동으로 재시작
2. **로그 관리**: 시스템 로그에 통합된 로그 관리
3. **의존성 관리**: 다른 서비스(pigpiod 등) 시작 후 실행
4. **권한 관리**: 적절한 그룹 권한 설정
5. **모니터링**: 서비스 상태 쉽게 확인 가능

## 문제 해결

### 서비스가 시작되지 않는 경우
1. 로그 확인:
   ```bash
   sudo journalctl -u cansat-hephaestus.service -n 50
   ```

2. 경로 확인:
   ```bash
   ls -la /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py
   ls -la /home/pi/env/bin/python3
   ```

3. 권한 확인:
   ```bash
   sudo chown -R pi:pi /home/pi/CANSAT_HEPHAESTUS_2025_FSW2
   ```

### 수동 테스트
서비스 설정 전에 수동으로 실행해보세요:
```bash
cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2
source /home/pi/env/bin/activate
python3 main.py
```

## 서비스 비활성화 (필요시)
```bash
sudo systemctl disable cansat-hephaestus.service
sudo systemctl stop cansat-hephaestus.service
```

## 현재 설정 확인
```bash
# 활성화된 서비스 목록 확인
sudo systemctl list-unit-files | grep cansat

# 서비스 상태 확인
sudo systemctl status cansat-hephaestus.service
``` 