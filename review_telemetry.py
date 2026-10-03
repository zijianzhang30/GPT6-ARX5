"""Readout and timing for attended review; no robot command or limit changes."""
import time


class ReviewTimer:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.ready_at = None
        self.pending = None
        self.completed = 0
        self.command_s = 0.
        self.input_wait_s = 0.

    def ready(self):
        self.ready_at = self.clock()

    def begin(self, command):
        if self.pending is not None:
            raise RuntimeError('A review command is already running')
        now = self.clock()
        wait = 0. if self.ready_at is None else max(0., now-self.ready_at)
        self.pending = dict(command_index=self.completed+1, command=command,
                            input_wait_before_s=wait, started_monotonic_s=now)
        self.input_wait_s += wait
        return dict(self.pending)

    def finish(self, outcome):
        if self.pending is None:
            raise RuntimeError('No review command is running')
        now = self.clock()
        result = {**self.pending, 'outcome': outcome,
                  'command_wall_s': max(0., now-self.pending['started_monotonic_s'])}
        self.command_s += result['command_wall_s']
        self.completed += 1
        self.pending = None
        self.ready_at = now
        result['totals'] = self.summary()
        return result

    def summary(self):
        return dict(completed_commands=self.completed,
                    completed_command_wall_s=self.command_s,
                    input_wait_before_commands_s=self.input_wait_s,
                    note='Command wall time includes planning, execution, settling and capture. '
                         'Input wait includes attended review/tool round trips; it is not '
                         'a measurement of model inference alone. Open idle time is excluded.')


def review_packet(state, images, stamp, *, initial=None):
    """Keep the small fields needed to decide the next step in one readout."""
    arms = {}
    for side, arm in state['arms'].items():
        raw = arm['raw_state']
        budget = arm.get('motion_budget', {})
        limits = budget.get('limits', {})
        remaining = {}
        for label, limit, used in (
                ('actions', 'session_proposals', 'accepted_proposals'),
                ('joint_travel_deg', 'session_joint_travel_deg', 'proposed_joint_travel_deg'),
                ('gripper_travel_raw', 'session_gripper_travel_raw', 'proposed_gripper_travel_raw')):
            if limit in limits and used in budget:
                remaining[label] = limits[limit]-budget[used]
        errors = None
        if initial is not None:
            goal = initial[side]['joints_deg']
            errors = {key: max(abs(a-b) for a, b in zip(raw[key], goal))
                      for key in ('joints_deg', 'command_deg')}
        arms[side] = {
            'observation_id': arm['observation_id'],
            'tcp': arm['tcp_command_xyzquat'],
            'measured_tcp': arm['tcp_xyzquat'],
            'opening': arm['gripper_command_normalized'],
            'bounds': arm['gripper_next_opening_bounds'],
            'health': {k: raw.get(k) for k in (
                'robot_status', 'enabled', 'moving', 'control_state', 'owner',
                'error_codes', 'worker_fault_reason', 'feedback_age_ms', 'rx_age_ms')},
            'joints_deg': raw['joints_deg'], 'command_deg': raw['command_deg'],
            'budget_remaining': remaining, 'return_error_deg': errors,
        }
    return {'observation': stamp, 'images': images, 'arms': arms,
            'collision_checked': False, 'physical_success_verified': False}
