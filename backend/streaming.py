from brainflow import BoardShim, BrainFlowInputParams, BoardIds, DataFilter
import numpy as np
import pandas as pd
import datetime
import os
import socket
import threading
import json
import time

# Map board IDs to human-readable names
BOARD_ID_MAP = {
    -1: 'Synthetic',
    0:  'Cyton',
    1:  'OpenBCI 8ch (Ganglion)',
    2:  'OpenBCI 16ch (CytonDaisy)',
    21: 'Muse 2016',
    22: 'Muse 2',
    38: 'Muse S',
    39: 'BrainBit',
    41: 'Notion 1',
    42: 'Notion 2',
    44: 'Crown',
}

# Boards that require a serial port
SERIAL_PORT_BOARDS = {0, 1, 2}

# Boards that require BLE/Bluetooth (no serial port needed)
BLE_BOARDS = {21, 22, 38, 39, 41, 42, 44}


class UDPStreamer:
    """Handles UDP streaming of EEG data to a target address."""

    def __init__(self, target_ip="127.0.0.1", target_port=12345):
        self.target_ip = target_ip
        self.target_port = target_port
        self.socket = None
        self.is_streaming = False
        self._thread = None
        self._stop_event = threading.Event()

    def configure(self, target_ip: str, target_port: int):
        self.target_ip = target_ip
        self.target_port = target_port
        print(f"[UDPStreamer] Configured -> {self.target_ip}:{self.target_port}")

    def start(self, board: 'BrainBoard', sample_rate_hz: int = 10):
        """Start streaming board data over UDP at the given poll rate."""
        if self.is_streaming:
            print("[UDPStreamer] Already streaming")
            return

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._stop_event.clear()
        self.is_streaming = True

        def _stream_loop():
            interval = 1.0 / sample_rate_hz
            while not self._stop_event.is_set():
                try:
                    if board.isStreaming and board.board is not None:
                        # Get latest samples from the ring buffer
                        data = board.board.get_current_board_data(256)
                        if data.size > 0: # type: ignore
                            eeg_channels = BoardShim.get_eeg_channels(board.get_id())
                            timestamp_channel = BoardShim.get_timestamp_channel(board.get_id())

                            packet = {
                                "board_id": board.get_id(),
                                "board_name": board.get_board_type(),
                                "eeg_channels": eeg_channels,
                                "num_samples": data.shape[1], # type: ignore
                                "timestamps": data[timestamp_channel].tolist()[-10:],
                                "eeg_data": {
                                    str(ch): data[ch].tolist()[-10:] # type: ignore
                                    for ch in eeg_channels
                                }
                            }
                            payload = json.dumps(packet).encode('utf-8')
                            self.socket.sendto(payload, (self.target_ip, self.target_port)) # type: ignore
                except Exception as e:
                    print(f"[UDPStreamer] Error: {e}")

                time.sleep(interval)

        self._thread = threading.Thread(target=_stream_loop, daemon=True)
        self._thread.start()
        print(f"[UDPStreamer] Started streaming to {self.target_ip}:{self.target_port}")

    def stop(self):
        """Stop UDP streaming."""
        if not self.is_streaming:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2)
        if self.socket:
            self.socket.close()
            self.socket = None
        self.is_streaming = False
        print("[UDPStreamer] Stopped")

    def get_status(self) -> dict:
        return {
            "is_streaming": self.is_streaming,
            "target_ip": self.target_ip,
            "target_port": self.target_port,
        }


class BrainBoard:
    """Wraps BrainFlow's BoardShim with session management, recording, and UDP streaming."""

    def __init__(self, debug=True, save_dir=''):
        self.isSetup = False
        self.isStreaming = False
        self.debug = debug
        self.save_dir = save_dir
        self.board = None
        self.params = None
        self.data = None
        self._board_id = None
        self.udp_streamer = UDPStreamer()

    def setup(self, board_id: int = BoardIds.SYNTHETIC_BOARD, serial_port: str = None,
              mac_address: str = None, ip_address: str = None, ip_port: int = 0):
        """
        Prepare a BrainFlow session for the given board.
        
        Args:
            board_id: BrainFlow board ID
            serial_port: COM port (e.g. 'COM3' or '/dev/ttyUSB0') for serial boards
            mac_address: Bluetooth MAC address for BLE boards
            ip_address: IP address for WiFi-based boards
            ip_port: IP port for WiFi-based boards
        """
        # Release any existing session first
        if self.isSetup:
            self.release()

        if self.debug:
            BoardShim.enable_dev_board_logger()

        self.params = BrainFlowInputParams()

        if serial_port:
            self.params.serial_port = serial_port
        if mac_address:
            self.params.mac_address = mac_address
        if ip_address:
            self.params.ip_address = ip_address
        if ip_port:
            self.params.ip_port = ip_port

        self._board_id = board_id
        self.board = BoardShim(board_id, self.params)
        self.board.prepare_session()
        self.isSetup = True
        self.data = None
        print(f"[BrainBoard] Successfully set up board: {self.get_board_type()} (ID: {board_id})")

    def start(self):
        """Start the data stream."""
        if not self.isSetup:
            raise RuntimeError("Board is not set up. Call setup() first.")
        if self.isStreaming:
            raise RuntimeError("Board is already streaming.")

        self.board.start_stream()
        self.isStreaming = True
        print(f"[BrainBoard] Started streaming")

    def stop(self):
        """Stop the data stream and retrieve collected data."""
        if not self.isStreaming:
            raise RuntimeError("Board is not currently streaming.")

        # Stop UDP if running
        if self.udp_streamer.is_streaming:
            self.udp_streamer.stop()

        self.board.stop_stream()
        self.data = self.board.get_board_data()
        self.isStreaming = False
        sample_count = self.data.shape[1] if self.data is not None else 0
        print(f"[BrainBoard] Stopped streaming. Collected {sample_count} samples.")

    def get_data(self):
        return self.data

    def get_id(self) -> int:
        return self._board_id if self._board_id is not None else -1

    def get_board_type(self, board_id: int = None) -> str:
        bid = board_id if board_id is not None else self._board_id
        return BOARD_ID_MAP.get(bid, f'Board_{bid}')

    def get_channels(self) -> list:
        if self._board_id is not None:
            return BoardShim.get_eeg_channels(self._board_id)
        return []

    def get_sampling_rate(self) -> int:
        if self._board_id is not None:
            return BoardShim.get_sampling_rate(self._board_id)
        return 0

    def get_board_info(self) -> dict:
        """Get comprehensive info about the current board."""
        if not self.isSetup or self._board_id is None:
            return {}
        try:
            return {
                "board_id": self._board_id,
                "board_name": self.get_board_type(),
                "sampling_rate": self.get_sampling_rate(),
                "eeg_channels": BoardShim.get_eeg_channels(self._board_id),
                "num_eeg_channels": len(BoardShim.get_eeg_channels(self._board_id)),
                "timestamp_channel": BoardShim.get_timestamp_channel(self._board_id),
            }
        except Exception:
            return {
                "board_id": self._board_id,
                "board_name": self.get_board_type(),
            }

    def save_data(self) -> str:
        """Save collected data to CSV. Returns the filename."""
        if self.data is None or self.data.size == 0:
            raise RuntimeError("No data to save.")

        os.makedirs(self.save_dir, exist_ok=True)
        board_type = str(self.get_board_type()).replace(' ', '_')
        filename = f"{get_timestamp()}_{board_type}.csv"
        filepath = os.path.join(self.save_dir, filename)
        DataFilter.write_file(self.data, filepath, 'w')
        print(f"[BrainBoard] Saved data to: {filepath}")
        return filename

    def release(self):
        """Release the BrainFlow session."""
        try:
            if self.udp_streamer.is_streaming:
                self.udp_streamer.stop()
            if self.isStreaming:
                self.board.stop_stream()
                self.isStreaming = False
            if self.board is not None:
                self.board.release_session()
        except Exception as e:
            print(f"[BrainBoard] Error during release: {e}")
        finally:
            self.isSetup = False
            self.board = None
            self._board_id = None
            print("[BrainBoard] Session released")

    def get_status(self) -> dict:
        """Get the full status of the board and UDP streamer."""
        return {
            "is_setup": self.isSetup,
            "is_streaming": self.isStreaming,
            "board_id": self._board_id,
            "board_name": self.get_board_type() if self._board_id is not None else None,
            "sample_count": self.data.shape[1] if self.data is not None else 0,
            "udp": self.udp_streamer.get_status(),
        }


def compose_response(message: str, data: dict = None, success: bool = True) -> dict:
    """Standardized API response format."""
    response = {"success": success, "message": message}
    if data is not None:
        response["data"] = data
    return response


def get_timestamp() -> str:
    return datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')