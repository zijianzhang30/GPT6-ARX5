"""Attended bimanual R5 adapter for GPT-Policy's original paired tools.

Preflight and time synchronization are numeric checks, not geometric collision
certification. Both complete swept paths must be clear in fresh shared views.
"""
import copy
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from jsonschema import Draft202012Validator

import r5_cartesian  # Installs the vendored GPT-Policy import path.
from r5_policy_backend import R5ExecutionFault, R5PoweredHoldFault
from visual_control import validate_action
from gpt_policy.harness.models import AgentContext
from gpt_policy.harness.protocol import instructions
from gpt_policy.motion.coordination import path_check_result, synchronize_bimanual_plan_times
from gpt_policy.tools.runtime import ToolExecutor


ARMS = ('left', 'right')


class DualCartesianBackend:
    active_arms = ARMS

    def __init__(self, robots, vision_check):
        if set(robots) != set(ARMS):
            raise ValueError('Both physical arms are required')
        for side, robot in robots.items():
            if robot.backend.client.arm != side or robot.stage != 'image_grasp':
                raise ValueError('Dual attended control requires routed image_grasp backends')
        owners = {robot.backend.client.client for robot in robots.values()}
        if len(owners) != 1:
            raise ValueError('Both arms must share the new coordinator owner')
        self.robots, self.vision_check = dict(robots), vision_check
        self.catalog = robots['left'].catalog
        self.fault = None
        self.fault_hold = False
        self.operation_lock = threading.Lock()

    @property
    def engaged(self):
        return any(robot.engaged for robot in self.robots.values())

    @property
    def last_plan_rejection(self):
        return next((robot.last_plan_rejection for robot in self.robots.values()
                     if robot.last_plan_rejection), None)

    @property
    def last_budget_rejection(self):
        return next((robot.last_budget_rejection for robot in self.robots.values()
                     if robot.last_budget_rejection), None)

    def check(self):
        if self.fault:
            if self.fault_hold:
                raise R5PoweredHoldFault(self.fault)
            raise R5ExecutionFault(self.fault)
        try:
            for robot in self.robots.values():
                robot.check()
            self.vision_check()
        except Exception as exc:
            self.abort(str(exc))

    def abort(self, reason):
        self.fault = self.fault or str(reason)
        self.fault_hold = False
        for robot in self.robots.values():
            try:
                robot.abort(self.fault)
            except R5ExecutionFault:
                pass
        raise R5ExecutionFault(self.fault)

    def retain_stationary_faults(self, reason):
        """Latch the idle companion too; any failed qualification aborts both."""
        try:
            if not any(r.backend.fault_hold is not None for r in self.robots.values()):
                raise R5ExecutionFault('No qualified arrival fault hold exists')
            states = {}
            for side, robot in self.robots.items():
                low = robot.backend
                if low.busy:
                    raise R5ExecutionFault('Paired fault hold requires finished execution')
                states[side] = (low.supervise() if low.fault_hold is not None
                                else low.retain_stationary_fault(str(reason)))
            self.fault = self.fault or str(reason)
            self.fault_hold = True
            return states
        except Exception as exc:
            self.abort('Paired fault hold unavailable: '+str(exc))

    def state(self):
        self.check()
        return {'arms': {side: robot.state() for side, robot in self.robots.items()},
                'interfaces': {'left': 'can0', 'right': 'can1'}}

    def context(self, task):
        text = instructions('R5', 'can0/can1', 6, ARMS,
                            {'runtime': {'robot_model': 'R5', 'interface': 'can0',
                                         'right_interface': 'can1'}}, self.catalog,
                            task_instruction=task)
        start = text.index('Robot and calibration conventions:')
        end = text.index('Return exactly one tool selection', start)
        conventions = (
            'Robot and camera conventions:\n'
            '- left is the physical left R5 on can0 with the white wrist camera; '
            'right is the physical right R5 on can1 with the black wrist camera. '
            'Tool keys and image names now refer to the matching physical arms.\n'
            '- Each arm has its own base: +X forward, +Y left, +Z up. Joint order '
            'is J1..J6. TCP targets are metres and xyzw unit quaternions in that '
            'arm base, using the configured nominal fingertip transform and the '
            'official R5 solver. Do not compare coordinates across the two bases.\n'
            '- left/right are the respective wrist RGB images; top is the shared '
            'external RGB overview. Cameras have no calibrated depth or pixel-to-base '
            'mapping here; locate_point is disabled. Capture receipts are fresh but '
            'the three exposures are not hardware synchronized.\n'
            '- No measured inter-base transform or geometric collision checker is '
            'available. The operator reports having manually tested the work areas. '
            'That report is not proof of clearance for a newly generated path. '
            'Inspect both complete arms, open fingers, cameras, cables, objects and '
            'the table in the shared overview before every paired command. Keep '
            'left and right approach corridors separate; never cross arms. If both '
            'paths are not clearly separated, move one arm and hold the other with '
            'null. Use smaller corrections near the shared central area.\n'
            '- One decision can command both arms; the host preflights both paths '
            'before dispatch and slows each segment to a common duration. HTTP starts '
            'are near-concurrent, not hard real-time synchronized. A null side holds '
            'its submitted targets. Arm motion and gripper changes are separate.\n'
            '- Use observed response independently for each arm. Screen-right is '
            'not base +Y. Camera placement and arm posture may change between runs; '
            'verify each local response from the current images and measured state. '
            'Do not transfer motion signs between arms or earlier camera views.\n\n')
        text = text[:start] + conventions + text[end:]
        text = text.replace('live joint and calibrated TCP feedback', 'live joint and nominal TCP feedback')
        text = text.replace('after SDK-reported obstruction, it brings the reference near measured position to avoid accumulating large error.',
                            'obstruction recovery is unavailable on this R5 adapter; a stall is not grasp evidence.')
        adaptation = self.robots['left'].context(task).instructions
        text += adaptation[adaptation.index('\nR5 adaptation:'):]
        text += ('\nFor this paired adapter, all measured joints, command joints, TCP command '
                 'poses, tracking errors and budgets appear independently under state.left '
                 'and state.right. Normalized gripper endpoints use each arm own profile; '
                 'right endpoints are nominal transfers, not independently calibrated. '
                 'Inspect external placement before each closure, then make a small lift '
                 'only after supported grasp evidence for that arm. One arm may finish '
                 'and hold while the other continues. Follow the current task order and '
                 'verify every requested final condition before done. For pick-and-place '
                 'or return tasks, lifting alone is incomplete: lower onto the intended '
                 'support, release only when supported, observe stability after release, '
                 'and withdraw clear. Record pickup/release poses for an object that must '
                 'return to its original position, then verify that placement visually. '
                 'Do not close or lift the unready side just to make both arms move. '
                 'After done keep powered hold without automatic homing or gripper changes.')
        return AgentContext(text, self.catalog.function_schemas(6, ARMS),
                            self.catalog.output_schema(6, ARMS))

    def executor(self):
        return ToolExecutor(self.catalog, ARMS, self, None)

    def _parallel(self, callbacks):
        barrier = threading.Barrier(len(callbacks))
        results = {}
        with ThreadPoolExecutor(max_workers=len(callbacks)) as pool:
            futures = {pool.submit(callback, barrier): side for side, callback in callbacks.items()}
            try:
                for future in as_completed(futures):
                    results[futures[future]] = future.result()
            except BaseException as exc:
                barrier.abort()
                if isinstance(exc, R5PoweredHoldFault) and len(callbacks) == 1:
                    self.retain_stationary_faults(str(exc))
                    raise
                self.abort('Paired execution interrupted: ' + str(exc))
        return results

    def execute(self, name, arguments):
        with self.operation_lock:
            self.check()
            tool = next(t for t in self.catalog.function_schemas(6, ARMS)
                        if t['function']['name'] == name)
            Draft202012Validator(tool['function']['parameters']).validate(arguments)
            note = arguments['note']
            if name == 'set_gripper':
                callbacks = {}
                for side, opening in arguments['positions'].items():
                    if opening is None:
                        continue
                    robot = self.robots[side]
                    grip = robot.settings['gripper']
                    raw = grip['command_closed_raw'] + opening * (grip['command_open_raw']-grip['command_closed_raw'])
                    low = robot.backend
                    args = {'gripper_raw': raw, 'note': note,
                            'observation_id': low.observation['observation_id'] if low.observation else ''}
                    state, target = low._action_target('set_gripper', args)
                    preview = copy.deepcopy(low.guard)
                    try:
                        preview.accept(state, target)
                    except ValueError as exc:
                        reason = preview.failure or str(exc)
                        if reason == 'Session gripper travel budget exhausted':
                            low.last_budget_rejection = reason
                        current = robot._normalized(state['gripper_target_raw'], 'command')
                        span = grip['command_open_raw']-grip['command_closed_raw']
                        limits = preview.snapshot()['limits']
                        lower = max(0., current-limits['gripper_close_step_raw']/span)
                        upper = min(1., current+limits['gripper_step_raw']/span)
                        # A rejected copy of the budget is not a live device fault.
                        raise ValueError(
                            f'{side} gripper proposal rejected before execution: {reason}; '
                            'neither arm moved, no budget consumed, live session remains healthy. '
                            f'Current commanded opening={current:.6f}; next absolute opening '
                            f'must be within [{lower:.6f}, {upper:.6f}] '
                            '(subject to remaining session budget). Use a smaller change with '
                            'fresh observations; do not give up solely for this rejection.') from exc
                    validate_action(state, target)
                    callbacks[side] = lambda barrier, low=low, args=args: low.execute(
                        'set_gripper', args, dispatch_barrier=barrier)
                plans = None
            elif name in ('move_to', 'move_eef_chunk', 'check_path'):
                requested = [arguments['target']] if name == 'move_to' else arguments['poses']
                plans = {}
                for side, robot in self.robots.items():
                    waypoints = [item[side] for item in requested]
                    if any(item is not None for item in waypoints):
                        plans[side] = robot.plan(waypoints, note)
                if not plans:
                    raise ValueError('At least one side must have a target')
                synchronize_bimanual_plan_times(plans)
                for side, plan in plans.items():
                    self.robots[side].backend.preview_timed_trajectory(plan)
                if name == 'check_path':
                    return path_check_result(plans)
                callbacks = {side: (lambda barrier, side=side, plan=plan:
                             self.robots[side].backend.execute_trajectory(plan, dispatch_barrier=barrier))
                             for side, plan in plans.items()}
            else:
                raise ValueError('Unsupported paired action')
            if not callbacks:
                raise ValueError('At least one side must have a target')
            if len(callbacks) > 1 and any(r.backend.retain_settle_fault_hold for r in self.robots.values()):
                raise ValueError('Fault hold mode requires one moving arm at a time')
            results = self._parallel(callbacks)
            self.check()
            return {'arms': results, 'held_sides': [side for side in ARMS if side not in results],
                    'trajectories': {side: plan['result'] for side, plan in plans.items()} if plans else {},
                    'grasp_verified': False, 'collision_checked': False,
                    'dispatch': 'barrier_released_HTTP; not_hardware_synchronized'}

    def renew_session(self):
        self.check()
        for robot in self.robots.values():
            robot.backend._read(holding=True)
        try:
            return {'renewed': True, 'arms': {side: robot.renew_session()
                                             for side, robot in self.robots.items()}}
        except Exception as exc:
            self.abort('Paired renewal interrupted: ' + str(exc))

    def finish(self, trigger):
        self.check()
        return {'trigger': trigger, 'arms': {side: robot.finish(trigger)
                                            for side, robot in self.robots.items()},
                'control_state': 'holding', 'grasp_verified': False, 'returned_home': False}


class DualSupervisor:
    """Join existing per-arm watchdogs and propagate any fault to the pair."""

    def __init__(self, robot, supervisors):
        self.robot, self.supervisors = robot, supervisors
        self.done = threading.Event()
        self.thread = None
        self.fault = None

    def check(self):
        if self.done.is_set() or self.fault:
            raise R5ExecutionFault(self.fault or 'Dual supervisor stopped')
        for supervisor in self.supervisors.values():
            supervisor.check()
        self.robot.vision_check()

    def start(self):
        self.check()
        self.thread = threading.Thread(target=self._run, daemon=True, name='r5-dual-watchdog')
        self.thread.start()

    def _run(self):
        try:
            while not self.done.wait(.05):
                self.check()
        except Exception as exc:
            self.fault = str(exc)
            try:
                self.robot.abort(self.fault)
            except R5ExecutionFault:
                pass

    def close(self):
        self.done.set()
        if self.thread:
            self.thread.join(timeout=1)
        for supervisor in self.supervisors.values():
            supervisor.close()
