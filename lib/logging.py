from typing import Type, TextIO
from datetime import datetime
from multiprocessing import Lock

# 이중 로깅 시스템 import
from . import dual_logging

mutex = Lock()

def logdata(target: Type[TextIO], text: str, printlogs=False): # 데이터를 로깅할 때 사용
    try:
        with mutex:
            t = datetime.now().isoformat(sep=' ', timespec='milliseconds')
            string_to_write = f'[{t}] {text}'
            if printlogs:
                print(string_to_write)
            target.write(string_to_write + '\n')
            target.flush()
    except Exception as e:
        print(f"Error while Logging : {e}")
        return
    
    # 이중 로깅 시스템에도 로깅
    try:
        dual_logging.logdata(target, text, printlogs)
    except Exception as e:
        print(f"이중 로깅 오류: {e}")

def init_dual_logging_system():
    """이중 로깅 시스템 초기화"""
    try:
        dual_logging.init_dual_logging()
        print("이중 로깅 시스템 초기화 완료")
    except Exception as e:
        print(f"이중 로깅 시스템 초기화 오류: {e}")

def close_dual_logging_system():
    """이중 로깅 시스템 종료"""
    try:
        dual_logging.close_dual_logging()
        print("이중 로깅 시스템 종료 완료")
    except Exception as e:
        print(f"이중 로깅 시스템 종료 오류: {e}")