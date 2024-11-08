from brainflow import BoardShim, BrainFlowInputParams, BoardIds, DataFilter
import numpy as np 
import pandas as pd
import datetime
import os

id_dict = {
    -1 : 'Synthetic',
    0  : 'Cyton'
}

class BrainBoard:

    def __init__(self, debug=True, save_dir=''):
        self.isSetup = False
        self.isStreaming = False
        self.debug = debug
        self.save_dir  = save_dir

    def setup(self, boardID=BoardIds.SYNTHETIC_BOARD):
        BoardShim.enable_dev_board_logger()
        self.params = BrainFlowInputParams()
        self.params.master_board  = boardID
        self.board = BoardShim(boardID, self.params)
        self.isSetup = True
        self.board.prepare_session()
        
        self.data = None
        print(f"[BrainBoard] Succesfully Setup Board")
    
    def get_board_type(self, id=-1):
        if id in id_dict.keys():
            return id_dict[id]
        else:
            return 'Unknown'


    def start(self):
        self.isStreaming = True
        self.board.start_stream()
        print(f"[BrainBoard] Succesfully Started Streaming")

    def stop(self):
        self.board.stop_stream()
        self.data = self.board.get_board_data()
        self.isStreaming = False
        print(f"[BrainBoard] Succesfully Stopped Streaming")
        print(f"[BrainBoard:Data] {self.data}")

    def get_data(self):
        return self.data
    
    def get_id(self) -> int:
        return self.board.board_id
    
    def get_channels(self):
        return BoardShim.get_eeg_channels(self.board.board_id)
    
    def save_data(self) -> str:
        board_type = str(self.get_board_type())
        filepath = get_timestamp()+f'_{board_type}.csv'
        print(f'Saved at {self.save_dir}')
        DataFilter.write_file(self.data, os.path.join(self.save_dir, filepath), 'w')  # use 'a' for append mode
        return filepath

    def release(self):
        self.board.release_session()

def compose_device_status(message:str, data:str="") -> dict:
    if data == "": 
        return message
    else:
        return {"message": message, "data": data}
    
def get_timestamp() -> str:
    timestamp = datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')   
    return timestamp