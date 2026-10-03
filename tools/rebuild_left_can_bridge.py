#!/usr/bin/env python3
"""Rebuild the known idle left CAN bridge; never connect or enable an SDK.

Use --check for a read-only preflight. Execution requires local sudo.
"""
import argparse
import json
import os
from pathlib import Path
import select
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = '/dev/serial/by-id/usb-Openlight_Labs_CANable2_b158aa7_github.com_normaldotcom_canable2.git_208833765931-if00'


def preflight():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for side, channel in (('left', 'can0'), ('right', 'can1')):
        with opener.open(f'http://127.0.0.1:8768/api/arms/{side}/state', timeout=2) as response:
            state = json.load(response)
        if (state.get('simulation') is not False or state.get('channel') != channel
                or state.get('enabled') is not False or state.get('moving') is not False
                or state.get('owner') is not None or state.get('robot_status') == 'initializing'
                or (side == 'left' and state.get('worker_running') is not False)):
            raise RuntimeError(f'{side}: requires disabled, unowned, stationary state; left SDK must be disconnected')
    if not Path(ADAPTER).is_char_device():
        raise RuntimeError('Expected left adapter serial number is missing')
    matches = []
    for proc in Path('/proc').glob('[0-9]*'):
        try:
            argv = proc.joinpath('cmdline').read_bytes().rstrip(b'\0').decode().split('\0')
        except (FileNotFoundError, ProcessLookupError):
            continue
        if any(Path(a).name == 'robot_worker.py' for a in argv) and argv[-1:] == ['can0']:
            raise RuntimeError('A left SDK worker is still running')
        if argv and Path(argv[0]).name == 'slcand':
            exact = argv[1:] == ['-o', '-f', '-s8', ADAPTER, 'can0']
            if ('can0' in argv or ADAPTER in argv) and not exact:
                raise RuntimeError('Unexpected left bridge arguments; nothing changed')
            if exact:
                matches.append((int(proc.name), argv))
    if len(matches) != 1 or not Path('/sys/class/net/can0').exists():
        raise RuntimeError('Expected exactly one existing left bridge and can0')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    pid, argv = preflight()
    print(json.dumps({'left_bridge_pid': pid, 'adapter': ADAPTER,
                      'read_only_check': args.check, 'right_bridge_unchanged': True}), flush=True)
    if args.check:
        return
    if os.geteuid() != 0:
        raise SystemExit('Local administrator authentication required; use sudo. Nothing changed.')
    fd = os.pidfd_open(pid)
    try:
        # Revalidate after opening a stable process handle; never signal a reused PID.
        if preflight() != (pid, argv):
            raise RuntimeError('Left bridge identity changed; nothing changed')
        signal.pidfd_send_signal(fd, signal.SIGTERM)
        poller = select.poll()
        poller.register(fd, select.POLLIN)
        if not poller.poll(3000):
            raise RuntimeError('Left bridge did not exit; no replacement started')
    finally:
        os.close(fd)
    deadline = time.monotonic() + 3
    while Path('/sys/class/net/can0').exists() and time.monotonic() < deadline:
        time.sleep(.1)
    if Path('/sys/class/net/can0').exists():
        raise RuntimeError('can0 remains; no replacement started')
    # Existing recovery script repeats SDK/device/ownership checks before creating can0.
    subprocess.run(['/bin/bash', str(ROOT/'tools/restore_can.sh')], check=True)
    print('Left CAN bridge rebuilt. SDK remains disconnected; no homing or arm enable requested.', flush=True)


if __name__ == '__main__':
    main()
