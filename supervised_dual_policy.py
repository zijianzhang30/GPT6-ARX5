#!/usr/bin/env python3
"""Attended, coordinated two-R5 GPT-Policy host using the existing workers."""
import argparse
import json
from pathlib import Path
import queue
import re
import threading
from types import SimpleNamespace
import uuid

from policy_adapter import ROOT, state_blockers
from policy_runner import new_agent, upstream_config
from r5_cartesian import CartesianBackend, profile_issues
from r5_dual_policy import ARMS, DualCartesianBackend, DualSupervisor
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5DualCameras, run_r5_policy
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from supervised_policy import (DeadlineAgent, check_tracking_contract, prepare_hold,
                               open_empty_gripper, queued_operator_command, wait_for_operator_start)
from visual_control import ArmWorkbenchClient


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supported-supervision', action='store_true')
    parser.add_argument('--wait-for-start', action='store_true')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--paired-client')
    adoption = parser.add_mutually_exclusive_group()
    adoption.add_argument('--adopt-held-from-pid', type=int,
                        help='Replace an idle fast_reset_closed helper without releasing hold')
    adoption.add_argument('--adopt-reset-from-pid', type=int,
                          help='Replace a completed held_dual_reset host without releasing hold')
    parser.add_argument('--left-profile', type=Path, default=ROOT/'r5_left_image_grasp_20260927_profile.json')
    parser.add_argument('--right-profile', type=Path, default=ROOT/'r5_right_image_grasp_20260927_profile.json')
    parser.add_argument('--input-json', type=Path, default=ROOT/'r5_dual_tennis_cola_20260927_context.json')
    parser.add_argument('--open-empty-grippers', action='store_true')
    parser.add_argument('--max-decisions', type=int, choices=range(1, 21), default=10)
    parser.add_argument('--max-segments', type=int, choices=range(1, 17), default=8)
    parser.add_argument('--auto-renew-budgets', action='store_true')
    args = parser.parse_args(argv)
    profiles = {side: json.loads(getattr(args, side+'_profile').read_text()) for side in ARMS}
    issues = {side: profile_issues(profile, 'both', 'image_grasp') for side, profile in profiles.items()}
    if args.check or any(issues.values()):
        print(json.dumps({'status': 'blocked' if any(issues.values()) else 'configuration_ready',
                          'blockers': issues, 'hardware_accessed': False, 'model_called': False,
                          'collision_checked': False, 'physical_trial_required': True}))
        return 2 if any(issues.values()) else 0
    if not args.supported_supervision:
        parser.error('--supported-supervision is required for an attended dual-arm trial')
    if not args.paired_client or not re.fullmatch(r'dual-policy-[a-f0-9]{32}', args.paired_client):
        parser.error('--paired-client must match the newly reserved workbench coordinator ID')
    from gpt_policy.input.request import resolve_run_input
    from gpt_policy.recording.trace import RunRecorder
    config = upstream_config()
    request = resolve_run_input(None, args.input_json, None, config.model)
    clients = {side: ArmWorkbenchClient(args.url, side) for side in ARMS}
    for client in clients.values():
        client.client = args.paired_client
    overview = clients['left'].request('/api/arms')
    if overview.get('paired_policy_client') != args.paired_client:
        raise ValueError('Workbench is not reserved for this dual-policy coordinator')
    for client in clients.values():
        before = client.state()
        blockers = ([] if (args.adopt_held_from_pid or args.adopt_reset_from_pid) else
                    state_blockers(before, require_gripper_target=False))
        if blockers:
            raise ValueError(client.arm + ': ' + '; '.join(blockers))
        check_tracking_contract(before)
        if before.get('policy_trajectory_protocol') != 1:
            raise ValueError('Both workers must support timed trajectory protocol 1')
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    robots = {side: CartesianBackend(R5PolicyBackend(client, cameras.check), profiles[side],
                                     'both', 'image_grasp') for side, client in clients.items()}
    robot = DualCartesianBackend(robots, cameras.check)
    individual = {side: R5PolicySupervisor(arm) for side, arm in robots.items()}
    supervisor = DualSupervisor(robot, individual)
    handoff = None
    if args.adopt_held_from_pid or args.adopt_reset_from_pid:
        from held_policy_handoff import IdleHoldHandoff, CompletedResetHandoff, held_snapshot
        held_snapshot(robots)
        factory = CompletedResetHandoff if args.adopt_reset_from_pid else IdleHoldHandoff
        handoff = factory(args.adopt_reset_from_pid or args.adopt_held_from_pid, args.paired_client, args.url)
    directory = ROOT/'analysis'/('dual-policy-'+uuid.uuid4().hex[:12])
    recorder = RunRecorder(directory, {'model': config.model, 'arms': list(ARMS),
                           'instruction': request.instruction, 'collision_checked': False,
                           'physical_success_verified': False, 'scope': 'attended_dual_image_grasp'})
    recorder.write('input_manifest', request.record())
    recorder.write('calibration_profiles', {'profiles': profiles})
    commands = queue.Queue()
    agent, status, error = None, 'failed', None

    def read_commands():
        import sys
        for line in sys.stdin:
            commands.put(line.strip())
        commands.put('stop')

    print(json.dumps({'status': 'preparing_both_arms', 'directory': str(directory),
                      'model': config.model}), flush=True)
    try:
        cameras.start()
        for side in ARMS:
            if handoff is None:
                prepare_hold(clients[side], cameras,
                             lambda kind, data, side=side: recorder.write(kind, {'arm': side, **data}),
                             enable_gripper_drift_raw=.05)
            individual[side].start()
            print(json.dumps({'status': 'arm_holding', 'arm': side}), flush=True)
        if handoff is not None:
            adopted = handoff.transfer(robots, individual)
            recorder.write('powered_hold_adopted', adopted)
            print(json.dumps({'status': 'powered_hold_adopted', **adopted}), flush=True)
            handoff.close()
        supervisor.start()
        threading.Thread(target=read_commands, daemon=True).start()
        if args.wait_for_start and not wait_for_operator_start(robot, commands, recorder.write):
            status = 'interrupted'
            return 2
        if args.open_empty_grippers:
            for side in ARMS:
                if clients[side].state()['gripper_raw'] >= 4.6:
                    continue
                low = robots[side].backend
                with low.command_lock:
                    low.busy = True
                try:
                    open_empty_gripper(clients[side], cameras, 4.8,
                        lambda kind, data, side=side: recorder.write(kind, {'arm': side, **data}))
                finally:
                    with low.command_lock:
                        low.busy = False
            robot.renew_session()
        runtime = SimpleNamespace(max_decisions=args.max_decisions, interface='can0',
                                  right_interface='can1', camera_mode='both', policy_interface='cartesian',
                                  auto_renew_budgets=args.auto_renew_budgets)
        agent = new_agent(config)
        started, segment = False, 1
        while True:
            recorder.segment = segment
            status = run_r5_policy(runtime, request, robot, cameras, DeadlineAgent(agent, supervisor),
                                   recorder, supervisor=supervisor, start_agent=not started)
            started = True
            print(json.dumps({'status': status, 'segment': segment,
                              'control': 'both_holding_for_operator', 'grasp_verified': False}), flush=True)
            command = queued_operator_command(commands)
            if command == 'stop':
                break
            auto = (args.auto_renew_budgets and segment < args.max_segments and status in (
                'budget_exhausted', 'motion_budget_boundary', 'gripper_budget_boundary'))
            if not auto and command != 'continue':
                while True:
                    supervisor.check()
                    try:
                        command = commands.get(timeout=.1)
                    except queue.Empty:
                        continue
                    if command in ('continue', 'stop'):
                        break
                if command == 'stop':
                    break
            renewal = robot.renew_session()
            segment += 1
            recorder.write('session_budget_renewed', {**renewal, 'segment': segment})
    except KeyboardInterrupt:
        status = 'interrupted'
    except Exception as exc:
        status, error = 'failed', type(exc).__name__
        recorder.write('host_error', {'detail': str(exc), 'error_type': error,
            'arm_feedback': {side: arm.last_execution_feedback for side, arm in robots.items()}})
        print(json.dumps({'status': status, 'error': str(exc)}), flush=True)
    finally:
        if handoff is not None:
            handoff.close()
        supervisor.close()
        for side, client in clients.items():
            try:
                state = client.state()
                if state.get('enabled') and state.get('owner') == client.client:
                    client.command('stop')
            except Exception as exc:
                recorder.write('cleanup_error', {'arm': side, 'error': str(exc)})
                status, error = 'failed', 'CleanupError'
        cameras.close()
        if agent:
            agent.close()
        destination = recorder.close(status, error)
        print(json.dumps({'status': status, 'directory': str(destination), 'grasp_verified': False}), flush=True)
    return 0 if status in ('completed', 'give_up', 'budget_exhausted') else 2


if __name__ == '__main__':
    raise SystemExit(main())
