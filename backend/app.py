from flask import Flask, jsonify, request
from flask_cors import CORS
import serial.tools.list_ports
from streaming import (
    BrainBoard, compose_response,
    BOARD_ID_MAP, SERIAL_PORT_BOARDS, BLE_BOARDS
)
import traceback
import os
import sys

app = Flask(__name__)
CORS(app)

if getattr(sys, 'frozen', False):
    # Running as a PyInstaller frozen executable
    filedir = os.path.dirname(sys.executable)
else:
    filedir = os.path.dirname(os.path.realpath(__file__))
root_dir = os.path.dirname(filedir)
save_dir = os.path.join(root_dir, 'save_data')

CURRENT_BOARD: BrainBoard = BrainBoard(save_dir=save_dir)
BANNER_MESSAGE: str = "Welcome to BDR! Select a device and press Start."


# --------------------------------------------------------------------------- #
#  Device discovery
# --------------------------------------------------------------------------- #

@app.route('/devices', methods=['GET'])
def get_devices():
    """
    Return available devices: known BrainFlow boards + detected serial ports.
    Each entry has: id (board_id), label, type, serial_port (if applicable),
    and requires_serial flag.
    """
    devices = []

    # 1. Always offer the synthetic board for testing
    devices.append({
        "id": "-1",
        "label": "Synthetic (Test Board)",
        "type": "synthetic",
        "requires_serial": False,
    })

    # 2. Detect serial ports and pair with known serial-based boards
    try:
        ports = serial.tools.list_ports.comports()
        for port in ports:
            devices.append({
                "id": f"serial:{port.device}",
                "label": f"Serial: {port.description}",
                "type": "serial_port",
                "serial_port": port.device,
                "requires_serial": False,  # already has port
            })
    except Exception as e:
        print(f"[Devices] Error scanning serial ports: {e}")

    # 3. Add known BrainFlow boards
    for board_id, name in BOARD_ID_MAP.items():
        if board_id == -1:
            continue  # already added synthetic
        requires_serial = board_id in SERIAL_PORT_BOARDS
        devices.append({
            "id": str(board_id),
            "label": name,
            "type": "ble" if board_id in BLE_BOARDS else "serial",
            "requires_serial": requires_serial,
        })

    return jsonify(devices)


# Keep the old endpoint for backwards compatibility
@app.route('/serial-devices', methods=['GET'])
def get_serial_devices():
    return get_devices()


# --------------------------------------------------------------------------- #
#  Board lifecycle: connect / start / stop / disconnect
# --------------------------------------------------------------------------- #

@app.route('/connect-device', methods=['POST'])
def connect_device():
    """
    Set up the board session without starting the stream.
    Expects JSON: { board_id: int, serial_port?: str, mac_address?: str }
    """
    global CURRENT_BOARD
    try:
        body = request.get_json() or {}
        board_id = int(body.get('board_id', -1))
        serial_port = body.get('serial_port', None)
        mac_address = body.get('mac_address', None)

        CURRENT_BOARD.setup(
            board_id=board_id,
            serial_port=serial_port, # type: ignore
            mac_address=mac_address, # type: ignore
        )

        info = CURRENT_BOARD.get_board_info()
        local_update_banner_message(
            f"Connected to {CURRENT_BOARD.get_board_type()}. Press Start to begin recording."
        )
        return jsonify(compose_response(
            f"Connected to {CURRENT_BOARD.get_board_type()}",
            data=info
        ))

    except Exception as e:
        traceback.print_exc()
        return jsonify(compose_response(f"Failed to connect: {str(e)}", success=False)), 500


@app.route('/disconnect-device', methods=['POST'])
def disconnect_device():
    """Release the board session."""
    global CURRENT_BOARD
    try:
        if CURRENT_BOARD.isSetup:
            CURRENT_BOARD.release()
            local_update_banner_message("Device disconnected.")
            return jsonify(compose_response("Device disconnected."))
        else:
            return jsonify(compose_response("No device connected.", success=False)), 400
    except Exception as e:
        traceback.print_exc()
        return jsonify(compose_response(f"Error disconnecting: {str(e)}", success=False)), 500


@app.route('/start-device', methods=['POST'])
def start_device_stream():
    """
    Start streaming data from the board.
    If not yet set up, attempt setup from the JSON body (backwards compatible).
    """
    global CURRENT_BOARD
    try:
        # If not set up yet, try to set up from request body
        if not CURRENT_BOARD.isSetup:
            body = request.get_json() or {}
            board_id = int(body.get('board_id', -1))
            serial_port = body.get('serial_port', None)
            CURRENT_BOARD.setup(board_id=board_id, serial_port=serial_port) # type: ignore

        CURRENT_BOARD.start()
        local_update_banner_message(
            f"Recording from {CURRENT_BOARD.get_board_type()}..."
        )
        return jsonify(compose_response(
            "Successfully started streaming.",
            data=CURRENT_BOARD.get_status()
        ))
    except Exception as e:
        traceback.print_exc()
        return jsonify(compose_response(f"Failed to start: {str(e)}", success=False)), 500


@app.route('/stop-device', methods=['POST'])
def stop_device_stream():
    """Stop the data stream and save recorded data."""
    global CURRENT_BOARD
    try:
        if not CURRENT_BOARD.isSetup:
            return jsonify(compose_response("No board connected.", success=False)), 400

        if not CURRENT_BOARD.isStreaming:
            return jsonify(compose_response("Board is not streaming.", success=False)), 400

        CURRENT_BOARD.stop()

        # Save data
        filename = CURRENT_BOARD.save_data()
        local_update_banner_message(f"Recording saved: {filename}")

        return jsonify(compose_response(
            "Stopped streaming and saved data.",
            data={
                "filename": filename,
                "status": CURRENT_BOARD.get_status(),
            }
        ))
    except Exception as e:
        traceback.print_exc()
        return jsonify(compose_response(f"Error stopping: {str(e)}", success=False)), 500


# --------------------------------------------------------------------------- #
#  Board status
# --------------------------------------------------------------------------- #

@app.route('/board-status', methods=['GET'])
def get_board_status():
    """Return the current board status."""
    global CURRENT_BOARD
    return jsonify(compose_response("OK", data=CURRENT_BOARD.get_status()))


@app.route('/board-info', methods=['GET'])
def get_board_info():
    """Return detailed board information (channels, sampling rate, etc.)."""
    global CURRENT_BOARD
    if not CURRENT_BOARD.isSetup:
        return jsonify(compose_response("No board connected.", data={}, success=False)), 400
    return jsonify(compose_response("OK", data=CURRENT_BOARD.get_board_info()))


# --------------------------------------------------------------------------- #
#  UDP streaming
# --------------------------------------------------------------------------- #

@app.route('/udp/configure', methods=['POST'])
def configure_udp():
    """
    Configure UDP streaming target.
    Expects JSON: { ip: str, port: int }
    """
    global CURRENT_BOARD
    try:
        body = request.get_json() or {}
        ip = body.get('ip', '127.0.0.1')
        port = int(body.get('port', 12345))
        CURRENT_BOARD.udp_streamer.configure(ip, port)
        return jsonify(compose_response(
            f"UDP configured: {ip}:{port}",
            data=CURRENT_BOARD.udp_streamer.get_status()
        ))
    except Exception as e:
        return jsonify(compose_response(f"Error: {str(e)}", success=False)), 500


@app.route('/udp/start', methods=['POST'])
def start_udp():
    """Start UDP streaming. Board must be streaming first."""
    global CURRENT_BOARD
    try:
        if not CURRENT_BOARD.isStreaming:
            return jsonify(compose_response(
                "Board must be streaming before starting UDP.", success=False
            )), 400

        CURRENT_BOARD.udp_streamer.start(CURRENT_BOARD)
        local_update_banner_message(
            f"UDP streaming to {CURRENT_BOARD.udp_streamer.target_ip}:"
            f"{CURRENT_BOARD.udp_streamer.target_port}"
        )
        return jsonify(compose_response(
            "UDP streaming started.",
            data=CURRENT_BOARD.udp_streamer.get_status()
        ))
    except Exception as e:
        return jsonify(compose_response(f"Error: {str(e)}", success=False)), 500


@app.route('/udp/stop', methods=['POST'])
def stop_udp():
    """Stop UDP streaming."""
    global CURRENT_BOARD
    try:
        CURRENT_BOARD.udp_streamer.stop()
        local_update_banner_message("UDP streaming stopped.")
        return jsonify(compose_response(
            "UDP streaming stopped.",
            data=CURRENT_BOARD.udp_streamer.get_status()
        ))
    except Exception as e:
        return jsonify(compose_response(f"Error: {str(e)}", success=False)), 500


@app.route('/udp/status', methods=['GET'])
def udp_status():
    """Get UDP streaming status."""
    global CURRENT_BOARD
    return jsonify(compose_response("OK", data=CURRENT_BOARD.udp_streamer.get_status()))


# --------------------------------------------------------------------------- #
#  Banner message
# --------------------------------------------------------------------------- #

@app.route('/banner-message', methods=['GET'])
def get_banner_message():
    global BANNER_MESSAGE
    return jsonify({'message': BANNER_MESSAGE})


@app.route('/banner-message', methods=['POST'])
def update_banner_message():
    global BANNER_MESSAGE
    body = request.get_json()
    if body and 'message' in body:
        BANNER_MESSAGE = body['message']
        return jsonify({'status': 'Message updated', 'new_message': BANNER_MESSAGE})
    return jsonify({'error': 'No message provided'}), 400


def local_update_banner_message(message: str) -> None:
    global BANNER_MESSAGE
    BANNER_MESSAGE = message


# --------------------------------------------------------------------------- #
#  Entry point
# --------------------------------------------------------------------------- #

if __name__ == '__main__':
    os.makedirs(save_dir, exist_ok=True)
    app.run(port=5000, debug=False, use_reloader=False)