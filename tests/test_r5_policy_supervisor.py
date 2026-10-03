import json
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock

from r5_policy_backend import R5ExecutionFault, R5PolicyBackend
from r5_policy_deployment import run_r5_policy
from r5_policy_supervisor import R5PolicySupervisor, SupervisedCameras
from test_r5_policy_backend import Workbench


class Cameras:
    def __init__(self):
        self.count = 0
        self.block = threading.Event()
        self.block.set()
        self.fail = False

    def snapshot(self, *, after=None):
        self.block.wait(2)
        if self.fail:
            raise RuntimeError('Disconnected camera')
        self.count += 1
        return {'left': self.count, 'top': self.count}

    def describe(self, images):
        return [{'sequence': images['left'], 'received_monotonic_s': time.monotonic()}]


class SupervisionTests(unittest.TestCase):
    def setUp(self):
        self.source = Cameras()
        self.cameras = SupervisedCameras(self.source)
        self.cameras.start()
        self.addCleanup(self.cameras.close)
        self.addCleanup(self.source.block.set)
        self.client = Workbench()
        self.backend = R5PolicyBackend(self.client, self.cameras.check)
        self.supervisor = R5PolicySupervisor(self.backend)
        self.supervisor.start()
        self.addCleanup(self.supervisor.close)

    def wait_fault(self):
        self.assertTrue(self.supervisor.done.wait(1.5), 'Supervisor failed to stop')
        with self.assertRaises(R5ExecutionFault):
            self.supervisor.check()

    def test_slow_provider_start_and_decide_use_original_loop_with_heartbeats(self):
        # Provider deliberately never polls the upstream health callback.
        backend = self.backend
        client = self.client

        class SlowAgent:
            def start(self, context):
                time.sleep(.4)

            def decide(self, turn):
                time.sleep(.4)
                return {'name': 'done', 'arguments': {'summary': 'Fixture', 'hindsight': ''}}

        heartbeat_times = []
        original_command = client.command

        def command(action, **fields):
            if action == 'heartbeat':
                heartbeat_times.append(time.monotonic())
            return original_command(action, **fields)

        client.command = command
        runtime = SimpleNamespace(max_decisions=1, interface='test', right_interface='')
        request = SimpleNamespace(instruction='Pick up the tennis ball', content=())
        result = run_r5_policy(runtime, request, backend, self.cameras, SlowAgent(),
                               MagicMock(), supervisor=self.supervisor, display=MagicMock())
        self.assertEqual(result, 'completed')
        self.assertGreater(len(heartbeat_times), 8)
        self.assertLess(max(b-a for a, b in zip(heartbeat_times, heartbeat_times[1:])), .3)
        self.assertTrue(client.current['enabled'])
        self.assertTrue(self.supervisor.thread.is_alive())
        count = len(heartbeat_times)
        time.sleep(.12)
        self.assertGreater(len(heartbeat_times), count)
        self.assertFalse(any(name in ('stop', 'enable', 'home', 'target') for name, _ in client.commands))

    def test_disconnected_camera_stops_without_waiting_for_model(self):
        self.source.fail = True
        self.wait_fault()
        self.assertFalse(self.client.current['enabled'])
        self.assertEqual(sum(n == 'stop' for n, _ in self.client.commands), 1)
        with self.assertRaises(R5ExecutionFault):
            self.backend._command('target', gripper_raw=4.4)
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))

    def test_late_model_motion_is_discarded_after_camera_fault(self):
        source = self.source

        class LateAgent:
            def start(self, context):
                pass

            def decide(self, turn):
                source.fail = True
                time.sleep(.25)
                state = json.loads(turn.observation)['state']
                return {'name': 'move_joints', 'arguments': {
                    'observation_id': state['observation_id'],
                    'positions': state['joint_positions_rad'], 'note': 'Late fixture action'}}

        with self.assertRaises(R5ExecutionFault):
            run_r5_policy(SimpleNamespace(max_decisions=1, interface='test', right_interface=''),
                          SimpleNamespace(instruction='Fixture', content=()), self.backend,
                          self.cameras, LateAgent(), MagicMock(), supervisor=self.supervisor,
                          display=MagicMock())
        self.assertFalse(self.client.current['enabled'])
        self.assertFalse(any(n == 'target' for n, _ in self.client.commands))

    def test_provider_start_failure_closes_owned_session(self):
        agent = MagicMock()
        agent.start.side_effect = RuntimeError('Provider startup failed')
        with self.assertRaisesRegex(RuntimeError, 'Provider startup failed'):
            run_r5_policy(None, None, self.backend, self.cameras, agent, MagicMock(),
                          supervisor=self.supervisor)
        self.assertFalse(self.client.current['enabled'])
        self.assertFalse(self.supervisor.thread.is_alive())

    def test_stuck_camera_acquisition_does_not_block_heartbeat_fault_detection(self):
        self.source.block.clear()
        self.wait_fault()
        self.assertFalse(self.client.current['enabled'])
        self.assertIn('stale', self.backend.fault)

    def test_operator_stop_does_not_reenable_or_stop_new_owner(self):
        self.client.current.update(enabled=False, owner=None)
        self.wait_fault()
        self.assertFalse(any(n in ('stop', 'enable') for n, _ in self.client.commands))

    def test_takeover_preserves_other_controller(self):
        self.client.current['owner'] = 'operator'
        self.wait_fault()
        self.supervisor.close()
        self.assertFalse(any(n == 'stop' for n, _ in self.client.commands))

    def test_camera_metadata_belongs_to_returned_images(self):
        first = self.cameras.snapshot()
        second = self.cameras.snapshot(after=time.time())
        self.assertGreater(second['left'], first['left'])
        self.assertEqual(self.cameras.describe(first)[0]['sequence'], first['left'])

    def test_fault_serializes_against_inflight_submission(self):
        entered, release = threading.Event(), threading.Event()
        original_command = self.client.command

        def command(action, **fields):
            if action == 'target':
                entered.set()
                release.wait(1)
            return original_command(action, **fields)

        self.client.command = command
        target = threading.Thread(target=lambda: self.backend._command('target', gripper_raw=4.4))
        target.start()
        self.assertTrue(entered.wait(1))
        errors = []

        def cancel():
            try:
                self.backend.abort('Injected fault')
            except R5ExecutionFault as exc:
                errors.append(str(exc))

        stopper = threading.Thread(target=cancel)
        stopper.start()
        release.set()
        target.join(1)
        stopper.join(1)
        self.assertFalse(target.is_alive() or stopper.is_alive())
        self.assertEqual(errors, ['Injected fault'])
        with self.assertRaises(R5ExecutionFault):
            self.backend._command('target', gripper_raw=4.5)
        actions = [n for n, _ in self.client.commands]
        self.assertLess(actions.index('target'), actions.index('stop'))
        self.assertEqual(actions.count('target'), 1)

    def test_budget_renewal_keeps_independent_heartbeat_running(self):
        entered, release = threading.Event(), threading.Event()
        original = self.backend._reanchor_hold_to_measured
        errors = []

        def delayed_reanchor(state):
            entered.set()
            while not release.wait(.01):
                self.backend.check()
            return original(state)

        self.backend._reanchor_hold_to_measured = delayed_reanchor

        def renew():
            try:
                self.backend.renew_session()
            except Exception as exc:
                errors.append(exc)

        worker = threading.Thread(target=renew)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            initial_check = self.supervisor.last_check
            deadline = time.monotonic()+.6
            while self.supervisor.last_check == initial_check and time.monotonic() < deadline:
                time.sleep(.01)
            self.assertNotEqual(self.supervisor.last_check, initial_check,
                                'Renewal starved the independent watchdog despite live heartbeats')
            self.supervisor.check()
        finally:
            release.set()
            worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, [])
        self.assertTrue(self.client.current['enabled'])
        self.assertFalse(any(action == 'stop' for action, _ in self.client.commands))

    def test_fault_during_renewal_cannot_be_cleared_or_followed_by_a_target(self):
        entered, release = threading.Event(), threading.Event()
        original = self.backend._reanchor_hold_to_measured
        self.client.current['joints_deg'][0] += .5
        errors = []

        def delayed_reanchor(state):
            entered.set()
            release.wait(1)
            return original(state)

        self.backend._reanchor_hold_to_measured = delayed_reanchor

        def renew():
            try:
                self.backend.renew_session()
            except R5ExecutionFault as exc:
                errors.append(str(exc))

        worker = threading.Thread(target=renew)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            with self.assertRaisesRegex(R5ExecutionFault, 'Fault during renewal'):
                self.backend.abort('Fault during renewal')
        finally:
            release.set()
            worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ['Fault during renewal'])
        self.assertEqual(self.backend.guard.failure, 'Fault during renewal')
        self.assertFalse(self.backend.busy)
        self.assertFalse(self.client.current['enabled'])
        self.assertFalse(any(action == 'target' for action, _ in self.client.commands))


if __name__ == '__main__':
    unittest.main()
