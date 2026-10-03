#!/usr/bin/env python3
"""One attended, contact-free translation through the original GPT-Policy planner.

This gathers commissioning evidence without claiming a calibrated robot or
starting a model. Default is configuration-only. Execution permits at most one
4 mm translation, holds the gripper, and never modifies the real profile.
"""
import argparse
import json
import math
import queue
import sys
import threading
import time
import uuid
from pathlib import Path

from control import ROOT
from r5_cartesian import CartesianBackend, profile_issues
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5Cameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import close_host, prepare_hold
from visual_control import WorkbenchClient


def validation_target(state, axis, distance_mm):
    if axis not in ('x', 'y', 'z') or not math.isfinite(distance_mm) or not 0 < abs(distance_mm) <= 4:
        raise ValueError('Choose a nonzero translation no larger than 4 mm')
    pose = state['tcp_command_xyzquat'][:]
    pose[('x', 'y', 'z').index(axis)] += distance_mm / 1000
    return {'pose_xyzquat': pose}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', type=Path, default=ROOT/'r5_cartesian_profile.json')
    parser.add_argument('--axis', choices=('x', 'y', 'z'), default='z')
    parser.add_argument('--distance-mm', type=float, default=1.)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--clearance-note', help='Observed clearance and attended support for this specific test')
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    args = parser.parse_args(argv)
    validation_target({'tcp_command_xyzquat': [0., 0., 0., 0., 0., 0., 1.]}, args.axis, args.distance_mm)
    settings = json.loads(args.profile.read_text())
    issues = profile_issues(settings, stage='motion', commissioning=True)
    if issues or not args.execute:
        print(json.dumps({'status': 'blocked' if issues else 'commissioning_configuration_ready',
                          'blockers': issues, 'autonomous_motion_blockers': profile_issues(settings, stage='motion'),
                          'hardware_accessed': False, 'model_called': False}))
        return 2 if issues else 0
    if not args.clearance_note or not args.clearance_note.strip():
        parser.error('--execute requires a specific --clearance-note')

    from gpt_policy.recording.trace import RunRecorder
    directory = ROOT/'analysis'/('cartesian-commission-'+uuid.uuid4().hex[:12])
    recorder = RunRecorder(directory, {'scope': 'one_step_commissioning',
                          'calibration': settings, 'clearance_note': args.clearance_note,
                          'axis': args.axis, 'distance_mm': args.distance_mm,
                          'model_called': False, 'physical_success_verified': False})
    client = WorkbenchClient(args.url)
    source = R5Cameras(client, camera_mode='wrist')
    cameras = SupervisedCameras(source)
    low = R5PolicyBackend(client, cameras.check)
    robot = CartesianBackend(low, settings, stage='motion', commissioning=True)
    supervisor = R5PolicySupervisor(robot)
    status, error = 'failed', None
    print(json.dumps({'status': 'preparing', 'directory': str(directory)}), flush=True)
    try:
        if client.state().get('policy_trajectory_protocol') != 1:
            raise ValueError('Timed trajectory transport is not deployed')
        source.snapshot()
        cameras.start()
        prepare_hold(client, cameras, recorder.write)
        supervisor.start()
        before = robot.state()
        recorder.write('before', before)
        image = cameras.snapshot()['left']
        (directory/'before.jpg').write_bytes(image.data)
        target = validation_target(before, args.axis, args.distance_mm)
        checked = robot.execute('check_path', {'poses': [target], 'note': 'One contact-free commissioning translation'})
        recorder.write('path_check', checked)
        # Refresh the observation after planning; execution always replans.
        before = robot.state()
        target = validation_target(before, args.axis, args.distance_mm)
        result = robot.execute('move_to', {'target': target, 'note': 'One contact-free commissioning translation'})
        recorder.write('execution_result', result)
        after = robot.state()
        recorder.write('after', after)
        image = cameras.snapshot(after=time.time())['left']
        (directory/'after.jpg').write_bytes(image.data)
        status = 'completed'
        print(json.dumps({'status': 'trajectory_executed', 'directory': str(directory),
                          'grasp_verified': False, 'physical_tcp_displacement_verified': False,
                          'instruction': 'Holding for observer; enter stop to end this session.'}), flush=True)
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
    except (Exception, KeyboardInterrupt) as exc:
        error = type(exc).__name__
        recorder.write('commissioning_error', {'type': error, 'detail': str(exc),
                                              'execution_feedback': low.last_execution_feedback})
        print(json.dumps({'status': 'failed', 'error': str(exc), 'directory': str(directory)}), flush=True)
    finally:
        if close_host(supervisor, client, cameras, None, recorder.write):
            status, error = 'failed', 'CleanupError'
        directory = recorder.close(status, error)
        print(json.dumps({'status': status, 'directory': str(directory),
                          'model_called': False, 'calibration_modified': False}), flush=True)
    return 0 if status == 'completed' else 2


if __name__ == '__main__':
    raise SystemExit(main())
