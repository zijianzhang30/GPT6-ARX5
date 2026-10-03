"""R5 bindings for the original GPT-Policy Cartesian tools and planner."""
import copy
import hashlib
import json
from pathlib import Path
import sys

import numpy as np
from jsonschema import Draft202012Validator

from control import LOWER, UPPER, ROOT, URDF
from r5_official_solver import R5Solver
from motion_safety import finite
from policy_trajectory import PolicyTrajectory, preview_trajectory, check_tracking_reserve
from motion_safety import (GRIPPER_STEP_RAW, GRIPPER_CLOSE_STEP_RAW, SESSION_GRIPPER_TRAVEL_RAW,
                           JOINT_STEP_DEG, JOINT_STEP_NORM_DEG, SESSION_PROPOSALS,
                           SESSION_EXCURSION_DEG, SESSION_JOINT_TRAVEL_DEG)

SOURCE = ROOT/'vendor/GPT-Policy-main/src'
if str(SOURCE) not in sys.path:
    sys.path.insert(0, str(SOURCE))

from gpt_policy.geometry.frames import FrameCalibration
from gpt_policy.geometry.poses import rpy_to_quaternion
from gpt_policy.harness.models import AgentContext
from gpt_policy.harness.protocol import instructions
from gpt_policy.motion.ik import ContinuousIK
from gpt_policy.tools.catalog import load_tool_catalog
from gpt_policy.tools.runtime import ToolExecutor
from gpt_policy.vision.perception import PixelLocalizer


STAGES = ('motion', 'vision', 'grasp', 'image_grasp')


def profile_issues(settings, camera_mode='wrist', stage='grasp', *, commissioning=False):
    """Report missing measured inputs before any device enable or model startup."""
    issues = []
    if stage not in STAGES:
        return ['Unknown Cartesian stage: '+str(stage)]
    if commissioning and stage != 'motion':
        return ['Commissioning permits motion-only validation, not grasping or localization']
    if not isinstance(settings, dict):
        return ['Profile must be an object']
    for section in ('calibration', 'vision', 'gripper', 'scene'):
        if not isinstance(settings.get(section), dict):
            return ['Profile section must be an object: '+section]
    for section, names in (('calibration', ('link6_from_camera', 'base_from_camera')),
                           ('vision', ('camera_intrinsics', 'distortion_coefficients', 'image_sizes', 'device_ids'))):
        if any(not isinstance(settings[section].get(name), dict) for name in names):
            return ['Missing mapping in profile section: '+section]
    if settings.get('version') != 1 or settings.get('robot_model') != 'R5':
        issues.append('Expected version 1 R5 profile')
    experimental_image_grasp = stage == 'image_grasp'
    if not commissioning and not experimental_image_grasp and settings.get('kinematics_verified') is not True:
        issues.append('R5 joint directions/zero offsets and kinematics require physical verification')
    if not commissioning and not experimental_image_grasp and (not isinstance(settings.get('measurement_record'), str) or not settings['measurement_record'].strip()):
        issues.append('Missing measurement_record for physical validation')
    if settings.get('urdf_sha256') != hashlib.sha256(URDF.read_bytes()).hexdigest():
        issues.append('Missing or mismatched validated URDF hash')
    calibration = settings.get('calibration') or {}

    def transform(value, name):
        try:
            m = np.asarray(value, dtype=float)
            valid = (m.shape == (4, 4) and np.isfinite(m).all()
                     and np.allclose(m[3], [0, 0, 0, 1], atol=1e-8)
                     and np.allclose(m[:3, :3].T@m[:3, :3], np.eye(3), atol=1e-6)
                     and abs(np.linalg.det(m[:3, :3])-1) < 1e-6)
        except (TypeError, ValueError):
            valid = False
        if not valid:
            issues.append('Missing/invalid rigid transform: '+name)

    transform(calibration.get('link6_from_tcp'), 'link6_from_tcp')
    tcp_validation = calibration.get('tcp_validation')
    if not commissioning and not experimental_image_grasp and tcp_validation is not None:
        if (not isinstance(tcp_validation, dict)
                or tcp_validation.get('status') != 'verified'
                or not isinstance(tcp_validation.get('physical_validation_record'), str)
                or not tcp_validation['physical_validation_record'].strip()):
            issues.append('TCP transform is an estimate; physical validation record is required')
    # The adapter solver returns link6 itself; it never uses the SDK's EEF mode.
    link6 = np.asarray(calibration.get('link6_from_sdk_eef'), dtype=float)
    if link6.shape != (4, 4) or not np.array_equal(link6, np.eye(4)):
        issues.append('link6_from_sdk_eef must be identity for the R5 URDF solver')
    if stage == 'motion':
        return issues
    if stage == 'image_grasp':
        grip = settings.get('gripper') or {}
        for kind in ('command', 'feedback'):
            closed, opened = grip.get(kind+'_closed_raw'), grip.get(kind+'_open_raw')
            if not (finite(closed) and finite(opened) and 0 <= closed < opened <= 5):
                issues.append('Missing measured gripper '+kind+' closed/open endpoints')
        return issues
    transform((calibration.get('link6_from_camera') or {}).get('left'), 'left wrist camera')
    vision = settings.get('vision') or {}
    if not isinstance(vision.get('mount_record'), str) or not vision['mount_record'].strip():
        issues.append('Missing current camera mount measurement record')
    for name in ('left', 'top') if camera_mode == 'both' else ('left',):
        try:
            k = np.asarray((vision.get('camera_intrinsics') or {}).get(name), dtype=float)
            valid = (k.shape == (3, 3) and np.isfinite(k).all() and k[0, 0] > 0
                     and k[1, 1] > 0 and np.allclose(k[2], [0, 0, 1]))
        except (TypeError, ValueError):
            valid = False
        if not valid:
            issues.append('Missing/invalid camera intrinsics: '+name)
        distortion = (vision.get('distortion_coefficients') or {}).get(name)
        if not isinstance(distortion, list) or len(distortion) != 5 or not all(finite(x) for x in distortion):
            issues.append('Missing measured five-coefficient distortion: '+name)
        size = (vision.get('image_sizes') or {}).get(name)
        if not isinstance(size, list) or len(size) != 2 or any(type(v) is not int or v <= 0 for v in size):
            issues.append('Missing calibrated image size: '+name)
        if not (vision.get('device_ids') or {}).get(name):
            issues.append('Missing calibrated camera device identity: '+name)
        if name == 'top':
            transform(((calibration.get('base_from_camera') or {}).get('top') or {}).get('left'), 'fixed top to R5 base')
            if vision.get('top_fixed') is not True:
                issues.append('Top camera must remain fixed for calibrated external geometry')
    if stage == 'vision':
        return issues
    grip = settings.get('gripper') or {}
    for kind in ('command', 'feedback'):
        closed, opened = grip.get(kind+'_closed_raw'), grip.get(kind+'_open_raw')
        if not (finite(closed) and finite(opened) and 0 <= closed < opened <= 5):
            issues.append('Missing measured gripper '+kind+' closed/open endpoints')
    return issues


def load_profile(path, camera_mode):
    settings = json.loads(Path(path).read_text())
    issues = profile_issues(settings, camera_mode)
    if issues:
        raise ValueError('; '.join(issues))
    return settings


class CartesianBackend:
    def __init__(self, backend, settings, camera_mode='wrist', stage='grasp', *, commissioning=False,
                 tracking_reserve_deg=0.0):
        if not finite(tracking_reserve_deg) or tracking_reserve_deg < 0:
            raise ValueError('Invalid planning tracking reserve')
        self.tracking_reserve_deg = tracking_reserve_deg
        issues = profile_issues(settings, camera_mode, stage, commissioning=commissioning)
        if issues:
            raise ValueError('; '.join(issues))
        from gpt_policy.motion.planner import EefTrajectoryPlanner
        from gpt_policy.motion.trajectory import MotionLimits
        self.backend, self.settings, self.camera_mode = backend, copy.deepcopy(settings), camera_mode
        self.stage = stage
        self.commissioning = commissioning
        self.commissioning_submitted = False
        geometry = copy.deepcopy(settings)
        if stage == 'motion':
            geometry['calibration']['link6_from_camera'] = {}
            geometry['calibration']['base_from_camera'] = {}
        self.frames = FrameCalibration(geometry)
        self.solver = R5Solver()
        self.ik = ContinuousIK(self.solver, LOWER+np.radians(2), UPPER-np.radians(2),
                               60, 2e-5, 2e-4, 2e-5, 2e-4)
        self.ik.name = self.solver.name
        limits = MotionLimits(50, .001, .01, .01, .05,
                              np.full(6, np.radians(9)), np.full(6, np.radians(45)),
                              np.full(6, np.radians(240)))
        self.planner = EefTrajectoryPlanner(
            lambda: np.radians(self.backend._read(holding=True)['command_deg']),
            self.frames, self.ik, 50, limits, .1)
        catalog = json.loads((SOURCE.parent/'configs/tools.json').read_text())
        unavailable = {'set_gripper'} if stage not in ('grasp', 'image_grasp') else set()
        if stage in ('motion', 'image_grasp'):
            unavailable.add('locate_point')
        for tool in catalog['tools']:
            if tool['name'] in unavailable:
                tool['enabled'] = False
        self.catalog = load_tool_catalog({'tool_catalog': catalog})
        self.localizer = PixelLocalizer(settings) if stage in ('vision', 'grasp') else None
        self.last_plan_rejection = None
        self.last_plan_rejection_guide = None

    def _demonstrated_pregrasp_guide(self, state):
        demonstration = self.settings.get('demonstrated_pregrasp')
        if not isinstance(demonstration, dict):
            return None
        goal_deg = np.asarray(demonstration.get('joints_deg'), dtype=float)
        current_deg = np.degrees(state['joint_command_positions_rad'])
        if goal_deg.shape != (6,) or not np.isfinite(goal_deg).all():
            return None
        delta = goal_deg-current_deg
        maximum = float(np.max(np.abs(delta)))
        norm = float(np.linalg.norm(delta))
        scale = min(1., 3.5/maximum if maximum > 1e-9 else 1.,
                    4.5/norm if norm > 1e-9 else 1.)
        next_deg = current_deg+scale*delta
        pose = self.frames.sdk_to_tcp(
            self.solver.forward_kinematics(np.radians(next_deg)))
        return {
            'source': demonstration.get('source'),
            'target_joints_deg': goal_deg.tolist(),
            'remaining_joint_delta_deg': delta.tolist(),
            'next_joints_deg': next_deg.tolist(),
            'next_tcp_xyzquat': [*pose[:3], *rpy_to_quaternion(pose[3:])],
            'reached': maximum <= .5,
            'instruction': ('Reference only for the demonstrated IK branch. Choose the next small '
                            'Cartesian target from fresh visual feedback; do not follow this pose '
                            'when its observed image response moves the object away from the gripper.'),
        }

    def __getattr__(self, name):
        return getattr(self.backend, name)

    def check(self):
        self.backend.check()
        if self.backend._read().get('policy_trajectory_protocol') != PolicyTrajectory.protocol:
            self.backend.abort('Workbench lacks timed Cartesian trajectory transport')

    def state(self):
        state = self.backend.state()
        pose = self.frames.sdk_to_tcp(self.solver.forward_kinematics(state['joint_positions_rad']))
        command = self.frames.sdk_to_tcp(self.solver.forward_kinematics(state['joint_command_positions_rad']))
        state.update(tcp_xyzrpy=pose.tolist(), tcp_xyzquat=[*pose[:3], *rpy_to_quaternion(pose[3:])],
                     tcp_command_xyzquat=[*command[:3], *rpy_to_quaternion(command[3:])],
                     gripper_normalized=self._normalized(state['gripper_raw'], 'feedback'),
                     gripper_command_normalized=self._normalized(state['raw_state']['gripper_command_raw'], 'command'))
        state['cartesian_stage'] = self.stage
        guide = self._demonstrated_pregrasp_guide(state)
        if guide is not None:
            state['demonstrated_pregrasp_guide'] = guide
        state['gripper_step_limit_normalized'] = None
        state['gripper_open_step_limit_normalized'] = None
        state['gripper_next_opening_bounds'] = None
        if self.stage in ('grasp', 'image_grasp'):
            grip = self.settings['gripper']
            span = grip['command_open_raw']-grip['command_closed_raw']
            state['gripper_step_limit_normalized'] = GRIPPER_CLOSE_STEP_RAW/span
            state['gripper_open_step_limit_normalized'] = GRIPPER_STEP_RAW/span
            current = state['gripper_command_normalized']
            state['gripper_next_opening_bounds'] = [
                max(0., current-GRIPPER_CLOSE_STEP_RAW/span),
                min(1., current+GRIPPER_STEP_RAW/span)]
        return state

    def _normalized(self, value, kind):
        if self.stage not in ('grasp', 'image_grasp'):
            return None
        grip = self.settings['gripper']
        lo, hi = grip[kind+'_closed_raw'], grip[kind+'_open_raw']
        return (value-lo)/(hi-lo)

    def context(self, task):
        if self.commissioning:
            raise ValueError('Commissioning has no model session; use the explicit one-step validation host')
        arm = getattr(getattr(self.backend, 'client', None), 'arm', 'left')
        arm = arm if arm in ('left', 'right') else 'left'
        channel = 'can0' if arm == 'left' else 'can1'
        config = {**self.settings, 'runtime': {'robot_model': 'R5', 'interface': channel}}
        text = instructions('R5', channel, 6, ('left',), config, self.catalog, task_instruction=task)
        start = text.index('Camera calibration and views:')
        end = text.index('Return exactly one tool selection', start)
        camera_text = ('left is the calibrated Gemini wrist RGB camera rigidly mounted to link6. '
                       'RGB has no depth. locate_point uses the measured intrinsics/extrinsics. '
                       'Two wrist observations need a stationary feature and sufficient parallax. ')
        camera_text += ('top is the calibrated fixed external RGB camera. ' if self.camera_mode == 'both'
                        else 'Only left wrist images are supplied; no top or right camera is available. ')
        if self.stage == 'motion':
            camera_text = ('RGB images are uncalibrated visual observations only. No pixel-to-base '
                           'mapping or depth is available; locate_point is disabled. '
                           'Use independently measured direction and clearance for motion tests. ')
        elif self.stage == 'image_grasp':
            camera_text = ('RGB images are uncalibrated visual observations only. No pixel-to-base '
                           'mapping or metric depth is available; locate_point is disabled. '
                           'This is an attended image-guided grasp, not a calibration test. '
                           'Use fresh views, known robot frame/kinematics, measured joints and '
                           'observed local responses to choose bounded contact-free approach '
                           'corrections when direction and clearance are supported. Missing camera '
                           'calibration or an exact metric target position alone does not require '
                           'give_up. Historical direction evidence must match the current posture '
                           'and views; never invent clearance or blindly repeat an ineffective move. ')
        text = text[:start]+'Camera calibration and views:\n'+camera_text+'\n\n'+text[end:]
        text += (f'\nControlled physical arm: {arm}, interface {channel}. '
                 'The single-arm tool key and wrist image key remain left for protocol compatibility; '
                 f'they refer to this physical {arm} arm, not to another robot. '
                 'The other physical arm is an obstacle and cannot be commanded in this session. '
                 'Select the target from the task instruction and fresh images. Any ball_detection '
                 'metadata is only an auxiliary tennis-ball candidate, not the task target when '
                 'the instruction names a different object. Do not transfer another arm\'s visual '
                 'direction evidence or demonstrated pose to this arm.')
        text += ('\nR5 adaptation: the enabled original Cartesian tools and planner are used. '
                 'gripper metres and torque are unavailable. Current measured TCP derives from '
                 'the official R5 solver with a checked base-origin conversion and the configured '
                 'fingertip transform; this does not establish physical calibration. Preserve tcp_command_xyzquat '
                 'orientation for position-only adjustments. The existing attended-trial limits '
                 f'apply to the entire requested path: {JOINT_STEP_DEG:g} degrees/joint, '
                 f'{JOINT_STEP_NORM_DEG:g} degrees joint norm, '
                 f'{SESSION_PROPOSALS} accepted actions, '
                 f'{SESSION_EXCURSION_DEG:g} degrees excursion, '
                 f'{SESSION_JOINT_TRAVEL_DEG:g} degrees total joint travel, '
                 f'{SESSION_GRIPPER_TRAVEL_RAW:g} raw total gripper travel, '
                 f'{GRIPPER_CLOSE_STEP_RAW:g} raw per closing action and '
                 f'{GRIPPER_STEP_RAW:g} raw per opening action. check_path includes '
                 'these limits but never certifies collision clearance. Completion holds for '
                 'operator handoff without automatic homing or opening. These are per attended '
                 'segment limits; the host may start a new supervised segment at powered hold. '
                 'The model has no budget-reset tool and must never claim or attempt a reset itself, '
                 'but it must not declare the overall task impossible merely because the final goal '
                 'lies beyond the current segment. Every observation exposes measured and commanded '
                 'joints in degrees, per-joint tracking errors, joint bounds, remaining limit margins '
                 'and near_singular. Before each action, assess J1..J6 trends and margins together '
                 'with the images. Prefer a motion that makes useful TCP progress without excessive '
                 'joint travel. During clear, contact-free coarse approach, a host-accepted action '
                 'with a small TCP discrepancy or one barely moving joint is not by itself a reason '
                 'to call give_up. Assess net measured and visual progress over the last three '
                 'distinct approach actions when available, including the size of each requested '
                 'joint change; observations and unchanged-target holds are not additional motion '
                 'trials. Continue an image-supported approach or correction while useful progress '
                 'and clearance remain. Do not require all joints to move on every action, exact '
                 'TCP arrival, or zero residual before continuing. A single tiny opposite-sign '
                 'FK change does not alone establish dangerous reverse motion. These discrepancies '
                 'are not proven random noise, and host acceptance is not proof of clearance. '
                 'If recent progress is absent, choose a meaningfully different supported correction '
                 'instead of repeating holds or increasing the same ineffective target. Stop '
                 'immediately for a host fault, stale feedback, visible obstruction/contact risk, '
                 'or clear unintended motion; do not wait for three actions in those cases. '
                 'Persistent growing residuals with no useful progress and no supported safe '
                 'alternative still require operator handoff. Never reset targets merely to hide '
                 'a residual or infer grasp success from a stall.')
        if self.stage == 'image_grasp':
            text += (' During clearly contact-free coarse approach, choose useful centimetre-scale '
                     'TCP progress or a short move_eef_chunk when fresh views establish the whole '
                     'path clearance. Model calls are slow: when a longer approach is supported, '
                     'prefer one longer continuous planned path over several tiny moves requiring '
                     'separate model calls. Use intermediate waypoints when needed to describe that '
                     'clear path; the whole path must fit the reported joint envelope and travel '
                     'budget. Do not combine an unverified approach, closure and lift without fresh '
                     'visual checks. Do not keep a previously small accepted step as a permanent '
                     'step-size rule. The larger joint envelope is a maximum, not a requested '
                     'displacement; near the target, table, cables, or uncertain contact, reduce '
                     'travel and observe again. If a target is rejected by joint limits or the '
                     'step envelope, reassess the pose and reduce the request; never bypass a '
                     'rejection by blindly replaying chunks without fresh observations.')
        if self.settings.get('demonstrated_pregrasp'):
            text += (' A current operator-confirmed pre-grasp joint demonstration is exposed in '
                     'state.demonstrated_pregrasp_guide as an IK-branch reference only. Fresh visual '
                     'feedback chooses the Cartesian direction. Do not mechanically follow its '
                     'next_tcp_xyzquat when the measured image response moves the target away from the '
                     'finger gap. ContinuousIK is seeded from the current held command, so bounded '
                     'local Cartesian corrections preserve the current branch.')
        if self.camera_mode == 'both' and self.stage == 'image_grasp':
            text += (' For this dual-view grasp, use the external/top view as the primary evidence '
                     'for vertical alignment, remaining approach gap, and whether the finger contact '
                     'surfaces actually straddle the target. This priority also applies at final '
                     'approach and closure, not only coarse approach. Wrist centering, a large target image, '
                     'or overlap with the finger roots in the wrist image is only a projection cue. '
                     'If the external view shows the fingers above/beside the target or still separated, '
                     'remain in alignment/approach and do not close further or lift. A remaining '
                     'gap is a reason to continue a supported contact-free approach, not by itself '
                     'a reason to terminate the task. When the views '
                     'disagree, keep grasp unconfirmed and resolve height/depth from fresh external '
                     'evidence. If already partly closed while misaligned, reopen enough for '
                     'clearance before correcting position; do not squeeze to compensate for an '
                     'approach gap. Neither view alone gives calibrated metric depth. If external '
                     'contact surfaces are occluded, treat them as unknown, not as touching. '
                     'For a closing or lifting decision, state the external-view evidence in the '
                     'tool note as well as wrist alignment; only lift after supported retention '
                     'evidence, then verify the target actually leaves its support and remains held.')
            text += (' Before closing, separately assess lateral alignment, fore-aft insertion '
                     'depth and contact height for each selected arm. A target ahead of the fingertips '
                     'has NOT entered the jaw contact region even if centered between their projected '
                     'image lines. A support below the object is not the object. If the external '
                     'camera or wrist body obscures the contact region, obtain a clearer view or '
                     'continue a supported open-jaw alignment; do not invent contact evidence. '
                     'After an empty lift, reopen for clearance before further approach; never '
                     'advance closed jaws toward the object to increase insertion depth.')
        if self.stage in ('grasp', 'image_grasp'):
            text += (' Normalized gripper opening maps through the configured R5 command/feedback endpoints; '
                     'consult the supplied per-arm evidence for their validation status. '
                     'gripper_step_limit_normalized is the closing increment limit; '
                     'gripper_open_step_limit_normalized is the smaller opening increment limit. '
                     'gripper_next_opening_bounds gives the next absolute opening interval from '
                     'the submitted command, before session budget checks; use its interior to '
                     'avoid rounding at a boundary. Opening by 0.2 is generally too large; '
                     'use the supplied opening increment, then observe and repeat as needed. '
                     'These are maxima, not mandatory step sizes. For a visible wide gap, choose '
                     'a larger closing increment when clearance supports it, then observe again. '
                     'Near possible object contact use smaller increments; do not multiply an absolute '
                     'gripper target or a contact-stage increment by ten. Raw position is not force. '
                     'R5 set_gripper currently executes one bounded raw step; upstream obstruction '
                     'recovery is unavailable. A stall is a fault, not evidence of contact or grasp.')
        else:
            text += (' Stage '+self.stage+': set_gripper is disabled and raw opening is held. '
                     'Normalized opening is unknown (null). This is a contact-free validation '
                     'stage; do not attempt grasping or object contact.')
        return AgentContext(text, self.catalog.function_schemas(6, ('left',)), self.catalog.output_schema(6, ('left',)))

    def executor(self):
        return ToolExecutor(self.catalog, ('left',), self, self.localizer)

    def plan(self, requested, note):
        from gpt_policy.geometry.poses import rotation_distance
        from gpt_policy.motion.trajectory import sample_count_for_segment
        if self.last_plan_rejection and any(text in self.last_plan_rejection for text in (
                'session envelope', 'session joint travel budget')):
            raise ValueError('Session renewal required after motion-budget boundary: '
                             + self.last_plan_rejection)
        state = self.backend._read(holding=True)
        if not isinstance(requested, list) or not 1 <= len(requested) <= 10000:
            raise ValueError('Invalid or oversized Cartesian waypoint list')
        # Keep reference continuity through a real, bounded hold residual. Measured
        # joints remain separate and are checked again immediately before dispatch.
        current = self.frames.sdk_to_tcp(self.solver.forward_kinematics(np.radians(state['command_deg'])))
        points = self.planner._model_points(requested, current)
        if self.commissioning:
            if (len(requested) != 1 or len(points) != 2
                    or np.linalg.norm(points[-1][:3]-current[:3]) > .004+1e-9
                    or rotation_distance(points[-1][3:], current[3:]) > 1e-6):
                raise ValueError('Commissioning permits one translation up to 4 mm with fixed orientation')
        count = max(2, int(np.ceil(self.planner.endpoint_hold_s*self.planner.trajectory_hz)))
        for start, end in zip(points, points[1:]):
            distance = float(np.linalg.norm(end[:3]-start[:3]))
            if not np.isfinite(distance):
                raise ValueError('Invalid Cartesian path length')
            count += sample_count_for_segment(distance, rotation_distance(start[3:], end[3:]), self.planner.limits)
            if count > 10000:
                raise ValueError('Cartesian path exceeds timed transport sample capacity')
        plan = self.planner.plan(requested, note, self._normalized(state['gripper_command_raw'], 'command'))
        plan['planning_measured_joint_positions_rad'] = np.radians(state['joints_deg']).tolist()
        plan['result']['reference_start'] = 'held_command'
        points = np.degrees(plan['joint_positions_rad']).tolist()
        PolicyTrajectory(np.degrees(plan['start_joint_positions_rad']).tolist(), points,
                         plan['relative_times_s'], state['lower_deg'], state['upper_deg'], self.clock())
        try:
            preview_trajectory(self.guard, state, points)
        except ValueError as exc:
            self.last_plan_rejection = str(exc)
            self.last_plan_rejection_guide = self._demonstrated_pregrasp_guide({
                'joint_command_positions_rad': np.radians(state['command_deg'])})
            raise
        self.last_plan_rejection = None
        self.last_plan_rejection_guide = None
        if self.tracking_reserve_deg:
            plan['result']['planning_tracking_reserve'] = check_tracking_reserve(
                state, points, self.tracking_reserve_deg)
        return plan

    def renew_session(self):
        result = self.backend.renew_session()
        self.last_plan_rejection = None
        self.last_plan_rejection_guide = None
        return result

    def execute(self, name, arguments):
        if self.commissioning and (name not in ('move_to', 'check_path') or self.commissioning_submitted):
            raise ValueError('Commissioning allows one move_to only; no repeated motion, gripper or model control')
        self.catalog.definition(name, ('left',))
        params = next(t['function']['parameters'] for t in self.catalog.function_schemas(6, ('left',))
                      if t['function']['name'] == name)
        Draft202012Validator(params).validate(arguments)
        if name == 'set_gripper':
            grip = self.settings['gripper']
            target = grip['command_closed_raw']+arguments['gripper']*(grip['command_open_raw']-grip['command_closed_raw'])
            return self.backend.execute('set_gripper', {'gripper_raw': target, 'note': arguments['note'],
                                        'observation_id': self.backend.observation['observation_id']})
        if name not in ('move_to', 'move_eef_chunk', 'check_path'):
            raise ValueError('Unsupported upstream robot tool')
        plan = self.plan([arguments['target']] if name == 'move_to' else arguments['poses'], arguments['note'])
        if name == 'check_path':
            from gpt_policy.motion.coordination import path_check_result
            return path_check_result({'left': plan})
        if self.commissioning:
            self.commissioning_submitted = True
        result = self.backend.execute_trajectory(plan)
        result['trajectory'] = plan['result']
        return result


class CartesianAgent:
    def __init__(self, agent, catalog, arms=('left',)):
        self.agent, self.catalog = agent, catalog
        self.arms = arms

    def __getattr__(self, name):
        return getattr(self.agent, name)

    def decide(self, turn):
        result = self.agent.decide(turn)
        json.dumps(result, allow_nan=False)
        Draft202012Validator(self.catalog.output_schema(6, self.arms)).validate(
            {k: v for k, v in result.items() if k != '_wire'})
        tool = next(t for t in self.catalog.function_schemas(6, self.arms) if t['function']['name'] == result['name'])
        params = tool['function']['parameters']
        # Upstream Codex represents omitted optional parameters as explicit nulls.
        checked = {k: v for k, v in result['arguments'].items()
                   if not (v is None and k in params['properties'] and k not in params['required'])}
        Draft202012Validator(params).validate(checked)
        return result


class CalibratedCameras:
    def __init__(self, cameras, settings):
        self.source, self.settings = cameras, settings

    def snapshot(self, **kwargs):
        images = self.source.snapshot(**kwargs)
        self.describe(images)
        return images

    def describe(self, images):
        descriptions = self.source.describe(images)
        vision = self.settings['vision']
        for camera in descriptions:
            name = camera['name']
            if ([camera['width'], camera['height']] != vision['image_sizes'][name]
                    or camera['device'] != vision['device_ids'][name]):
                raise ValueError('Current camera differs from the measured calibration: '+name)
            camera['intrinsics'] = vision['camera_intrinsics'][name]
            camera['calibration_record'] = vision['mount_record']
        return descriptions
