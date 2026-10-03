import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from control import Kinematics, rpy_matrix
from r5_official_solver import R5Solver


class OfficialSolverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.solver = R5Solver()

    def test_official_zero_origin_is_converted_to_existing_link6_frame(self):
        for q in (np.zeros(6), np.array([.6, 0, 0, 0, 0, 0]),
                  np.radians([-14.87, 24.75, 1.21, 11.64, -4.75, -2.63])):
            with self.subTest(q=q):
                raw = np.asarray(self.solver.native.forward_kinematics(q))
                actual = self.solver.forward_kinematics(q)
                expected = Kinematics().fk(q)
                np.testing.assert_allclose(actual[:3], expected[:3, 3], atol=1e-9)
                np.testing.assert_allclose(rpy_matrix(actual[3:]), expected[:3, :3], atol=1e-9)
                np.testing.assert_allclose(actual[:3]-raw[:3], self.solver.base_offset_m)

    def test_official_inverse_roundtrip_does_not_call_python_inverse(self):
        q = np.radians([-14.87, 24.75, 1.21, 11.64, -4.75, -2.63])
        pose = self.solver.forward_kinematics(q)
        saved = pose.copy()
        with patch.object(Kinematics, 'solve', side_effect=AssertionError('Python IK called')):
            status, solved = self.solver.multi_trial_ik(pose, q, 5)
        self.assertEqual(status, 0)
        np.testing.assert_allclose(solved, q, atol=2e-4)
        np.testing.assert_array_equal(pose, saved)
        np.testing.assert_allclose(self.solver.forward_kinematics(solved)[:3], pose[:3], atol=2e-5)

    def test_invalid_or_distant_branch_returns_seed_for_upstream_refinement(self):
        seed = np.array([0., .8, 1.2, .3, .4, .1])
        pose = self.solver.forward_kinematics(seed)
        for candidate, expected in ((np.full(6, np.nan), -1), ([0]*5, -1),
                                    (seed+np.array([.5, 0, 0, 0, 0, 0]), -2),
                                    (np.array([0, -1., 1.2, .3, .4, .1]), -2)):
            with self.subTest(candidate=candidate):
                native = SimpleNamespace(inverse_kinematics=lambda p: candidate)
                with patch.object(self.solver, 'native', native):
                    status, result = self.solver.multi_trial_ik(pose, seed, 5)
                self.assertEqual(status, expected)
                np.testing.assert_array_equal(result, seed)
                self.assertIsNot(result, seed)

    def test_bad_input_never_reaches_native_pointer_interface(self):
        native = SimpleNamespace(forward_kinematics=lambda q: self.fail('Native called'))
        with patch.object(self.solver, 'native', native):
            for q in ([0]*5, [0]*7, [np.nan]*6, [[0]*6]):
                with self.assertRaises(ValueError):
                    self.solver.forward_kinematics(q)

    def test_native_nonconvergence_retains_seed_but_unexpected_errors_propagate(self):
        seed = np.array([0., .8, 1.2, .3, .4, .1])
        pose = self.solver.forward_kinematics(seed)
        native = SimpleNamespace(inverse_kinematics=Mock(side_effect=RuntimeError(
            'Inverse kinematics computation failed.')))
        with patch.object(self.solver, 'native', native):
            status, result = self.solver.multi_trial_ik(pose, seed, 5)
            self.assertEqual(status, -1)
            np.testing.assert_array_equal(result, seed)
            self.assertIsNot(result, seed)
            native.inverse_kinematics.side_effect = RuntimeError('Native library unavailable')
            with self.assertRaisesRegex(RuntimeError, 'library unavailable'):
                self.solver.multi_trial_ik(pose, seed, 5)


if __name__ == '__main__':
    unittest.main()
