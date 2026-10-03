import unittest

from policy_hold_gate import PolicyHoldGate
from test_r5_policy_backend import Workbench


class HoldGateTests(unittest.TestCase):
    def test_bounded_residual_qualifies_but_excessive_residual_does_not(self):
        self.state['joints_deg'][0] += 2.8
        self.feed()
        self.assertTrue(self.gate.available(self.state['owner'], True))
        self.gate.reset()
        self.state['joints_deg'][0] += .3
        self.feed()
        self.assertFalse(self.gate.available(self.state['owner'], True))

    def setUp(self):
        self.gate = PolicyHoldGate()
        self.state = Workbench().state()

    def feed(self, duration=3.2):
        for index in range(round(duration/.05)+1):
            self.gate.observe(self.state, 100+index*.05)

    def test_requires_three_seconds_of_real_stable_samples(self):
        self.feed(2.9)
        self.assertFalse(self.gate.available(self.state['owner'], True))
        self.gate.observe(self.state, 103.)
        self.assertTrue(self.gate.available(self.state['owner'], True))
        self.state['control_state'] = 'active'
        self.gate.observe(self.state, 103.1)
        self.assertTrue(self.gate.available(self.state['owner'], True))
        self.assertFalse(self.gate.available(self.state['owner'], False))

    def test_duplicate_samples_and_faults_do_not_qualify(self):
        for _ in range(200):
            self.gate.observe(self.state, 100.)
        self.assertFalse(self.gate.available(self.state['owner'], True))
        for field, value in (('control_state', 'active'), ('worker_protocol_version', None),
                             ('error_codes', [12]), ('feedback_age_ms', 500),
                             ('gripper_command_raw', float('nan'))):
            with self.subTest(field=field):
                self.setUp()
                self.state[field] = value
                self.feed()
                self.assertFalse(self.gate.available(self.state['owner'], True))

    def test_drift_or_changed_command_never_qualifies(self):
        for field in ('joints_deg', 'command_deg'):
            self.setUp()
            for index in range(100):
                self.state[field][0] = .2*(index % 2)
                self.gate.observe(self.state, 100+index*.05)
            self.assertFalse(self.gate.available(self.state['owner'], True))

    def test_disable_or_new_owner_loses_qualification(self):
        self.feed()
        self.state.update(enabled=False, owner=None)
        self.gate.observe(self.state, 103.3)
        self.assertIsNone(self.gate.qualified_owner)
        self.setUp()
        self.feed()
        self.state['owner'] = 'another'
        self.gate.observe(self.state, 103.3)
        self.assertFalse(self.gate.available('another', True))
