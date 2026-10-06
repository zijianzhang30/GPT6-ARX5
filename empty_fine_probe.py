"""One-shot, contact-free small-motion measurement, not a grasp controller.

Ordinary Cartesian execution retains its session minimum. The sole exception is
an explicitly reviewed, open-empty-gripper +3 mm base-Z probe. A stationary
under-response is a FAILED measurement, never a settled move/contact inference.
Its target is cancelled using the existing measured-hold reanchor. The session
then prohibits every new target, including renewal, on success AND failure.
Health, vision, ownership, tracking and transport failures keep original stops.
"""
from collections import deque

import numpy as np

from policy_trajectory import debit_trajectory, check_tracking_reserve
from r5_policy_backend import R5PolicyBackend, R5ExecutionFault
from visual_control import step_settled


def probe_metrics(initial, target, samples, now):
    q0 = np.asarray(initial['joints_deg'])
    command0 = np.asarray(initial['command_deg'])
    target = np.asarray(target)
    latest = np.asarray(samples[-1][1])
    delta = target-command0
    changed = np.abs(delta) > .1
    if not np.any(changed):
        raise ValueError('Probe must have measurable joint displacement')
    projected = float(np.dot((latest-q0)[changed], delta[changed]) /
                      np.dot(delta[changed], delta[changed]))
    residual = float(np.max(np.abs(latest-target)))
    stable = step_settled({'joints_deg': latest}, latest, samples, now,
                          max_residual_deg=.15)
    passed = (stable and .8 <= projected <= 1.2 and residual <= .15
              and step_settled({'joints_deg': target}, q0, samples, now,
                    command_initial=command0, aggregate_progress=True,
                    min_progress=.8, max_residual_deg=.15))
    return {'passed': bool(passed), 'stationary': bool(stable),
            'projected_progress': projected, 'max_endpoint_error_deg': residual,
            'measured_delta_deg': (latest-q0).tolist()}


class EmptyFineProbeBackend(R5PolicyBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.probe_attempted = False
        self._probe_preflight = False

    def _action_target(self, *args, **kwargs):
        if self.probe_attempted:
            raise ValueError('One-shot probe finished; new targets are locked pending review')
        return super()._action_target(*args, **kwargs)

    def renew_session(self):
        if self.probe_attempted:
            raise ValueError('Probe lock cannot be cleared by renewing the session')
        return super().renew_session()

    def _validate_cartesian_amplitude(self, amplitude):
        if self._probe_preflight:
            if not .25 <= amplitude <= 1.:
                raise ValueError('Empty probe requires 0.25..1 degree endpoint amplitude')
        else:
            super()._validate_cartesian_amplitude(amplitude)

    def preview_probe(self, robot, plan):
        from gpt_policy.geometry.poses import rotation_distance
        if self.probe_attempted:
            raise ValueError('Only one empty probe is permitted')
        state = self._read(holding=True)
        if (state.get('moving') is not False or state.get('policy_trajectory_active') is not False
                or not 4.79 <= state['gripper_command_raw'] <= 4.81
                or abs(state['gripper_raw']-state['gripper_command_raw']) > .15):
            raise ValueError('Probe requires stationary, fully open empty gripper; visually verify empty')
        if np.max(np.abs(np.subtract(state['command_deg'], state['joints_deg']))) > .05:
            raise ValueError('Probe needs a fresh measured hold anchor before planning')
        if robot.tracking_reserve_deg < 3.5:
            raise ValueError('Probe retains at least 3.5 degree tracking reserve')
        points = np.asarray(plan['joint_positions_rad'])
        start = np.asarray(plan['start_joint_positions_rad'])
        if np.max(np.abs(np.degrees(points-start))) > 1.:
            raise ValueError('Every probe point must remain within 1 degree of start')
        if np.sum(np.abs(np.diff(np.degrees(np.vstack([start, points])), axis=0))) > 3.:
            raise ValueError('Probe joint path travel exceeds 3 degrees')
        poses = np.asarray([robot.frames.sdk_to_tcp(robot.solver.forward_kinematics(q))
                            for q in np.vstack([start, points])])
        delta = poses[:, :3]-poses[0, :3]
        if (np.max(np.abs(delta[:, :2])) > .00005 or np.min(delta[:, 2]) < -.00005
                or np.max(delta[:, 2]) > .00305 or abs(delta[-1, 2]-.003) > .00005
                or np.min(np.diff(delta[:, 2])) < -.00002
                or any(rotation_distance(p[3:], poses[0, 3:]) > .0002 for p in poses)):
            raise ValueError('Probe is exclusively +3 mm base Z with fixed orientation')
        check_tracking_reserve(state, np.degrees(points).tolist(), robot.tracking_reserve_deg)
        self._probe_preflight = True
        try:
            return self._trajectory_inputs(plan)
        finally:
            self._probe_preflight = False

    def execute_probe(self, robot, plan):
        with self.operation_lock:
            points, args, initial, target, start, measured_start = self.preview_probe(robot, plan)
            with self.command_lock:
                debit_trajectory(self.guard, initial, points)
                self.consumed, self.busy, self.probe_attempted = True, True, True
            try:
                self._command('resume')
                fresh = self._read()
                if (np.max(np.abs(np.subtract(fresh['joints_deg'], measured_start))) > .05
                        or abs(fresh['gripper_command_raw']-initial['gripper_command_raw']) > .01):
                    raise R5ExecutionFault('Probe state changed while resuming')
                self.vision_check()
                self._command('policy_trajectory', start_deg=start, points_deg=points,
                              times_s=plan['relative_times_s'], issued_at=self.clock())
                playback_deadline = self.clock()+plan['relative_times_s'][-1]+1
                while True:
                    self.check()
                    current = self._read()
                    self._check_probe_target(current, initial, points[-1])
                    if current.get('policy_trajectory_active') is False:
                        if np.max(np.abs(np.subtract(current['command_deg'], points[-1]))) > .05:
                            raise R5ExecutionFault('Probe path ended before target submission')
                        break
                    if self.clock() > playback_deadline:
                        raise R5ExecutionFault('Probe playback timed out')
                    self.sleep(.02)
                deadline = self.clock()+5
                samples, trace = deque(maxlen=16), []
                while True:
                    self.check()
                    current = self._read()
                    self._check_probe_target(current, initial, points[-1])
                    if np.max(np.abs(np.subtract(current['command_deg'], points[-1]))) > .05:
                        raise R5ExecutionFault('Probe endpoint command changed')
                    now = self.clock()
                    samples.append((now, np.asarray(current['joints_deg'])))
                    trace.append({'at_s': now, 'joints_deg': current['joints_deg'],
                                  'command_deg': current['command_deg'],
                                  'gripper_raw': current['gripper_raw']})
                    self.last_execution_feedback = {'initial_measured_deg': initial['joints_deg'],
                        'initial_command_deg': initial['command_deg'], 'target': target, 'samples': trace}
                    metrics = probe_metrics(initial, points[-1], samples, now)
                    if metrics['passed'] or now >= deadline:
                        break
                    self.sleep(.05)
                if not metrics['stationary']:
                    raise R5ExecutionFault('Probe did not become stationary; original fault stop required')
                # A failed stationary measurement is not a successful motion. Cancel
                # the outstanding tiny empty-arm error rather than retry/accumulate.
                self._command('pause_hold')
                deadline = self.clock()+1
                while self._read().get('control_state') != 'holding':
                    self.check()
                    if self.clock() > deadline:
                        raise R5ExecutionFault('Probe did not establish powered hold')
                    self.sleep(.02)
                held = self._read(holding=True)
                if np.max(np.abs(np.subtract(held['command_deg'], points[-1]))) > .05:
                    raise R5ExecutionFault('Probe hold changed endpoint unexpectedly')
                if not metrics['passed']:
                    held = self._reanchor_hold_to_measured(held)
                elif np.max(np.abs(np.subtract(held['joints_deg'], points[-1]))) > .15:
                    raise R5ExecutionFault('Probe moved outside endpoint tolerance while establishing hold')
                self._check_probe_target(held, initial, points[-1])
                return {**metrics, 'requested_joints_deg': points[-1],
                        'pre_cancel_measured_joints_deg': current['joints_deg'],
                        'held_joints_deg': held['command_deg'], 'motion_locked': True,
                        'failed_target_cancelled': not metrics['passed'],
                        'control_state': 'holding', 'source_observation_id': args['observation_id'],
                        'grasp_verified': False, 'collision_checked': False,
                        'contact_motion_qualified': False, 'feedback': self.last_execution_feedback}
            except Exception as exc:
                self._fail(exc, request_stop=True)
            finally:
                self.busy = False

    @staticmethod
    def _check_probe_target(state, initial, target):
        if abs(state['gripper_command_raw']-initial['gripper_command_raw']) > .01:
            raise R5ExecutionFault('Gripper changed during empty probe')
        if np.max(np.abs(np.subtract(state['joints_deg'], initial['joints_deg']))) > 1.15:
            raise R5ExecutionFault('Measured probe excursion exceeded 1.15 degrees')
        delta = np.subtract(target, initial['command_deg'])
        moved = np.subtract(state['joints_deg'], initial['joints_deg'])
        changed = np.abs(delta) > .1
        if np.any(moved[changed]*np.sign(delta[changed]) < -.1):
            raise R5ExecutionFault('Measured probe moved in the wrong direction')
