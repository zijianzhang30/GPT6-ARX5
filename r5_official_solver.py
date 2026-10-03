"""Offline adapter for ARX R5's native kinematic_solver; never opens CAN."""
import ctypes
from functools import lru_cache
import importlib.util
import sysconfig

import numpy as np

from control import Kinematics, LOWER, UPPER, ROOT, rpy_matrix, rotation_error
from motion_safety import JOINT_MARGIN_DEG, JOINT_STEP_DEG, JOINT_STEP_NORM_DEG


@lru_cache(maxsize=1)
def _native_module():
    sdk = ROOT/'vendor/R5-master/py/ARX_R5_python/bimanual'
    extension = sdk/'api/arx_r5_python'/(
        'kinematic_solver'+sysconfig.get_config_var('EXT_SUFFIX'))
    try:
        # Resolve bundled dependencies without importing bimanual's arm classes
        # or requiring LD_LIBRARY_PATH in every policy entry point.
        handles = [ctypes.CDLL(str(path), mode=ctypes.RTLD_GLOBAL) for path in (
            ROOT/'kdl_local/lib/libkdl_parser.so', sdk/'lib/libkinematic_solver.so')]
        spec = importlib.util.spec_from_file_location('kinematic_solver', extension)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module._dependency_handles = handles
        return module
    except (OSError, ImportError) as exc:
        raise RuntimeError(
            'Official R5 kinematic_solver could not load; build its Python binding '
            'for this interpreter and install the bundled KDL dependency'
        ) from exc


def _six(value):
    result = np.asarray(value, dtype=float)
    if result.shape != (6,) or not np.isfinite(result).all():
        raise ValueError('Expected six finite joint radians or xyzrpy values')
    return np.ascontiguousarray(result).copy()


class R5Solver:
    """Official FK/IK in the existing policy's base-to-link6 convention.

    ARX's standalone solver subtracts its zero-pose translation from FK.
    Restore that base-frame offset before the separate link6-to-TCP transform.
    The Python URDF model is used only to establish and audit this convention.
    """
    name = 'ARX R5 official kinematic_solver + upstream ContinuousIK refinement'

    def __init__(self):
        self.native = _native_module().KinematicSolver()
        model = Kinematics()
        zero = np.zeros(6)
        self.base_offset_m = model.fk(zero)[:3, 3]-_six(
            self.native.forward_kinematics(zero))[:3]
        for joints in (zero, np.array([.6, 0, 0, 0, 0, 0]),
                       np.array([-.25, .43, .02, .20, -.08, -.04]),
                       np.array([0., .8, 1.2, .3, .4, .1])):
            official = self.forward_kinematics(joints)
            expected = model.fk(joints)
            if (np.linalg.norm(official[:3]-expected[:3, 3]) > 1e-8
                    or np.linalg.norm(rotation_error(
                        rpy_matrix(official[3:]), expected[:3, :3])) > 1e-7):
                raise ValueError('Official R5 solver and configured URDF frames disagree')

    def forward_kinematics(self, q):
        pose = _six(self.native.forward_kinematics(_six(q)))
        pose[:3] += self.base_offset_m
        return pose

    def multi_trial_ik(self, pose, seed, trials):
        target, current = _six(pose), _six(seed)
        target[:3] -= self.base_offset_m
        try:
            candidate = _six(self.native.inverse_kinematics(target))
        except ValueError:
            return -1, current
        except RuntimeError as exc:
            # Native non-convergence is a rejected candidate, not a device fault.
            # Upstream still refines from the seed and audits the complete path.
            if str(exc).strip().rstrip('.') != 'Inverse kinematics computation failed':
                raise
            return -1, current
        candidate += 2*np.pi*np.round((current-candidate)/(2*np.pi))
        delta = np.degrees(candidate-current)
        margin = np.radians(JOINT_MARGIN_DEG)
        # The official API has no seed argument or success status. Never start
        # upstream refinement on a distant branch or an out-of-bounds result.
        if (np.any(candidate < LOWER+margin) or np.any(candidate > UPPER-margin)
                or np.max(np.abs(delta)) > JOINT_STEP_DEG
                or np.linalg.norm(delta) > JOINT_STEP_NORM_DEG):
            return -2, current
        return 0, candidate

    @staticmethod
    def get_ik_status_name(status):
        return {0: 'R5_OFFICIAL_IK_CANDIDATE', -1: 'R5_OFFICIAL_IK_INVALID',
                -2: 'R5_OFFICIAL_IK_BRANCH_REJECTED'}.get(status, 'R5_OFFICIAL_IK_UNKNOWN')
