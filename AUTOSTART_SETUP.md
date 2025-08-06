# CANSAT HEPHAESTUS 2025 FSW2 자동 시작 설정 가이드

## 📋 개요
라즈베리파이가 부팅될 때 자동으로 CANSAT FSW가 실행되도록 설정하는 방법을 설명합니다.

## 🚀 방법 1: systemd 서비스 (권장)

### 1.1 서비스 파일 설치
```bash
# 서비스 파일을 systemd 디렉토리로 복사
sudo cp cansat-hephaestus.service /etc/systemd/system/

# systemd 재로드
sudo systemctl daemon-reload

# 서비스 활성화 (부팅 시 자동 시작)
sudo systemctl enable cansat-hephaestus.service

# 서비스 시작
sudo systemctl start cansat-hephaestus.service
```

### 1.2 서비스 상태 확인
```bash
# 서비스 상태 확인
sudo systemctl status cansat-hephaestus.service

# 로그 확인
sudo journalctl -u cansat-hephaestus.service -f

# 서비스 중지
sudo systemctl stop cansat-hephaestus.service

# 서비스 비활성화 (자동 시작 해제)
sudo systemctl disable cansat-hephaestus.service
```

## 🔧 방법 2: rc.local 사용

### 2.1 rc.local 편집
```bash
sudo nano /etc/rc.local
```

### 2.2 다음 내용 추가 (exit 0 앞에)
```bash
# CANSAT HEPHAESTUS FSW 자동 시작
cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2
source /home/pi/env/bin/activate
python3 main.py &
```

## 📝 방법 3: crontab 사용

### 3.1 crontab 편집
```bash
crontab -e
```

### 3.2 다음 내용 추가
```bash
# 부팅 시 CANSAT FSW 시작 (1분 지연)
@reboot sleep 60 && cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2 && source /home/pi/env/bin/activate && python3 main.py
```

## 🔍 방법 4: startup.sh 스크립트 사용

### 4.1 스크립트 실행 권한 부여
```bash
chmod +x startup.sh
```

### 4.2 자동 시작 설정
```bash
# rc.local에 추가
sudo nano /etc/rc.local
# 다음 줄 추가: /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/startup.sh &
```

## ⚠️ 주의사항

### 하드웨어 접근 권한
```bash
# pi 사용자를 필요한 그룹에 추가
sudo usermod -a -G gpio,video,i2c pi

# 재부팅 후 적용
sudo reboot
```

### 환경 변수 확인
```bash
# 가상환경 경로 확인
ls -la /home/pi/env/bin/python3

# 프로젝트 경로 확인
ls -la /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py
```

## 🛠️ 문제 해결

### 서비스 시작 실패 시
```bash
# 상세 로그 확인
sudo journalctl -u cansat-hephaestus.service -n 50

# 서비스 파일 문법 검사
sudo systemd-analyze verify /etc/systemd/system/cansat-hephaestus.service
```

### 권한 문제 시
```bash
# 파일 권한 확인
ls -la /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py
ls -la /home/pi/env/bin/python3

# 권한 수정
chmod +x /home/pi/CANSAT_HEPHAESTUS_2025_FSW2/main.py
```

## 📊 권장 설정

**가장 안정적인 방법은 systemd 서비스 사용을 권장합니다:**

1. **자동 재시작**: 서비스가 중단되면 자동으로 재시작
2. **로그 관리**: systemd journal을 통한 체계적인 로그 관리
3. **의존성 관리**: pigpiod 등 필요한 서비스가 먼저 시작된 후 실행
4. **권한 관리**: 적절한 그룹 권한으로 하드웨어 접근

## 🔄 수동 실행

자동 시작을 비활성화하고 수동으로 실행하려면:
```bash
# 서비스 비활성화
sudo systemctl disable cansat-hephaestus.service

# 수동 실행
cd /home/pi/CANSAT_HEPHAESTUS_2025_FSW2
source /home/pi/env/bin/activate
python3 main.py
```

---
**팀**: HEPHAESTUS  
**문서 버전**: 1.0  
**최종 업데이트**: 2025년 8월 