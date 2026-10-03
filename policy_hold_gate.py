"""Qualify one owner's powered hold for an explicitly supervised policy trial.

This is measured readiness, not certification of fault or power-loss behavior.
"""
from collections import deque

from motion_safety import feedback_issues, finite, vector, POLICY_HOLD_ERROR_DEG


class PolicyHoldGate:
    def __init__(self):
        self.reset()

    def reset(self):
        self.owner = None
        self.qualified_owner = None
        self.samples = deque(maxlen=200)

    def available(self, owner, enabled):
        return bool(enabled and owner and owner == self.qualified_owner)

    def observe(self, state, sample_time):
        owner = state.get('owner')
        if not state.get('enabled') or not owner:
            self.reset()
            return
        if owner != self.owner:
            self.reset()
            self.owner = owner
        if self.qualified_owner == owner:
            return
        healthy = (state.get('control_state') == 'holding'
                   and state.get('worker_protocol_version') == 2
                   and state.get('robot_status') == 'ready'
                   and state.get('error_codes') == []
                   and not feedback_issues(state)
                   and vector(state.get('command_deg'))
                   and vector(state.get('hold_target_deg'))
                   and finite(state.get('gripper_command_raw'))
                   and finite(sample_time))
        if not healthy:
            self.samples.clear()
            return
        q, command = state['joints_deg'], state['command_deg']
        grip = state['gripper_command_raw']
        if (max(abs(a-b) for a, b in zip(q, command)) > POLICY_HOLD_ERROR_DEG
                or max(abs(a-b) for a, b in zip(state['hold_target_deg'], command)) > .05
                or abs(grip-state['gripper_target_raw']) > .001):
            self.samples.clear()
            return
        if self.samples:
            last = self.samples[-1]
            if sample_time == last[0]:
                return
            if (not 0 < sample_time-last[0] <= .15
                    or max(abs(a-b) for a, b in zip(command, last[2])) > .001
                    or abs(grip-last[3]) > .001):
                self.samples.clear()
        self.samples.append((sample_time, q[:], command[:], grip, state['gripper_raw']))
        while self.samples and sample_time-self.samples[0][0] > 3.3:
            self.samples.popleft()
        if len(self.samples) < 21 or sample_time-self.samples[0][0] < 3:
            return
        stable_arm = all(max(axis)-min(axis) <= .1 for axis in zip(*(s[1] for s in self.samples)))
        grips = [s[4] for s in self.samples]
        if stable_arm and max(grips)-min(grips) <= .02:
            self.qualified_owner = owner
