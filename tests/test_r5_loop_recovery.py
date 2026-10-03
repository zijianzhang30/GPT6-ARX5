import unittest
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import r5_policy_deployment  # Adds the bundled GPT-Policy source path.
from supervised_policy import DeadlineAgent
from gpt_policy.harness.errors import AgentDecisionTimeoutError, AgentTimeoutError, AgentOverloadedError
from gpt_policy.harness.waiting import monitor_health
from gpt_policy.runtime.runner import run_loop


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.robot = MagicMock()
        self.robot.state.side_effect = lambda: {'sample': self.robot.state.call_count}
        self.camera = MagicMock()
        self.camera.snapshot.side_effect = lambda **kw: {'frame': self.camera.snapshot.call_count}
        self.agent = MagicMock()
        self.executor = MagicMock()
        self.executor.is_terminal.return_value = False
        self.executor.execute.return_value = {'executed': True}
        self.recorder = MagicMock()
        self.health = MagicMock()

    def run_loop(self, boundary=None):
        with patch('gpt_policy.runtime.runner.wait_with_health'):
            return run_loop(SimpleNamespace(max_decisions=2, right_interface='', interface='test'),
                            SimpleNamespace(instruction='test', content=()), self.robot,
                            self.camera, self.camera, self.agent, self.executor, self.recorder,
                            observation_fn=lambda task, state, *args: str(state['sample']),
                            health_check=self.health, display=MagicMock(),
                            finish_fn=self.robot.finish, fail_on_state_error=True,
                            segment_boundary=boundary)

    def test_timeout_retry_captures_fresh_state_and_images(self):
        action = {'name': 'move_to', 'arguments': {}}
        self.agent.decide.side_effect = [AgentDecisionTimeoutError('expired'), action, action]
        self.assertEqual(self.run_loop(), 'budget_exhausted')
        turns = [call.args[0] for call in self.agent.decide.call_args_list]
        self.assertNotEqual(turns[0].observation, turns[1].observation)
        self.assertNotEqual(turns[0].images, turns[1].images)
        self.assertEqual(self.executor.execute.call_count, 2)
        self.assertTrue(any(c.args[0] == 'model_retry' for c in self.recorder.write.call_args_list))

    def test_budget_rejection_returns_before_another_model_call(self):
        self.agent.decide.return_value = {'name': 'move_to', 'arguments': {}}
        self.executor.execute.side_effect = ValueError('session envelope')
        boundary = lambda: 'motion_budget_boundary' if self.executor.execute.called else None
        self.assertEqual(self.run_loop(boundary), 'motion_budget_boundary')
        self.agent.decide.assert_called_once()
        self.robot.finish.assert_called_once_with('motion_budget_boundary')

    def test_unrecoverable_timeout_and_hardware_fault_are_not_retried(self):
        for error in (AgentTimeoutError('outer deadline'), RuntimeError('tracking fault')):
            self.agent.decide.reset_mock(side_effect=True)
            self.agent.decide.side_effect = error
            with self.assertRaises(type(error)):
                self.run_loop()
            self.agent.decide.assert_called_once()
        self.executor.execute.assert_not_called()

    def test_retry_limit_is_bounded_and_never_executes(self):
        self.agent.decide.side_effect = AgentDecisionTimeoutError('expired')
        with patch('gpt_policy.runtime.runner.MODEL_RETRY_DELAYS_S', (0, 0)):
            with self.assertRaises(AgentDecisionTimeoutError):
                self.run_loop()
        self.assertEqual(self.agent.decide.call_count, 3)
        self.executor.execute.assert_not_called()

    def test_expired_decision_resets_transport_before_retry(self):
        supervisor, agent = MagicMock(), MagicMock()
        agent.decide.side_effect = AgentTimeoutError('expired')
        with self.assertRaises(AgentDecisionTimeoutError):
            DeadlineAgent(agent, supervisor).decide(None)
        agent.reset_after_timeout.assert_called_once()

    def test_malformed_json_discards_provider_and_reobserves_before_execution(self):
        provider = MagicMock()
        action = {'name': 'move_to', 'arguments': {}}
        provider.decide.side_effect = [json.JSONDecodeError('missing comma', '{', 1), action, action]
        self.agent = DeadlineAgent(provider, self.health)
        self.assertEqual(self.run_loop(), 'budget_exhausted')
        provider.reset_after_timeout.assert_called_once()
        turns = [call.args[0] for call in provider.decide.call_args_list]
        self.assertNotEqual(turns[0].observation, turns[1].observation)
        self.assertNotEqual(turns[0].images, turns[1].images)
        self.assertEqual(self.executor.execute.call_count, 2)
        retries = [c.args[1] for c in self.recorder.write.call_args_list if c.args[0] == 'model_retry']
        self.assertEqual(retries[0]['code'], 'invalid_decision_json')

    def test_repeated_malformed_json_is_bounded_without_execution(self):
        provider = MagicMock()
        provider.decide.side_effect = json.JSONDecodeError('missing comma', '{', 1)
        self.agent = DeadlineAgent(provider, self.health)
        with patch('gpt_policy.runtime.runner.MODEL_RETRY_DELAYS_S', (0, 0)):
            with self.assertRaises(AgentOverloadedError):
                self.run_loop()
        self.assertEqual(provider.decide.call_count, 3)
        self.executor.execute.assert_not_called()

    def test_json_recovery_does_not_mask_hardware_fault(self):
        provider, supervisor = MagicMock(), MagicMock()
        provider.decide.side_effect = json.JSONDecodeError('missing comma', '{', 1)
        provider.reset_after_timeout.side_effect = lambda: setattr(
            supervisor.check, 'side_effect', RuntimeError('hardware fault'))
        with self.assertRaisesRegex(RuntimeError, 'hardware fault'):
            DeadlineAgent(provider, supervisor).decide(None)
        provider.reset_after_timeout.assert_called_once()

    def test_inner_deadline_cannot_mask_overall_recovery_deadline(self):
        with patch('gpt_policy.harness.waiting.time.monotonic', return_value=0) as now:
            with monitor_health(None, deadline=10):
                with monitor_health(None, deadline=25) as check:
                    now.return_value = 11
                    with self.assertRaises(AgentTimeoutError):
                        check()

    def test_provider_restarts_transport_and_replays_only_completed_history(self):
        from gpt_policy.harness.providers.codex import CodexSession
        from gpt_policy.harness.models import AgentTurn
        config = SimpleNamespace(executable='codex', effort='low', live_image_window=8)
        with patch('gpt_policy.harness.providers.codex.CodexAppServer') as factory:
            old, new = MagicMock(), MagicMock()
            factory.side_effect = [old, new]
            session = CodexSession(config, 'test', False, 85)
            session.start(SimpleNamespace(instructions='test', tools=[], output_schema={}))
            session.reset_after_timeout()
            old.close.assert_called_once()
            new.decide.return_value = {'name': 'observe', '_wire': {}}
            session.decide(AgentTurn('fresh observation', {}, ()))
            new.refresh_thread.assert_called_once()
            self.assertEqual(new.decide.call_args.args[0], 'fresh observation')
            self.assertEqual(len(session._history), 1)
            old.decide.assert_not_called()
