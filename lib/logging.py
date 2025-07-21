from typing import Type, TextIO
from datetime import datetime
from multiprocessing import Lock

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