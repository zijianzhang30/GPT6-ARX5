#!/usr/bin/env python3
"""Bounded passive CAN capture; never constructs the SDK or sends frames."""
import argparse
import json
import math
import socket
import struct
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='can0')
    parser.add_argument('--seconds', type=float, default=20)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 30:
        parser.error('--seconds must be in (0, 30]')
    with socket.socket(socket.PF_CAN, socket.SOCK_RAW, socket.CAN_RAW) as bus:
        bus.bind((args.channel,))
        bus.settimeout(.2)
        with args.output.open('x') as stream:
            start = time.monotonic()
            count = 0
            stream.write(json.dumps({'event': 'capture_started', 'at_s': time.time(),
                                     'monotonic_s': start, 'channel': args.channel})+'\n')
            print('Passive CAN capture ready: '+str(args.output), flush=True)
            while time.monotonic()-start < args.seconds and count < 200000:
                try:
                    data, ancillary, flags, address = bus.recvmsg(16)
                except socket.timeout:
                    continue
                if len(data) != 16 or flags & socket.MSG_TRUNC:
                    continue
                can_id, length, payload = struct.unpack('=IB3x8s', data)
                stream.write(json.dumps({'monotonic_s': time.monotonic(),
                                         'can_id': can_id, 'length': length,
                                         'local_tx': bool(flags & socket.MSG_DONTROUTE),
                                         'payload': payload[:length].hex()})+'\n')
                count += 1
            stream.write(json.dumps({'event': 'capture_finished', 'frames': count,
                                     'monotonic_s': time.monotonic()})+'\n')
    print(json.dumps({'frames': count, 'output': str(args.output)}))


if __name__ == '__main__':
    main()
