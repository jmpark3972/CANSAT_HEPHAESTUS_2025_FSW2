#!/usr/bin/env python3
"""
CANSAT FSW 로그 파일 로테이션 스크립트
로그 파일의 크기와 나이를 관리하여 디스크 공간을 효율적으로 사용
"""

import os
import gzip
import shutil
import logging
from datetime import datetime, timedelta
from pathlib import Path

class LogRotator:
    """로그 파일 로테이션 클래스"""
    
    def __init__(self, max_size_mb=10, max_age_days=30):
        self.max_size_mb = max_size_mb
        self.max_age_days = max_age_days
        self.log_dirs = ['logs', 'eventlogs']
        
        # 로그 디렉토리 생성
        for log_dir in self.log_dirs:
            Path(log_dir).mkdir(exist_ok=True)
    
    def rotate_logs(self):
        """모든 로그 파일 로테이션"""
        print("🔄 로그 파일 로테이션 시작...")
        
        for log_dir in self.log_dirs:
            if not os.path.exists(log_dir):
                continue
                
            print(f"📁 {log_dir} 디렉토리 처리 중...")
            
            for filename in os.listdir(log_dir):
                filepath = os.path.join(log_dir, filename)
                
                if not os.path.isfile(filepath):
                    continue
                
                # 이미 압축된 파일은 건너뛰기
                if filename.endswith('.gz'):
                    continue
                
                # 파일 크기 확인
                file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                if file_size_mb > self.max_size_mb:
                    print(f"📦 {filename} 압축 중... ({file_size_mb:.1f}MB)")
                    self.compress_log(filepath)
                
                # 오래된 파일 확인
                if self.is_old_file(filepath):
                    print(f"🗑️ 오래된 파일 삭제: {filename}")
                    os.remove(filepath)
        
        print("✅ 로그 파일 로테이션 완료")
    
    def compress_log(self, filepath):
        """로그 파일 압축"""
        try:
            with open(filepath, 'rb') as f_in:
                with gzip.open(filepath + '.gz', 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            # 원본 파일 삭제
            os.remove(filepath)
            print(f"✅ {os.path.basename(filepath)} 압축 완료")
            
        except Exception as e:
            print(f"❌ 압축 실패: {e}")
    
    def is_old_file(self, filepath):
        """파일이 지정된 일수보다 오래되었는지 확인"""
        try:
            file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
            return datetime.now() - file_time > timedelta(days=self.max_age_days)
        except Exception:
            return False
    
    def get_disk_usage(self):
        """디스크 사용량 확인"""
        try:
            import psutil
            disk_usage = psutil.disk_usage('/')
            return {
                'total_gb': disk_usage.total / (1024**3),
                'used_gb': disk_usage.used / (1024**3),
                'free_gb': disk_usage.free / (1024**3),
                'percent': disk_usage.percent
            }
        except ImportError:
            return None
    
    def check_and_rotate(self):
        """디스크 사용량 확인 후 필요시 로테이션"""
        disk_info = self.get_disk_usage()
        
        if disk_info and disk_info['percent'] > 80:
            print(f"⚠️ 디스크 사용량 경고: {disk_info['percent']:.1f}%")
            print(f"💾 사용 중: {disk_info['used_gb']:.1f}GB / {disk_info['total_gb']:.1f}GB")
            self.rotate_logs()
            return True
        
        return False

def main():
    """메인 함수"""
    rotator = LogRotator(max_size_mb=10, max_age_days=30)
    
    # 디스크 사용량 확인
    disk_info = rotator.get_disk_usage()
    if disk_info:
        print(f"💾 디스크 사용량: {disk_info['percent']:.1f}%")
        print(f"📊 사용 중: {disk_info['used_gb']:.1f}GB / {disk_info['total_gb']:.1f}GB")
    
    # 로그 로테이션 실행
    rotator.rotate_logs()
    
    # 로테이션 후 디스크 사용량 확인
    disk_info_after = rotator.get_disk_usage()
    if disk_info_after:
        print(f"✅ 로테이션 후 디스크 사용량: {disk_info_after['percent']:.1f}%")

if __name__ == "__main__":
    main() 