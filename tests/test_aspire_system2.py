"""Exercise the System 2 wire and guarded host adapter with no hardware."""
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import queue
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import Mock, patch

from aspire_review import AspireRequest, AspireReview, review_socket
from tools.aspire_system2_mcp import LegacyReview, host_call, list_tools, rpc


def pose_request(observation_id, frame='right_base', arm='right'):
    return AspireRequest('v2.cap_move_to_pose', {'arm': arm, 'observation_id': observation_id, 'note': 'mock',
        'target_pose': {'position': [.2, .1, .3], 'quaternion_wxyz': [.5, .5, -.5, -.5], 'frame': frame}})


def gripper_request(observation_id):
    return AspireRequest('v2.cap_set_gripper',
                         {'arm': 'right', 'observation_id': observation_id, 'note': 'mock', 'position': .6})


def packet(sequence, images=None):
    arms = {side: {'channel': channel, 'measured_tcp': [.1, .2, .3, -.5, .5, -.5, .5], 'joints_deg': [0]*6,
                   'opening': .65, 'measured_opening': .61, 'bounds': [.6, .7],
                   'health': {'owner': 'private-owner'}}
            for side, channel in (('left', 'can0'), ('right', 'can1'))}
    return {'observation': sequence, 'arms': arms, 'images': images or dict.fromkeys(('top', 'left', 'right'), '/unused')}


def result(profile='left'):
    return {'arms': {profile: {'control_state': 'holding',
                              'settle': {'settled': True, 'partial_tracking_accepted': True}}}}


class AspireReviewTests(unittest.TestCase):
    def test_default_observes_and_rejects_motion(self):
        host = AspireReview(False)
        execute = Mock()
        observation = host.dispatch(AspireRequest('observe', {}), lambda: packet(1), execute, 'left')
        state = observation['observation']['state']['left']
        self.assertEqual((state['frame'], state['channel']), ('left_base', 'can1'))
        self.assertEqual(observation['observation']['state']['right']['channel'], 'can0')
        self.assertEqual(state['tcp_quaternion_wxyz'], [.5, -.5, .5, -.5])
        self.assertEqual(state['gripper_measured_normalized'], .61)
        self.assertNotIn('private-owner', json.dumps(observation))
        with self.assertRaisesRegex(ValueError, 'explicit host'):
            host.dispatch(pose_request('1'), lambda: packet(2), execute, 'left')
        execute.assert_not_called()

    def test_pose_conversion_single_arm_and_receipt(self):
        host = AspireReview(True)
        host.observe(lambda: packet(1))
        execute = Mock(return_value=result())
        receipt = host.dispatch(pose_request('1'), lambda: packet(2), execute, 'left')
        execute.assert_called_once_with({'tool': 'move_to', 'arguments': {
            'target': {'left': {'pose_xyzquat': [.2, .1, .3, .5, -.5, -.5, .5]}, 'right': None}, 'note': 'mock'}})
        self.assertEqual(receipt['status'], 'review_completed')
        self.assertEqual(receipt['receipt']['arm'], 'right')
        self.assertEqual(receipt['receipt']['channel'], 'can0')
        self.assertTrue(receipt['receipt']['settle']['partial_tracking_accepted'])
        self.assertFalse(receipt['receipt']['grasp_verified'])
        self.assertFalse(receipt['receipt']['collision_checked'])
        self.assertEqual(receipt['observation']['observation_id'], '2')
        with self.assertRaisesRegex(ValueError, 'fresh observation'):
            host.dispatch(pose_request('1'), lambda: packet(3), execute, 'left')
        self.assertEqual(execute.call_count, 1)

    def test_pose_correction_receipt_carries_fresh_observation_for_next_action(self):
        host = AspireReview(True)
        host.observe(lambda: packet(1))
        missed = result()
        missed['arms']['left']['settle'] = {'settled': False, 'reason': 'position_not_reached'}
        execute = Mock(side_effect=[missed, result()])

        receipt = host.dispatch(pose_request('1'), lambda: packet(2), execute, 'left')

        self.assertTrue(receipt['ok'])
        self.assertEqual(receipt['status'], 'correction_required')
        self.assertFalse(receipt['receipt']['settle']['settled'])
        self.assertEqual(receipt['receipt']['control_state'], 'holding')
        self.assertEqual(receipt['observation']['observation_id'], '2')
        with self.assertRaisesRegex(ValueError, 'fresh observation'):
            host.dispatch(pose_request('1'), lambda: packet(3), execute, 'left')
        followup = host.dispatch(pose_request('2'), lambda: packet(3), execute, 'left')
        self.assertEqual(followup['status'], 'review_completed')
        self.assertEqual(execute.call_count, 2)

    def test_gripper_and_rejection_consume_observation(self):
        host = AspireReview(True)
        host.observe(lambda: packet(1))
        execute = Mock(side_effect=ValueError('gripper guard'))
        with self.assertRaisesRegex(ValueError, 'gripper guard'):
            host.dispatch(gripper_request('1'), lambda: packet(2), execute, 'left')
        execute.assert_called_once_with({'tool': 'set_gripper', 'arguments': {
            'positions': {'left': .6, 'right': None}, 'note': 'mock'}})
        with self.assertRaisesRegex(ValueError, 'fresh observation'):
            host.dispatch(gripper_request('1'), lambda: packet(2), execute, 'left')
        self.assertEqual(execute.call_count, 1)

    def test_rejects_sim_replay_wrong_arm_and_nonfinite(self):
        host = AspireReview(True)
        host.observe(lambda: packet(1))
        execute = Mock()
        invalid = [pose_request('1', 'world'), pose_request('1', 'left_base'),
                   AspireRequest('cap_set_gripper', gripper_request('1').arguments),
                   AspireRequest('cap_set_gripper', {'arm': 'left', 'position': 0.})]
        bad = pose_request('1')
        bad.arguments['target_pose']['position'][0] = float('nan')
        invalid.append(bad)
        overlarge = pose_request('1')
        overlarge.arguments['target_pose']['position'][0] = 10**400
        invalid.append(overlarge)
        for request in invalid:
            with self.assertRaises(ValueError):
                host.dispatch(request, lambda: packet(2), execute, 'left')
        with self.assertRaisesRegex(ValueError, 'Provide arm=left'):
            host.dispatch(pose_request('1'), lambda: packet(2), execute, 'right')
        execute.assert_not_called()

    def test_left_command_routes_to_can1_and_requires_channel_checked_feedback(self):
        host = AspireReview(True)
        observation = packet(1, dict(top='/overview', left='/can0', right='/can1'))
        execute = Mock(return_value=result('right'))
        initial = host.observe(lambda: observation)
        self.assertEqual(initial['images']['left_wrist'], '/can1')
        self.assertEqual(initial['images']['right_wrist'], '/can0')
        confirmation = host.dispatch(pose_request('1', 'left_base', 'left'),
                                     lambda: packet(2), execute, 'right')
        target = execute.call_args.args[0]['arguments']['target']
        self.assertIsNone(target['left'])
        self.assertIsNotNone(target['right'])
        self.assertEqual(confirmation['receipt']['channel'], 'can1')
        observation['arms']['right']['channel'] = 'can0'
        with self.assertRaisesRegex(ValueError, 'Expected left feedback from can1'):
            host.observe(lambda: observation)
        self.assertIsNone(host.current)

    def test_failed_post_action_capture_does_not_reuse_old_snapshot(self):
        host = AspireReview(True)
        host.observe(lambda: packet(1))
        execute = Mock(return_value=result())
        capture = Mock(side_effect=ValueError('camera lost'))
        with self.assertRaisesRegex(RuntimeError, 'Post-action observation failed'):
            host.dispatch(pose_request('1'), capture, execute, 'left')
        self.assertIsNone(host.current)
        execute.assert_called_once()


class StdioTests(unittest.TestCase):
    def test_queued_timeout_cancels_undispatched_request(self):
        with TemporaryDirectory(dir='/tmp') as temporary:
            address = Path(temporary) / 'review.sock'
            commands = queue.Queue()
            with patch('aspire_review.HOST_TIMEOUT_S', .01), review_socket(address, commands):
                result = host_call(address, 'observe', {})
                self.assertEqual(result['status'], 'not_dispatched')
                request = commands.get_nowait()
                self.assertFalse(request.reply.set_running_or_notify_cancel())
                self.assertTrue(commands.empty())

    def test_actual_stdio_lifecycle_and_local_socket(self):
        with TemporaryDirectory(dir='/tmp') as temporary:
            root = Path(temporary)
            address = root / 'review.sock'
            pictures = {key: str(root / f'{key}.jpg') for key in ('top', 'left', 'right')}
            for path in pictures.values():
                Path(path).write_bytes(bytes.fromhex('ffd8ffd9'))

            def owner():
                request = commands.get(timeout=5)
                self.assertTrue(request.reply.set_running_or_notify_cancel())
                request.reply.set_result(bridge.dispatch(
                    request, lambda: packet(123, pictures), Mock(), 'left'))

            payload = [
                {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-06-18'}},
                {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
                {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
                {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call',
                 'params': {'name': 'observe', 'arguments': {'cameras': ['left_wrist']}}},
            ]
            bridge, commands = AspireReview(False), queue.Queue()
            cli = Path(__file__).resolve().parents[1] / 'tools' / 'aspire_system2_mcp.py'
            with review_socket(address, commands), ThreadPoolExecutor(max_workers=1) as pool:
                pending = pool.submit(owner)
                process = subprocess.run([sys.executable, str(cli), '--socket', str(address)],
                    input='\n'.join(map(json.dumps, payload)), text=True, capture_output=True, check=True, timeout=10)
                pending.result(timeout=5)
                self.assertEqual(address.stat().st_mode & 0o777, 0o600)
            self.assertFalse(address.exists())
            initialize, tools, observe = (json.loads(line)['result'] for line in process.stdout.splitlines())
            self.assertEqual(initialize['protocolVersion'], '2025-06-18')
            self.assertEqual({tool['name'] for tool in tools['tools']}, {'observe','r5_task','get_capability_graph'})
            self.assertEqual(observe['structuredContent']['image_cameras'], ['left_wrist'])
            self.assertEqual(observe['content'][1], {'type': 'text', 'text': 'camera: left_wrist'})
            self.assertEqual(observe['content'][2]['mimeType'], 'image/jpeg')

    def test_bad_camera_query_and_motion_gate_fail_before_socket_dispatch(self):
        path = Path('/missing/supervised.sock')
        for name, args, allow in (('observe', {'cameras': [['bad']]}, True),
                                  ('cap_set_gripper', {'position': 1}, False)):
            r = rpc({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                     'params': {'name': name, 'arguments': args}}, path, allow)
            self.assertEqual(r['result']['structuredContent']['status'], 'rejected')
        self.assertEqual(host_call(path, 'observe', {})['status'], 'not_dispatched')
        self.assertTrue(any(tool['name'] == 'cap_move_to_pose' for tool in list_tools(True)))

    def test_v1_bridge_requires_fresh_observation_and_translates_only_the_can0_profile(self):
        bridge = LegacyReview.__new__(LegacyReview)
        bridge.path, bridge.allow_motion, bridge.current = Path('/legacy'), True, None
        def old_observation(identifier):
            return {'ok': True, 'receipt': {}, 'observation': {'observation_id': identifier,
                'state': {'left': {'frame': 'left_base'}, 'right': {'frame': 'right_base'}},
                'images': {'overview': '/top', 'left_wrist': '/can0', 'right_wrist': '/can1'}}}
        with patch('tools.aspire_system2_mcp.host_call',
                   side_effect=[old_observation('1'), old_observation('2')]) as call:
            with self.assertRaisesRegex(ValueError, 'fresh observation'):
                bridge.dispatch(pose_request('1'))
            initial = bridge.dispatch(AspireRequest('observe', {}))
            self.assertEqual(initial['observation']['images']['right_wrist'], '/can0')
            self.assertEqual(initial['observation']['state']['left']['channel'], 'can1')
            with self.assertRaisesRegex(ValueError, 'Provide arm=right'):
                bridge.dispatch(pose_request('1', 'left_base', 'left'))
            receipt = bridge.dispatch(pose_request('1'))['receipt']
            self.assertEqual(receipt, {'arm': 'right', 'channel': 'can0', 'frame': 'right_base'})
            path, name, args = call.call_args.args
            self.assertEqual((path, name, args['arm'], args['target_pose']['frame']),
                             (bridge.path, 'cap_move_to_pose', 'left', 'left_base'))


if __name__ == '__main__':
    unittest.main()
