import unittest
from unittest.mock import Mock

from control import START
from worker_control import WorkerControl


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.now = 100.
        self.arm = Mock()
        self.worker = WorkerControl(self.arm, clock=lambda: self.now)

    def target(self, **changes):
        return {'action': 'target', 'q': START.tolist(), 'grip': .8,
                'issued_at': self.now, **changes}

    def cycle(self, *commands, **health):
        self.worker.cycle(commands, **{'rx_age': .01, 'error_codes': [], **health})

    def test_fresh_target_and_idle_cycles_preserve_active_state(self):
        self.cycle(self.target())
        self.assertTrue(self.worker.active)
        self.arm.set_joint_positions.assert_called_once_with(START.tolist())
        self.arm.set_catch.assert_called_once_with(.8)
        self.now += .02
        self.cycle()
        self.assertIsNone(self.worker.fault)

    def test_expired_unstamped_future_and_replayed_targets_never_move(self):
        for stamp in (None, 99., 101., True, float('nan')):
            with self.subTest(stamp=stamp):
                self.setUp()
                self.cycle(self.target(issued_at=stamp))
                self.arm.set_joint_positions.assert_not_called()
                self.assertIsNotNone(self.worker.fault)
                self.now += .02
                self.cycle(self.target())
                self.arm.set_joint_positions.assert_not_called()
        self.setUp()
        target = self.target()
        self.cycle(target)
        self.now += .01
        self.cycle(target)
        self.assertEqual(self.arm.set_joint_positions.call_count, 1)
        self.assertFalse(self.worker.active)

    def test_lease_expiry_checked_before_new_target_and_latches(self):
        self.cycle(self.target())
        self.now += .36
        self.cycle(self.target())
        self.assertEqual(self.worker.fault, 'Worker command timeout')
        self.assertEqual(self.arm.set_joint_positions.call_count, 1)
        self.now += .02
        self.cycle(self.target())
        self.assertEqual(self.arm.set_joint_positions.call_count, 1)

    def test_pause_and_shutdown_supersede_queued_targets(self):
        for action in ('pause', 'shutdown'):
            with self.subTest(action=action):
                self.setUp()
                self.cycle(self.target(issued_at=99.99), {'action': action}, self.target())
                self.arm.set_joint_positions.assert_not_called()
                self.arm.set_arm_status.assert_called_once_with(2)
                self.assertFalse(self.worker.active)
                self.assertEqual(self.worker.closed, action == 'shutdown')

    def test_sdk_or_can_fault_prevents_even_first_target(self):
        for health in ({'error_codes': [12]}, {'rx_age': 1.}, {'rx_age': float('nan')}):
            with self.subTest(health=health):
                self.setUp()
                self.cycle(self.target(), **health)
                self.arm.set_joint_positions.assert_not_called()
                self.assertIsNotNone(self.worker.fault)

    def test_batch_is_validated_before_any_target_and_coalesced(self):
        self.cycle(self.target(issued_at=99.98), self.target(grip=float('nan')))
        self.arm.set_joint_positions.assert_not_called()
        self.setUp()
        self.cycle(self.target(issued_at=99.98), self.target(grip=.9))
        self.arm.set_joint_positions.assert_called_once()
        self.arm.set_catch.assert_called_once_with(.9)


if __name__ == '__main__':
    unittest.main()
