"""One reviewed return segment while both arms are healthy and powered.

Never called by fault cleanup. Visual assertions come from the reviewing caller,
not a force/contact sensor or an automatic collision detector. No enable, fault
reset, gripper action, budget renewal or shutdown is performed here.
"""
import copy

import numpy as np

from dual_return_pose import return_plan
from motion_safety import POLICY_SETTLE_ERROR_DEG, finite, vector
from policy_trajectory import check_tracking_reserve


class ReviewedReturn:
    def __init__(self, initial):
        if not isinstance(initial, dict) or set(initial) != {'left', 'right'}:
            raise ValueError('Both saved initial arm references are required')
        self._reference = {}
        for side, channel in (('left', 'can0'), ('right', 'can1')):
            state = initial[side]
            if state.get('channel') != channel or not vector(state.get('joints_deg')):
                raise ValueError('Initial reference arm/channel or joints are invalid')
            self._reference[side] = {'channel': channel, 'joints_deg': list(state['joints_deg'])}
        self._used_observation = None

    def step(self, robot, side, review):
        if side not in self._reference:
            raise ValueError('Select a saved arm for reviewed return')
        fields = {'observation_id', 'empty_gripper', 'path_clear', 'recording_active', 'note'}
        if not isinstance(review, dict) or set(review) != fields:
            raise ValueError('Return requires an observation, explicit visual review and recording check')
        if any(review[k] is not True for k in ('empty_gripper', 'path_clear', 'recording_active')):
            raise ValueError('Review empty gripper, full return corridor and active recording first')
        if not isinstance(review['note'], str) or not 1 <= len(review['note']) <= 500:
            raise ValueError('A bounded visual review note is required')
        with robot.operation_lock:
            if robot.fault is not None or any(
                    a.backend.fault is not None or a.backend.busy for a in robot.robots.values()):
                raise ValueError('Faulted or moving arms cannot start a reviewed return')
            arm = robot.robots[side]
            low = arm.backend
            observed = low.observation
            if (not observed or low.consumed
                    or review['observation_id'] != observed['observation_id']
                    or review['observation_id'] == self._used_observation
                    or not finite(observed.get('received_monotonic_s'))
                    or not 0 <= low.clock()-observed['received_monotonic_s'] <= 30):
                raise ValueError('A fresh, unconsumed observation is required for each return segment')
            # Existing health/camera/owner checks remain authoritative. A fault
            # propagates to the normal stop path; it never initiates a return.
            robot.check()
            states = {s: a.backend._read(holding=True) for s, a in robot.robots.items()}
            if any(s.get('moving') is not False or s.get('policy_trajectory_active') is not False
                   for s in states.values()):
                raise ValueError('Both arms must be stationary in powered hold')
            state, old = states[side], observed['raw_state']
            if (any(max(abs(a-b) for a, b in zip(state[k], old[k])) > .05
                    for k in ('joints_deg', 'command_deg'))
                    or abs(state['gripper_raw']-old['gripper_raw']) > .01
                    or abs(state['gripper_command_raw']-old['gripper_command_raw']) > .01):
                raise ValueError('State changed after return review; capture and review again')
            reference = copy.deepcopy(self._reference[side])
            plan = return_plan(state, reference, arm.planner.limits, low.clock())
            if plan is not None:
                if arm.tracking_reserve_deg:
                    check_tracking_reserve(state, np.degrees(plan['joint_positions_rad']).tolist(),
                                           arm.tracking_reserve_deg)
                low.preview_timed_trajectory(plan)
            self._used_observation = review['observation_id']
            executed = low.execute_trajectory(plan) if plan is not None else None
            robot.check()
            after = {s: a.backend._read(holding=True) for s, a in robot.robots.items()}
            other = 'right' if side == 'left' else 'left'
            if (any(s.get('moving') is not False or s.get('policy_trajectory_active') is not False
                    for s in after.values())
                    or max(abs(a-b) for a, b in zip(after[other]['command_deg'], states[other]['command_deg'])) > .05
                    or any(abs(after[s]['gripper_command_raw']-states[s]['gripper_command_raw']) > .01
                           for s in states)):
                robot.abort('Unexpected motion or command change during reviewed return')
            errors = {k: max(abs(a-b) for a, b in zip(after[side][k], reference['joints_deg']))
                      for k in ('joints_deg', 'command_deg')}
            return {'arm': side, 'at_initial': all(e <= POLICY_SETTLE_ERROR_DEG for e in errors.values()),
                    'max_error_deg': errors, 'reference': reference,
                    'executed_segment': executed, 'control_state': 'holding',
                    'review': copy.deepcopy(review), 'review_source': 'caller_visual_review',
                    'collision_checked': False, 'fault_recovery': False}
