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
