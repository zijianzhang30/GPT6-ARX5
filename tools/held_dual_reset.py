#!/usr/bin/env python3
"""Attended, staged reset from a parked policy without an enable/stop cycle."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from control import ROOT
from dual_return_pose import load_reference_file, return_step_with_renewal, check_goal
from held_policy_handoff import ParkedPolicyHandoff
from r5_cartesian import CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend, DualSupervisor
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import open_empty_gripper
from visual_control import ArmWorkbenchClient


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-pid', type=int, required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--paired-client', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--reference', type=Path, default=ROOT/'dual_return_start_20260927.json')
    args = parser.parse_args()
    reference, profiles = load_reference_file(args.reference)
    clients = {side: ArmWorkbenchClient(args.url, side) for side in ARMS}
    if clients['left'].request('/api/arms').get('paired_policy_client') != args.paired_client:
        raise ValueError('Reserved paired owner mismatch')
    for client in clients.values():
        client.client = args.paired_client
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    robots = {side: CartesianBackend(R5PolicyBackend(client, cameras.check), profiles[side],
                                    'both', 'image_grasp') for side, client in clients.items()}
    individual = {side: R5PolicySupervisor(arm) for side, arm in robots.items()}
    robot = DualCartesianBackend(robots, cameras.check)
    supervisor = DualSupervisor(robot, individual)
    for side in ARMS:
        check_goal(clients[side].state(), reference['arms'][side])
    handoff = ParkedPolicyHandoff(args.from_pid, args.paired_client, args.url, args.run)
    handoff.snapshot(robots)
    args.output.mkdir(exist_ok=True, parents=True)
    commands = queue.Queue()
    lowered = 0
    released = False

    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip())

    with (args.output/'events.jsonl').open('x') as stream:
        def log(event, data):
            stream.write(json.dumps({'at_s': time.time(), 'event': event, **data})+'\n')
            stream.flush()

        def capture(label):
            for name, frame in cameras.snapshot().items():
                (args.output/f'{label}_{name}.jpg').write_bytes(frame.data)
            state = {side: clients[side].state() for side in ARMS}
            (args.output/f'{label}_state.json').write_text(json.dumps(state, indent=2))
            return state

        def opening(side):
            low = robots[side].backend
            with low.command_lock:
                low.busy = True
            try:
                open_empty_gripper(clients[side], cameras, 4.8,
                                   lambda event, data: log(event, {'arm': side, **data}))
            finally:
                with low.command_lock:
                    low.busy = False

        try:
            cameras.start()
            for item in individual.values():
                item.start()
            log('powered_hold_adopted', handoff.transfer(robots, individual))
            handoff.close()
            supervisor.start()
            threading.Thread(target=read_commands, daemon=True).start()
            capture('adopted')
            print('READY: lower-left (6 mm), release-supported, return, stop. Await visual review between stages.', flush=True)
            while True:
                supervisor.check()
                try:
                    command = commands.get(timeout=.1)
                except queue.Empty:
                    continue
                if command == 'stop':
                    break
                if command == 'lower-left' and not released and lowered < 3:
                    state = robot.state()
                    pose = state['arms']['left']['tcp_command_xyzquat'][:]
                    pose[2] -= .006
                    result = robot.execute('move_to', {'target': {
                        'left': {'pose_xyzquat': pose}, 'right': None},
                        'note': 'Operator reset: lower retained tennis ball 6 mm toward its support'})
                    lowered += 1
                    log('lower_left', result)
                    capture(f'lower_{lowered}')
                    print(json.dumps({'lowered_steps': lowered}), flush=True)
                elif command == 'release-supported' and not released:
                    # The caller confirms support/clearance in fresh images before
                    # issuing this command. No automatic contact inference here.
                    for side in ARMS:
                        opening(side)
                    released = True
                    robot.renew_session()
                    capture('released')
                    print('RELEASED: inspect ball support and both return paths before return.', flush=True)
                elif command == 'return' and released:
                    for index in range(64):
                        result = return_step_with_renewal(robot, reference, log)
                        log('return_step', {'index': index, **result})
                        print(json.dumps({'return_step': index, 'at_reference': result['at_reference']}), flush=True)
                        if result['at_reference']:
                            break
                    else:
                        raise RuntimeError('Return did not converge within 64 bounded steps')
                    robot.renew_session()
                    for side in ARMS:
                        low = robots[side].backend
                        closed = profiles[side]['gripper']['command_closed_raw']
                        while True:
                            state = low.state()
                            current = state['raw_state']['gripper_command_raw']
                            if current <= closed + .01:
                                break
                            result = low.execute('set_gripper', {
                                'observation_id': state['observation_id'],
                                'gripper_raw': max(closed, current-1.),
                                'note': 'Operator reset: close empty gripper at initial pose'})
                            log('close_empty_gripper', {'arm': side, **result})
                    final = capture('reset_complete')
                    print(json.dumps({'reset_complete': True, 'max_error_deg': {
                        side: max(abs(a-b) for a, b in zip(final[side]['joints_deg'],
                            reference['arms'][side]['joints_deg'])) for side in ARMS}}), flush=True)
                    print('HOLDING: reset complete; stop releases powered hold.', flush=True)
                else:
                    print('Command unavailable in this reset stage; holding.', flush=True)
        finally:
            handoff.close()
            supervisor.close()
            cameras.close()


if __name__ == '__main__':
    main()
