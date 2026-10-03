"""Bounded, timestamped reference playback for the existing R5 worker."""
import bisect
import copy
import math

import numpy as np

from motion_safety import (finite, vector, JOINT_STEP_DEG, JOINT_STEP_NORM_DEG,
                           SUPERVISED_SPEED)


class PolicyTrajectory:
    protocol = 1

    def __init__(self, start_deg, points_deg, times_s, lower_deg, upper_deg, now):
        if (not vector(start_deg) or not isinstance(points_deg, list)
                or not 1 <= len(points_deg) <= 10000
                or not all(vector(q) for q in points_deg)
                or not isinstance(times_s, list) or len(times_s) != len(points_deg)
                or not all(finite(t) for t in times_s) or not finite(now)):
            raise ValueError('Invalid trajectory samples')
        if not vector(lower_deg) or not vector(upper_deg):
            raise ValueError('Invalid trajectory joint limits')
        self.times = np.r_[0., times_s]
        self.points = np.asarray([start_deg]+points_deg, dtype=float)
        self.started = self.last_tick = now
        if np.any(np.diff(self.times) <= 0) or self.times[-1] > 30:
            raise ValueError('Trajectory times must increase within 30 seconds')
        if (np.any(self.points < np.asarray(lower_deg)+2)
                or np.any(self.points > np.asarray(upper_deg)-2)):
            raise ValueError('Trajectory enters joint limit margin')
        displacement = self.points-self.points[0]
        if (np.max(np.abs(displacement)) > JOINT_STEP_DEG+1e-9
                or np.max(np.linalg.norm(displacement, axis=1)) > JOINT_STEP_NORM_DEG+1e-9):
            raise ValueError('Whole trajectory exceeds the existing observed-step envelope')
        velocity = np.diff(self.points, axis=0)/np.diff(self.times)[:, None]
        if np.max(np.abs(velocity)) > 30*SUPERVISED_SPEED+1e-6:
            raise ValueError(
                f'Trajectory exceeds {SUPERVISED_SPEED:.0%} joint speed'
            )

    def sample(self, now):
        if not finite(now) or now < self.last_tick or now-self.last_tick > .15:
            raise ValueError('Trajectory playback deadline missed')
        self.last_tick = now
        elapsed = now-self.started
        if elapsed >= self.times[-1]:
            return self.points[-1].copy(), np.zeros(6), True
        index = bisect.bisect_right(self.times, elapsed)-1
        duration = self.times[index+1]-self.times[index]
        velocity = (self.points[index+1]-self.points[index])/duration
        return self.points[index]+velocity*(elapsed-self.times[index]), velocity, False


def preview_trajectory(guard, state, points_deg):
    """Reject a candidate without describing the copied guard as a live fault."""
    guard.require_healthy()
    preview = copy.deepcopy(guard)
    try:
        debit_trajectory(preview, state, points_deg)
    except ValueError as exc:
        reason = preview.failure or str(exc)
        raise ValueError('Trajectory preview rejected before execution: ' + reason
                         + '; no motion or budget consumed; live session is not fault-latched. '
                         'Adjust the target for a step-limit rejection; a session-budget '
                         'boundary requires host renewal.') from exc


def check_tracking_reserve(state, points_deg, reserve_deg):
    """Reject a path before dispatch; never alter the measured-state guard.

    A held command already within the extra reserve can remain still or move
    inward, but cannot move farther toward that boundary. Every intermediate
    sample is checked, including the held-command path start.
    """
    from motion_safety import JOINT_MARGIN_DEG
    if not finite(reserve_deg) or reserve_deg < 0:
        raise ValueError('Invalid planning tracking reserve')
    if (not vector(state.get('command_deg')) or not vector(state.get('lower_deg'))
            or not vector(state.get('upper_deg')) or not points_deg
            or not all(vector(q) for q in points_deg)):
        raise ValueError('Invalid planning reserve inputs')
    start = np.asarray(state['command_deg'], dtype=float)
    lower, upper = np.asarray(state['lower_deg']), np.asarray(state['upper_deg'])
    q = np.asarray([start.tolist(), *points_deg], dtype=float)
    if (np.any(lower >= upper) or np.any(q < lower+JOINT_MARGIN_DEG)
            or np.any(q > upper-JOINT_MARGIN_DEG)):
        raise ValueError('Path violates existing joint limit margin')
    margin = JOINT_MARGIN_DEG+reserve_deg
    floor = np.minimum(lower+margin, start)
    ceiling = np.maximum(upper-margin, start)
    bad = (q < floor-1e-9) | (q > ceiling+1e-9)
    if np.any(bad):
        sample, joint = np.argwhere(bad)[0]
        raise ValueError(
            f'Planning tracking reserve rejected before execution: J{joint+1}, '
            f'sample {sample}, target {q[sample, joint]:.6f} deg; '
            f'allowed [{floor[joint]:.6f}, {ceiling[joint]:.6f}] deg. '
            'Adjust the path; no motion or budget consumed. '
            'Existing runtime guards are unchanged.')
    return {'extra_tracking_reserve_deg': reserve_deg,
            'requested_total_margin_deg': margin,
            'min_distance_to_limit_deg': np.minimum(q-lower, upper-q).min(axis=0).tolist(),
            'held_start_inside_extra_reserve': ((start < lower+margin) | (start > upper-margin)).tolist()}


def debit_trajectory(guard, state, points_deg):
    """Debit one model action, counting every segment including reversals."""
    from motion_safety import SESSION_JOINT_TRAVEL_DEG, SESSION_EXCURSION_DEG
    guard.check_state(state)
    if not points_deg or not all(vector(q) for q in points_deg):
        guard.fail('Invalid trajectory joint samples')
    cost = 0.
    previous = state['joints_deg']
    for q in points_deg:
        guard._check_margin(q)
        if max(abs(a-b) for a, b in zip(q, guard.anchor)) > SESSION_EXCURSION_DEG:
            guard.fail('Trajectory leaves session envelope')
        delta = [a-b for a, b in zip(q, state['joints_deg'])]
        if max(map(abs, delta)) > JOINT_STEP_DEG+1e-9 or math.hypot(*delta) > JOINT_STEP_NORM_DEG+1e-9:
            guard.fail('Trajectory exceeds observed-step envelope')
        cost += sum(abs(a-b) for a, b in zip(q, previous))
        previous = q
    if guard.joint_travel+cost > SESSION_JOINT_TRAVEL_DEG+1e-9:
        guard.fail('Trajectory exhausts session joint travel budget')
    old_cost = guard.joint_travel
    guard.accept(state, {'joints_deg': points_deg[-1]})
    guard.joint_travel = old_cost+cost
