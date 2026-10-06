"""One isolated, open-empty-left J3 measurement; never a contact-task recovery.

The previous Cartesian probe remains failed/locked in its immutable log. This
diagnostic grants only one fixed +0.65 degree J3 path, then locks again on every
outcome. Original vision, owner, heartbeat, tracking and fault stops still apply.
"""
import numpy as np

from empty_fine_probe import EmptyFineProbeBackend
from policy_trajectory import check_tracking_reserve


def joint_diagnostic_plan(state):
    start = np.radians(state['command_deg'])
    t = np.linspace(0., 1., 101)[1:]
    fraction = 10*t**3-15*t**4+6*t**5
    points = np.tile(start, (len(t), 1))
    points[:, 2] += np.radians(.65)*fraction
    return {'start_joint_positions_rad': start,
            'planning_measured_joint_positions_rad': np.radians(state['joints_deg']),
            'joint_positions_rad': points, 'relative_times_s': (2*t).tolist(),
            'result': {'note': 'Single open-empty-left J3 +0.65deg CAN response diagnostic',
                       'planned_duration_s': 2., 'collision_checked': False,
                       'contact_motion_qualified': False}}


class EmptyJointDiagnosticBackend(EmptyFineProbeBackend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostic_reanchors = 0

    def renew_session(self):
        if self.diagnostic_reanchors >= 2:
            raise ValueError('At most two diagnostic start reanchors; no repeated recovery')
        result = super().renew_session()
        self.diagnostic_reanchors += 1
        return result

    def preview_probe(self, robot, plan):
        if self.probe_attempted:
            raise ValueError('Isolated joint diagnostic completed; all new targets locked')
        state = self._read(holding=True)
        if (state.get('channel') != 'can0' or state.get('moving') is not False
                or state.get('policy_trajectory_active') is not False
                or not 4.79 <= state['gripper_command_raw'] <= 4.81
                or abs(state['gripper_raw']-state['gripper_command_raw']) > .15):
            raise ValueError('Diagnostic needs stationary fully open empty left; visually verify empty')
        if np.max(np.abs(np.subtract(state['command_deg'], state['joints_deg']))) > .05:
            raise ValueError('Fresh measured hold anchor within 0.05 degrees required')
        if robot.tracking_reserve_deg < 3.5:
            raise ValueError('Diagnostic retains 3.5 degree tracking reserve')
        expected = joint_diagnostic_plan(state)
        # Exact path allowlist, not an arbitrary joint-motion interface.
        for key in ('start_joint_positions_rad', 'planning_measured_joint_positions_rad',
                    'joint_positions_rad', 'relative_times_s'):
            supplied, wanted = np.asarray(plan[key]), np.asarray(expected[key])
            if (supplied.shape != wanted.shape or not np.all(np.isfinite(supplied))
                    or not np.allclose(supplied, wanted, rtol=0, atol=1e-9)):
                raise ValueError('Only the fixed two-second +0.65 degree J3 diagnostic is allowed')
        check_tracking_reserve(state, np.degrees(expected['joint_positions_rad']).tolist(),
                               robot.tracking_reserve_deg)
        self._probe_preflight = True
        try:
            return self._trajectory_inputs(plan)
        finally:
            self._probe_preflight = False
