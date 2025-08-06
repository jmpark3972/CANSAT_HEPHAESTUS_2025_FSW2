#!/usr/bin/env python3
"""
Pi Camera Standalone Test Script
CANSAT 카메라 모듈을 독립적으로 테스트하기 위한 스크립트
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib import logging

def safe_log(message: str, level: str = "INFO", printlogs: bool = True):
    """안전한 로깅 함수"""
    try:
        formatted_message = f"[StandaloneCamera] [{level}] {message}"
        logging.log(formatted_message, printlogs)
    except Exception as e:
        print(f"[StandaloneCamera] 로깅 실패: {e}")
        print(f"[StandaloneCamera] 원본 메시지: {message}")

class StandaloneCamera:
    """독립 실행 가능한 카메라 클래스"""
    
    def __init__(self):
        self.running = False
        self.recording = False
        self.video_count = 0
        self.camera_status = "IDLE"
        self.disk_usage = 0.0
        
        # 설정
        self.video_dir = "logs/cansat_videos"
        self.temp_dir = "logs/cansat_camera_temp"
        self.log_dir = "logs/cansat_camera_logs"
        self.video_duration = 5  # 5초
        self.recording_interval = 10  # 10초마다 녹화
        
        # 디렉토리 생성
        self.ensure_directories()
        
        # 시그널 핸들러 설정
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        safe_log(f"시그널 {signum} 수신, 종료 중...", "INFO", True)
        self.stop()
    
    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        try:
            os.makedirs(self.video_dir, exist_ok=True)
            os.makedirs(self.temp_dir, exist_ok=True)
            os.makedirs(self.log_dir, exist_ok=True)
            safe_log("디렉토리 생성 완료", "INFO", True)
            return True
        except Exception as e:
            safe_log(f"디렉토리 생성 실패: {e}", "ERROR", True)
            return False
    
    def check_camera_hardware(self):
        """카메라 하드웨어 확인"""
        try:
            import subprocess
            result = subprocess.run(['vcgencmd', 'get_camera'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and 'detected=1' in result.stdout:
                safe_log("카메라 하드웨어 감지됨", "INFO", True)
                return True
            else:
                safe_log("카메라 하드웨어 감지되지 않음", "ERROR", True)
                return False
        except Exception as e:
            safe_log(f"카메라 하드웨어 확인 오류: {e}", "ERROR", True)
            return False
    
    def check_camera_driver(self):
        """카메라 드라이버 확인"""
        try:
            video_devices = list(Path('/dev').glob('video*'))
            if video_devices:
                safe_log(f"비디오 디바이스 발견: {[str(d) for d in video_devices]}", "INFO", True)
                return True
            else:
                safe_log("비디오 디바이스 없음", "ERROR", True)
                return False
        except Exception as e:
            safe_log(f"카메라 드라이버 확인 오류: {e}", "ERROR", True)
            return False
    
    def check_ffmpeg(self):
        """FFmpeg 설치 확인"""
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                safe_log("FFmpeg 설치 확인됨", "INFO", True)
                return True
            else:
                safe_log("FFmpeg 설치되지 않음", "ERROR", True)
                return False
        except Exception as e:
            safe_log(f"FFmpeg 확인 오류: {e}", "ERROR", True)
            return False
    
    def get_disk_usage(self):
        """디스크 사용량 확인"""
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.video_dir)
            usage_percent = (used / total) * 100
            return round(usage_percent, 1)
        except Exception as e:
            safe_log(f"디스크 사용량 확인 오류: {e}", "ERROR", True)
            return 0.0
    
    def get_video_count(self):
        """저장된 비디오 파일 수 확인"""
        try:
            video_files = list(Path(self.video_dir).glob('*.mp4'))
            return len(video_files)
        except Exception as e:
            safe_log(f"비디오 파일 수 확인 오류: {e}", "ERROR", True)
            return 0
    
    def record_video(self):
        """비디오 녹화"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = os.path.join(self.video_dir, f"cansat_video_{timestamp}.mp4")
            
            # FFmpeg 명령어 구성
            cmd = [
                'ffmpeg',
                '-f', 'v4l2',           # Video4Linux2 입력
                '-video_size', '1920x1080',  # 해상도
                '-framerate', '30',     # 프레임레이트
                '-i', '/dev/video0',    # 비디오 디바이스
                '-t', str(self.video_duration),  # 녹화 시간
                '-c:v', 'libx264',      # 비디오 코덱
                '-preset', 'ultrafast',  # 인코딩 속도
                '-crf', '23',           # 품질 설정
                '-y',                   # 기존 파일 덮어쓰기
                output_file
            ]
            
            safe_log(f"녹화 시작: {output_file}", "INFO", True)
            
            import subprocess
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 녹화 완료 대기
            stdout, stderr = process.communicate(timeout=self.video_duration + 5)
            
            if process.returncode == 0:
                self.video_count = self.get_video_count()
                safe_log(f"녹화 완료: {output_file}", "INFO", True)
                return True
            else:
                safe_log(f"녹화 실패: {stderr.decode()}", "ERROR", True)
                return False
                
        except subprocess.TimeoutExpired:
            process.kill()
            safe_log("녹화 타임아웃", "ERROR", True)
            return False
        except Exception as e:
            safe_log(f"녹화 오류: {e}", "ERROR", True)
            return False
    
    def recording_loop(self):
        """녹화 루프"""
        safe_log("녹화 루프 시작", "INFO", True)
        
        while self.running:
            try:
                if not self.recording:
                    time.sleep(1)
                    continue
                
                # 비디오 녹화
                if self.record_video():
                    self.video_count += 1
                
                # 상태 업데이트
                self.disk_usage = self.get_disk_usage()
                
                # 다음 녹화까지 대기
                time.sleep(self.recording_interval)
                
            except Exception as e:
                safe_log(f"녹화 루프 오류: {e}", "ERROR", True)
                time.sleep(1)
        
        safe_log("녹화 루프 종료", "INFO", True)
    
    def status_loop(self):
        """상태 모니터링 루프"""
        safe_log("상태 모니터링 루프 시작", "INFO", True)
        
        while self.running:
            try:
                # 상태 업데이트
                old_status = self.camera_status
                self.camera_status = "RECORDING" if self.recording else "IDLE"
                
                if old_status != self.camera_status:
                    safe_log(f"카메라 상태 변경: {old_status} -> {self.camera_status}", "INFO", True)
                
                # 비디오 수 업데이트
                old_count = self.video_count
                self.video_count = self.get_video_count()
                
                if old_count != self.video_count:
                    safe_log(f"비디오 수 업데이트: {old_count} -> {self.video_count}", "INFO", True)
                
                # 디스크 사용량 업데이트
                old_usage = self.disk_usage
                self.disk_usage = self.get_disk_usage()
                
                if abs(old_usage - self.disk_usage) > 5:  # 5% 이상 변화 시 로그
                    safe_log(f"디스크 사용량 업데이트: {old_usage:.1f}% -> {self.disk_usage:.1f}%", "INFO", True)
                
                time.sleep(5)  # 5초마다 업데이트
                
            except Exception as e:
                safe_log(f"상태 모니터링 오류: {e}", "ERROR", True)
                time.sleep(5)
        
        safe_log("상태 모니터링 루프 종료", "INFO", True)
    
    def start(self):
        """카메라 시작"""
        safe_log("카메라 시작 중...", "INFO", True)
        
        # 하드웨어 확인
        if not self.check_camera_hardware():
            safe_log("카메라 하드웨어 확인 실패", "ERROR", True)
            return False
        
        # 드라이버 확인
        if not self.check_camera_driver():
            safe_log("카메라 드라이버 확인 실패", "ERROR", True)
            return False
        
        # FFmpeg 확인
        if not self.check_ffmpeg():
            safe_log("FFmpeg 확인 실패", "ERROR", True)
            return False
        
        self.running = True
        
        # 스레드 시작
        self.recording_thread = threading.Thread(target=self.recording_loop, daemon=True)
        self.status_thread = threading.Thread(target=self.status_loop, daemon=True)
        
        self.recording_thread.start()
        self.status_thread.start()
        
        safe_log("카메라 시작 완료", "INFO", True)
        return True
    
    def stop(self):
        """카메라 중지"""
        safe_log("카메라 중지 중...", "INFO", True)
        
        self.running = False
        self.recording = False
        
        # 스레드 종료 대기
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            self.recording_thread.join(timeout=3)
        
        if hasattr(self, 'status_thread') and self.status_thread.is_alive():
            self.status_thread.join(timeout=3)
        
        safe_log("카메라 중지 완료", "INFO", True)
    
    def start_recording(self):
        """녹화 시작"""
        if not self.running:
            safe_log("카메라가 실행되지 않음", "ERROR", True)
            return False
        
        self.recording = True
        safe_log("녹화 시작됨", "INFO", True)
        return True
    
    def stop_recording(self):
        """녹화 중지"""
        self.recording = False
        safe_log("녹화 중지됨", "INFO", True)
    
    def get_status(self):
        """현재 상태 반환"""
        return {
            'status': self.camera_status,
            'recording': self.recording,
            'video_count': self.video_count,
            'disk_usage': self.disk_usage,
            'running': self.running
        }

def main():
    """메인 함수"""
    print("=" * 60)
    print("Pi Camera Standalone Test")
    print("=" * 60)
    print("사용법:")
    print("  r - 녹화 시작/중지")
    print("  s - 상태 확인")
    print("  q - 종료")
    print("=" * 60)
    
    camera = StandaloneCamera()
    
    if not camera.start():
        print("카메라 시작 실패")
        return
    
    try:
        while True:
            command = input("명령어 (r/s/q): ").strip().lower()
            
            if command == 'r':
                if camera.recording:
                    camera.stop_recording()
                else:
                    camera.start_recording()
            
            elif command == 's':
                status = camera.get_status()
                print(f"\n현재 상태:")
                print(f"  상태: {status['status']}")
                print(f"  녹화 중: {status['recording']}")
                print(f"  비디오 수: {status['video_count']}")
                print(f"  디스크 사용량: {status['disk_usage']:.1f}%")
                print(f"  실행 중: {status['running']}")
                print()
            
            elif command == 'q':
                break
            
            else:
                print("잘못된 명령어입니다. r/s/q 중 하나를 입력하세요.")
    
    except KeyboardInterrupt:
        print("\n키보드 인터럽트 감지")
    
    finally:
        camera.stop()
        print("프로그램 종료")

if __name__ == "__main__":
    main() 