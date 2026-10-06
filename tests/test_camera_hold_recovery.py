import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from camera_hold_recovery import (CAMERA_REJECTION, CAMERA_TIMEOUT_REJECTION, CAMERA_DECODE_REJECTION,
                                  CameraHoldHandoff, require_unchanged_targets,
                                  validate_camera_hold_log)


class CameraHoldRecoveryTests(unittest.TestCase):
    def events(self, reason=CAMERA_TIMEOUT_REJECTION):
        states = {side: dict(channel=channel, enabled=True, moving=False,
                            control_state='holding', policy_trajectory_active=False,
                            robot_status='ready', error_codes=[], command_deg=[0.] * 6,
                            gripper_command_raw=4.8, owner='test-owner')
                  for side, channel in [('left', 'can0'), ('right', 'can1')]}
        return [dict(event='observation', state={'arms': {
                    side: {'raw_state': state} for side, state in states.items()}}),
                dict(event='review_command_finished', outcome='completed'),
                dict(event='review_command_started', command_index=2),
                dict(event='rejected', reason=reason),
                dict(event='review_command_finished', command_index=2, outcome='rejected')]

    def test_only_completed_stationary_camera_rejections_are_eligible(self):
        for reason in (CAMERA_REJECTION, CAMERA_TIMEOUT_REJECTION, CAMERA_DECODE_REJECTION):
            self.assertEqual(set(validate_camera_hold_log(self.events(reason))), {'left', 'right'})
        for reason in ('Independent policy heartbeat stalled', 'motor fault',
                       CAMERA_TIMEOUT_REJECTION + '; protective stop unconfirmed',
                       CAMERA_DECODE_REJECTION + '; protective stop unconfirmed',
                       'Camera supervision failed: OSError: broken data stream when reading image file',
                       'Fresh camera observation required; stationary hold retained: Camera supervision failed: OSError: unrelated failure',
                       'Supervised camera frames are stale'):
            with self.subTest(reason=reason), self.assertRaises(ValueError):
                validate_camera_hold_log(self.events(reason))
        for events in (self.events()[:-1], self.events() + [dict(event='request')],
                       self.events()[:2], self.events()[1:]):
            with self.assertRaises(ValueError):
                validate_camera_hold_log(events)
        for key, value in [('enabled', False), ('moving', True),
                           ('policy_trajectory_active', True), ('error_codes', [1]),
                           ('command_deg', [float('nan')] * 6), ('channel', 'can1')]:
            events = self.events()
            events[0]['state']['arms']['left']['raw_state'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_camera_hold_log(events)

    def test_owner_joint_and_gripper_targets_must_remain_unchanged(self):
        saved = validate_camera_hold_log(self.events())
        require_unchanged_targets(saved, copy.deepcopy(saved))
        for change in ({'owner': 'other'}, {'command_deg': [1.] * 6},
                       {'gripper_command_raw': 4.0}):
            states = copy.deepcopy(saved)
            states['left'].update(change)
            with self.assertRaises(ValueError):
                require_unchanged_targets(saved, states)

    @patch('camera_hold_recovery.time.monotonic', side_effect=[0., .4, .8, 1.2, 1.6, 2.1, 2.2])
    def test_qualification_requires_advancing_original_devices_and_held_targets(self, clock):
        handoff = object.__new__(CameraHoldHandoff)
        handoff.expected_devices = dict(top='a', left='b', right='c')
        handoff.snapshot = Mock()
        cameras = Mock()
        cameras.describe.side_effect = [
            [dict(name=side, device=device, sequence=i) for side, device in handoff.expected_devices.items()]
            for i in range(5)]
        robots = Mock()
        result = handoff.qualify(cameras, robots)
        self.assertFalse(result['hardware_commands_sent'])
        self.assertEqual(result['batches'], 5)
        self.assertEqual(handoff.snapshot.call_count, 5)
        self.assertEqual(cameras.check.call_count, 5)

    def test_qualification_rejects_frozen_changed_or_failed_cameras(self):
        for condition in ('frozen', 'changed', 'failed', 'hold_changed'):
            handoff = object.__new__(CameraHoldHandoff)
            handoff.expected_devices = dict(top='a', left='b', right='c')
            handoff.snapshot = Mock()
            cameras = Mock()
            cameras.describe.return_value = [dict(name=s, device=d, sequence=1)
                                              for s, d in handoff.expected_devices.items()]
            if condition == 'changed':
                cameras.describe.return_value[0]['device'] = 'unexpected'
            elif condition == 'failed':
                cameras.check.side_effect = RuntimeError('camera failure')
            elif condition == 'hold_changed':
                handoff.snapshot.side_effect = ValueError('hold changed')
            with self.subTest(condition=condition), self.assertRaises((ValueError, RuntimeError)):
                handoff.qualify(cameras, Mock())

    def test_transfer_requires_unchanged_log_and_recent_qualification(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff = object.__new__(CameraHoldHandoff)
            handoff.events = Path(directory) / 'events.jsonl'
            handoff.contents = b'original'
            handoff.events.write_bytes(handoff.contents)
            for stamp in (None, 0., 20.):
                handoff.qualified_at = stamp
                with patch('camera_hold_recovery.time.monotonic', return_value=10.), self.assertRaises(ValueError):
                    handoff.require_transfer_ready()
            handoff.qualified_at = 9.
            with patch('camera_hold_recovery.time.monotonic', return_value=10.):
                handoff.require_transfer_ready()
                handoff.events.write_bytes(b'changed')
                with self.assertRaises(ValueError):
                    handoff.require_transfer_ready()

    def test_host_qualifies_before_starting_replacement_supervision_and_transfer(self):
        from tools import held_policy_review as module
        for qualification_failed in (False, True):
            with self.subTest(qualification_failed=qualification_failed), tempfile.TemporaryDirectory() as directory:
                calls = []
                client = Mock()
                client.request.return_value = {'paired_policy_client': 'test-owner'}
                camera = Mock()
                camera.start.side_effect = lambda: calls.append('cameras_start')
                handoff = Mock()
                def qualify(*args):
                    calls.append('qualify')
                    if qualification_failed:
                        raise RuntimeError('qualification failed')
                    return {'hardware_commands_sent': False}
                handoff.qualify.side_effect = qualify
                handoff.transfer.side_effect = lambda *args: calls.append('transfer') or {'adopted': True}
                supervisors = [Mock(), Mock()]
                for side, supervisor in zip(('left', 'right'), supervisors):
                    supervisor.start.side_effect = lambda s=side: calls.append('start_' + s)
                    supervisor.diagnostics.return_value = {}
                dual = Mock()
                dual.start.side_effect = RuntimeError('test ends before command loop')
                with patch.object(module, 'ArmWorkbenchClient', return_value=client), \
                     patch.object(module, 'R5DualCameras'), \
                     patch.object(module, 'SupervisedCameras', return_value=camera), \
                     patch.object(module, 'CartesianBackend', side_effect=[Mock(), Mock()]), \
                     patch.object(module, 'DualCartesianBackend'), \
                     patch.object(module, 'R5PolicySupervisor', side_effect=supervisors), \
                     patch.object(module, 'DualSupervisor', return_value=dual), \
                     patch.object(module, 'CameraHoldHandoff', return_value=handoff), \
                     patch.object(module, 'prepare_hold') as prepare, \
                     patch.object(module.sys, 'argv', ['review', '--from-camera-review-pid', '123',
                         '--run', directory, '--output', str(Path(directory) / 'new'),
                         '--working-arm', 'left', '--paired-client', 'test-owner',
                         '--tracking-reserve-deg', '3.5']):
                    with self.assertRaises(RuntimeError):
                        module.main()
                self.assertEqual(calls, ['cameras_start', 'qualify'] if qualification_failed else
                                 ['cameras_start', 'qualify', 'start_left', 'start_right', 'transfer'])
                prepare.assert_not_called()
                client.command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
