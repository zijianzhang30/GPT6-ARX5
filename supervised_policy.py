#!/usr/bin/env python3
"""Attended R5 trial using the original GPT-Policy loop and existing HTTP worker."""
import argparse
import json
import queue
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
import uuid

from gripper_check import JOINT_DRIFT_LIMIT_DEG
from policy_adapter import ROOT, state_blockers
from policy_runner import new_agent, upstream_config
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5Cameras, run_r5_policy
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from visual_control import ArmWorkbenchClient, WorkbenchClient, check_state
from motion_safety import (finite, SUPERVISED_SPEED, POLICY_SETTLE_ERROR_DEG,
                           POLICY_HOLD_ERROR_DEG, POLICY_TRACKING_ERROR_DEG,
                           JOINT_STEP_DEG, JOINT_STEP_NORM_DEG,
                           GRIPPER_OPEN_SPEED_MULTIPLIER, EMPTY_GRIPPER_OPEN_STEP_RAW)


def check_tracking_contract(state):
    expected = {'settle': POLICY_SETTLE_ERROR_DEG, 'hold': POLICY_HOLD_ERROR_DEG,
                'trajectory': POLICY_TRACKING_ERROR_DEG}
    if state.get('policy_tracking_limits_deg') != expected:
        raise ValueError('Workbench tracking tolerances differ from policy host; deploy matching service first')
    if state.get('policy_step_limits_deg') != {'joint': JOINT_STEP_DEG, 'norm': JOINT_STEP_NORM_DEG}:
        raise ValueError('Workbench step limits differ from policy host; deploy matching service first')


def prepare_hold(client, cameras, log, *, speed=SUPERVISED_SPEED,
                 enable_gripper_drift_raw=.03,
                 clock=time.monotonic, sleep=time.sleep):
    if not finite(speed) or not 0 < speed <= SUPERVISED_SPEED:
        raise ValueError('Hold preparation speed exceeds the supervised range')
    if not finite(enable_gripper_drift_raw) or not 0 < enable_gripper_drift_raw <= .1:
        raise ValueError('Enable gripper drift must be within one small raw opening step')
    before = client.state()
    issues = state_blockers(before, require_gripper_target=False)
    if issues:
        raise ValueError('; '.join(issues))
    if (before.get('policy_execution_scope') != 'supervised_trial'
            or before.get('hold_available') is not True
            or before.get('worker_protocol_version') != 2):
        raise ValueError('Workbench must explicitly run in supervised policy mode with worker v2')
    if not 0 <= before['gripper_raw']+.1 <= 5:
        raise ValueError('Initial gripper reference is outside the command range')
    cameras.check()
    attempted = False
    try:
        client.command('settings', mode='joint', speed=speed)
        fresh = client.state()
        if (state_blockers(fresh, require_gripper_target=False)
                or max(abs(a-b) for a, b in zip(before['joints_deg'], fresh['joints_deg'])) > .1
                or abs(before['gripper_raw']-fresh['gripper_raw']) > .01):
            raise ValueError('State changed before enabling')
        attempted = True
        client.command('enable')
        started = clock()
        paused = False
        while clock()-started < 8:
            cameras.check()
            state = client.command('heartbeat')
            log('hold_preparation', {'state': state})
            check_state(state)
            if state.get('owner') != client.client or state.get('enabled') is not True:
                raise ValueError('Ownership lost during hold preparation')
            joint_drift = max(abs(a-b) for a, b in zip(before['joints_deg'], state['joints_deg']))
            gripper_drift = abs(before['gripper_raw']-state['gripper_raw'])
            if joint_drift > JOINT_DRIFT_LIMIT_DEG or gripper_drift > enable_gripper_drift_raw:
                raise ValueError(f'Enable displacement exceeded preparation limits: '
                                 f'joint={joint_drift:.6f}/{JOINT_DRIFT_LIMIT_DEG:.6f} deg, '
                                 f'gripper={gripper_drift:.6f}/{enable_gripper_drift_raw:.6f} raw')
            if clock()-started >= 1 and not paused:
                client.command('pause_hold')
                paused = True
            if paused and state.get('policy_execution_available') is True:
                if state.get('control_state') != 'holding':
                    raise ValueError('Policy qualification without powered hold')
                return state
            sleep(.05)
        raise TimeoutError('Measured powered hold did not qualify within eight seconds')
    except BaseException:
        if attempted:
            state = client.state()
            if state.get('enabled') and state.get('owner') == client.client:
                client.command('stop')
        raise


# GPT-6 decisions can take longer than the original 25-second window.  The
# supervisor still checks hardware health while this call is in progress.
MODEL_DECISION_TIMEOUT_S = 60.0


class DeadlineAgent:
    def __init__(self, agent, supervisor):
        self.agent, self.supervisor = agent, supervisor

    def __getattr__(self, name):
        return getattr(self.agent, name)

    def decide(self, turn):
        from gpt_policy.harness.waiting import monitor_health
        from gpt_policy.harness.errors import (AgentTimeoutError, AgentDecisionTimeoutError,
                                              AgentOverloadedError)
        deadline = time.monotonic()+MODEL_DECISION_TIMEOUT_S
        try:
            with monitor_health(self.supervisor.check, deadline=deadline) as check:
                decision = self.agent.decide(turn)
                check()
        except json.JSONDecodeError as exc:
            # Discard this provider turn completely; retry with fresh images,
            # never repair malformed actuator arguments or replay old actions.
            reset = getattr(self.agent, 'reset_after_timeout', None)
            if reset is None:
                raise
            reset()
            self.supervisor.check()
            raise AgentOverloadedError(
                'Malformed decision JSON discarded; fresh observation required',
                provider='codex', code='invalid_decision_json') from exc
        except AgentTimeoutError as exc:
            reset = getattr(self.agent, 'reset_after_timeout', None)
            if reset is None:
                raise
            reset()
            self.supervisor.check()
            raise AgentDecisionTimeoutError('Decision expired; old request discarded') from exc
        return decision


def open_empty_gripper(client, cameras, target, log, *, clock=time.monotonic, sleep=time.sleep):
    """Explicit operator preparation: opening only, separate from model budgets."""
    if not finite(target) or not 0 <= target <= 5:
        raise ValueError('Opening target must be a finite raw value in 0..5')
    before = client.state()
    check_state(before)
    reference = before.get('gripper_command_raw')
    if (before.get('control_state') != 'holding' or before.get('owner') != client.client
            or not finite(reference) or target < reference):
        raise ValueError('Opening preparation requires an owned hold and a non-closing target')
    if target-reference <= .001:
        return before
    opening_scale = before.get('gripper_open_speed_multiplier', 1.)
    if not finite(opening_scale) or opening_scale not in (1., GRIPPER_OPEN_SPEED_MULTIPLIER):
        raise ValueError('Unknown gripper opening speed profile')
    opening_step = min(EMPTY_GRIPPER_OPEN_STEP_RAW, .1*opening_scale)

    def inspect(state):
        cameras.check()
        check_state(state)
        if (state.get('enabled') is not True or state.get('owner') != client.client
                or state.get('mode') != 'joint' or state.get('speed') != SUPERVISED_SPEED):
            raise ValueError('Control changed during opening preparation')
        if max(abs(a-b) for a, b in zip(before['joints_deg'], state['joints_deg'])) > JOINT_DRIFT_LIMIT_DEG:
            raise ValueError('Joint drift during gripper opening preparation')
        if not finite(state.get('gripper_command_raw')):
            raise ValueError('Missing submitted gripper command')
        if state.get('gripper_open_speed_multiplier', 1.) != opening_scale:
            raise ValueError('Gripper opening speed profile changed during preparation')

    inspect(before)
    log('gripper_preparation_profile', {'opening_speed_multiplier': opening_scale,
                                      'step_raw': opening_step, 'target_raw': target})
    client.command('resume')
    state = before
    started = clock()
    previous_step = None
    while target-reference > .001:
        inspect(state)
        if clock()-started > 100:
            raise TimeoutError('Opening preparation exceeded 100 seconds')
        next_reference = min(target, reference+opening_step)
        initial_raw = state['gripper_raw']
        progress_reference, progress_initial = reference, initial_raw
        # A short final remainder can be below the encoder/controller response
        # resolution even though the absolute endpoint is already reached.
        # Measure its progress together with the preceding *completed* step;
        # full steps and a standalone request still need their own progress.
        final_remainder = (previous_step is not None and next_reference == target
                           and next_reference-reference < opening_step-1e-9)
        if final_remainder:
            progress_reference, progress_initial = previous_step
        required_progress = .5*(next_reference-progress_reference)
        client.command('target', gripper_raw=next_reference)
        log('gripper_preparation_target', {
            'gripper_raw': next_reference,
            'progress_includes_previous_step': final_remainder,
            'progress_initial_raw': progress_initial,
            'required_progress_raw': required_progress})
        print(json.dumps({'status': 'opening_empty_gripper', 'target_raw': round(next_reference, 3)}), flush=True)
        deadline = clock()+4
        recent = []
        settle_checks = None
        while clock() < deadline:
            state = client.command('heartbeat')
            inspect(state)
            log('gripper_preparation_feedback', {'state': state})
            if not initial_raw-.03 <= state['gripper_raw'] <= next_reference+.05:
                raise ValueError('Unexpected gripper opening feedback')
            recent.append((clock(), state['gripper_raw']))
            recent = [(stamp, value) for stamp, value in recent if clock()-stamp <= .4]
            stable = (len(recent) >= 5 and recent[-1][0]-recent[0][0] >= .25
                      and max(v for _, v in recent)-min(v for _, v in recent) <= .02)
            settle_checks = {
                'stable': stable,
                'command_acknowledged': abs(state['gripper_command_raw']-next_reference) <= .002,
                'absolute_endpoint_reached': state['gripper_raw'] >= next_reference-.15,
                'progress_sufficient': (next_reference-reference <= .01
                                       or state['gripper_raw']-progress_initial >= required_progress),
            }
            if all(settle_checks.values()):
                break
            sleep(.05)
        else:
            log('gripper_preparation_stalled', {
                'gripper_raw': state['gripper_raw'], 'target_raw': next_reference,
                'observed_progress_raw': state['gripper_raw']-progress_initial,
                'required_progress_raw': required_progress, 'checks': settle_checks})
            raise TimeoutError('Opening step stalled; no retry or force increase')
        previous_step = reference, initial_raw
        reference = next_reference
    state = client.command('pause_hold')
    inspect(state)
    if state.get('control_state') != 'holding':
        raise ValueError('Opening did not finish in powered hold')
    log('gripper_preparation_complete', {'state': state, 'gripper_raw': target})
    return state


def close_host(supervisor, client, cameras, agent, log):
    def stop_owned():
        state = client.state()
        if state.get('enabled') and state.get('owner') == client.client:
            client.command('stop')

    failures = []
    for name, close in (('supervisor', supervisor.close), ('owned_control', stop_owned),
                        ('cameras', cameras.close), ('agent', agent.close if agent else lambda: None)):
        try:
            close()
        except Exception as exc:
            failures.append({'resource': name, 'error_type': type(exc).__name__})
    for failure in failures:
        log('cleanup_error', failure)
    return failures


def guided_budget_renewal(robot):
    """Renew an explicit gripper budget or an unfinished demonstrated approach."""
    if getattr(robot, 'last_budget_rejection', None) == 'Session gripper travel budget exhausted':
        return {'remaining_joint_delta_deg': [], 'reason': 'gripper_budget_boundary'}
    rejection = getattr(robot, 'last_plan_rejection', None)
    if not rejection or not any(text in rejection for text in (
            'session envelope', 'session joint travel budget')):
        return None
    # Planning caches the guide before raising. Do not request a new observation
    # through the rejected session's fault gate before renew_session clears it.
    guide = getattr(robot, 'last_plan_rejection_guide', None)
    if not isinstance(guide, dict) or guide.get('reached') is not False:
        return None
    return guide


def automatic_budget_renewal(status, robot, *, all_budgets, guided, segment, limit):
    if (status not in ('budget_exhausted', 'motion_budget_boundary', 'gripper_budget_boundary')
            or segment >= limit or robot.fault is not None):
        return None
    if all_budgets:
        return {'remaining_joint_delta_deg': [], 'reason': status}
    return guided_budget_renewal(robot) if guided else None


def queued_operator_command(commands):
    """A queued stop wins over continuation at every segment boundary."""
    result = None
    while True:
        try:
            command = commands.get_nowait()
        except queue.Empty:
            return result
        if command == 'stop':
            result = 'stop'
        elif command == 'continue' and result != 'stop':
            result = 'continue'


def wait_for_operator_start(robot, commands, log, *, sleep=time.sleep):
    """Maintain qualified hold until an explicit start, without model or targets."""
    log('waiting_for_operator_start', {})
    print(json.dumps({'status': 'holding_waiting_for_start',
                      'instruction': 'Clear hands, then send start. Stop releases hold.'}), flush=True)
    while True:
        robot.check()
        start = stop = False
        while True:
            try:
                command = commands.get_nowait()
            except queue.Empty:
                break
            start |= command == 'start'
            stop |= command == 'stop'
        if stop:
            return False
        if start:
            robot.check()
            log('operator_start', {})
            return True
        sleep(.05)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--supported-supervision', action='store_true')
    parser.add_argument('--wait-for-start', action='store_true',
                        help='Establish powered hold, then wait for start before opening or model calls')
    parser.add_argument('--policy-interface', choices=('cartesian', 'joint'), default='cartesian',
                        help='Original GPT-Policy Cartesian tools (default), or legacy joint diagnostics')
    parser.add_argument('--calibration-profile', type=Path, default=ROOT/'r5_cartesian_profile.json')
    parser.add_argument('--cartesian-stage', choices=('motion', 'vision', 'grasp', 'image_grasp'), default='grasp',
                        help='motion: verified TCP only; vision: add localization; grasp: add gripper')
    parser.add_argument('--check', action='store_true', help='Validate local configuration only; no device or model access')
    parser.add_argument('--task')
    parser.add_argument('--input-json', type=Path,
                        help='Original GPT-Policy input manifest for reviewed setup evidence or demonstrations')
    parser.add_argument('--open-gripper-to', type=float,
                        help='Explicit empty-gripper preparation target in raw units, before the model starts')
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--arm', choices=('left', 'right'),
                        help='Select an explicit arm and its wrist camera through the dual workbench')
    parser.add_argument('--camera-mode', choices=('both', 'wrist'), default='wrist')
    parser.add_argument('--max-decisions', type=int, choices=range(1, 21), default=10,
                        help='Model observe/decide turns (1-20); actuator travel budgets remain unchanged')
    parser.add_argument('--auto-renew-guided', action='store_true',
                        help='Renew only demonstrated-guide motion budget boundaries while attended')
    parser.add_argument('--auto-renew-budgets', action='store_true',
                        help='While attended, renew decision and motion budgets; never restart done/give_up/fault')
    parser.add_argument('--max-guided-segments', type=int, choices=range(1, 33), default=16)
    args = parser.parse_args(argv)
    settings = None
    if args.policy_interface == 'cartesian':
        from r5_cartesian import profile_issues, STAGES
        import importlib.util
        try:
            settings = json.loads(args.calibration_profile.read_text())
            issues = profile_issues(settings, args.camera_mode, args.cartesian_stage)
        except (OSError, ValueError, TypeError) as exc:
            issues = [str(exc)]
        if importlib.util.find_spec('ruckig') is None:
            issues.append('Ruckig missing: use .venv-policy/bin/python')
        if args.check or issues:
            print(json.dumps({'status': 'blocked' if issues else 'configuration_ready',
                              'policy_interface': 'cartesian', 'blockers': issues,
                              'cartesian_stage': args.cartesian_stage,
                              'stage_blockers': {stage: profile_issues(settings, args.camera_mode, stage)
                                                 for stage in STAGES} if settings is not None else {},
                              'hardware_accessed': False, 'model_called': False}), flush=True)
            return 2 if issues else 0
    elif args.check:
        print(json.dumps({'status': 'configuration_ready', 'policy_interface': 'joint',
                          'hardware_accessed': False, 'model_called': False}), flush=True)
        return 0
    if not args.supported_supervision:
        parser.error('--supported-supervision is required for a live trial')
    if args.policy_interface == 'cartesian' and args.cartesian_stage in ('motion', 'vision'):
        if not args.task:
            parser.error('A contact-free validation --task is required for motion/vision stages')
        if args.open_gripper_to is not None:
            parser.error('Gripper preparation is unavailable in motion/vision stages')
    config = upstream_config()
    from gpt_policy.input.request import resolve_run_input
    from gpt_policy.recording.trace import RunRecorder
    instruction = args.task if args.task or args.input_json else 'Pick up the tennis ball.'
    run_input = resolve_run_input(instruction, args.input_json, None, config.model)
    directory = ROOT/'analysis'/('live-policy-'+uuid.uuid4().hex[:12])
    recorder = RunRecorder(directory, {'model': config.model, 'scope': 'supervised_trial',
                           'instruction': run_input.instruction, 'physical_success_verified': False,
                           'camera_mode': args.camera_mode, 'policy_interface': args.policy_interface,
                           'arm': args.arm,
                           'cartesian_stage': args.cartesian_stage if settings is not None else None})
    recorder.write('input_manifest', run_input.record())
    if settings is not None:
        recorder.write('calibration_profile', {'settings': settings,
                       'path': str(args.calibration_profile.resolve())})
    client = ArmWorkbenchClient(args.url, args.arm) if args.arm else WorkbenchClient(args.url)
    source = R5Cameras(client, camera_mode=args.camera_mode)
    if settings is not None:
        from r5_cartesian import CalibratedCameras, CartesianBackend
        if args.cartesian_stage in ('vision', 'grasp'):
            source = CalibratedCameras(source, settings)
    cameras = SupervisedCameras(source)
    robot = R5PolicyBackend(client, cameras.check)
    if settings is not None:
        robot = CartesianBackend(robot, settings, args.camera_mode, args.cartesian_stage)
    supervisor = R5PolicySupervisor(robot)
    agent = None
    status, error = 'failed', None
    print(json.dumps({'status': 'preparing', 'directory': str(directory), 'model': config.model}), flush=True)
    try:
        initial_state = client.state()
        check_tracking_contract(initial_state)
        if settings is not None and initial_state.get('policy_trajectory_protocol') != 1:
            raise ValueError('Workbench must deploy timed policy trajectory protocol 1 before enabling')
        cameras.start()
        prepare_hold(client, cameras, recorder.write)
        commands = queue.Queue()

        def read_commands():
            for line in sys.stdin:
                commands.put(line.strip())
            commands.put('stop')

        threading.Thread(target=read_commands, daemon=True).start()
        if args.wait_for_start and not wait_for_operator_start(robot, commands, recorder.write):
            status = 'interrupted'
            return 0
        if args.open_gripper_to is not None:
            open_empty_gripper(client, cameras, args.open_gripper_to, recorder.write)
        supervisor.start()
        runtime = SimpleNamespace(max_decisions=args.max_decisions, interface='existing-r5-worker',
                                  right_interface='', camera_mode=args.camera_mode,
                                  policy_interface=args.policy_interface,
                                  auto_renew_budgets=args.auto_renew_budgets)
        agent = new_agent(config)
        guided_segments = 1
        agent_started = False
        while True:
            recorder.segment = guided_segments
            status = run_r5_policy(runtime, run_input, robot, cameras,
                                  DeadlineAgent(agent, supervisor), recorder, supervisor=supervisor,
                                  start_agent=not agent_started)
            agent_started = True
            print(json.dumps({'status': status, 'control': 'holding_for_operator',
                              'grasp_verified': False, 'directory': str(directory),
                              'instruction': 'Send continue to renew the budget at the current powered hold, or stop to release control.'}), flush=True)
            command = queued_operator_command(commands)
            if command == 'stop':
                break
            guide = automatic_budget_renewal(status, robot,
                all_budgets=args.auto_renew_budgets, guided=args.auto_renew_guided,
                segment=guided_segments, limit=args.max_guided_segments)
            if guide is not None or command == 'continue':
                renewal = robot.renew_session()
                guided_segments += 1
                recorder.write('session_budget_renewed' if command == 'continue' else 'guided_session_budget_renewed', {
                    **renewal, 'segment': guided_segments,
                    'reason': 'operator_continue' if command == 'continue' else guide.get('reason', 'guided_boundary'),
                    'remaining_joint_delta_deg': guide['remaining_joint_delta_deg'] if guide else []})
                print(json.dumps({'status': 'continuing' if command == 'continue' else 'auto_continuing_budget', 'segment': guided_segments,
                                  **renewal}), flush=True)
                continue
            while True:
                supervisor.check()
                try:
                    command = commands.get(timeout=.1)
                except queue.Empty:
                    continue
                if command == 'stop':
                    break
                if command == 'continue':
                    renewal = robot.renew_session()
                    guided_segments += 1
                    recorder.write('session_budget_renewed', {**renewal, 'segment': guided_segments})
                    print(json.dumps({'status': 'continuing', 'segment': guided_segments, **renewal}), flush=True)
                    break
            if command == 'stop':
                break
    except KeyboardInterrupt:
        status = 'interrupted'
    except Exception as exc:
        status, error = 'failed', type(exc).__name__
        detail = str(exc)
        recorder.write('host_error', {'error_type': error, 'detail': detail,
                                      'robot_fault': robot.fault})
        print(json.dumps({'status': 'failed', 'error_type': error,
                          'detail': detail, 'robot_fault': robot.fault}), flush=True)
    finally:
        failures = close_host(supervisor, client, cameras, agent, recorder.write)
        if failures:
            status, error = 'failed', 'HostCleanupError'
        directory = recorder.close(status, error)
        print(json.dumps({'status': status, 'directory': str(directory), 'grasp_verified': False}), flush=True)
    return 0 if status in ('completed', 'give_up', 'budget_exhausted') else 2


if __name__ == '__main__':
    raise SystemExit(main())
