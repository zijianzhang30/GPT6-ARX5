#!/usr/bin/env python3
"""Attended close/open diagnostic using the existing worker and powered hold."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import uuid

from gripper_check import JOINT_DRIFT_LIMIT_DEG
from motion_safety import GRIPPER_CLOSE_STEP_RAW, GRIPPER_STEP_RAW
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5Cameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import check_tracking_contract, close_host, prepare_hold
from visual_control import WorkbenchClient


def run_cycle(robot, capture, log):
    before = robot.state()['raw_state']
    start = before['gripper_command_raw']
    target = start-GRIPPER_CLOSE_STEP_RAW
    if target < 0:
        raise ValueError('Insufficient closing travel for a full 1.0-raw test')
    capture('before')

    def move(goal, label):
        state = robot.state()
        raw = state['raw_state']
        if (max(abs(a-b) for a, b in zip(raw['command_deg'], before['command_deg'])) > .05
                or max(abs(a-b) for a, b in zip(raw['joints_deg'], before['joints_deg'])) > JOINT_DRIFT_LIMIT_DEG):
            raise RuntimeError('Arm moved outside the stationary gripper-test envelope')
        result = robot.execute('set_gripper', {'observation_id': state['observation_id'],
            'gripper_raw': goal, 'note': 'Attended stationary gripper cycle: '+label})
        log('gripper_cycle_step', {'label': label, 'target_raw': goal, 'result': result})
        if (max(abs(a-b) for a, b in zip(result['submitted_joints_deg'], before['command_deg'])) > .05
                or max(abs(a-b) for a, b in zip(result['measured_joints_deg'], before['joints_deg'])) > JOINT_DRIFT_LIMIT_DEG):
            raise RuntimeError('Arm moved during the stationary gripper test')
        capture(label)
        return result

    closed = move(target, 'closed')
    while target < start-1e-9:
        target = min(start, target+GRIPPER_STEP_RAW)
        opened = move(target, f'opening-{round((target-(start-GRIPPER_CLOSE_STEP_RAW))/GRIPPER_STEP_RAW):02d}')
    return {'initial_command_raw': start, 'initial_measured_raw': before['gripper_raw'],
            'closed_measured_raw': closed['measured_gripper_raw'],
            'reopened_measured_raw': opened['measured_gripper_raw'],
            'final_command_raw': opened['submitted_gripper_raw'],
            'arm_target_changed': False, 'grasp_attempted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supported-supervision', action='store_true', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent/'analysis'/('gripper-cycle-'+uuid.uuid4().hex[:12])
    directory.mkdir()
    client = WorkbenchClient(args.url)
    cameras = SupervisedCameras(R5Cameras(client, camera_mode='both'))
    robot = R5PolicyBackend(client, cameras.check)
    supervisor = R5PolicySupervisor(robot)
    with (directory/'events.jsonl').open('x') as stream:
        def log(event, payload):
            stream.write(json.dumps({'event': event, **payload}, allow_nan=False)+'\n')
            stream.flush()

        def capture(label):
            for name, image in cameras.snapshot().items():
                (directory/f'{label}-{name}.jpg').write_bytes(image.data)

        try:
            check_tracking_contract(client.state())
            cameras.start()
            prepare_hold(client, cameras, log)
            supervisor.start()
            print(json.dumps({'status': 'testing_gripper_cycle', 'directory': str(directory)}), flush=True)
            result = run_cycle(robot, capture, log)
            log('cycle_complete', result)
            print(json.dumps({'status': 'holding_for_operator', 'directory': str(directory), **result}), flush=True)
            commands = queue.Queue()
            def read_commands():
                for line in sys.stdin:
                    commands.put(line.strip())
                commands.put('stop')
            threading.Thread(target=read_commands, daemon=True).start()
            while True:
                supervisor.check()
                try:
                    if commands.get(timeout=.1) == 'stop':
                        break
                except queue.Empty:
                    pass
        except BaseException as exc:
            log('test_error', {'error': str(exc), 'type': type(exc).__name__})
            raise
        finally:
            close_host(supervisor, client, cameras, None, log)


if __name__ == '__main__':
    main()
