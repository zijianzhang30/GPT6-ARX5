import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch


class StartIdleReviewTests(unittest.TestCase):
    def test_single_arm_launch_uses_single_host_without_actuation_or_stdin_replacement(self):
        spec = importlib.util.spec_from_file_location('start_review_test',
            Path(__file__).resolve().parents[1]/'tools/start_idle_review.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        clients = []
        def make_client(*args):
            client = Mock()
            client.state.return_value = dict(robot_status='ready', enabled=False,
                                              moving=False, owner=None)
            clients.append(client)
            return client
        camera = Mock();camera.base='http://127.0.0.1:8768'
        response = Mock();response.headers.get.return_value = 'frame-1'
        camera.opener.open.return_value.__enter__ = Mock(return_value=response)
        camera.opener.open.return_value.__exit__ = Mock(return_value=False)
        with patch.object(module, 'ArmWorkbenchClient', side_effect=make_client), \
             patch.object(module, 'WorkbenchClient', return_value=camera), \
             patch.object(module.os, 'execv') as execute, \
             patch.object(module.sys, 'argv', ['start_idle_review.py','--arm','left',
                 '--output','/tmp/test-review','--paired-client','test-owner']):
            original_stdin = module.sys.stdin
            module.main()
            self.assertIs(module.sys.stdin, original_stdin)
        argv = execute.call_args.args[1]
        self.assertTrue(argv[2].endswith('/tools/single_policy_review.py'))
        self.assertEqual(argv[argv.index('--arm')+1], 'left')
        self.assertNotIn('--prepare-idle', argv)
        self.assertEqual(camera.opener.open.call_count, 9)
        for client in clients:
            client.command.assert_not_called()


if __name__ == '__main__':
    unittest.main()
