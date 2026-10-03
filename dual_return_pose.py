#!/usr/bin/env python3
"""Return both R5 arms to a recorded run's first observed joint pose, then hold.

The default is a read-only preview. Execution requires an idle workbench and
the reserved paired owner. This host never connects, homes, or calls a model.
"""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time
import uuid

import numpy as np

from control import ROOT
from motion_safety import finite, vector, POLICY_SETTLE_ERROR_DEG
from policy_adapter import state_blockers
from policy_trajectory import PolicyTrajectory
from r5_cartesian import CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend, DualSupervisor
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import prepare_hold, wait_for_operator_start
from visual_control import ArmWorkbenchClient
from gpt_policy.motion.trajectory import retime_path_segment


RETURN_JOINT_DEG = 6.
RETURN_NORM_DEG = 8.25


def load_reference(directory):
    profiles = None
    with (Path(directory)/'events.jsonl').open() as stream:
        for line in stream:
            row = json.loads(line)
            if row.get('event') == 'calibration_profiles':
                profiles = row['profiles']
            if row.get('event') != 'observation':
                continue
            arms = row.get('state', {}).get('arms', {})
            reference = {}
            for side, channel in zip(ARMS, ('can0', 'can1')):
                state = arms.get(side, {}).get('raw_state', {})
                if state.get('channel') != channel or not vector(state.get('joints_deg')):
                    raise ValueError('Recorded start is missing or has a different arm/channel mapping')
                reference[side] = {'channel': channel, 'joints_deg': state['joints_deg']}
            if not isinstance(profiles, dict) or set(profiles) != set(ARMS):
                raise ValueError('Recorded profiles for both arms are required')
            return {'source_run': str(Path(directory).resolve()), 'at_s': row['at_s'],
                    'arms': reference}, profiles
    raise ValueError('No dual-arm observation in the specified run')


def load_reference_file(path):
    data = json.loads(Path(path).read_text())
    reference, profiles = data['reference'], data['profiles']
    if set(reference.get('arms', {})) != set(ARMS) or set(profiles) != set(ARMS):
        raise ValueError('Saved reference must contain both arms and profiles')
    for side, channel in zip(ARMS, ('can0', 'can1')):
        arm = reference['arms'][side]
        if arm.get('channel') != channel or not vector(arm.get('joints_deg')):
            raise ValueError('Saved reference has an invalid arm/channel mapping')
    return reference, profiles


def check_return_contract(state):
    expected = {'settle': 2.5, 'hold': 3., 'trajectory': 3.}
    if state.get('policy_tracking_limits_deg') != expected:
        raise ValueError('Return requires the verified 2.5/3/3 degree tracking contract')
    limits = state.get('policy_step_limits_deg') or {}
    # A fixed small return path fits both deployed and pending larger envelopes.
    for name, minimum in (('joint', RETURN_JOINT_DEG), ('norm', RETURN_NORM_DEG)):
        if not finite(limits.get(name)) or limits[name] < minimum:
            raise ValueError('Service trajectory envelope is too small or unavailable')
    if state.get('policy_trajectory_protocol') != 1:
        raise ValueError('Timed trajectory protocol 1 is required')


def check_goal(state, reference):
    check_return_contract(state)
    goal = reference.get('joints_deg')
    if (state.get('channel') != reference.get('channel') or not vector(goal)
            or not vector(state.get('lower_deg')) or not vector(state.get('upper_deg'))):
        raise ValueError('Return reference does not match the current arm')
    if any(not lo+2 <= q <= hi-2 for q, lo, hi in zip(
            goal, state['lower_deg'], state['upper_deg'])):
        raise ValueError('Saved return pose enters a joint limit margin')


def check_idle_pair(states, reference):
    for side in ARMS:
        check_goal(states[side], reference['arms'][side])
        blockers = state_blockers(states[side], require_gripper_target=False)
        if blockers:
            raise ValueError(side + ': ' + '; '.join(blockers)
                             + '; finish the old controller before starting this host')


def return_plan(state, reference, limits, now):
    check_goal(state, reference)
    start = np.asarray(state['command_deg'], dtype=float)
    measured = state['joints_deg']
    if not vector(start.tolist()) or not vector(measured):
        raise ValueError('Fresh measured and commanded joints are required')
    delta = np.asarray(reference['joints_deg'])-start
    largest = float(np.max(np.abs(delta)))
    measured_error = max(abs(a-b) for a, b in zip(measured, reference['joints_deg']))
    # Renewal can re-anchor an already reached goal to measured feedback. Do
    # not command another tiny correction inside the accepted settle tolerance.
    if largest <= POLICY_SETTLE_ERROR_DEG and measured_error <= POLICY_SETTLE_ERROR_DEG:
        return None
    if largest <= .01:
        if measured_error > POLICY_SETTLE_ERROR_DEG:
            raise ValueError('Return command arrived but measured joints have not settled')
        return None
    scale = min(1., RETURN_JOINT_DEG/largest, RETURN_NORM_DEG/float(np.linalg.norm(delta)))
    fractions = np.linspace(0., 1., 61)
    joints = np.radians(start+fractions[:, None]*scale*delta)
    timing = retime_path_segment(fractions, joints, 0., 0., limits)
    points = np.vstack((joints[1:], joints[-1]))
    times = [*timing.times_s[1:].tolist(), float(timing.times_s[-1]+.1)]
    PolicyTrajectory(start.tolist(), np.degrees(points).tolist(), times,
                     state['lower_deg'], state['upper_deg'], now)
    return {'start_joint_positions_rad': np.radians(start).tolist(),
            'planning_measured_joint_positions_rad': np.radians(measured).tolist(),
            'joint_positions_rad': points, 'relative_times_s': times,
            'result': {'note': 'Operator-requested return to recorded initial joints',
                       'planned_duration_s': times[-1], 'collision_checked': False}}


def next_return_step(robot, reference):
    """Preflight both arms before dispatch; keep gripper targets unchanged."""
    with robot.operation_lock:
        robot.check()
        plans = {}
        for side, arm in robot.robots.items():
            state = arm.backend.state()['raw_state']
            plan = return_plan(state, reference['arms'][side], arm.planner.limits, arm.clock())
            if plan is not None:
                plans[side] = plan
        if not plans:
            return {'at_reference': True, 'arms': {}, 'control_state': 'holding'}
        duration = max(plan['relative_times_s'][-1] for plan in plans.values())
        for side, plan in plans.items():
            scale = duration/plan['relative_times_s'][-1]
            plan['relative_times_s'] = [t*scale for t in plan['relative_times_s']]
            plan['result']['planned_duration_s'] = duration
            robot.robots[side].backend.preview_timed_trajectory(plan)
        callbacks = {side: (lambda barrier, side=side, plan=plan:
            robot.robots[side].backend.execute_trajectory(plan, dispatch_barrier=barrier))
            for side, plan in plans.items()}
        return {'at_reference': False, 'arms': robot._parallel(callbacks),
                'control_state': 'holding', 'collision_checked': False}


def preview(states, reference, robots):
    report = {'reference': reference, 'executed': False, 'collision_checked': False, 'arms': {}}
    for side, state in states.items():
        check_goal(state, reference['arms'][side])
        # Disabled services may not have a held command yet; preview from feedback.
        sample = {**state, 'command_deg': state['joints_deg'][:]}
        steps, duration = 0, 0.
        while True:
            plan = return_plan(sample, reference['arms'][side], robots[side].planner.limits, 0.)
            if plan is None:
                break
            steps += 1
            if steps > 64:
                raise ValueError('Return preview exceeds 64 bounded steps')
            duration += plan['relative_times_s'][-1]
            target = np.degrees(plan['joint_positions_rad'][-1]).tolist()
            sample = {**sample, 'joints_deg': target, 'command_deg': target}
        report['arms'][side] = {'current_joints_deg': state['joints_deg'],
            'target_joints_deg': reference['arms'][side]['joints_deg'],
            'planned_steps': steps, 'playback_seconds_without_settling': duration,
            'enabled': state.get('enabled'), 'owner': state.get('owner')}
    return report


def return_step_with_renewal(robot, reference, log):
    # Renew at a finite budget boundary while both arms still hold.
    try:
        return next_return_step(robot, reference)
    except ValueError as exc:
        if not any(s in str(exc) for s in ('session envelope', 'session joint travel budget',
                                         'Session proposal count exhausted')):
            raise
        log('session_budget_renewed', robot.renew_session())
        return next_return_step(robot, reference)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--run', type=Path, help='Recorded dual-policy run directory')
    source.add_argument('--reference', type=Path, help='Saved reference and profiles JSON')
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--supported-supervision', action='store_true')
    parser.add_argument('--paired-client')
    args = parser.parse_args(argv)
    reference, profiles = (load_reference(args.run) if args.run else load_reference_file(args.reference))
    clients = {side: ArmWorkbenchClient(args.url, side) for side in ARMS}
    if args.execute:
        if not args.supported_supervision or not args.paired_client:
            parser.error('Execution requires --supported-supervision and --paired-client')
        overview = clients['left'].request('/api/arms')
        if overview.get('paired_policy_client') != args.paired_client:
            raise ValueError('Return host must match the reserved paired owner')
    for client in clients.values():
        client.client = args.paired_client or 'return-preview'
    states = {side: client.state() for side, client in clients.items()}
    # Reject an occupied controller before any cleanup can touch its ownership.
    if args.execute:
        check_idle_pair(states, reference)
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    robots = {side: CartesianBackend(R5PolicyBackend(client, cameras.check), profiles[side],
                                     'both', 'image_grasp') for side, client in clients.items()}
    print(json.dumps(preview(states, reference, robots)), flush=True)
    if not args.execute:
        return 0
    robot = DualCartesianBackend(robots, cameras.check)
    individual = {side: R5PolicySupervisor(arm) for side, arm in robots.items()}
    supervisor = DualSupervisor(robot, individual)
    directory = ROOT/'analysis'/('dual-return-'+uuid.uuid4().hex[:12])
    directory.mkdir()
    (directory/'reference.json').write_text(json.dumps(reference, indent=2))
    commands = queue.Queue()

    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip())
        commands.put('stop')

    with (directory/'events.jsonl').open('x') as stream:
        def log(event, payload):
            stream.write(json.dumps({'at_s': time.time(), 'event': event, **payload})+'\n')
            stream.flush()

        def capture(label):
            for name, frame in cameras.snapshot().items():
                (directory/f'{label}-{name}.jpg').write_bytes(frame.data)

        try:
            cameras.start()
            for side in ARMS:
                prepare_hold(clients[side], cameras,
                             lambda kind, data, side=side: log(kind, {'arm': side, **data}),
                             enable_gripper_drift_raw=.05)
                individual[side].start()
            supervisor.start()
            threading.Thread(target=read_commands, daemon=True).start()
            capture('initial')
            print(json.dumps({'status': 'both_holding', 'directory': str(directory),
                              'instruction': 'Inspect both return paths, then start; stop releases hold.'}), flush=True)
            if not wait_for_operator_start(robot, commands, log):
                return 0
            for index in range(64):
                supervisor.check()
                if not commands.empty() and commands.get_nowait() == 'stop':
                    return 0
                result = return_step_with_renewal(robot, reference, log)
                log('return_step', {'index': index, **result})
                capture(f'{index:03d}-after')
                print(json.dumps({'status': 'at_reference' if result['at_reference'] else 'step_complete',
                                  'index': index, **result}), flush=True)
                if result['at_reference']:
                    break
            else:
                raise ValueError('Return did not converge within 64 bounded steps')
            final = {side: clients[side].state() for side in ARMS}
            (directory/'result.json').write_text(json.dumps({'returned_to_recorded_start': True,
                'state': final, 'reference': reference, 'collision_checked': False}, indent=2))
            print('Both arms remain powered at the recorded start. Use stop only after support/takeover.', flush=True)
            while True:
                supervisor.check()
                try:
                    if commands.get(timeout=.1) == 'stop':
                        break
                except queue.Empty:
                    pass
        except BaseException as exc:
            log('return_error', {'detail': str(exc), 'type': type(exc).__name__})
            raise
        finally:
            supervisor.close()
            for side, client in clients.items():
                try:
                    state = client.state()
                    if state.get('enabled') and state.get('owner') == client.client:
                        client.command('stop')
                except Exception as exc:
                    log('cleanup_error', {'arm': side, 'detail': str(exc)})
            cameras.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
