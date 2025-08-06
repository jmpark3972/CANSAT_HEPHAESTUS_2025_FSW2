from lib import logging
from multiprocessing import Queue
from lib import types

class MsgStructure:
    sender_app: types.AppID = None # AppID of sender
    receiver_app: types.AppID = None # AppID of receiver
    MsgID: types.MID = None # Message ID should be unique for identification
    data: str = None # Data

def fill_msg(target: MsgStructure, _sender : int, _receiver : int, _MsgID : int, _data: str):
    try:
        # 입력값 검증
        if not isinstance(_sender, int) or not isinstance(_receiver, int) or not isinstance(_MsgID, int):
            logging.log(f"[MsgStructure] Invalid type: sender={type(_sender)}, receiver={type(_receiver)}, MsgID={type(_MsgID)}", True)
            return False
        
        if not isinstance(_data, str):
            logging.log(f"[MsgStructure] Data must be string, got {type(_data)}", True)
            return False
            
        if '|' in _data:
            logging.log(f"[MsgStructure] Data should not contain '|' since it is used to divide fields", True)
            return False
            
        # 음수 값 검증
        if _sender < 0 or _receiver < 0 or _MsgID < 0:
            logging.log(f"[MsgStructure] Negative values not allowed: sender={_sender}, receiver={_receiver}, MsgID={_MsgID}", True)
            return False
            
        target.sender_app = _sender
        target.receiver_app = _receiver
        target.MsgID = _MsgID
        target.data = _data
        return True
    except Exception as e:
        logging.log(f"[MsgStructure] Error when filling message: {e}", True)
        return False

def pack_msg (target: MsgStructure) -> str:
    try:
        # None 체크 및 타입 검증
        if target.sender_app is None or target.receiver_app is None or target.MsgID is None or target.data is None:
            logging.log(f"[MsgStructure] Error when packing message: message is not filled", True)
            return "ERROR"
            
        # 타입 검증
        if not isinstance(target.sender_app, int) or not isinstance(target.receiver_app, int) or not isinstance(target.MsgID, int) or not isinstance(target.data, str):
            logging.log(f"[MsgStructure] Error when packing message: invalid types", True)
            return "ERROR"
            
        return str(target.sender_app) + "|" + str(target.receiver_app) + "|" + str(target.MsgID) + "|" + target.data
    except Exception as e:
        logging.log(f"[MsgStructure] Error when packing message: {e}", True)
        return "ERROR"
    
def unpack_msg (target : MsgStructure, msg: str) -> bool:
    try:
        # 입력 검증
        if not isinstance(msg, str):
            logging.log(f"[MsgStructure] Error when unpacking message: msg must be string, got {type(msg)}", True)
            return False
            
        if not msg or msg.strip() == "":
            logging.log(f"[MsgStructure] Error when unpacking message: empty message", True)
            return False
            
        msg_list = msg.split('|')
        if len(msg_list) != 4:
            logging.log(f"[MsgStructure] Error when unpacking message: Expected length of msg_list of 4 but {len(msg_list)}", True)
            return False
            
        # 숫자 변환 검증
        try:
            sender_app = int(msg_list[0])
            receiver_app = int(msg_list[1])
            msg_id = int(msg_list[2])
        except ValueError as e:
            logging.log(f"[MsgStructure] Error when unpacking message: invalid numeric values: {e}", True)
            return False
            
        # 음수 값 검증
        if sender_app < 0 or receiver_app < 0 or msg_id < 0:
            logging.log(f"[MsgStructure] Error when unpacking message: negative values not allowed", True)
            return False
            
        target.sender_app = sender_app
        target.receiver_app = receiver_app
        target.MsgID = msg_id
        target.data = msg_list[3]
        return True
    except Exception as e:
        logging.log(f"[MsgStructure] Error when unpacking message: {e}", True)
        return False
    
# Send message for SB Methods to route
def send_msg (Main_Queue : Queue, target: MsgStructure, _sender : types.AppID, _receiver : types.AppID, _MsgID : types.MID, _data: str):
    try:
        # Fill Message
        fill_msg(target, _sender, _receiver, _MsgID, _data)
        
        # Pack Message
        packed_msg = pack_msg(target)
        
        # Send Message
        if packed_msg == "ERROR":
            logging.log(f"[MsgStructure] Error when sending message: packing failed", True)
            return False
            
        Main_Queue.put(packed_msg)
        return True
    except Exception as e:
        logging.log(f"[MsgStructure] Error when sending message: {e}", True)
        return False