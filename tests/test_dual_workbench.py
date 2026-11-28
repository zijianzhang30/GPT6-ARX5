import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from app import Workbench
from record_workbench import CameraRouter, RecordingWorkbench
from visual_control import ArmWorkbenchClient


class Cameras:
    def __init__(self, name):
        self.name = name

    def get(self, key):
        return self.name.encode(), '1', self.name

    def close(self):
        pass


class FailingCamera(Cameras):
    def get(self, key):
        raise RuntimeError(f'{self.name} busy')


class DualWorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.left = Workbench(('127.0.0.1', 0), cameras=Cameras('left-camera'))
        self.right = Workbench(('127.0.0.1', 0), cameras=Cameras('right-camera'))
        self.servers = [self.left, self.right]
        self.threads = []
        for server in self.servers:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            self.threads.append(thread)
        self.proxy = RecordingWorkbench(('127.0.0.1', 0),
            f'http://127.0.0.1:{self.right.server_port}', Path(self.temp.name),
            right_upstream=f'http://127.0.0.1:{self.left.server_port}')
        self.servers.append(self.proxy)
        thread = threading.Thread(target=self.proxy.serve_forever, daemon=True)
        thread.start()
        self.threads.append(thread)
        self.base = f'http://127.0.0.1:{self.proxy.server_port}'
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        for server in reversed(self.servers):
            server.shutdown()
            server.server_close()
        for thread in self.threads:
            thread.join()
        self.temp.cleanup()

    def request(self, path, data=None, token=True):
        headers = {'X-Control-Token': self.proxy.token} if token else {}
        request = urllib.request.Request(self.base+path,
            data=json.dumps(data).encode() if data is not None else None, headers=headers)
        with self.opener.open(request) as response:
            return json.load(response)

    def test_channel_bound_commands_reach_only_the_selected_arm(self):
        for side, channel, selected, peer in (
            ('left', 'can1', self.left, self.right), ('right', 'can0', self.right, self.left)
        ):
            path = f'/api/arms/{side}/{channel}/command'
            self.request(path, {'action': 'enable', 'client': 'test'})
            self.assertTrue(selected.controller.enabled)
            self.assertFalse(peer.controller.enabled)
            self.request(path, {'action': 'stop', 'client': 'test'})
        self.request('/api/command', {'action': 'enable', 'client': 'test'})
        self.assertTrue(self.right.controller.enabled)
        self.assertFalse(self.left.controller.enabled)

    def test_trajectory_rejection_logs_both_hops_and_reaches_the_client(self):
        client = ArmWorkbenchClient(self.base, 'left')
        error = 'Expired trajectory request'
        with patch.object(self.left.controller, 'command', side_effect=ValueError(error)), \
                self.assertLogs('r5.workbench.http', level='WARNING') as access:
            with self.assertRaises(urllib.error.HTTPError) as caught:
                client.command('policy_trajectory')

        with caught.exception as response:
            self.assertEqual(response.code, 400)
            self.assertIn(error, str(response))
            self.assertEqual(json.load(response), {'error': f'控制服务：{error}'})
        self.assertEqual(len(access.output), 2)
        for entry, port, path in (
            (access.output[0], self.left.server_port, '/api/command'),
            (access.output[1], self.proxy.server_port, '/api/arms/left/can1/command'),
        ):
            self.assertIn(f'port={port} method=POST path={path!r} status=400', entry)
            self.assertIn("action='policy_trajectory'", entry)
            self.assertIn(error, entry)
            self.assertNotIn(client.token, entry)
            self.assertNotIn(client.client, entry)

    def test_cross_arm_interlock_also_covers_legacy_connect(self):
        with self.left.lock:
            self.left.controller.enabled = True
            self.left.controller.last_beat = self.left.controller.clock()+10
        for path in ('/api/command', '/api/arms/right/can0/command'):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.request(path, {'action': 'connect', 'client': 'test',
                                    'acknowledge_initialization': True})
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()
        self.assertFalse(self.right.controller.enabled)

    def test_camera_routes_and_independent_state(self):
        with self.opener.open(self.base+'/api/cameras/gemini_right/frame.jpg') as response:
            self.assertEqual(response.read(), b'left-camera')
        result = self.request('/api/arms')
        self.assertEqual([(arm['id'], arm['channel']) for arm in result['arms']],
                         [('left', 'can1'), ('right', 'can0')])
        self.assertEqual(result['recording_arm'], 'right')
        self.assertTrue(all(arm['state'] is not None for arm in result['arms']))
        for arm in result['arms']:
            with self.opener.open(self.base + arm['wrist_camera_path']) as response:
                self.assertEqual(response.read(), f"{arm['id']}-camera".encode())

    def test_slow_state_trace_links_client_proxy_and_upstream(self):
        client = ArmWorkbenchClient(self.base, 'left')
        with patch('workbench_timing.STAGE_TIMING_ENABLED', True), \
             patch('workbench_timing.SLOW_REQUEST_S', 0), \
             self.assertLogs('r5.workbench.timing', level='WARNING') as records:
            self.assertTrue(client.state()['simulation'])
        traces = [entry.split('trace_id=', 1)[1].split()[0] for entry in records.output]
        self.assertEqual(len(traces), 3)
        self.assertEqual(len(set(traces)), 1)
        self.assertRegex(traces[0], r'^[0-9a-f]{32}$')
        for component in ('client', 'proxy', 'upstream'):
            self.assertTrue(any(f'R5 timing {component}' in entry for entry in records.output))

    def test_stop_log_identifies_browser_trigger_and_paired_process(self):
        path = '/api/arms/left/can1/command'
        caller = 'browser-client-private-id'
        request = urllib.request.Request(self.base+path,
            data=json.dumps({'action': 'stop', 'client': caller}).encode(),
            headers={'Origin': self.base, 'X-Control-Token': self.proxy.token,
                     'X-R5-Stop-Trigger': 'space_key'})
        with patch('workbench_timing.STAGE_TIMING_ENABLED', False), \
             self.assertLogs('r5.workbench.http', level='INFO') as access:
            with self.opener.open(request) as response:
                self.assertEqual(response.status, 200)
        upstream, proxy = access.output
        self.assertIn('source=workbench_proxy', upstream)
        self.assertIn('source=browser peer=127.0.0.1:', proxy)
        self.assertIn('stop_trigger=space_key', proxy)
        for field in ('trace_id', 'client_fingerprint'):
            value = proxy.split(f'{field}=', 1)[1].split()[0]
            self.assertRegex(value, r'^[0-9a-f]+$')
            self.assertIn(f'{field}={value}', upstream)
        self.assertNotIn(caller, '\n'.join(access.output))
        self.assertNotIn(self.proxy.token, '\n'.join(access.output))

        client = ArmWorkbenchClient(self.base, 'left')
        self.proxy.paired_policy_client = client.client
        with patch('visual_control.sys.argv', ['/local/tools/held_policy_review.py']), \
             patch('visual_control.os.getpid', return_value=12345), \
             self.assertLogs('r5.workbench.http', level='INFO') as access:
            client.command('stop')
        proxy = access.output[-1]
        self.assertIn("action='stop'", proxy)
        self.assertIn('source=paired_policy', proxy)
        self.assertIn('reported_program=held_policy_review.py reported_pid=12345', proxy)
        self.assertNotIn(client.client, proxy)

    def test_external_camera_router_falls_back_to_available_upstream(self):
        left = FailingCamera('left-camera')
        right = Cameras('right-camera')
        router = CameraRouter([left, right])
        self.assertEqual(router.get('external'), (b'right-camera', '1', 'right-camera'))
        self.assertIs(router.preferred, right)
        self.assertEqual(router.get('external'), (b'right-camera', '1', 'right-camera'))

    def test_missing_peer_blocks_enable_but_not_stop(self):
        with patch.object(self.proxy.arms['right'], 'snapshot', side_effect=ValueError('offline')):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.request('/api/arms/left/can1/command', {'action': 'enable', 'client': 'test'})
            self.assertEqual(caught.exception.code, 400)
            caught.exception.close()
            state = self.request('/api/arms/left/can1/command', {'action': 'stop', 'client': 'test'})
            self.assertFalse(state['enabled'])
            summary = self.request('/api/arms')
            self.assertIsNone(summary['arms'][1]['state'])

    def test_routes_require_token_and_reject_wrong_can_mapping(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.request('/api/arms/right/can0/command', {'action': 'enable', 'client': 'test'}, token=False)
        self.assertEqual(caught.exception.code, 403)
        caught.exception.close()
        with patch.object(self.proxy.arms['right'], 'snapshot',
                          return_value={'simulation': False, 'channel': 'can1'}), \
             patch.object(self.proxy.arms['right'], 'command') as command:
            with self.assertRaises(ValueError):
                self.proxy.arm_command('right', {'action': 'enable', 'client': 'test'})
            command.assert_not_called()

    def test_old_or_mismatched_control_route_is_rejected_before_dispatch(self):
        with patch.object(self.proxy, 'arm_command') as command:
            for path in ('/api/arms/right/command', '/api/arms/left/can0/command',
                         '/api/arms/right/can1/command'):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    self.request(path, {'action': 'enable', 'client': 'test'})
                self.assertEqual(caught.exception.code, 409)
                caught.exception.close()
            command.assert_not_called()
