#!/usr/bin/env python3
"""Observe and issue bounded GPT-Policy tools after taking over an idle inference."""
import argparse
import json
from pathlib import Path
import queue
import sys
import threading
import time
import numpy as np
from jsonschema import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from control import ROOT
from held_policy_handoff import ObservingPolicyHandoff, CompletedReviewHandoff, SingleReviewHandoff
from camera_hold_recovery import CameraHoldHandoff
from initial_review_handoff import InitialReviewInputHandoff
from adopted_review_handoff import AdoptedReviewInputHandoff
from healthy_probe_handoff import HealthyProbeHandoff
from empty_fine_probe import EmptyFineProbeBackend
from empty_joint_diagnostic import EmptyJointDiagnosticBackend, joint_diagnostic_plan
from measured_probe_diagnostic_handoff import MeasuredProbeDiagnosticHandoff
from reviewed_task_handoff import ReviewedTaskHandoff
from r5_cartesian import CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend, DualSupervisor
from r5_policy_backend import R5PolicyBackend, R5ExecutionFault, R5PoweredHoldFault
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras, StationaryCameraGate
from supervised_policy import open_empty_gripper, prepare_hold
from dual_return_pose import return_plan
from r5_sequential_trial import LeftReturnGate, WorkingArmGate, require_idle, renew_sequential_segment
from review_telemetry import ReviewTimer, review_packet
from reviewed_return import ReviewedReturn
from visual_control import ArmWorkbenchClient
from gpt_policy.motion.coordination import TrajectoryIKError


def require_empty_probe_command(line, joint_diagnostic=False):
    probe_command = 'diagnose-empty-left-j3' if joint_diagnostic else 'probe-empty-up-3mm'
    if line not in ('observe', 'renew', probe_command):
        raise ValueError('Probe host permits observe, renew empty left, and one probe only')


def quarantine_arrival_fault(robot, supervisor, error, log, *, sleep=time.sleep):
    """Keep supervision alive without returning to the command dispatcher."""
    states = robot.retain_stationary_faults(str(error))
    log('arrival_fault_hold', {
        'reason': str(error), 'task_completion_verified': False,
        'new_commands_blocked': True, 'fault_fallback_hardware_validated': False,
        'states': states,
        'last_execution_feedback': {
            s: arm.backend.last_execution_feedback for s, arm in robot.robots.items()}})
    print('ARRIVAL FAILED: stationary powered hold retained; all new commands blocked. '
          'Camera, heartbeat, ownership and hardware protections remain active.', flush=True)
    try:
        while True:
            supervisor.check()
            for arm in robot.robots.values():
                arm.supervise()
            sleep(.1)
    except BaseException as exc:
        log('arrival_fault_hold_ended', {
            'reason': str(exc), 'exception_type': type(exc).__name__,
            'hold_failures': {s: arm.backend.fault_hold_failure
                              for s, arm in robot.robots.items()}})
        raise


def software_error_hold_snapshot(robots, supervisor, error):
    """Contain only idle software errors; never reinterpret a device/vision fault.

This does not restart anything or clear a fault. The original independent
supervisors remain responsible for every heartbeat and health decision.
"""
    if not isinstance(error, Exception) or isinstance(error, R5ExecutionFault):
        return None
    try:
        supervisor.check()
        states = {}
        for side, arm in robots.items():
            low = arm.backend
            if low.engaged is not True or low.busy is not False or low.fault is not None:
                return None
            state = low._read(holding=True)
            if (state.get('enabled') is not True or state.get('moving') is not False
                    or state.get('control_state') != 'holding'
                    or state.get('policy_trajectory_active') is not False):
                return None
            states[side] = state
        return states if set(states) == {'left', 'right'} else None
    except Exception:
        return None


def adopt_single_then_prepare_other(side, clients, robots, individual, handoff, cameras, log):
    """Retire the single-arm interlock before enabling the observation arm."""
    other = 'right' if side == 'left' else 'left'
    idle_state = clients[other].state()
    require_idle({other: idle_state})
    if not 0 <= idle_state['gripper_raw'] + .1 <= 5:
        raise ValueError('Observer initial gripper reference is outside the command range')
    individual[side].start()
    log('powered_hold_adopted', handoff.transfer(
        {side: robots[side]}, {side: individual[side]}))
    handoff.close()
    # There is now only one host; the adopted arm's watchdog remains running.
    require_idle({other: clients[other].state()})
    prepare_hold(clients[other], cameras,
                 lambda event, data: log(event, {'arm': other, **data}),
                 enable_gripper_drift_raw=.05)
    individual[other].start()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--from-pid', type=int)
    source.add_argument('--from-review-pid', type=int)
    source.add_argument('--from-single-review-pid', type=int)
    source.add_argument('--from-camera-review-pid', type=int)
    source.add_argument('--from-initial-review-pid', type=int)
    source.add_argument('--from-adopted-review-pid', type=int)
    source.add_argument('--from-healthy-probe-pid', type=int)
    source.add_argument('--from-measured-probe-pid', type=int)
    source.add_argument('--from-reviewed-diagnostic-pid', type=int)
    source.add_argument('--prepare-idle', action='store_true')
    parser.add_argument('--run', type=Path)
    parser.add_argument('--diagnostic-review', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--left-return-before-right', action='store_true')
    mode.add_argument('--working-arm', choices=('left', 'right'),
                      help='Only this arm can receive targets; switch explicitly after visual review')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--paired-client', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--adopt-arm', choices=('left', 'right'))
    parser.add_argument('--tracking-reserve-deg', type=float, default=0.0)
    parser.add_argument('--minimum-cartesian-command-step-deg', type=float, default=0.0,
                        help='Reject smaller endpoint joint changes before dispatch; does not enlarge motion')
    parser.add_argument('--retain-settle-fault-hold', action='store_true',
                        help='Opt-in stationary arrival-fault quarantine; one arm at a time; not hardware qualified')
    parser.add_argument('--one-empty-left-probe', action='store_true',
                        help='Only observe, renew empty left, and one +3mm no-contact probe; then motion locked')
    parser.add_argument('--one-empty-left-joint-diagnostic', action='store_true',
                        help='Only observe, bounded reanchor, and one fixed empty-left J3 diagnostic; no task recovery')
    args = parser.parse_args()
    probe_mode = args.one_empty_left_probe or args.one_empty_left_joint_diagnostic
    if args.retain_settle_fault_hold and (not args.working_arm or probe_mode):
        parser.error('Arrival fault hold requires ordinary --working-arm mode')
    if (args.from_pid or args.from_review_pid or args.from_camera_review_pid
            or args.from_initial_review_pid or args.from_adopted_review_pid or args.from_healthy_probe_pid
            or args.from_measured_probe_pid or args.from_reviewed_diagnostic_pid) and not args.run:
        parser.error('A handoff source requires --run')
    if args.left_return_before_right and not (args.prepare_idle or args.from_review_pid):
        parser.error('Sequential trial requires idle preparation or a completed review handoff')
    if args.from_review_pid and not args.left_return_before_right:
        parser.error('Completed review handoff requires a new sequential trial')
    if bool(args.from_single_review_pid) != bool(args.adopt_arm):
        parser.error('Single review handoff requires --adopt-arm and its PID together')
    if args.from_single_review_pid and not args.working_arm:
        parser.error('Single review handoff requires explicit --working-arm')
    if args.from_camera_review_pid and not args.working_arm:
        parser.error('Camera hold handoff requires explicit --working-arm')
    if args.from_initial_review_pid and not args.working_arm:
        parser.error('Initial input handoff requires explicit --working-arm')
    if args.from_adopted_review_pid and (not args.working_arm or probe_mode):
        parser.error('Adopted input handoff requires ordinary explicit --working-arm')
    if bool(args.from_healthy_probe_pid) != args.one_empty_left_probe:
        parser.error('One-shot empty probe and healthy source PID are required together')
    if bool(args.from_measured_probe_pid) != args.one_empty_left_joint_diagnostic:
        parser.error('Isolated diagnostic and measured probe source are required together')
    if args.one_empty_left_probe and args.one_empty_left_joint_diagnostic:
        parser.error('Select only one fixed diagnostic protocol')
    if probe_mode and args.working_arm != 'left':
        parser.error('One-shot probe requires working arm left')
    if bool(args.from_reviewed_diagnostic_pid) != bool(args.diagnostic_review):
        parser.error('Reviewed diagnostic source and review file are required together')
    if args.from_reviewed_diagnostic_pid and (probe_mode or not args.working_arm):
        parser.error('Reviewed task requires ordinary one-arm-at-a-time mode')
    stationary_gated = bool(args.from_single_review_pid or args.from_camera_review_pid
                            or args.from_adopted_review_pid)
    if args.retain_settle_fault_hold and stationary_gated:
        parser.error('Arrival fault hold requires strict camera supervision')
    clients = {s: ArmWorkbenchClient(args.url, s) for s in ARMS}
    if clients['left'].request('/api/arms').get('paired_policy_client') != args.paired_client:
        raise ValueError('Paired owner mismatch')
    for c in clients.values():
        c.client = args.paired_client
    if args.prepare_idle:
        require_idle({s: c.state() for s, c in clients.items()})
    profiles = {s: json.loads((ROOT/f'r5_{s}_image_grasp_20260927_profile.json').read_text()) for s in ARMS}
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    robots = {s: CartesianBackend((EmptyJointDiagnosticBackend if args.one_empty_left_joint_diagnostic and s == 'left'
                                  else EmptyFineProbeBackend if args.one_empty_left_probe and s == 'left'
                                  else R5PolicyBackend)(clients[s], cameras.check,
                                 retain_settle_fault_hold=args.retain_settle_fault_hold,
                                 minimum_cartesian_command_step_deg=args.minimum_cartesian_command_step_deg), profiles[s], 'both', 'image_grasp',
                                 tracking_reserve_deg=args.tracking_reserve_deg) for s in ARMS}
    camera_gates = {s: StationaryCameraGate(cameras, robots[s].backend) for s in ARMS}
    if stationary_gated:
        for s in ARMS:
            robots[s].backend.vision_check = camera_gates[s].check
    def vision_check():
        if stationary_gated:
            for gate in camera_gates.values():
                gate.check()
        else:
            cameras.check()
    individual = {s: R5PolicySupervisor(robots[s]) for s in ARMS}
    robot = DualCartesianBackend(robots, vision_check)
    supervisor = DualSupervisor(robot, individual)
    handoff = (ReviewedTaskHandoff(args.from_reviewed_diagnostic_pid, args.paired_client,
                                 args.url, args.run, args.tracking_reserve_deg,
                                 args.minimum_cartesian_command_step_deg, args.diagnostic_review)
               if args.from_reviewed_diagnostic_pid else
               MeasuredProbeDiagnosticHandoff(args.from_measured_probe_pid, args.paired_client,
                                 args.url, args.run, args.tracking_reserve_deg,
                                 args.minimum_cartesian_command_step_deg)
               if args.from_measured_probe_pid else
               HealthyProbeHandoff(args.from_healthy_probe_pid, args.paired_client,
                                 args.url, args.run, args.tracking_reserve_deg,
                                 args.minimum_cartesian_command_step_deg)
               if args.from_healthy_probe_pid else
               AdoptedReviewInputHandoff(args.from_adopted_review_pid, args.paired_client,
                                        args.url, args.run, args.tracking_reserve_deg,
                                        args.minimum_cartesian_command_step_deg)
               if args.from_adopted_review_pid else
               InitialReviewInputHandoff(args.from_initial_review_pid, args.paired_client,
                                       args.url, args.run, args.tracking_reserve_deg,
                                       args.minimum_cartesian_command_step_deg)
               if args.from_initial_review_pid else
               CameraHoldHandoff(args.from_camera_review_pid, args.paired_client, args.url,
                               args.run, args.tracking_reserve_deg)
               if args.from_camera_review_pid else
               SingleReviewHandoff(args.from_single_review_pid, args.paired_client, args.url, args.adopt_arm)
               if args.from_single_review_pid else
               CompletedReviewHandoff(args.from_review_pid, args.paired_client, args.url, args.run)
               if args.from_review_pid else
               ObservingPolicyHandoff(args.from_pid, args.paired_client, args.url, args.run)
               if args.from_pid else None)
    if handoff:
        handoff.snapshot({args.adopt_arm: robots[args.adopt_arm]} if args.from_single_review_pid else robots)
    if args.from_single_review_pid:
        other = 'right' if args.adopt_arm == 'left' else 'left'
        require_idle({other: clients[other].state()})
    gate = None
    working = WorkingArmGate(args.working_arm) if args.working_arm else None
    initial = None
    reviewed_return = None
    args.output.mkdir(parents=True, exist_ok=True)
    commands = queue.Queue()
    def read_commands():
        for line in sys.stdin:
            commands.put(line.strip())
    with (args.output/'events.jsonl').open('x') as stream:
        timer = ReviewTimer()
        def log(event, data):
            stream.write(json.dumps({'at_s': time.time(), 'event': event, **data})+'\n')
            stream.flush()
        def capture():
            capture_gate = camera_gates[args.adopt_arm or args.working_arm] if stationary_gated else None
            if capture_gate:
                capture_gate.require_fresh()
            began = time.monotonic()
            stamp = time.time_ns()
            images = {}
            frames = capture_gate.snapshot() if capture_gate else cameras.snapshot()
            for name, frame in frames.items():
                path = args.output/f'{stamp}_{name}.jpg'
                path.write_bytes(frame.data)
                images[name] = str(path.resolve())
                (args.output/f'current_{name}.jpg').write_bytes(frame.data)
            state = robot.state()
            (args.output/'current_state.json').write_text(json.dumps(state, indent=2))
            packet = review_packet(state, images, stamp, initial=initial)
            packet['working_arm'] = working.side if working else None
            packet['capture_wall_s'] = time.monotonic()-began
            packet['timing_before_current_command_finishes'] = timer.summary()
            temporary = args.output/'review_packet.tmp'
            temporary.write_text(json.dumps(packet, indent=2))
            temporary.replace(args.output/'review_packet.json')
            log('observation', {'state': state, 'image_stamp': stamp,
                                'capture_wall_s': packet['capture_wall_s']})
            print(json.dumps(packet), flush=True)
        try:
            cameras.start()
            if (args.from_camera_review_pid or args.from_initial_review_pid or args.from_adopted_review_pid
                    or args.from_healthy_probe_pid or args.from_measured_probe_pid
                    or args.from_reviewed_diagnostic_pid):
                log('replacement_cameras_qualified', handoff.qualify(cameras, robots))
            if args.from_single_review_pid:
                try:
                    adopt_single_then_prepare_other(args.adopt_arm, clients, robots, individual,
                                                    handoff, cameras, log)
                except Exception as exc:
                    # If observer preparation failed after transfer, retain a healthy
                    # adopted hold instead of dropping the extended working arm.
                    log('observer_preparation_failed', {'reason': str(exc)})
                    print('OBSERVER PREPARATION FAILED: retaining healthy adopted hold; no motion.', flush=True)
                    while True:
                        individual[args.adopt_arm].check()
                        time.sleep(.1)
            else:
                for s in ARMS:
                    if not handoff:
                        require_idle({s: clients[s].state()})
                        prepare_hold(clients[s], cameras,
                            lambda event, data, s=s: log(event, {'arm': s, **data}),
                            enable_gripper_drift_raw=.05)
                    individual[s].start()
            if handoff and not args.from_single_review_pid:
                log('powered_hold_adopted', handoff.transfer(robots, individual))
                handoff.close()
            supervisor.start()
            log('planning_configuration', {'tracking_reserve_deg': args.tracking_reserve_deg,
                                            'retain_settle_fault_hold': args.retain_settle_fault_hold,
                                            'fault_fallback_hardware_validated': False,
                                            'minimum_cartesian_command_step_deg': args.minimum_cartesian_command_step_deg,
                                            'one_empty_left_probe': args.one_empty_left_probe,
                                            'one_empty_left_joint_diagnostic': args.one_empty_left_joint_diagnostic,
                                            'one_arm_at_a_time': working is not None})
            initial = {s: clients[s].state() for s in ARMS}
            (args.output/'initial_state.json').write_text(json.dumps(initial, indent=2))
            if args.left_return_before_right:
                gate = LeftReturnGate(initial['left']['joints_deg'])
                log('sequential_trial_started', {'initial_joints_deg': {
                    s: initial[s]['joints_deg'] for s in ARMS}, 'right_blocked': True})
            threading.Thread(target=read_commands, daemon=True).start()
            capture()
            timer.ready()
            if probe_mode:
                name = 'diagnose-empty-left-j3' if args.one_empty_left_joint_diagnostic else 'probe-empty-up-3mm'
                print('DIAGNOSTIC HOLD: observe, renew, '+name+'. One attempt; no task recovery; all further motion locked.', flush=True)
            else:
                print('HOLDING: observe, renew, open-empty-right/left, or JSON {tool, arguments}. EOF retains hold.', flush=True)
            if gate:
                print('SEQUENTIAL: verify-left-placement, return-left-step, begin-right, verify-stack, return-right-step. Returns are bounded; visual clearance review required.', flush=True)
            if working:
                log('working_arm_selected', {'arm': working.side, 'source': 'startup'})
                if not probe_mode:
                    print('SINGLE ARM: select-left/right only after visual phase/clearance review; return-working-step after empty-gripper clearance review. No automatic collision or task validation.', flush=True)
                    print('REVIEWED RETURN: reviewed-return-step {observation_id, empty_gripper, path_clear, recording_active, note}; one segment per fresh visual review; never a fault handler.', flush=True)
            while True:
                supervisor.check()
                try:
                    line = commands.get(timeout=.1)
                except queue.Empty:
                    continue
                label = 'tool_json' if line.startswith('{') else line[:80]
                log('review_command_started', timer.begin(label))
                outcome = 'failed'
                try:
                    if probe_mode:
                        require_empty_probe_command(line, args.one_empty_left_joint_diagnostic)
                    if stationary_gated:
                        camera_gates[args.adopt_arm or working.side].require_fresh()
                    if line == 'observe':
                        capture()
                        outcome = 'completed'
                        continue
                    if line in ('probe-empty-up-3mm', 'diagnose-empty-left-j3'):
                        if not probe_mode:
                            raise ValueError('Explicit one-shot probe host required')
                        with robot.operation_lock:
                            robot.check()
                            arm = robots['left']
                            before = robots['right'].backend._read(holding=True)
                            # The last reviewed observation must still be valid;
                            # do not silently replace it before execution.
                            if args.one_empty_left_joint_diagnostic:
                                plan = joint_diagnostic_plan(arm.backend._read(holding=True))
                                target = None
                            else:
                                current = arm.frames.sdk_to_tcp(arm.solver.forward_kinematics(
                                    np.radians(arm.backend._read(holding=True)['command_deg'])))
                                from gpt_policy.geometry.poses import rpy_to_quaternion
                                target = [*current[:3], *rpy_to_quaternion(current[3:])]
                                target[2] += .003
                                plan = arm.plan([{'pose_xyzquat': target}],
                                                'One-shot open empty left upward 3mm response measurement')
                            log('joint_diagnostic_requested' if args.one_empty_left_joint_diagnostic else 'empty_probe_requested', {'target_xyzquat': target,
                                'plan': plan['result'], 'empty_gripper_clearance': 'attended_visual_review',
                                'contact_motion_qualified': False})
                            result = arm.backend.execute_probe(arm, plan)
                            after = robots['right'].backend._read(holding=True)
                            if (max(abs(a-b) for a,b in zip(before['command_deg'], after['command_deg'])) > .05
                                    or abs(before['gripper_command_raw']-after['gripper_command_raw']) > .01):
                                robot.abort('Held right-arm targets changed during empty left probe')
                            result_key = 'joint_diagnostic_result' if args.one_empty_left_joint_diagnostic else 'empty_probe_result'
                            log(result_key, result)
                            print(json.dumps({result_key: result}), flush=True)
                    elif line == 'renew':
                        log('budget_renewed', working.renew(robot) if working else renew_sequential_segment(robot, gate))
                    elif line in ('select-left', 'select-right'):
                        if working is None:
                            raise ValueError('Working-arm mode required')
                        cameras.check()
                        with robot.operation_lock:
                            robot.check()
                            states = {s: robots[s].backend._read(holding=True) for s in ARMS}
                            working.select(line.rsplit('-', 1)[1], states)
                        log('working_arm_selected', {'arm': working.side, 'source': 'attended_review'})
                    elif line == 'return-working-step':
                        if args.from_single_review_pid:
                            raise ValueError('Use reviewed Cartesian return targets with tracking reserve')
                        if working is None:
                            raise ValueError('Working-arm mode required')
                        cameras.check()
                        with robot.operation_lock:
                            robot.check()
                            arm = robots[working.side]
                            state = arm.backend.state()['raw_state']
                            plan = return_plan(state, initial[working.side], arm.planner.limits, arm.clock())
                            if plan is not None:
                                arm.backend.preview_timed_trajectory(plan)
                                result = arm.backend.execute_trajectory(plan)
                                log(working.side+'_return_step', result)
                            else:
                                log(working.side+'_return_complete', {'at_initial': True})
                                print(working.side.upper()+'_RETURN_COMPLETE: inspect full-arm clearance and object stability.', flush=True)
                    elif line.startswith('reviewed-return-step '):
                        if working is None or args.from_single_review_pid:
                            raise ValueError('Reviewed return requires a working arm and this host initial reference')
                        review = json.loads(line.split(' ', 1)[1])
                        if reviewed_return is None:
                            reviewed_return = ReviewedReturn(initial)
                        result = reviewed_return.step(robot, working.side, review)
                        log('reviewed_return_step', result)
                        print(json.dumps({'reviewed_return_step': result}), flush=True)
                    elif line in ('verify-left-placement', 'return-left-step', 'begin-right', 'verify-stack', 'return-right-step'):
                        if gate is None:
                            raise ValueError('Sequential trial mode required')
                        cameras.check()
                        if line == 'verify-left-placement':
                            if gate.right_started:
                                raise ValueError('Right phase already started')
                            gate.placement_verified = True
                            log('left_placement_visually_verified', {'source': 'attended_review'})
                        elif line == 'begin-right':
                            gate.begin_right(robots['left'].backend._read(holding=True))
                            log('right_phase_authorized', {'left_at_initial': True,
                                'clearance_review_source': 'attended_review'})
                        elif line == 'verify-stack':
                            gate.verify_stack(robots['left'].backend._read(holding=True))
                            log('stack_release_and_withdrawal_visually_verified', {'source': 'attended_review'})
                        else:
                            side = 'right' if line == 'return-right-step' else 'left'
                            if side == 'right':
                                gate.require_right_return(robots['left'].backend._read(holding=True))
                            elif not gate.placement_verified or gate.right_started:
                                raise ValueError('Left return is only allowed after placement and before right')
                            arm = robots[side]
                            with robot.operation_lock:
                                state = arm.backend.state()['raw_state']
                                plan = return_plan(state, initial[side], arm.planner.limits, arm.clock())
                                if plan is not None:
                                    arm.backend.preview_timed_trajectory(plan)
                                    result = arm.backend.execute_trajectory(plan)
                                    log(side+'_return_step', result)
                                else:
                                    log(side+'_return_complete', {'at_initial': True})
                                    print(side.upper()+'_RETURN_COMPLETE: inspect full-arm clearance and cup stability.', flush=True)
                    elif line in ('open-empty-right', 'open-empty-left'):
                        side = line.rsplit('-', 1)[1]
                        if working:
                            working.check_action('set_gripper', {'positions': {
                                s: 1.0 if s == side else None for s in ARMS}})
                        if gate:
                            gate.check_action('set_gripper', {'positions': {
                                s: 1.0 if s == side else None for s in ARMS}},
                                robots['left'].backend._read(holding=True))
                        low = robots[side].backend
                        with low.command_lock:
                            low.busy = True
                        try:
                            open_empty_gripper(clients[side], cameras, 4.8,
                                lambda event, data: log(event, {'arm': side, **data}))
                        finally:
                            with low.command_lock:
                                low.busy = False
                        if working:
                            working.renew(robot)
                        else:
                            renew_sequential_segment(robot, gate)
                    else:
                        command = json.loads(line)
                        if set(command) != {'tool', 'arguments'} or command['tool'] not in ('move_to', 'move_eef_chunk', 'check_path', 'set_gripper'):
                            raise ValueError('Expected a bounded GPT-Policy motion tool')
                        if gate:
                            gate.check_action(command['tool'], command['arguments'],
                                robots['left'].backend._read(holding=True))
                        if working:
                            working.check_action(command['tool'], command['arguments'])
                        log('request', command)
                        result = robot.execute(command['tool'], command['arguments'])
                        log('result', result)
                        print(json.dumps({'result': {k: v for k, v in result.items()
                            if k != 'trajectories'}}), flush=True)
                    capture()
                    outcome = 'completed'
                except (ValueError, ValidationError, TrajectoryIKError) as exc:
                    outcome = 'rejected'
                    log('rejected', {'reason': str(exc)})
                    print(json.dumps({'rejected': str(exc)}), flush=True)
                finally:
                    measured = timer.finish(outcome)
                    log('review_command_finished', measured)
                    temporary = args.output/'review_timing.tmp'
                    temporary.write_text(json.dumps(measured, indent=2))
                    temporary.replace(args.output/'review_timing.json')
        except BaseException as exc:
            if isinstance(exc, R5PoweredHoldFault):
                quarantine_arrival_fault(robot, supervisor, exc, log)
            retained = software_error_hold_snapshot(robots, supervisor, exc)
            if retained is not None:
                log('host_quarantined', {'exception_type': type(exc).__name__, 'reason': str(exc),
                    'task_completion_verified': False, 'new_commands_blocked': True,
                    'healthy_stationary_hold': retained})
                print('SOFTWARE ERROR: healthy stationary hold retained; all new commands blocked. '
                      'Original camera/heartbeat/hardware protection remains active.', flush=True)
                # No retries, input dispatch, target change, renewal or fault reset.
                # If original supervision fails later, normal cleanup still applies.
                while True:
                    supervisor.check()
                    for arm in robots.values():
                        held = arm.backend._read(holding=True)
                        if held.get('moving') is not False or held.get('policy_trajectory_active') is not False:
                            raise R5ExecutionFault('Quarantined hold is no longer stationary')
                    time.sleep(.1)
            log('host_terminated', {'exception_type': type(exc).__name__, 'reason': str(exc),
                                   'task_completion_verified': False,
                                   # Historical per-arm traces; an idle arm may
                                   # still hold feedback from an earlier command.
                                   'last_execution_feedback': {
                                       s: robots[s].backend.last_execution_feedback for s in ARMS},
                                   'supervisor_diagnostics': {
                                       s: individual[s].diagnostics() for s in ARMS}})
            raise
        finally:
            if handoff:
                handoff.close()
            supervisor.close()
            cameras.close()


if __name__ == '__main__':
    main()
