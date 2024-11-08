from flask import Flask, jsonify, request
from flask_cors import CORS
import serial.tools.list_ports
from streaming import BrainBoard, compose_device_status
import numpy as np
import pandas as pd
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

filedir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(filedir)
save_dir = os.path.join(root_dir, 'save_data')

CURRENT_BOARD: BrainBoard = BrainBoard(save_dir=save_dir)
BANNER_MESSAGE:str        = "Welcome to BDR!"

@app.route('/serial-devices', methods=['GET'])
def get_serial_devices():
    global CURRENT_BOARD
    ports = serial.tools.list_ports.comports()
    devices = [{"id": port.device, "label": port.description} for port in ports]
    devices = [{"id": "-1", "label":"Synthetic"}]
    return jsonify(devices)

@app.route('/start-device', methods=['POST'])
def start_device_stream():
    global CURRENT_BOARD
    try:
        if not CURRENT_BOARD.isSetup:
            CURRENT_BOARD.setup(boardID=-1)
        CURRENT_BOARD.start()
        local_update_banner_message(message="Successfully started streaming")
    except:
        raise Exception("Failed to Start Device")
    return compose_device_status(message="Successfully Started Device")

@app.route('/stop-device', methods=['POST'])
def stop_device_stream():
    global CURRENT_BOARD
    if not CURRENT_BOARD.isSetup:
        return compose_device_status(message="No board to stop!")
    else:
        if CURRENT_BOARD.isStreaming:
            CURRENT_BOARD.stop()

            save_filepath = CURRENT_BOARD.save_data()
            local_update_banner_message(message=f"Successfully stopped steam. Data saved at: {save_filepath}")
        else:
            return compose_device_status(message="Board was already stopped")
    return compose_device_status(message="Successfully Stopped Device")

@app.route('/banner-message', methods=['GET'])
def get_banner_message():
    global BANNER_MESSAGE
    return jsonify({'message': BANNER_MESSAGE})

def local_update_banner_message(message) -> None:
    global BANNER_MESSAGE
    BANNER_MESSAGE = message

# @app.route('/banner-message', methods=['POST'])
# def update_banner_message(message):
#     global BANNER_MESSAGE
#     BANNER_MESSAGE = message
#     return jsonify({'status': 'Message updated', 'new_message': BANNER_MESSAGE})

@app.route('/banner-message', methods=['POST'])
def update_banner_message():
    global BANNER_MESSAGE
    message = request.get_json()
    if message and 'message' in message:
        BANNER_MESSAGE = message['message']  # Extract the actual string from the JSON object
        return jsonify({'status': 'Message updated', 'new_message': BANNER_MESSAGE})
    else:
        return jsonify({'error': 'No message provided'}), 400

if __name__ == '__main__':
    app.run(port=5000)
