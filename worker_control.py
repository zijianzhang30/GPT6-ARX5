"""Bounded SDK command dispatch, importable without constructing hardware."""
import time

from control import LOWER, UPPER, vector
from motion_safety import finite

PROTOCOL_VERSION = 2


class WorkerControl:
    def __init__(self, arm, *, clock=time.monotonic):
        self.arm, self.clock = arm, clock
        self.active = False
        self.fault = None
        self.last_command = None
        self.last_issued = None
        self.closed = False

    def protect(self, reason=None):
        self.arm.set_arm_status(2)
        self.active = False
        if reason is not None and self.fault is None:
            self.fault = reason

    def cycle(self, commands, *, rx_age, error_codes):
        if self.closed:
            return
        if any(cmd.get('action') == 'shutdown' for cmd in commands):
            self.protect()
            self.closed = True
            return
        # A pause supersedes every target already queued in this batch.
        if any(cmd.get('action') == 'pause' for cmd in commands):
            self.protect()
            return
        now = self.clock()
        if self.fault is not None:
            return
        if not finite(rx_age) or not 0 <= rx_age <= .5:
            self.protect('CAN feedback timeout or invalid age')
            return
        if any(code > 10 for code in error_codes):
            self.protect('SDK motor fault')
            return
        # Check before draining targets: queued traffic cannot revive a lost lease.
        if self.active and now-self.last_command > .35:
            self.protect('Worker command timeout')
            return
        targets = []
        previous = self.last_issued
        for cmd in commands:
            if cmd.get('action') != 'target':
                self.protect('Unknown worker command')
                return
            issued = cmd.get('issued_at')
            if (not finite(issued) or not 0 <= now-issued <= .15
                    or previous is not None and issued <= previous):
                self.protect('Expired, unordered or unstamped target')
                return
            try:
                q = vector(cmd['q'], 6)
                g = cmd.get('grip')
                if (q < LOWER).any() or (q > UPPER).any():
                    raise ValueError('Joint target outside SDK limits')
                if g is not None and (not finite(g) or not 0 <= g <= 5):
                    raise ValueError('Gripper target outside SDK limits')
            except (KeyError, TypeError, ValueError) as exc:
                self.protect(str(exc))
                return
            previous = issued
            targets.append((q, g, issued))
        if not targets:
            return
        # All entries were validated; only the newest setpoint is useful now.
        q, g, issued = targets[-1]
        if self.clock()-issued > .15:
            self.protect('Target expired before SDK submission')
            return
        self.arm.set_joint_positions(q.tolist())
        if g is not None:
            self.arm.set_catch(g)
        self.arm.set_arm_status(5)
        self.last_command = issued
        self.last_issued = issued
        self.active = True
