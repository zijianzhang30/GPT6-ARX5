#!/usr/bin/env python3
"""Attended Cartesian review for one disabled R5; the other arm stays disabled."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time
from jsonschema import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control import ROOT
from held_policy_handoff import SingleReviewHandoff, ObserverPreparationHoldHandoff
from r5_cartesian import CartesianBackend
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras, StationaryCameraGate
from supervised_policy import open_empty_gripper, prepare_hold
from visual_control import ArmWorkbenchClient
from gpt_policy.motion.coordination import TrajectoryIKError


def require_disabled(state):
    if state.get('enabled') is not False or state.get('moving') is not False or state.get('owner') is not None:
        raise ValueError('Expected an unowned, disabled stationary arm')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--arm', choices=('left', 'right'), required=True)
    parser.add_argument('--paired-client', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--adopt-review-from-pid', type=int)
    source.add_argument('--adopt-observer-hold-from-pid', type=int)
    parser.add_argument('--tracking-reserve-deg', type=float, default=0.0,
                        help='Additional command-path margin; runtime protections are unchanged')
    args = parser.parse_args()
    clients = {s: ArmWorkbenchClient(args.url, s) for s in ('left', 'right')}
    if clients['left'].request('/api/arms').get('paired_policy_client') != args.paired_client:
        raise ValueError('Paired owner mismatch')
    for side, client in clients.items():
        if not (args.adopt_review_from_pid or args.adopt_observer_hold_from_pid) or side != args.arm:
            require_disabled(client.state())
        client.client = args.paired_client
    other = 'right' if args.arm == 'left' else 'left'
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    profile = json.loads((ROOT/f'r5_{args.arm}_image_grasp_20260927_profile.json').read_text())
    low = R5PolicyBackend(clients[args.arm], cameras.check)
    camera_gate = StationaryCameraGate(cameras, low)
    low.vision_check = camera_gate.check
    robot = CartesianBackend(low, profile, 'both', 'image_grasp',
                             tracking_reserve_deg=args.tracking_reserve_deg)
    supervisor = R5PolicySupervisor(robot)
    handoff = (ObserverPreparationHoldHandoff(args.adopt_observer_hold_from_pid, args.paired_client,
                    args.url, args.arm, lambda: require_disabled(clients[other].state()))
               if args.adopt_observer_hold_from_pid else
               SingleReviewHandoff(args.adopt_review_from_pid, args.paired_client, args.url, args.arm)
               if args.adopt_review_from_pid else None)
    if handoff:
        handoff.snapshot({args.arm: robot})
    commands = queue.Queue()
    args.output.mkdir(parents=True, exist_ok=True)

    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip())

    with (args.output/'events.jsonl').open('x') as stream:
        def log(event, data):
            stream.write(json.dumps({'at_s': time.time(), 'event': event, **data})+'\n')
            stream.flush()

        def capture():
            stamp = time.time_ns()
            for name, frame in camera_gate.snapshot().items():
                for filename in (f'{stamp}_{name}.jpg', f'current_{name}.jpg'):
                    (args.output/filename).write_bytes(frame.data)
            state = robot.state()
            (args.output/'current_state.json').write_text(json.dumps(state, indent=2))
            log('observation', {'state': state, 'image_stamp': stamp})
            print(json.dumps({'observation': stamp, 'arm': args.arm,
                'tcp': state['tcp_command_xyzquat'],
                'opening': state['gripper_command_normalized'],
                'bounds': state['gripper_next_opening_bounds']}), flush=True)

        try:
            cameras.start()
            require_disabled(clients[other].state())
            if not handoff:
                prepare_hold(clients[args.arm], cameras, log, enable_gripper_drift_raw=.05)
            supervisor.start()
            if handoff:
                log('powered_hold_adopted', handoff.transfer({args.arm: robot}, {args.arm: supervisor}))
                handoff.close()
            log('single_arm_hold', {'arm': args.arm, 'other_arm_disabled': True,
                                    'planning_tracking_reserve_deg': args.tracking_reserve_deg})
            capture()
            threading.Thread(target=read_commands, daemon=True).start()
            print('HOLDING: observe, renew, open-supported, or original single-arm tool JSON. EOF retains hold.', flush=True)
            last_camera_block = None
            while True:
                supervisor.check()
                require_disabled(clients[other].state())
                if camera_gate.blocked_reason != last_camera_block:
                    last_camera_block = camera_gate.blocked_reason
                    log('camera_gate', {'blocked_reason': last_camera_block, 'holding': True})
                    print(json.dumps({'camera_blocked': last_camera_block, 'holding': True}), flush=True)
                try:
                    line = commands.get(timeout=.1)
                except queue.Empty:
                    continue
                try:
                    if line == 'observe':
                        capture()
                        continue
                    camera_gate.require_fresh()
                    if line == 'renew':
                        log('budget_renewed', robot.renew_session())
                    elif line == 'open-supported':
                        low = robot.backend
                        with low.command_lock:
                            low.busy = True
                        try:
                            open_empty_gripper(clients[args.arm], cameras, 4.8, log)
                        finally:
                            with low.command_lock:
                                low.busy = False
                        robot.renew_session()
                    else:
                        command = json.loads(line)
                        if set(command) != {'tool', 'arguments'} or command['tool'] not in ('move_to', 'move_eef_chunk', 'check_path', 'set_gripper'):
                            raise ValueError('Expected an original bounded Cartesian tool')
                        log('request', command)
                        result = robot.execute(command['tool'], command['arguments'])
                        log('result', result)
                        print(json.dumps({'result_recorded': True, 'tool': command['tool']}), flush=True)
                    capture()
                except (ValueError, ValidationError, TrajectoryIKError) as exc:
                    log('rejected', {'reason': str(exc)})
                    print(json.dumps({'rejected': str(exc)}), flush=True)
        except BaseException as exc:
            log('host_error', {'error': str(exc), 'camera_fault': cameras.fault,
                'camera_received_at': cameras.received_at, 'camera_capture_started_at': cameras.capture_started_at,
                'execution_feedback': robot.backend.last_execution_feedback})
            raise
        finally:
            if handoff:
                handoff.close()
            supervisor.close()
            cameras.close()


if __name__ == '__main__':
    main()
