"""Completed sequential sources may enter a new explicit one-arm task."""
import contextlib
import io
import unittest
from unittest.mock import patch

from tools import held_policy_review


class CompletedReviewTaskModeTests(unittest.TestCase):
    def test_requires_explicit_destination_mode_before_opening_clients(self):
        argv = ['held_policy_review', '--from-review-pid', '123', '--run', '/source',
                '--output', '/new-task', '--paired-client', 'owner']
        with patch('sys.argv', argv), patch.object(held_policy_review, 'ArmWorkbenchClient') as client:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                held_policy_review.main()
            self.assertEqual(caught.exception.code, 2)
            client.assert_not_called()

    def test_explicit_modes_reach_unchanged_client_and_handoff_preconditions(self):
        argv = ['held_policy_review', '--from-review-pid', '123', '--run', '/source',
                '--output', '/new-task', '--paired-client', 'owner']
        for mode in (['--left-return-before-right'], ['--working-arm', 'left'],
                     ['--working-arm', 'right']):
            with self.subTest(mode=mode), patch('sys.argv', argv + mode):
                with patch.object(held_policy_review, 'ArmWorkbenchClient',
                                  side_effect=RuntimeError('client boundary; no hardware')):
                    with self.assertRaisesRegex(RuntimeError, 'client boundary'):
                        held_policy_review.main()

