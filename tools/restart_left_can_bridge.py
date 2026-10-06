#!/usr/bin/env python3
"""Restart only the identified, disconnected left CAN bridge; never start SDK.

Default is a read-only preflight. --restart needs administrator authentication.
"""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ADAPTER = '/dev/serial/by-id/usb-Openlight_Labs_CANable2_b158aa7_github.com_normaldotcom_canable2.git_208833765931-if00'
EXPECTED = ['-o', '-f', '-s8', ADAPTER, 'can0']


def argv(pid):
    return [a.decode() for a in (Path('/proc') / str(pid) / 'cmdline').read_bytes().split(b'\0') if a]


def preflight():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8765/api/state', timeout=2) as response:
        state = json.load(response)
    if state.get('enabled') is not False or state.get('owner') or state.get('worker_running') is not False:
        raise RuntimeError('Left controller is active or its state is uncertain; nothing changed')
    if state.get('robot_status') not in ('fault', 'disconnected'):
        raise RuntimeError('This recovery is only for a disconnected/faulted left controller')
    if not Path(ADAPTER).is_char_device():
        raise RuntimeError('Expected left USB adapter is missing')
    matches = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            args = argv(entry.name)
        except (OSError, UnicodeError):
            continue
        if any(Path(a).name == 'robot_worker.py' for a in args) and 'can0' in args:
            raise RuntimeError('Left SDK worker exists; nothing changed')
        if args and Path(args[0]).name == 'slcand' and args[1:] == EXPECTED:
            matches.append(int(entry.name))
    if len(matches) != 1:
        raise RuntimeError(f'Expected exactly one identified left bridge, found {len(matches)}')
    return matches[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restart', action='store_true')
    args = parser.parse_args()
    pid = preflight()
    print(json.dumps({'preflight': 'passed', 'left_bridge_pid': pid,
                      'adapter': ADAPTER, 'sdk_will_be_initialized': False}), flush=True)
    if not args.restart:
        return
    if os.geteuid() != 0:
        raise RuntimeError('Administrator authentication required; nothing changed')
    # Pin process identity and recheck immediately before signalling.
    handle = os.pidfd_open(pid)
    try:
        if preflight() != pid or argv(pid)[1:] != EXPECTED:
            raise RuntimeError('Bridge identity changed; nothing changed')
        right_index = Path('/sys/class/net/can1/ifindex').read_text()
        signal.pidfd_send_signal(handle, signal.SIGTERM)
        print('Requested graceful exit of identified left bridge.', flush=True)
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline and (Path(f'/proc/{pid}').exists() or Path('/sys/class/net/can0').exists()):
            time.sleep(.1)
        if Path(f'/proc/{pid}').exists() or Path('/sys/class/net/can0').exists():
            raise RuntimeError('Old bridge/interface did not exit; no replacement started')
        subprocess.run([str(ROOT / 'tools/restore_can.sh')], check=True, timeout=10)
        if Path('/sys/class/net/can1/ifindex').read_text() != right_index:
            raise RuntimeError('Right interface identity changed unexpectedly; stop and inspect')
        print('Left bridge restart complete. SDK remains disconnected; motor health is not yet verified.', flush=True)
    finally:
        os.close(handle)


if __name__ == '__main__':
    main()
