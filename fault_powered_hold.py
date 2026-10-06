"""Opt-in quarantine after a stationary joint arrival failure.

This is not a safety stop or hardware qualification. No enable, target, resume,
gripper change, retry, fault reset or homing command is available here.
"""
import copy

from motion_safety import POLICY_HOLD_ERROR_DEG, vector
from r5_policy_backend import R5ExecutionFault


def stationary(state):
    if (state.get('moving') is not False
            or state.get('policy_trajectory_active') is not False
            or not vector(state.get('velocity_deg'))
            or max(map(abs, state['velocity_deg'])) > .5):
        raise R5ExecutionFault('Fault hold requires stationary measured feedback and no active trajectory')
    if max(abs(a-b) for a, b in zip(state['command_deg'], state['joints_deg'])) > POLICY_HOLD_ERROR_DEG:
        raise R5ExecutionFault('Fault hold exceeds the original hold tracking limit')
    if abs(state['gripper_target_raw']-state['gripper_command_raw']) > .01:
        raise R5ExecutionFault('Fault hold cannot retain a pending gripper change')
    if any(not lo <= q <= hi for q, lo, hi in zip(
            state['command_deg'], state['lower_deg'], state['upper_deg'])):
        raise R5ExecutionFault('Fault hold command is outside joint limits')


def require_stationary_arrival(low, state):
    trace = low.last_execution_feedback or {}
    target = trace.get('target', {})
    if set(target) != {'joints_deg'} or not vector(target['joints_deg']):
        raise R5ExecutionFault('Only a joint arrival failure can retain fault hold')
    now = low.clock()
    samples = [s for s in trace.get('samples', []) if 0 <= now-s['at_s'] <= .65]
    if (len(samples) < 5 or samples[-1]['at_s']-samples[0]['at_s'] < .5
            or not 0 <= now-samples[-1]['at_s'] <= .15
            or any(not 0 < b['at_s']-a['at_s'] <= .15 for a, b in zip(samples, samples[1:]))):
        raise R5ExecutionFault('Fault hold requires a fresh continuous stationary history')
    if any(not vector(s['joints_deg']) or not vector(s['command_deg']) for s in samples):
        raise R5ExecutionFault('Invalid arrival history')
    measured = [s['joints_deg'] for s in samples] + [state['joints_deg']]
    if any(max(q)-min(q) > .1 for q in zip(*measured)):
        raise R5ExecutionFault('Measured joints have not stopped')
    if any(max(abs(a-b) for a, b in zip(q, target['joints_deg'])) > .05
           for q in [s['command_deg'] for s in samples] + [state['command_deg']]):
        raise R5ExecutionFault('Final joint command has not been submitted and held')
    if any(s.get('checks', {}).get('grip_ok') is not True
           or abs(s['gripper_command_raw']-state['gripper_command_raw']) > .01 for s in samples):
        raise R5ExecutionFault('Gripper changed during arrival history')


class FaultHold:
    def __init__(self, low, state):
        self.low = low
        # Preserve the exact session envelope; this monitor never accepts a
        # proposal. The actual task guard is latched and never reset.
        self.guard = copy.deepcopy(low.guard)
        self.reference = copy.deepcopy(state)
        self.last_state = None
        self.deadline = low.clock()+1.
        self.phase = 'entering'

    def check(self):
        low = self.low
        state = low._validate_state(low.client.state(), holding=self.phase == 'holding', guard=self.guard)
        stationary(state)
        if (max(abs(a-b) for a, b in zip(state['command_deg'], self.reference['command_deg'])) > .05
                or abs(state['gripper_command_raw']-self.reference['gripper_command_raw']) > .01
                or max(abs(a-b) for a, b in zip(state['joints_deg'], self.reference['joints_deg'])) > .1):
            raise R5ExecutionFault('Fault hold target changed or measured position drifted')
        if state.get('control_state') == 'holding':
            low._validate_state(state, holding=True, guard=self.guard)
            self.phase = 'holding'
        elif self.phase == 'holding' or low.clock() >= self.deadline:
            raise R5ExecutionFault('Fault powered hold was not established or was lost')
        elif state.get('control_state') not in ('active', 'pausing'):
            raise R5ExecutionFault('Unexpected fault hold transition')
        low.vision_check()
        low.client.command('heartbeat')
        self.last_state = copy.deepcopy(state)
        return state


def begin_fault_hold(low, error, *, from_settle):
    with low.command_lock:
        if not low.retain_settle_fault_hold or low.fault is not None or not low.engaged:
            raise R5ExecutionFault('Fault hold is not enabled for a healthy owned session')
        if not from_settle and low.busy:
            raise R5ExecutionFault('Companion arm is executing; cannot retain stationary fault hold')
        state = low._read_locked(holding=not from_settle)
        stationary(state)
        low.vision_check()
        if from_settle:
            require_stationary_arrival(low, state)
        hold = FaultHold(low, state)
        low.fault = str(error)
        low.guard.latch(low.fault)
        low.fault_hold = hold
        if state.get('control_state') != 'holding':
            low.client.command('pause_hold')
    # Never monopolize the command lock while waiting for the pause profile.
    while True:
        low.supervise()
        if hold.phase == 'holding':
            return copy.deepcopy(hold.last_state)
        low.sleep(.02)
