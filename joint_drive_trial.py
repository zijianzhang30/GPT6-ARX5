#!/usr/bin/env python3
"""Attended, one-arm joint commissioning through explicit dual-workbench routes."""
import argparse
import json
import math
from pathlib import Path
import queue
import sys
import threading
import time
import uuid

from motion_safety import vector
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5Cameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import prepare_hold, check_tracking_contract, close_host
from visual_control import ArmWorkbenchClient as ArmClient


def trial_targets(reference, step_deg=2., joints=None):
    if not vector(reference):
        raise ValueError('Six finite initial joint commands required')
    joints = list(range(1, 7)) if joints is None else list(joints)
    if step_deg not in (2., 3.) or not joints or len(set(joints)) != len(joints) or any(
            type(joint) is not int or not 1 <= joint <= 6 for joint in joints):
        raise ValueError('Use distinct joints 1..6 and a 2 or 3 degree test step')
    for number in joints:
        joint = number - 1
        target = list(reference)
        target[joint] += step_deg
        yield joint, 'out', target
        yield joint, 'return', list(reference)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=('left', 'right'), required=True)
    parser.add_argument('--supported-supervision', action='store_true', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--step-deg', type=float, choices=(2., 3.), default=2.)
    parser.add_argument('--joints', type=int, nargs='+', choices=range(1, 7))
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent/'analysis'/('joint-drive-'+args.arm+'-'+uuid.uuid4().hex[:10])
    directory.mkdir()
    client = ArmClient(args.url, args.arm)
    cameras = SupervisedCameras(R5Cameras(client, camera_mode='both'))
    robot = R5PolicyBackend(client, cameras.check)
    supervisor = R5PolicySupervisor(robot)
    commands = queue.Queue()
    completed = []
    status = 'failed'
    with (directory/'events.jsonl').open('x') as stream:
        def log(event, payload):
            stream.write(json.dumps({'event': event, 'at_s': time.time(), **payload}, allow_nan=False)+'\n')
            stream.flush()

        def capture(label):
            for name, frame in cameras.snapshot().items():
                (directory/f'{label}-{name}.jpg').write_bytes(frame.data)

        try:
            state = client.state()
            check_tracking_contract(state)
            if state.get('enabled') or state.get('owner'):
                raise ValueError('An existing controller must release control before this trial')
            cameras.start()
            prepare_hold(client, cameras, log, speed=.1)
            supervisor.start()
            reference = robot.state()['raw_state']['command_deg'][:]
            capture('initial')

            def read_commands():
                for line in sys.stdin:
                    commands.put(line.strip())
                commands.put('stop')

            threading.Thread(target=read_commands, daemon=True).start()
            print(json.dumps({'status': 'holding', 'arm': args.arm, 'directory': str(directory),
                              'step_deg': args.step_deg, 'joints': args.joints,
                              'instruction': 'Inspect current views, then next for one out/return step; stop releases hold.'}), flush=True)
            for index, (joint, direction, target) in enumerate(trial_targets(reference, args.step_deg, args.joints)):
                while True:
                    supervisor.check()
                    try:
                        command = commands.get(timeout=.05)
                    except queue.Empty:
                        continue
                    if command == 'stop':
                        status = 'interrupted'
                        return 0
                    if command == 'next':
                        break
                    print('Use next or stop.', flush=True)
                capture(f'{index:02d}-before')
                observed = robot.state()
                result = robot.execute('move_joints', {
                    'observation_id': observed['observation_id'],
                    'positions': [math.radians(q) for q in target],
                    'note': f'Attended {args.arm} J{joint+1} {args.step_deg:g}-degree commissioning {direction}'})
                item = {'index': index, 'joint': joint+1, 'direction': direction, **result}
                completed.append(item)
                log('joint_result', item)
                capture(f'{index:02d}-after')
                print(json.dumps({'status': 'step_complete', 'arm': args.arm, 'index': index,
                                  'joint': joint+1, 'direction': direction,
                                  'measured_delta_deg': result['measured_joint_delta_deg'],
                                  'measured_joints_deg': result['measured_joints_deg']}), flush=True)
            status = 'complete'
            return 0
        except Exception as exc:
            log('trial_error', {'type': type(exc).__name__, 'detail': str(exc)})
            print(json.dumps({'status': 'failed', 'detail': str(exc), 'directory': str(directory)}), flush=True)
            return 2
        finally:
            close_host(supervisor, client, cameras, None, log)
            final = client.state()
            result = {'status': status, 'arm': args.arm, 'completed_steps': len(completed),
                      'enabled': final.get('enabled'), 'owner': final.get('owner'),
                      'error_codes': final.get('error_codes'), 'final_state': final}
            (directory/'result.json').write_text(json.dumps(result, indent=2))
            print(json.dumps({k: v for k, v in result.items() if k != 'final_state'}), flush=True)


if __name__ == '__main__':
    raise SystemExit(main())
