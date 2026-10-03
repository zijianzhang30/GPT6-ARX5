#!/usr/bin/env python3
"""Observe and issue bounded GPT-Policy tools after taking over an idle inference."""
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
from held_policy_handoff import ObservingPolicyHandoff, CompletedReviewHandoff, SingleReviewHandoff
from camera_hold_recovery import CameraHoldHandoff
from r5_cartesian import CartesianBackend
from r5_dual_policy import ARMS, DualCartesianBackend, DualSupervisor
from r5_policy_backend import R5PolicyBackend
from r5_policy_deployment import R5DualCameras
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras, StationaryCameraGate
from supervised_policy import open_empty_gripper, prepare_hold
from dual_return_pose import return_plan
from r5_sequential_trial import LeftReturnGate, WorkingArmGate, require_idle, renew_sequential_segment
from review_telemetry import ReviewTimer, review_packet
from visual_control import ArmWorkbenchClient
from gpt_policy.motion.coordination import TrajectoryIKError


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
    source.add_argument('--prepare-idle', action='store_true')
    parser.add_argument('--run', type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--left-return-before-right', action='store_true')
    mode.add_argument('--working-arm', choices=('left', 'right'),
                      help='Only this arm can receive targets; switch explicitly after visual review')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--paired-client', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8768')
    parser.add_argument('--adopt-arm', choices=('left', 'right'))
    parser.add_argument('--tracking-reserve-deg', type=float, default=0.0)
    args = parser.parse_args()
    if (args.from_pid or args.from_review_pid or args.from_camera_review_pid) and not args.run:
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
    stationary_gated = bool(args.from_single_review_pid or args.from_camera_review_pid)
    clients = {s: ArmWorkbenchClient(args.url, s) for s in ARMS}
    if clients['left'].request('/api/arms').get('paired_policy_client') != args.paired_client:
        raise ValueError('Paired owner mismatch')
    for c in clients.values():
        c.client = args.paired_client
    if args.prepare_idle:
        require_idle({s: c.state() for s, c in clients.items()})
    profiles = {s: json.loads((ROOT/f'r5_{s}_image_grasp_20260927_profile.json').read_text()) for s in ARMS}
    cameras = SupervisedCameras(R5DualCameras(clients['left'], clients['right']))
    robots = {s: CartesianBackend(R5PolicyBackend(clients[s], cameras.check), profiles[s], 'both', 'image_grasp',
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
    handoff = (CameraHoldHandoff(args.from_camera_review_pid, args.paired_client, args.url,
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
            if args.from_camera_review_pid:
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
            print('HOLDING: observe, renew, open-empty-right/left, or JSON {tool, arguments}. EOF retains hold.', flush=True)
            if gate:
                print('SEQUENTIAL: verify-left-placement, return-left-step, begin-right, verify-stack, return-right-step. Returns are bounded; visual clearance review required.', flush=True)
            if working:
                log('working_arm_selected', {'arm': working.side, 'source': 'startup'})
                print('SINGLE ARM: select-left/right only after visual phase/clearance review; return-working-step after empty-gripper clearance review. No automatic collision or task validation.', flush=True)
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
                    if stationary_gated:
                        camera_gates[args.adopt_arm or working.side].require_fresh()
                    if line == 'observe':
                        capture()
                        outcome = 'completed'
                        continue
                    if line == 'renew':
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
            log('host_terminated', {'exception_type': type(exc).__name__, 'reason': str(exc),
                                   'task_completion_verified': False,
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
