#!/usr/bin/env python3
"""Restore an attended paired hold and close both R5 grippers.

This keeps the measured joint pose while re-enabling the existing supervised
workers; it does not home or reconnect either arm. The caller must inspect the
physical workspace and keep both arms attended until the script is stopped.
"""
import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

ROOT = '/home/tuojing/arx_r5_control'
sys.path.insert(0, ROOT)

from visual_control import ArmWorkbenchClient
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from r5_policy_backend import R5PolicyBackend
from supervised_policy import prepare_hold

parser = argparse.ArgumentParser()
parser.add_argument('--url', default='http://127.0.0.1:8768')
parser.add_argument('--paired-client', required=True)
parser.add_argument('--closed-raw', type=float, default=0.23275337219238282)
args = parser.parse_args()
URL, OWNER, CLOSED = args.url, args.paired_client, args.closed_raw
if not 0 <= CLOSED <= 5:
    raise SystemExit('--closed-raw must be within 0..5')

clients = {side: ArmWorkbenchClient(URL, side) for side in ('left', 'right')}
for client in clients.values():
    client.client = OWNER
cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
robots = {side: R5PolicyBackend(clients[side], cameras.check)
          for side in ('left', 'right')}
supervisors = {side: R5PolicySupervisor(robots[side]) for side in ('left', 'right')}

def close_one(side):
    robot = robots[side]
    count = 0
    while True:
        state = robot.state()
        raw = state['raw_state']
        current = float(raw['gripper_target_raw'])
        if current <= CLOSED + 0.01:
            return {'side': side, 'steps': count, 'state': clients[side].state()}
        target = max(CLOSED, current - 1.0)
        result = robot.execute('set_gripper', {
            'observation_id': state['observation_id'],
            'gripper_raw': target,
            'note': 'Fast operator reset: close gripper while holding reset pose',
        })
        count += 1
        print(json.dumps({'event': 'gripper_step', 'side': side,
                          'target_raw': target,
                          'measured_raw': result['measured_gripper_raw']},
                         ensure_ascii=False), flush=True)

try:
    cameras.start()
    for side in ('left', 'right'):
        state = prepare_hold(clients[side], cameras,
                             lambda *_args, **_kwargs: None,
                             enable_gripper_drift_raw=.05)
        supervisors[side].start()
        print(json.dumps({'event': 'holding', 'side': side,
                          'joints_deg': state['joints_deg'],
                          'gripper_raw': state['gripper_raw'],
                          'gripper_command_raw': state['gripper_command_raw']},
                         ensure_ascii=False), flush=True)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(close_one, ('left', 'right')))
    print(json.dumps({'event': 'reset_complete', 'closed_raw': CLOSED,
                      'arms': results}, ensure_ascii=False), flush=True)
    print('READY: both arms held at the reset pose with closed grippers; type stop or press Ctrl+C to release.', flush=True)
    stop_requested = threading.Event()
    def read_stop():
        for line in sys.stdin:
            if line.strip().lower() == 'stop':
                stop_requested.set()
                return
    threading.Thread(target=read_stop, daemon=True).start()
    while not stop_requested.is_set():
        for supervisor in supervisors.values():
            supervisor.check()
        time.sleep(.1)
except KeyboardInterrupt:
    pass
finally:
    for supervisor in supervisors.values():
        try:
            supervisor.close()
        except Exception:
            pass
    # Keep the hold alive on normal operation; only an explicit stop/interrupt
    # releases the existing supervised control owner.
    if any(robot.engaged for robot in robots.values()):
        for side, client in clients.items():
            try:
                state = client.state()
                if state.get('enabled') and state.get('owner') == OWNER:
                    client.command('stop')
            except Exception:
                pass
    cameras.close()
