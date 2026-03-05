"""
UDP Listener — Test script for BDR's UDP streaming feature.

Run this in a separate terminal while BDR is streaming with UDP enabled.
It will print incoming EEG data packets to the console.

Usage:
    python udp_listener.py
    python udp_listener.py --port 12345
    python udp_listener.py --ip 0.0.0.0 --port 12345
"""

import socket
import json
import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="BDR UDP Listener")
    parser.add_argument("--ip", default="127.0.0.1", help="IP to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=12345, help="Port to listen on (default: 12345)")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((args.ip, args.port))

    print(f"[UDP Listener] Listening on {args.ip}:{args.port}")
    print(f"[UDP Listener] Press Ctrl+C to stop\n")

    packet_count = 0
    try:
        while True:
            data, addr = sock.recvfrom(65536)
            packet_count += 1
            try:
                packet = json.loads(data.decode('utf-8'))
                board = packet.get('board_name', 'Unknown')
                n_samples = packet.get('num_samples', 0)
                n_channels = len(packet.get('eeg_data', {}))
                print(f"[#{packet_count}] {board} | {n_channels} ch | {n_samples} samples | from {addr[0]}:{addr[1]}")
            except json.JSONDecodeError:
                print(f"[#{packet_count}] Raw data ({len(data)} bytes) from {addr}")

    except KeyboardInterrupt:
        print(f"\n[UDP Listener] Stopped. Received {packet_count} packets.")
    finally:
        sock.close()


if __name__ == "__main__":
    main()