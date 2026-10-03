#!/usr/bin/env python3
"""Attended gripper-only control; never connects, homes, or restores joint poses."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import uuid

from gripper_check import JOINT_DRIFT_LIMIT_DEG
from motion_safety import finite, vector, GRIPPER_CLOSE_STEP_RAW, GRIPPER_STEP_RAW
from r5_policy_backend import R5PolicyBackend, R5ExecutionFault
from r5_policy_deployment import R5Cameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import check_tracking_contract, prepare_hold, close_host
from visual_control import WorkbenchClient


class StationaryGripperBackend(R5PolicyBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.arm_reference = None

    def anchor(self):
        self.arm_reference = self._read(holding=True)
        return self.arm_reference

    def _read_locked(self, *, holding=False):
        state = super()._read_locked(holding=holding)
        if self.arm_reference is not None:
            if max(abs(a-b) for a, b in zip(
                    state['command_deg'], self.arm_reference['command_deg'])) > .05:
                raise R5ExecutionFault('Stationary gripper test: arm command changed')
            if max(abs(a-b) for a, b in zip(
                    state['joints_deg'], self.arm_reference['joints_deg'])) > JOINT_DRIFT_LIMIT_DEG:
                raise R5ExecutionFault('Stationary gripper test: arm drift exceeded limit')
        return state

    def execute(self, name, arguments):
        if name != 'set_gripper' or self.arm_reference is None:
            raise ValueError('Only gripper actions after stationary anchoring are allowed')
        return super().execute(name, arguments)

    def execute_trajectory(self, *args, **kwargs):
        raise ValueError('Arm trajectories are disabled in stationary gripper mode')

    def renew_session(self):
        raise ValueError('Stationary test does not re-anchor or renew motion budgets')

    def step(self, command):
        fields = command.split()
        if len(fields) != 2 or fields[0] not in ('close', 'open'):
            raise ValueError('Use close RAW_DELTA or open RAW_DELTA')
        amount = float(fields[1])
        limit = GRIPPER_CLOSE_STEP_RAW if fields[0] == 'close' else GRIPPER_STEP_RAW
        if not finite(amount) or not 0 < amount <= limit:
            raise ValueError(f'Allowed {fields[0]} increment: > 0 and <= {limit} raw')
        state = self.state()
        target = state['raw_state']['gripper_command_raw'] + (
            -amount if fields[0] == 'close' else amount)
        if not 0 <= target <= 5:
            raise ValueError('Gripper target is outside 0..5 raw')
        return self.execute('set_gripper', {'observation_id': state['observation_id'],
            'gripper_raw': target, 'note': 'Operator-requested stationary gripper test: '+command})


def check_reference(state, reference):
    expected = reference.get('measured_joints_deg')
    if not vector(expected) or not vector(state.get('joints_deg')):
        raise ValueError('Reference and current state need six finite joint angles')
    if max(abs(a-b) for a, b in zip(state['joints_deg'], expected)) > JOINT_DRIFT_LIMIT_DEG:
        raise ValueError('Arm moved away from saved reference; no automatic pose restoration')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supported-supervision', action='store_true', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8765')
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    reference = json.loads(args.reference.read_text())
    directory = Path(__file__).resolve().parent/'analysis'/('stationary-gripper-'+uuid.uuid4().hex[:12])
    directory.mkdir()
    client = WorkbenchClient(args.url)
    cameras = SupervisedCameras(R5Cameras(client, camera_mode='both'))
    robot = StationaryGripperBackend(client, cameras.check)
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
            check_reference(initial, reference)
            if initial.get('enabled') or initial.get('owner'):
                raise ValueError('Existing owner must hand off with mechanical support before starting')
            cameras.start()
            prepare_hold(client, cameras, log)
            check_reference(client.state(), reference)
            log('stationary_reference', {'state': robot.anchor(), 'source': str(args.reference)})
            supervisor.start()
            capture('initial')
            print(json.dumps({'status': 'holding_for_gripper_command', 'directory': str(directory),
                              'commands': ['close 0.2', 'open 0.1', 'status', 'stop'],
                              'arm_motion_enabled': False}), flush=True)
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
                if command == 'status':
                    print(json.dumps({'status': 'holding', 'state': robot.state()['raw_state']}), flush=True)
                    continue
                index += 1
                capture(f'{index:03d}-before')
                try:
                    result = robot.step(command)
                except ValueError as exc:
                    log('rejected', {'command': command, 'error': str(exc)})
                    print(json.dumps({'status': 'rejected', 'error': str(exc)}), flush=True)
                    continue
                capture(f'{index:03d}-after')
                log('gripper_result', {'command': command, 'result': result})
                print(json.dumps({'status': 'holding_for_gripper_command', 'result': result}), flush=True)
        except KeyboardInterrupt:
            log('interrupted', {})
        except Exception as exc:
            log('failed', {'error': str(exc)})
            raise
        finally:
            close_host(supervisor, client, cameras, None, log)


if __name__ == '__main__':
    main()
