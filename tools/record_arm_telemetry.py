#!/usr/bin/env python3
"""Bounded read-only dual-arm samples for correlation with passive CAN capture."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_control import ArmWorkbenchClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=20.)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or not 0 < args.seconds <= 30:
        parser.error('seconds must be in (0, 30]')
    clients = {s: ArmWorkbenchClient('http://127.0.0.1:8768', s) for s in ('left','right')}
    with args.output.open('x') as stream, ThreadPoolExecutor(max_workers=2) as pool:
        started = time.monotonic()
        print('Read-only telemetry ready: '+str(args.output), flush=True)
        count = 0
        while time.monotonic()-started < args.seconds:
            before = time.monotonic()
            pending = {s: pool.submit(c.state) for s,c in clients.items()}
            row = {'at_s':time.time(),'monotonic_s':before,'arms':{},'errors':{}}
            for side, future in pending.items():
                try: row['arms'][side] = future.result()
                except Exception as exc: row['errors'][side] = type(exc).__name__+': '+str(exc)
            row['finished_monotonic_s'] = time.monotonic()
            stream.write(json.dumps(row)+'\n')
            stream.flush()
            count += 1
            time.sleep(max(0., .05-(time.monotonic()-before)))
    print(json.dumps({'samples':count,'output':str(args.output)}), flush=True)


if __name__ == '__main__':
    main()
