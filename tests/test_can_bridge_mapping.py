"""Exercise bridge identity checks with fake processes and no hardware access."""
import importlib.util
import io
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('rebuild_left', ROOT / 'tools/rebuild_left_can_bridge.py')
rebuild = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rebuild)


class CanBridgeMappingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'proc').mkdir()
        (self.root / 'sys/class/net/can0').mkdir(parents=True)
        self.states = {side: dict(simulation=False, channel=channel, enabled=False,
                                 moving=False, owner=None, robot_status='fault',
                                 worker_running=side == 'right')
                       for side, channel in [('left', 'can0'), ('right', 'can1')]}
        self.left = ['/usr/bin/slcand', '-o', '-f', '-s8', rebuild.ADAPTER, 'can0']
        self.right = ['/usr/bin/slcand', '-o', '-f', '-s8',
                      rebuild.ADAPTER.replace('2088335E5931', '208833765931'), 'can1']
        self.proc(101, self.left)
        self.proc(202, self.right)
        self.proc(303, ['/usr/bin/python3', '/project/robot_worker.py', 'can1'])
        def fake_path(value):
            path = Path(value)
            return self.root / str(path).lstrip('/') if path.is_absolute() else path
        self.addCleanup(patch.stopall)
        patch.object(rebuild, 'Path', side_effect=fake_path).start()
        patch.object(Path, 'is_char_device', return_value=True).start()
        opener = patch.object(rebuild.urllib.request, 'build_opener').start().return_value
        opener.open.side_effect = lambda url, timeout: io.StringIO(
            json.dumps(self.states[url.split('/')[-2]]))
        self.signal = patch.object(rebuild.signal, 'pidfd_send_signal').start()
        self.run = patch.object(rebuild.subprocess, 'run').start()

    def tearDown(self):
        self.signal.assert_not_called()
        self.run.assert_not_called()

    def proc(self, pid, argv):
        directory = self.root / 'proc' / str(pid)
        directory.mkdir(exist_ok=True)
        (directory / 'cmdline').write_bytes(('\0'.join(argv) + '\0').encode())

    def test_exchanged_mapping_selects_only_physical_left(self):
        self.assertEqual(rebuild.preflight(), (101, self.left))

    def test_old_mapping_is_rejected(self):
        self.proc(101, self.left[:-2] + [self.right[-2], 'can0'])
        with self.assertRaisesRegex(RuntimeError, 'Unexpected left bridge arguments'):
            rebuild.preflight()

    def test_wrong_channel_for_left_adapter_is_rejected(self):
        self.proc(101, self.left[:-1] + ['can1'])
        with self.assertRaisesRegex(RuntimeError, 'Unexpected left bridge arguments'):
            rebuild.preflight()

    def test_active_left_sdk_process_is_rejected(self):
        self.proc(404, ['/usr/bin/python3', '/project/robot_worker.py', 'can0'])
        with self.assertRaisesRegex(RuntimeError, 'left SDK worker'):
            rebuild.preflight()

    def test_enabled_arm_is_rejected(self):
        self.states['left']['enabled'] = True
        with self.assertRaisesRegex(RuntimeError, 'left: requires disabled'):
            rebuild.preflight()

    def test_owned_right_arm_is_rejected(self):
        self.states['right']['owner'] = 'active-controller'
        with self.assertRaisesRegex(RuntimeError, 'right: requires disabled'):
            rebuild.preflight()

    def test_duplicate_left_bridges_are_rejected(self):
        self.proc(405, self.left)
        with self.assertRaisesRegex(RuntimeError, 'found 2'):
            rebuild.preflight()

    def test_check_mode_does_not_open_process_handle(self):
        with patch('sys.argv', ['rebuild_left_can_bridge.py', '--check']), \
                patch.object(rebuild.os, 'pidfd_open') as handle, patch('sys.stdout', io.StringIO()):
            rebuild.main()
            handle.assert_not_called()

    def test_restore_and_restart_use_same_physical_left(self):
        restore = (ROOT / 'tools/restore_can.sh').read_text()
        restart = (ROOT / 'tools/restart_left_can_bridge.py').read_text()
        self.assertEqual(re.search(r"^adapter='([^']+)'", restore, re.M)[1], rebuild.ADAPTER)
        self.assertEqual(re.search(r"^ADAPTER = '([^']+)'", restart, re.M)[1], rebuild.ADAPTER)
        self.assertIn('2088335E5931-if00', rebuild.ADAPTER)


if __name__ == '__main__':
    unittest.main()
