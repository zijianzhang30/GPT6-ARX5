import copy
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from healthy_probe_handoff import validate_healthy_probe_source
from test_initial_review_handoff import InitialReviewTests


class HealthyProbeHandoffTests(unittest.TestCase):
    def events(self):
        observation = InitialReviewTests().events()[-2]
        observation['state']['arms']['left']['raw_state']['gripper_command_raw'] = 4.8
        return [dict(event='working_arm_selected', arm='left'),
                dict(event='review_command_started', command='observe', command_index=9),
                observation,
                dict(event='review_command_finished', command='observe', command_index=9, outcome='completed')]

    def test_healthy_observe_accepts_preloaded_right_unchanged(self):
        saved = validate_healthy_probe_source(self.events(), 'owner')
        self.assertEqual(saved['right']['gripper_command_raw'], 1.02)

    def test_rejects_unfinished_changed_arm_faulted_or_prior_probe_sources(self):
        original = self.events()
        cases = [original[:-1], original+[dict(event='request')]]
        for event in ('host_terminated', 'empty_probe_result'):
            cases.append([dict(event=event)]+original)
        for index, key, value in [(0, 'arm', 'right'), (1, 'command', 'renew'),
                                   (-1, 'outcome', 'rejected'), (-1, 'command_index', 8)]:
            changed = copy.deepcopy(original); changed[index][key] = value; cases.append(changed)
        for key, value in [('owner', 'other'), ('enabled', False), ('moving', True),
                           ('error_codes', [1]), ('worker_fault_reason', 'old fault'),
                           ('command_deg', [float('nan')]*6), ('gripper_command_raw', 1.)]:
            changed = copy.deepcopy(original)
            changed[-2]['state']['arms']['left']['raw_state'][key] = value
            cases.append(changed)
        for i, events in enumerate(cases):
            with self.subTest(i=i), self.assertRaises(ValueError):
                validate_healthy_probe_source(events, 'owner')

    def test_host_whitelist_rejects_all_gripper_return_selection_and_json_commands(self):
        from tools.held_policy_review import require_empty_probe_command
        for allowed in ('observe', 'renew', 'probe-empty-up-3mm'):
            require_empty_probe_command(allowed)
        for blocked in ('select-right', 'select-left', 'open-empty-left', 'open-empty-right',
                        'return-working-step', 'return-right-step', 'begin-right',
                        json.dumps({'tool': 'set_gripper', 'arguments': {}}),
                        json.dumps({'tool': 'move_to', 'arguments': {}})):
            with self.subTest(blocked=blocked), self.assertRaises(ValueError):
                require_empty_probe_command(blocked)

    def test_idle_software_error_can_quarantine_but_never_active_or_health_faults(self):
        from tools.held_policy_review import software_error_hold_snapshot
        from r5_policy_backend import R5ExecutionFault
        arms = {s: Mock() for s in ('left','right')}
        for s, arm in arms.items():
            arm.backend.engaged, arm.backend.busy, arm.backend.fault = True, False, None
            arm.backend._read.return_value = self.events()[-2]['state']['arms'][s]['raw_state']
        supervisor = Mock()
        self.assertEqual(set(software_error_hold_snapshot(arms, supervisor, UnboundLocalError('fixture'))),
                         {'left','right'})
        for error in (R5ExecutionFault('camera'), KeyboardInterrupt(), SystemExit()):
            self.assertIsNone(software_error_hold_snapshot(arms, supervisor, error))
        for field, bad, good in [('engaged',False,True), ('busy',True,False), ('fault','SDK fault',None)]:
            setattr(arms['left'].backend,field,bad)
            self.assertIsNone(software_error_hold_snapshot(arms, supervisor, RuntimeError('fixture')))
            setattr(arms['left'].backend,field,good)
        for field, value in [('moving',True), ('policy_trajectory_active',True), ('enabled',False),
                             ('control_state','active')]:
            arm = arms['left'].backend
            prior = copy.deepcopy(arm._read.return_value)
            arm._read.return_value[field] = value
            self.assertIsNone(software_error_hold_snapshot(arms, supervisor, RuntimeError('fixture')))
            arm._read.return_value = prior
        supervisor.check.side_effect = R5ExecutionFault('heartbeat overdue')
        self.assertIsNone(software_error_hold_snapshot(arms, supervisor, RuntimeError('fixture')))
        for arm in arms.values():
            arm.backend._command.assert_not_called()
            arm.backend.client.command.assert_not_called()

    def test_host_qualifies_before_watchdogs_and_never_enables_or_prepares_arms(self):
        from tools import held_policy_review as module
        for failed in (False, True):
            with self.subTest(failed=failed), tempfile.TemporaryDirectory() as d:
                calls = []
                client = Mock(); client.request.return_value = {'paired_policy_client': 'owner'}
                camera, handoff = Mock(), Mock()
                camera.start.side_effect = lambda: calls.append('cameras')
                def qualify(*args):
                    calls.append('qualify')
                    if failed: raise RuntimeError('unhealthy cameras')
                    return {'hardware_commands_sent': False}
                handoff.qualify.side_effect = qualify
                handoff.transfer.side_effect = lambda *args: calls.append('transfer') or {}
                supervisors = [Mock(), Mock()]
                for side, supervisor in zip(('left', 'right'), supervisors):
                    supervisor.start.side_effect = lambda s=side: calls.append(s)
                    supervisor.diagnostics.return_value = {}
                dual = Mock(); dual.start.side_effect = RuntimeError('test stops before input loop')
                arms = [Mock(), Mock()]
                for arm in arms:
                    arm.backend.last_execution_feedback = None
                with patch.object(module, 'ArmWorkbenchClient', return_value=client), \
                     patch.object(module, 'R5DualCameras'), \
                     patch.object(module, 'SupervisedCameras', return_value=camera), \
                     patch.object(module, 'CartesianBackend', side_effect=arms), \
                     patch.object(module, 'DualCartesianBackend'), \
                     patch.object(module, 'R5PolicySupervisor', side_effect=supervisors), \
                     patch.object(module, 'DualSupervisor', return_value=dual), \
                     patch.object(module, 'HealthyProbeHandoff', return_value=handoff), \
                     patch.object(module, 'prepare_hold') as prepare, \
                     patch.object(module.sys, 'argv', ['review', '--from-healthy-probe-pid', '123',
                         '--run', d, '--output', str(Path(d)/'new'), '--working-arm', 'left',
                         '--paired-client', 'owner', '--tracking-reserve-deg', '3.5',
                         '--minimum-cartesian-command-step-deg', '2', '--one-empty-left-probe']):
                    with self.assertRaises(RuntimeError): module.main()
                self.assertEqual(calls, ['cameras', 'qualify'] if failed else
                                 ['cameras', 'qualify', 'left', 'right', 'transfer'])
                prepare.assert_not_called()
                client.command.assert_not_called()

    def test_full_probe_host_input_loop_idle_observe_rejection_renew_and_probe(self):
        self.run_full_probe_host_input_loop(False)

    def test_full_joint_diagnostic_host_input_loop_idle_observe_rejection_renew_and_probe(self):
        self.run_full_probe_host_input_loop(True)

    def test_full_reviewed_task_input_loop_starts_held_and_accepts_observe_without_enable(self):
        self.run_full_probe_host_input_loop(False, reviewed_task=True)

    def run_full_probe_host_input_loop(self, joint_diagnostic, reviewed_task=False):
        """Exercise the real loop, not just startup before the first queue read."""
        from tools import held_policy_review as module
        class EndFixture(BaseException): pass
        with tempfile.TemporaryDirectory() as d:
            raw = {s: self.events()[-2]['state']['arms'][s]['raw_state']
                   for s in ('left', 'right')}
            for state in raw.values(): state['joints_deg'] = state['command_deg'][:]
            clients = {s: Mock() for s in raw}
            for s, c in clients.items():
                c.request.return_value = {'paired_policy_client': 'owner'}
                c.state.return_value = copy.deepcopy(raw[s])
            arms = {s: Mock() for s in raw}
            for s, arm in arms.items():
                arm.backend._read.return_value = copy.deepcopy(raw[s])
                arm.backend.last_execution_feedback = None
                arm.renew_session.return_value = {'renewed': True}
            arms['left'].frames.sdk_to_tcp.return_value = [0,0,.3,0,0,0]
            arms['left'].plan.return_value = {'result': {'note': 'fixture'}}
            arms['left'].backend.execute_probe.return_value = {'passed': False, 'motion_locked': True}
            dual_robot = Mock()
            dual_robot.operation_lock = threading.Lock()
            dual_robot.robots = arms
            dual_robot.state.return_value = {'arms': {
                s: dict(raw_state=raw[s], observation_id='fixture', tcp_command_xyzquat=[0]*7,
                        tcp_xyzquat=[0]*7, gripper_command_normalized=1., gripper_next_opening_bounds=[0,1])
                for s in raw}}
            camera = Mock()
            camera.snapshot.return_value = {s: SimpleNamespace(data=b'fixture camera bytes')
                                            for s in ('left','right','top')}
            handoff = Mock()
            handoff.qualify.return_value = {'hardware_commands_sent': False}
            handoff.transfer.return_value = {'released_hold': False}
            supervisors = [Mock(), Mock()]
            for supervisor in supervisors: supervisor.diagnostics.return_value = {}
            command_queue = Mock()
            action = 'diagnose-empty-left-j3' if joint_diagnostic else 'probe-empty-up-3mm'
            command_queue.get.side_effect = [module.queue.Empty(), 'observe', 'select-right',
                '{"tool":"set_gripper","arguments":{}}', 'renew', action, EndFixture()]
            source_flag = '--from-measured-probe-pid' if joint_diagnostic else '--from-healthy-probe-pid'
            source_class = 'MeasuredProbeDiagnosticHandoff' if joint_diagnostic else 'HealthyProbeHandoff'
            extra_flags = ['--one-empty-left-joint-diagnostic' if joint_diagnostic else '--one-empty-left-probe']
            if reviewed_task:
                source_flag, source_class = '--from-reviewed-diagnostic-pid', 'ReviewedTaskHandoff'
                extra_flags = ['--diagnostic-review', str(Path(d)/'review.json')]
                command_queue.get.side_effect = [module.queue.Empty(), 'observe', EndFixture()]
            with patch.object(module, 'ArmWorkbenchClient', side_effect=clients.values()), \
                 patch.object(module, 'R5DualCameras'), \
                 patch.object(module, 'SupervisedCameras', return_value=camera), \
                 patch.object(module, 'CartesianBackend', side_effect=arms.values()), \
                 patch.object(module, 'DualCartesianBackend', return_value=dual_robot), \
                 patch.object(module, 'R5PolicySupervisor', side_effect=supervisors), \
                 patch.object(module, 'DualSupervisor'), \
                 patch.object(module, source_class, return_value=handoff), \
                 patch.object(module, 'prepare_hold') as prepare, \
                 patch.object(module.queue, 'Queue', return_value=command_queue), \
                 patch.object(module.threading, 'Thread'), \
                 patch.object(module.sys, 'argv', ['review',source_flag,'123',
                     '--run',d,'--output',str(Path(d)/'new'),'--working-arm','left',
                     '--paired-client','owner','--tracking-reserve-deg','3.5',
                     '--minimum-cartesian-command-step-deg','2', *extra_flags]):
                with self.assertRaises(EndFixture): module.main()
            events = [json.loads(line) for line in (Path(d)/'new/events.jsonl').read_text().splitlines()]
            outcomes = [e['outcome'] for e in events if e['event']=='review_command_finished']
            if reviewed_task:
                self.assertEqual(outcomes,['completed'])
                handoff.qualify.assert_called_once()
                handoff.transfer.assert_called_once()
                prepare.assert_not_called()
                for c in clients.values():c.command.assert_not_called()
                for arm in arms.values():arm.backend.execute_probe.assert_not_called()
                dual_robot.execute.assert_not_called()
                return
            self.assertEqual(outcomes, ['completed','rejected','rejected','completed','completed'])
            result_key = 'joint_diagnostic_result' if joint_diagnostic else 'empty_probe_result'
            self.assertEqual(len([e for e in events if e['event']==result_key]), 1)
            arms['left'].backend.execute_probe.assert_called_once()
            arms['right'].backend.execute_probe.assert_not_called()
            arms['left'].renew_session.assert_called_once()
            arms['right'].renew_session.assert_not_called()
            dual_robot.execute.assert_not_called()
            prepare.assert_not_called()
            for client in clients.values(): client.command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
