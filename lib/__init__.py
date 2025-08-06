# CANSAT HEPHAESTUS 2025 FSW2 - lib 패키지
# 공통 라이브러리 모듈들

# 강제 종료 유틸리티
from . import force_kill

# 진단 스크립트
from . import diagnostic_script

# 편의 함수들
def force_kill_cansat():
    """CANSAT 프로세스들을 강제 종료"""
    from .force_kill import force_kill_all
    force_kill_all()

def check_cansat_status():
    """CANSAT 시스템 상태 확인"""
    from .force_kill import check_system_status
    check_system_status()

def run_diagnostic():
    """시스템 진단 실행"""
    from .diagnostic_script import run_full_diagnostic
    run_full_diagnostic()

def quick_diagnostic():
    """빠른 시스템 진단"""
    from .diagnostic_script import check_system_resources, check_cansat_processes, check_gpio_access
    check_system_resources()
    check_cansat_processes()
    check_gpio_access() 