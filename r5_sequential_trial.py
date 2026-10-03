"""Attended cup-trial phase gate; not an automatic visual/collision validator."""
from motion_safety import POLICY_SETTLE_ERROR_DEG, vector


def renew_sequential_segment(robot, gate):
    """Renew only the working arm so an inactive returned arm is not re-anchored."""
    if gate is None:
        return robot.renew_session()
    with robot.operation_lock:
        robot.check()
        for arm in robot.robots.values():
            arm.backend._read(holding=True)
        side = 'right' if gate.right_started else 'left'
        return {'renewed': True, 'arms': {side: robot.robots[side].renew_session()}}


class WorkingArmGate:
    """Explicit attended arm selection, not a contact or collision validator."""
    def __init__(self, side):
        if side not in ('left', 'right'):
            raise ValueError('Select left or right')
        self.side = side

    def select(self, side, states):
        if side not in ('left', 'right'):
            raise ValueError('Select left or right')
        if set(states) != {'left', 'right'}:
            raise ValueError('Both arm states are required')
        for state in states.values():
            if (state.get('enabled') is not True or state.get('moving') is not False
                    or state.get('control_state') != 'holding'
                    or state.get('policy_trajectory_active') is not False):
                raise ValueError('Both arms must be stationary in powered hold before switching')
        self.side = side

    def check_action(self, name, arguments):
        if not isinstance(arguments, dict):
            raise ValueError('Expected tool arguments')
        if name == 'set_gripper':
            targets = [arguments.get('positions')]
        elif name == 'move_to':
            targets = [arguments.get('target')]
        elif name in ('move_eef_chunk', 'check_path'):
            targets = arguments.get('poses')
        else:
            raise ValueError('Unsupported bounded tool')
        if (not isinstance(targets, list) or not targets
                or any(not isinstance(t, dict) or set(t) != {'left', 'right'} for t in targets)):
            raise ValueError('Explicit left/right target fields required')
        requested = {s for t in targets for s in ('left', 'right') if t[s] is not None}
        if requested != {self.side}:
            raise ValueError(f'Only the selected {self.side} arm may receive targets')

    def renew(self, robot):
        with robot.operation_lock:
            robot.check()
            states = {side: arm.backend._read(holding=True) for side, arm in robot.robots.items()}
            self.select(self.side, states)
            return {'renewed': True, 'arms': {self.side: robot.robots[self.side].renew_session()}}


def require_idle(states):
    for side, state in states.items():
        if (state.get('robot_status') != 'ready' or state.get('enabled') is not False
                or state.get('moving') is not False or state.get('owner') is not None):
            raise ValueError(f'{side}: expected ready, unowned, disabled stationary arm')


class LeftReturnGate:
    def __init__(self, initial):
        if not vector(initial):
            raise ValueError('Six finite initial left joint values required')
        self.initial = list(initial)
        self.placement_verified = False
        self.right_started = False
        self.stack_verified = False

    def require_returned(self, state):
        if not self.placement_verified:
            raise ValueError('Verify left cup placement and release first')
        if (state.get('enabled') is not True or state.get('moving') is not False
                or state.get('control_state') != 'holding'):
            raise ValueError('Left must be stationary in powered hold')
        for key in ('joints_deg', 'command_deg'):
            values = state.get(key)
            if (not vector(values) or max(abs(a-b) for a, b in zip(values, self.initial))
                    > POLICY_SETTLE_ERROR_DEG):
                raise ValueError('Left has not returned to this trial initial joints')

    def begin_right(self, state):
        self.require_returned(state)
        self.right_started = True

    def verify_stack(self, left_state):
        self.require_returned(left_state)
        if not self.right_started:
            raise ValueError('Right phase must start before stack verification')
        self.stack_verified = True

    def require_right_return(self, left_state):
        self.require_returned(left_state)
        if not self.right_started or not self.stack_verified:
            raise ValueError('Verify stack release and empty right gripper withdrawal first')

    def check_action(self, name, arguments, left_state):
        if name == 'set_gripper':
            targets = [arguments['positions']]
        elif name == 'move_to':
            targets = [arguments['target']]
        else:
            targets = arguments['poses']
        requested = {side for target in targets for side in ('left', 'right')
                     if target[side] is not None}
        if not self.right_started and 'right' in requested:
            raise ValueError('Right blocked until verified left placement, initial return and begin-right')
        if self.right_started:
            self.require_returned(left_state)
            if 'left' in requested:
                raise ValueError('Left must stay at initial pose during the right phase')
