#!/usr/bin/env python3
"""Warm read-only camera routes, then exec review with the original terminal stdin."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_control import ArmWorkbenchClient, WorkbenchClient
from r5_sequential_trial import require_idle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--arm', choices=('left', 'right'),
                        help='Use the existing single-arm host; the other arm stays disabled')
    args, remaining = parser.parse_known_args()
    clients = {side: ArmWorkbenchClient(args.url, side) for side in ('left', 'right')}
    require_idle({side: client.state() for side, client in clients.items()})

    def warm(key):
        client = WorkbenchClient(args.url)
        with client.opener.open(client.base+f'/api/cameras/{key}/frame.jpg', timeout=8) as response:
            response.read()
            return key, response.headers.get('X-Frame-Id')

    with ThreadPoolExecutor(max_workers=3) as pool:
        for _ in range(3):
            print('CAMERA_PREWARM', dict(pool.map(warm, ('external', 'gemini', 'gemini_right'))), flush=True)
    require_idle({side: client.state() for side, client in clients.items()})
    host = str(Path(__file__).with_name('single_policy_review.py' if args.arm else 'held_policy_review.py').resolve())
    mode_args = ['--arm', args.arm] if args.arm else ['--prepare-idle']
    # A file-backed launcher preserves the PTY. A `python - <<...` heredoc does not.
    os.execv(sys.executable, [sys.executable, '-u', host, *mode_args,
                             '--url', args.url, *remaining])


if __name__ == '__main__':
    main()
