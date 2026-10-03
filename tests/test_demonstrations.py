import io
import json
import tarfile
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest.mock import patch

from app import Workbench
from record_workbench import RecordingWorkbench


class Cameras:
    def __init__(self):
        self.sequence = 0
        self.failed = False

    def get(self, key):
        if self.failed:
            raise RuntimeError('camera disconnected')
        self.sequence += 1
        return b'\xff\xd8test\xff\xd9', self.sequence, '/dev/test'

    def close(self):
        pass


class RecordingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.cameras = Cameras()
        self.upstream = Workbench(('127.0.0.1', 0), cameras=self.cameras)
        self.upstream_thread = threading.Thread(target=self.upstream.serve_forever, daemon=True)
        self.upstream_thread.start()
        self.server = RecordingWorkbench(('127.0.0.1', 0),
            f'http://127.0.0.1:{self.upstream.server_port}', Path(self.temp.name))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f'http://127.0.0.1:{self.server.server_port}'
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.upstream.shutdown()
        self.upstream.server_close()
        self.upstream_thread.join()
        self.temp.cleanup()

    def get(self, path):
        with self.opener.open(self.base + path, timeout=5) as response:
            return json.load(response)

    def post(self, path, data, token=None, origin=None):
        headers = {'Content-Type': 'application/json',
                   'X-Control-Token': self.server.token if token is None else token}
        if origin:
            headers['Origin'] = origin
        request = urllib.request.Request(self.base + path, data=json.dumps(data).encode(), headers=headers)
        with self.opener.open(request, timeout=6) as response:
            return json.load(response)

    def wait_for(self, predicate):
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(.03)
        self.fail('Recording did not become ready')

    def test_timed_trajectory_exceeding_16kb_reaches_upstream_unchanged(self):
        payload = {'action': 'policy_trajectory', 'client': 'fixture',
                   'start_deg': [0.] * 6,
                   'points_deg': [[i * .0001] * 6 for i in range(600)],
                   'times_s': [(i + 1) * .02 for i in range(600)], 'issued_at': time.monotonic()}
        self.assertGreater(len(json.dumps(payload).encode()), 16384)
        with patch.object(self.upstream.controller, 'command') as command:
            self.post('/api/command', payload)
            command.assert_called_once_with(payload)
            with self.assertRaises(urllib.error.HTTPError) as error:
                self.post('/api/command', {'action': 'target', 'client': 'fixture', 'note': 'x' * 17000})
            self.assertEqual(error.exception.code, 400)
            error.exception.close()
            self.assertEqual(command.call_count, 1)

    def test_recording_is_observation_only_and_downloadable(self):
        before = self.get('/api/state')
        episode = self.post('/api/recording/start', {'name': 'tennis <test>'})
        self.wait_for(lambda: self.get('/api/recording/status')['episode']['counts']['external'] >= 2)
        self.post('/api/recording/marker', {'phase': 'grasp', 'note': 'manual label'})
        result = self.post('/api/recording/stop', {'result': 'partial'})
        after = self.get('/api/state')
        self.assertEqual(result['status'], 'saved')
        self.assertEqual(before['events'], after['events'])
        self.assertEqual(before['joints_deg'], after['joints_deg'])
        self.assertFalse(after['enabled'])
        self.assertGreater(result['counts']['states'], 0)
        self.assertGreater(result['counts']['gemini'], 0)
        self.assertEqual(result['markers'][0]['phase'], 'grasp')
        self.assertEqual(result['counts']['commands'], 0)
        with self.opener.open(self.base + f"/api/recordings/{episode['id']}/download") as response:
            data = response.read()
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            names = archive.getnames()
            self.assertIn(episode['id'] + '/manifest.json', names)
            timeline = archive.extractfile(episode['id'] + '/timeline.jsonl').read().decode()
            rows = [json.loads(line) for line in timeline.splitlines()]
            frames = [row for row in rows if row['type'] == 'frame']
            self.assertTrue(all(episode['id']+'/'+row['path'] in names for row in frames))
            self.assertTrue(all(row['t_ns'] >= 0 for row in rows))

    def test_commands_and_rejections_are_recorded(self):
        self.post('/api/recording/start', {'name': 'commands'})
        self.post('/api/command', {'action': 'settings', 'speed': .15, 'client': 'test'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post('/api/command', {'action': 'target', 'joints_deg': [1]*6, 'client': 'test'})
        caught.exception.close()
        result = self.post('/api/recording/stop', {})
        self.assertEqual(result['counts']['commands'], 2)
        self.assertEqual(result['counts']['rejected_commands'], 1)
        self.assertEqual(self.get('/api/state')['speed'], .15)
        self.assertFalse(self.get('/api/state')['enabled'])

    def test_auth_origin_and_duplicate_start(self):
        for arguments in ({'token': 'wrong'}, {'origin': 'https://example.com'}):
            with self.assertRaises(urllib.error.HTTPError) as caught:
                self.post('/api/recording/start', {'name': 'bad'}, **arguments)
            self.assertEqual(caught.exception.code, 403)
            caught.exception.close()
        self.assertIsNone(self.server.recorder.current)
        self.post('/api/recording/start', {'name': 'one'})
        with self.assertRaises(urllib.error.HTTPError) as caught:
            self.post('/api/recording/start', {'name': 'two'})
        self.assertEqual(caught.exception.code, 400)
        caught.exception.close()
        self.post('/api/recording/stop', {})

    def test_camera_failure_does_not_discard_feedback(self):
        self.cameras.failed = True
        self.post('/api/recording/start', {'name': 'camera failure'})
        self.wait_for(lambda: self.get('/api/recording/status')['episode']['counts']['capture_errors'] >= 2)
        result = self.post('/api/recording/stop', {'result': 'failed'})
        self.assertGreater(result['counts']['states'], 0)
        self.assertGreaterEqual(result['counts']['capture_errors'], 2)
        self.assertEqual(result['counts']['gemini'], 0)

    def test_restart_retains_history_and_rejects_traversal(self):
        self.post('/api/recording/start', {'name': 'persist'})
        result = self.post('/api/recording/stop', {})
        self.server.recorder.current = None
        history = self.get('/api/recordings')
        self.assertEqual(history[0]['id'], result['id'])
        with self.assertRaises(ValueError):
            self.server.recorder.episode_path('../outside')

    def test_shutdown_does_not_disconnect_upstream(self):
        self.post('/api/recording/start', {'name': 'shutdown'})
        self.server.recorder.close()
        self.assertEqual(self.server.recorder.current.status()['status'], 'saved')
        self.assertEqual(self.server.recorder.current.status()['result'], 'partial')
        self.assertIsNone(self.upstream.controller.owner)

    def test_recording_stop_preserves_control_and_heartbeat(self):
        self.post('/api/recording/start', {'name': 'control remains independent'})
        self.post('/api/command', {'action': 'enable', 'client': 'test'})
        for _ in range(8):
            state = self.post('/api/command', {'action': 'heartbeat', 'client': 'test', 'jog': [0.1, 0, 0, 0, 0, 0]})
            self.assertTrue(state['enabled'])
            time.sleep(.06)
        self.post('/api/recording/stop', {})
        self.assertTrue(self.get('/api/state')['enabled'])
        self.post('/api/command', {'action': 'stop', 'client': 'test'})

    def test_disk_failure_is_visible_and_does_not_enable_arm(self):
        with patch.object(Path, 'write_bytes', side_effect=OSError('disk full')):
            self.post('/api/recording/start', {'name': 'disk failure'})
            self.wait_for(lambda: self.server.recorder.current.done.is_set())
        result = self.get('/api/recording/status')['episode']
        self.assertEqual(result['status'], 'error')
        self.assertIn('disk full', result['error'])
        self.assertFalse(self.get('/api/state')['enabled'])


if __name__ == '__main__':
    unittest.main()
