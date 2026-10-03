#!/usr/bin/env python3
"""Attended, individually reviewed return steps followed by a fixed-arm grasp."""
import argparse
import json
import math
from pathlib import Path
import queue
import sys
import threading
import uuid

from motion_safety import vector
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5Cameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from stationary_gripper_trial import StationaryGripperBackend, check_reference
from supervised_policy import check_tracking_contract, close_host, prepare_hold
from visual_control import WorkbenchClient


def return_target(current, goal):
    if not vector(current) or not vector(goal):
        raise ValueError('Six finite current and goal joint angles are required')
    delta = [b-a for a, b in zip(current, goal)]
    if max(map(abs, delta)) <= 1.0:
        return None
    scale = min(1., 6./max(map(abs, delta)), 8.25/math.hypot(*delta))
    return [a+scale*d for a, d in zip(current, delta)]


class ReturnThenGripBackend(StationaryGripperBackend):
    def __init__(self, *args, reference, **kwargs):
        super().__init__(*args, **kwargs)
        self.reference = reference
        if not vector(reference.get('measured_joints_deg')):
            raise ValueError('Invalid saved pose')

    def execute(self, name, arguments):
        if self.arm_reference is not None:
            return super().execute(name, arguments)
        if name != 'move_joints':
            raise ValueError('Lock the arm at the saved pose before gripper actions')
        return R5PolicyBackend.execute(self, name, arguments)

    def next_step(self):
        if self.arm_reference is not None:
            raise ValueError('Arm is locked for gripper testing')
        state = self.state()
        target = return_target(state['raw_state']['joints_deg'],
                               self.reference['measured_joints_deg'])
        if target is None:
            return {'at_reference': True, 'executed': False}
        return self.execute('move_joints', {
            'positions': [math.radians(q) for q in target],
            'observation_id': state['observation_id'],
            'note': 'Operator-authorized saved-pose return; one visually reviewed step'})

    def lock_arm(self):
        check_reference(self._read(holding=True), self.reference)
        return self.anchor()

    def renew_session(self):
        if self.arm_reference is not None:
            raise ValueError('Cannot renew after locking the arm')
        return R5PolicyBackend.renew_session(self)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supported-supervision', action='store_true', required=True)
    parser.add_argument('--restore-saved-pose', action='store_true', required=True)
    parser.add_argument('--reference', type=Path, required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    directory = Path(__file__).resolve().parent/'analysis'/('return-grip-'+uuid.uuid4().hex[:12])
    directory.mkdir()
    client = WorkbenchClient(args.url)
    cameras = SupervisedCameras(R5Cameras(client, camera_mode='both'))
    robot = ReturnThenGripBackend(client, cameras.check, reference=reference)
    supervisor = R5PolicySupervisor(robot)
    with (directory/'events.jsonl').open('x') as stream:
        def log(event, payload):
            stream.write(json.dumps({'event': event, **payload}, allow_nan=False)+'\n')
            stream.flush()

        def capture(label):
            for name, frame in cameras.snapshot().items():
                (directory/f'{label}-{name}.jpg').write_bytes(frame.data)

        try:
            initial = client.state()
            check_tracking_contract(initial)
            if initial.get('enabled') or initial.get('owner'):
                raise ValueError('An existing controller owns or enables the arm')
            log('authorized_return', {'reference': str(args.reference), 'initial': initial})
            cameras.start()
            prepare_hold(client, cameras, log)
            supervisor.start()
            capture('initial')
            print(json.dumps({'status': 'holding', 'directory': str(directory),
                              'commands': ['next', 'renew', 'lock', 'close 0.2', 'status', 'stop']}), flush=True)
            commands = queue.Queue()

            def read_commands():
                for line in sys.stdin:
                    commands.put(line.strip())
                commands.put('stop')

            threading.Thread(target=read_commands, daemon=True).start()
            index = 0
            while True:
                supervisor.check()
                try:
                    command = commands.get(timeout=.1)
                except queue.Empty:
                    continue
                if command == 'stop':
                    break
                index += 1
                capture(f'{index:03d}-before')
                try:
                    if command == 'next':
                        result = robot.next_step()
                    elif command == 'renew':
                        result = robot.renew_session()
                    elif command == 'lock':
                        result = robot.lock_arm()
                    elif command == 'status':
                        result = robot.state()['raw_state']
                    else:
                        result = robot.step(command)
                except ValueError as exc:
                    log('rejected', {'command': command, 'error': str(exc)})
                    print(json.dumps({'status': 'rejected', 'error': str(exc)}), flush=True)
                    continue
                capture(f'{index:03d}-after')
                log('result', {'command': command, 'result': result})
                print(json.dumps({'status': 'holding', 'index': index, 'result': result}), flush=True)
        except BaseException as exc:
            log('failed', {'error': str(exc), 'type': type(exc).__name__,
                           'execution_feedback': robot.last_execution_feedback})
            raise
        finally:
            close_host(supervisor, client, cameras, None, log)


if __name__ == '__main__':
    main()
