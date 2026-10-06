"""R5 device-side implementation of GPT-Policy's state/execute contract.

No SDK construction, enable, home, or model calls. The control service must
advertise qualified supervised execution; this is not unattended certification.
The caller must maintain independent heartbeat and camera supervision during
model waits; check() is also suitable for the upstream health callback.
"""
import copy
import math
import threading
import time
import uuid
from collections import deque

import numpy as np

from motion_safety import (ProposalGuard, feedback_issues, finite, vector, SUPERVISED_SPEED,
                           POLICY_SETTLE_ERROR_DEG, POLICY_HOLD_ERROR_DEG, POLICY_REVERSE_DEADBAND_DEG)
from visual_control import step_settled, validate_action
from policy_trajectory import PolicyTrajectory, debit_trajectory, preview_trajectory


GRIPPER_SETTLE_TOLERANCE_RAW = .15


class R5ExecutionFault(RuntimeError):
    pass


class R5SettleTimeout(R5ExecutionFault):
    """The existing arrival test failed; never means a successful grasp."""


class R5PoweredHoldFault(R5ExecutionFault):
    """Task remains faulted while independent supervision maintains hold."""


class R5PolicyBackend:
    def __init__(self, client, vision_check, *, clock=time.monotonic, sleep=time.sleep,
                 minimum_cartesian_command_step_deg=0., retain_settle_fault_hold=False):
        if type(retain_settle_fault_hold) is not bool:
            raise ValueError('retain_settle_fault_hold must be a boolean')
        if (not finite(minimum_cartesian_command_step_deg)
                or not 0 <= minimum_cartesian_command_step_deg <= 24.):
            raise ValueError('Minimum Cartesian command step must be finite within 0..24 degrees')
        # Optional conservative proposal filter. This is not a calibrated motor
        # deadband and never changes an endpoint, settle rule, or fault response.
        self.minimum_cartesian_command_step_deg = minimum_cartesian_command_step_deg
        self.client = client
        self.vision_check = vision_check
        self.clock, self.sleep = clock, sleep
        self.guard = ProposalGuard()
        self.observation = None
        self.consumed = False
        self.fault = None
        self.retain_settle_fault_hold = retain_settle_fault_hold
        self.fault_hold = None
        self.fault_hold_failure = None
        self.stop_requested = False
        self.busy = False
        self.engaged = False
        self.last_execution_feedback = None
        self.last_budget_rejection = None
        self.operation_lock = threading.Lock()
        # Serialize fault cancellation with submission, as in upstream MotionControl.
        self.command_lock = threading.RLock()

    def _read(self, *, holding=False):
        with self.command_lock:
            return self._read_locked(holding=holding)

    def _read_locked(self, *, holding=False):
        if self.fault is not None:
            if self.fault_hold is not None:
                raise R5PoweredHoldFault(self.fault)
            raise R5ExecutionFault(self.fault)
        state = self.client.state()
        return self._validate_state(state, holding=holding, guard=self.guard)

    def _validate_state(self, state, *, holding, guard):
        """Shared health checks; the task-facing read always enforces its latch."""
        issues = feedback_issues(state)
        for key, expected in (("simulation", False), ("worker_running", True),
                              ("model_ready", True), ("enabled", True),
                              ("hold_available", True), ("policy_execution_available", True)):
            if state.get(key) is not expected:
                issues.append(f"{key} must be {expected}")
        if state.get('worker_protocol_version') != 2:
            issues.append('Worker protocol 2 with target expiry is required')
        if state.get("robot_status") != "ready" or state.get("error_codes") != []:
            issues.append("Robot is not ready or SDK errors are present")
        if state.get("owner") != self.client.client:
            issues.append("An explicitly assigned control owner is required")
        if (state.get("mode") != "joint" or not finite(state.get("speed"))
                or not 0 < state["speed"] <= SUPERVISED_SPEED):
            issues.append(
                f"Expected joint mode at no more than {SUPERVISED_SPEED:.0%} speed"
            )
        if not vector(state.get("command_deg")) or not finite(state.get("gripper_command_raw")):
            issues.append("Actual submitted targets are unavailable")
        elif not 0 <= state["gripper_command_raw"] <= 5:
            issues.append("Submitted gripper target is outside raw limits")
        if holding:
            if state.get("control_state") != "holding" or not vector(state.get("hold_target_deg")):
                issues.append("A completed powered hold is required")
            elif vector(state.get("joints_deg")) and vector(state.get("command_deg")):
                residual = max(abs(a-b) for a, b in zip(state["hold_target_deg"], state["joints_deg"]))
                command_error = max(abs(a-b) for a, b in zip(state["hold_target_deg"], state["command_deg"]))
                if residual > POLICY_HOLD_ERROR_DEG or command_error > .05:
                    issues.append(f"Hold target and measured/submitted positions disagree: "
                                  f"measured_error_deg={residual:.6f}, limit_deg={POLICY_HOLD_ERROR_DEG}, "
                                  f"command_error_deg={command_error:.6f}, command_limit_deg=0.05")
            if (finite(state.get("gripper_command_raw")) and finite(state.get("gripper_target_raw"))
                    and abs(state["gripper_target_raw"]-state["gripper_command_raw"]) > .01):
                issues.append("Held gripper still has a pending target")
        if issues:
            raise R5ExecutionFault("; ".join(issues))
        guard.check_state(state)
        return state

    def _fail(self, error, *, request_stop):
        # Only this typed arrival failure may try the optional hold path. A
        # camera, watchdog, transport or hardware error never enters it.
        if (type(error) is R5SettleTimeout and request_stop
                and self.retain_settle_fault_hold and self.fault is None):
            try:
                from fault_powered_hold import begin_fault_hold
                begin_fault_hold(self, error, from_settle=True)
            except Exception as exc:
                self.fault_hold_failure = str(exc)
            else:
                raise R5PoweredHoldFault(self.fault) from error
        with self.command_lock:
            if isinstance(error, R5PoweredHoldFault) and self.fault_hold is not None:
                raise R5PoweredHoldFault(self.fault) from error
            if self.fault is None:
                self.fault = str(error)
                self.guard.latch(self.fault)
            if self.fault_hold is not None:
                self.fault_hold_failure = self.fault_hold_failure or str(error)
                self.fault_hold = None
            if request_stop and not self.stop_requested:
                self.stop_requested = True
                try:
                    state = self.client.state()
                    if state.get("enabled") and state.get("owner") == self.client.client:
                        self.client.command("stop")
                except Exception:
                    self.fault += "; protective stop unconfirmed"
            raise R5ExecutionFault(self.fault) from error

    def retain_stationary_fault(self, reason):
        """Quarantine an idle companion, without submitting an actuator target."""
        from fault_powered_hold import begin_fault_hold
        return begin_fault_hold(self, R5ExecutionFault(reason), from_settle=False)

    def supervise(self):
        """Watchdog-only entry: monitor hold without reopening the task API."""
        try:
            with self.command_lock:
                if self.fault_hold is not None:
                    return self.fault_hold.check()
                return self.check()
        except Exception as exc:
            self._fail(exc, request_stop=self.engaged or self.busy)

    def abort(self, reason):
        self._fail(R5ExecutionFault(reason), request_stop=self.engaged or self.busy)

    def _command(self, action, **fields):
        with self.command_lock:
            if self.fault is not None:
                raise R5ExecutionFault(self.fault)
            return self.client.command(action, **fields)

    def check(self):
        """Health callback; never acquires ownership or enables a disabled arm."""
        if self.fault_hold is not None:
            raise R5PoweredHoldFault(self.fault)
        try:
            with self.command_lock:
                state = self._read(holding=not self.busy)
                self.engaged = True
                self.vision_check()
                self._command("heartbeat")
                return state
        except Exception as exc:
            self._fail(exc, request_stop=self.busy or self.engaged)

    def renew_session(self):
        """Start a new attended budget segment without releasing powered hold."""
        with self.operation_lock:
            with self.command_lock:
                # Validate the powered hold before an explicit segment re-anchor.
                state = self._read_locked(holding=False)
                if (state.get('control_state') != 'holding'
                        or not vector(state.get('hold_target_deg'))
                        or max(abs(a-b) for a, b in zip(
                            state['hold_target_deg'], state['command_deg'])) > .05):
                    raise R5ExecutionFault('A completed powered hold is required')
                if (abs(state['gripper_target_raw']-state['gripper_command_raw']) > .01):
                    raise R5ExecutionFault('Held gripper still has a pending target')
                self.busy = True
            try:
                # Individual reads/commands still serialize with abort. Do not
                # hold their lock through polling and starve the watchdog.
                state = self._reanchor_hold_to_measured(state)
                with self.command_lock:
                    state = self._read_locked(holding=True)
                    guard = ProposalGuard()
                    guard.check_state(state)
                    self.guard = guard
                    self.observation = None
                    self.consumed = False
                    self.last_execution_feedback = None
                    self.last_budget_rejection = None
                    return {"renewed": True, "anchor_joints_deg": list(guard.anchor)}
            finally:
                with self.command_lock:
                    self.busy = False

    def state(self):
        raw = self._read(holding=not self.busy)
        result = {
            "observation_id": uuid.uuid4().hex,
            "joint_positions_rad": [math.radians(q) for q in raw["joints_deg"]],
            "joint_command_positions_rad": [math.radians(q) for q in raw["command_deg"]],
            "joint_velocities_rad_s": ([math.radians(q) for q in raw["velocity_deg"]]
                                       if vector(raw.get("velocity_deg")) else None),
            "joint_torques_nm": None, "tcp_xyzrpy": None, "tcp_xyzquat": None,
            "gripper_position_m": None, "gripper_normalized": None,
            "gripper_velocity_m_s": None, "gripper_torque_nm": None,
            "gripper_raw": raw["gripper_raw"], "gripper_units": "vendor_raw_0_to_5",
            "raw_state": raw, "received_monotonic_s": self.clock(),
            "motion_budget": {k: v for k, v in self.guard.snapshot().items()
                              if k not in ('execution_available', 'physical_stop_validated', 'collision_checked')},
        }
        self.observation = copy.deepcopy(result)
        self.consumed = False
        return result

    def execute(self, name, arguments, *, dispatch_barrier=None):
        """One absolute/relative joint or raw-gripper action, followed by hold."""
        if not self.operation_lock.acquire(blocking=False):
            raise ValueError("An action is already in progress")
        try:
            return self._execute(name, arguments, dispatch_barrier=dispatch_barrier)
        finally:
            self.operation_lock.release()

    def _action_target(self, name, arguments):
        fields = {"move_joints": "positions", "move_joint_step": "delta_rad",
                  "check_joint_step": "delta_rad", "set_gripper": "gripper_raw"}
        if name not in fields:
            raise ValueError("Unsupported R5 tool; calibrated TCP/normalized gripper unavailable")
        field = fields[name]
        if not isinstance(arguments, dict) or set(arguments) != {field, "observation_id", "note"}:
            raise ValueError("Expected one actuator target, observation_id and note")
        if not isinstance(arguments["note"], str) or not 1 <= len(arguments["note"]) <= 500:
            raise ValueError("A bounded action note is required")
        previous = self.observation
        if (previous is None or self.consumed
                or arguments["observation_id"] != previous["observation_id"]
                or not 0 <= self.clock()-previous["received_monotonic_s"] <= 30):
            raise ValueError("A fresh, unconsumed observation is required")
        state = self._read(holding=True)
        old = previous["raw_state"]
        if (max(abs(a-b) for a, b in zip(old["joints_deg"], state["joints_deg"])) > .5
                or abs(old["gripper_raw"]-state["gripper_raw"]) > .15
                or abs(old["gripper_target_raw"]-state["gripper_target_raw"]) > .01):
            raise ValueError("Robot changed after observation")
        if field in ("positions", "delta_rad"):
            if not vector(arguments[field]):
                raise ValueError("Six finite joint values in radians are required")
            values = [math.degrees(x) for x in arguments[field]]
            # Anchor relative requests to the image's measured pose, not later drift.
            if field == "delta_rad":
                values = [q+d for q, d in zip(old["joints_deg"], values)]
            target = {"joints_deg": values}
        else:
            target = {"gripper_raw": arguments[field]}
        return state, target

    def check_joint_step(self, arguments):
        """Read-only numeric preview; never debit, consume, move or clear faults."""
        with self.operation_lock:
            state, target = self._action_target("check_joint_step", arguments)
            self.vision_check()
            preview = copy.deepcopy(self.guard)
            try:
                validate_action(state, target)
                preview.accept(state, target)
            except ValueError as exc:
                return {"accepted": False, "reason": str(exc), "executed": False,
                        "collision_checked": False, "clearance_verified": False}
            return {"accepted": True, "target_joints_deg": target["joints_deg"],
                    "executed": False, "collision_checked": False,
                    "clearance_verified": False,
                    "note": "Numeric limits only; execution rechecks fresh feedback and budgets."}

    def _execute(self, name, arguments, *, dispatch_barrier=None):
        if self.busy:
            raise ValueError("An action is already in progress")
        if name not in ("move_joints", "move_joint_step", "set_gripper"):
            raise ValueError("Unsupported R5 motion tool")
        state, target = self._action_target(name, arguments)
        try:
            self.vision_check()
        except Exception as exc:
            self._fail(exc, request_stop=self.engaged)
        with self.command_lock:
            if self.fault is not None:
                raise R5ExecutionFault(self.fault)
            preview = copy.deepcopy(self.guard)
            try:
                preview.accept(state, target)
            except ValueError as exc:
                reason = preview.failure or str(exc)
                if reason == 'Session gripper travel budget exhausted':
                    self.last_budget_rejection = reason
                raise ValueError('Proposal rejected before execution: ' + reason
                                 + '; no motion or budget consumed; live session is not fault-latched') from exc
            if dispatch_barrier is not None:
                dispatch_barrier.wait(timeout=1)
            self.guard.accept(state, target)
            self.consumed = True
            self.busy = True
        try:
            self._command("resume")
            fresh = self._read()
            self.vision_check()
            if (max(abs(a-b) for a, b in zip(state["joints_deg"], fresh["joints_deg"])) > .05
                    or abs(state["gripper_command_raw"]-fresh["gripper_command_raw"]) > .01
                    or max(abs(a-b) for a, b in zip(state["command_deg"], fresh["command_deg"])) > .05):
                # Preserve the original guard and include the paired samples so
                # an attended restart can distinguish feedback from target drift.
                raise R5ExecutionFault(
                    "State changed while resuming hold"
                    f"; measured_before={state['joints_deg']}"
                    f"; measured_after={fresh['joints_deg']}"
                    f"; command_before={state['command_deg']}"
                    f"; command_after={fresh['command_deg']}"
                    f"; gripper_command_before={state['gripper_command_raw']}"
                    f"; gripper_command_after={fresh['gripper_command_raw']}")
            validate_action(fresh, target)
            # Gripper-only actions do not re-anchor the arm to lagging encoders.
            self._command("target", **target)
            # Judge joint progress against the submitted command, as with
            # trajectories; tiny secondary corrections can remain in deadband.
            final = self._settle(state, target, command_relative='joints_deg' in target)
            self._command("pause_hold")
            deadline = self.clock() + 1
            while True:
                self.check()
                held = self._read()
                if held.get("control_state") == "holding":
                    held = self._read(holding=True)
                    if (max(abs(a-b) for a, b in zip(held["command_deg"], final["command_deg"])) > .05
                            or abs(held["gripper_command_raw"]-final["gripper_command_raw"]) > .01):
                        raise R5ExecutionFault("Hold changed the settled target")
                    break
                if self.clock() >= deadline:
                    raise R5ExecutionFault("Powered hold was not established")
                self.sleep(.05)
            return {"requested": target, "source_observation_id": arguments["observation_id"],
                    "measured_joint_delta_deg": [q-p for q, p in zip(held["joints_deg"], state["joints_deg"])],
                    "submitted_joints_deg": held["command_deg"],
                    "submitted_gripper_raw": held["gripper_command_raw"],
                    "measured_joints_deg": held["joints_deg"], "measured_gripper_raw": held["gripper_raw"],
                    "settle": {"settled": True}, "control_state": "holding",
                    "grasp_verified": False, "collision_checked": False}
        except Exception as exc:
            self._fail(exc, request_stop=True)
        finally:
            self.busy = False

    def _settle(self, initial, target, *, command_relative=False, min_progress=.7,
                reverse_deadband_deg=0.):
        timeout = 5.
        if 'gripper_raw' in target:
            # The worker ramps raw gripper targets at 0.6 * speed units/second.
            travel = abs(target['gripper_raw']-initial['gripper_command_raw'])
            timeout = max(timeout, travel/(.6*initial['speed']) + 2.)
        deadline = self.clock() + timeout
        samples, grips = deque(maxlen=16), deque(maxlen=16)
        requested_q = target.get("joints_deg", initial["command_deg"])
        # Gripper-only actions require stable held joints, not progress toward
        # a pre-existing position-control residual that was never a new motion.
        arm_initial = np.array(initial['joints_deg'] if 'joints_deg' in target else requested_q)
        trace = []
        # Diagnostic data only: no file I/O or extra hardware reads in this loop.
        # Reset at entry so an early check failure cannot expose a previous settle
        # trace as though it belonged to this attempt.
        feedback = {'initial_measured_deg': initial['joints_deg'],
                    'initial_command_deg': initial['command_deg'],
                    'target': target, 'samples': [],
                    'started_at_s': deadline-timeout, 'deadline_at_s': deadline,
                    'settle_parameters': {
                        'command_relative': command_relative, 'min_progress': min_progress,
                        'max_residual_deg': POLICY_SETTLE_ERROR_DEG,
                        'reverse_deadband_deg': reverse_deadband_deg}}
        self.last_execution_feedback = feedback
        while self.clock() < deadline:
            self.check()
            state = self._read()
            now = self.clock()
            trace.append({'at_s': now, 'joints_deg': state['joints_deg'],
                          'command_deg': state['command_deg'], 'gripper_raw': state['gripper_raw'],
                          'gripper_command_raw': state['gripper_command_raw']})
            feedback['samples'] = trace[-120:]
            samples.append((now, np.array(state["joints_deg"])))
            grips.append((now, state["gripper_raw"]))
            arm_ok = step_settled({"joints_deg": requested_q}, arm_initial, samples, now,
                                 command_initial=np.array(initial['command_deg']) if command_relative else None,
                                 min_progress=min_progress,
                                 aggregate_progress=command_relative,
                                 max_residual_deg=POLICY_SETTLE_ERROR_DEG,
                                 reverse_deadband_deg=reverse_deadband_deg)
            command_ok = max(abs(a-b) for a, b in zip(state["command_deg"], requested_q)) <= .05
            grip_ok = abs(state["gripper_command_raw"]-initial["gripper_command_raw"]) <= .01
            if "gripper_raw" in target:
                recent = [g for stamp, g in grips if now-stamp <= .6]
                delta = target["gripper_raw"]-initial["gripper_target_raw"]
                measured_delta = state["gripper_raw"]-initial["gripper_raw"]
                progress = (measured_delta/delta
                            if abs(delta) > .01 else 1)
                # Tiny setpoint changes can reverse encoder bias/backlash while
                # both endpoints remain inside the existing position tolerance.
                within_deadband = (
                    abs(delta) <= GRIPPER_SETTLE_TOLERANCE_RAW
                    and abs(initial["gripper_raw"]-target["gripper_raw"]) <= GRIPPER_SETTLE_TOLERANCE_RAW
                    and abs(measured_delta) <= GRIPPER_SETTLE_TOLERANCE_RAW)
                grip_ok = (len(recent) >= 5 and max(recent)-min(recent) <= .02
                           and abs(state["gripper_command_raw"]-target["gripper_raw"]) <= .01
                           and abs(state["gripper_raw"]-target["gripper_raw"]) <= GRIPPER_SETTLE_TOLERANCE_RAW
                           and (progress >= .5 or within_deadband))
            trace[-1]['checks'] = {'arm_ok': bool(arm_ok), 'command_ok': bool(command_ok),
                                   'grip_ok': bool(grip_ok)}
            if arm_ok and command_ok and grip_ok:
                return state
            self.sleep(.05)
        latest = trace[-1] if trace else None
        detail = ''
        if latest is not None:
            detail = (f"; initial={list(map(float, initial['joints_deg']))}, "
                      f"target={list(map(float, requested_q))}, "
                      f"measured={list(map(float, latest['joints_deg']))}")
            if 'gripper_raw' in target:
                detail += (f"; gripper_initial_raw={initial['gripper_raw']}, "
                           f"gripper_initial_command_raw={initial['gripper_command_raw']}, "
                           f"gripper_target_raw={target['gripper_raw']}, "
                           f"gripper_measured_raw={latest['gripper_raw']}, "
                           f"gripper_command_raw={latest['gripper_command_raw']}")
        raise R5SettleTimeout("Action did not settle; no grasp/contact inferred from a stall"+detail)

    def _reanchor_hold_to_measured(self, held):
        """Remove accepted tracking residual without commanding extra motion."""
        if max(abs(a-b) for a, b in zip(held['command_deg'], held['joints_deg'])) <= .05:
            return held
        measured = held['joints_deg'][:]
        self._command('resume')
        self._command('target', joints_deg=measured)
        submit_deadline = self.clock()+1
        while True:
            self.check()
            current = self._read()
            if max(abs(a-b) for a, b in zip(current['command_deg'], measured)) <= .05:
                break
            if self.clock() > submit_deadline:
                raise R5ExecutionFault('Measured hold re-anchor was not submitted')
            self.sleep(.02)
        self._command('pause_hold')
        deadline = self.clock()+1
        while True:
            self.check()
            current = self._read()
            if current.get('control_state') == 'holding':
                # The worker snapshots fresh encoder feedback when pause_hold is
                # accepted, so its held command may legitimately differ from
                # the earlier measured frame. The holding read validates the
                # new command against both the hold target and live feedback.
                current = self._read(holding=True)
                return current
            if self.clock() > deadline:
                raise R5ExecutionFault('Measured hold re-anchor timed out')
            self.sleep(.02)

    def preview_timed_trajectory(self, plan):
        """Recheck a prepared path without consuming budget or sending commands."""
        with self.operation_lock:
            self._trajectory_inputs(plan)

    def _validate_cartesian_amplitude(self, amplitude):
        if amplitude < self.minimum_cartesian_command_step_deg:
            raise ValueError(
                f'Cartesian command step {amplitude:.6f} degrees is below this session minimum '
                f'{self.minimum_cartesian_command_step_deg:g}; stationary hold retained. '
                'Reassess geometry; do not automatically enlarge or accumulate rejected steps')

    def _trajectory_inputs(self, plan):
        points = np.degrees(plan['joint_positions_rad']).tolist()
        args = {'observation_id': self.observation['observation_id'] if self.observation else '',
                'positions': plan['joint_positions_rad'][-1].tolist(), 'note': plan['result']['note']}
        state, target = self._action_target('move_joints', args)
        if state.get('policy_trajectory_protocol') != PolicyTrajectory.protocol:
            raise ValueError('Timed trajectory transport is not deployed')
        start = np.degrees(plan['start_joint_positions_rad']).tolist()
        measured_start = np.degrees(plan['planning_measured_joint_positions_rad']).tolist()
        if not vector(measured_start) or max(abs(a-b) for a, b in zip(measured_start, state['joints_deg'])) > .05:
            raise ValueError('Robot changed during Cartesian planning; replan from fresh state')
        if max(abs(a-b) for a, b in zip(start, state['command_deg'])) > .05:
            raise ValueError('Held command differs from path start; cannot jump to the measured pose')
        amplitude = max(abs(a-b) for a, b in zip(points[-1], start))
        self._validate_cartesian_amplitude(amplitude)
        PolicyTrajectory(start, points, plan['relative_times_s'],
                         state['lower_deg'], state['upper_deg'], self.clock())
        preview_trajectory(self.guard, state, points)
        self.vision_check()
        return points, args, state, target, start, measured_start

    def execute_trajectory(self, plan, *, dispatch_barrier=None):
        """Submit the entire upstream timed path to the existing owned worker host."""
        with self.operation_lock:
            points, args, state, target, start, measured_start = self._trajectory_inputs(plan)
            if dispatch_barrier is not None:
                dispatch_barrier.wait(timeout=1)
            with self.command_lock:
                self.guard.require_healthy()
                debit_trajectory(self.guard, state, points)
                self.consumed, self.busy = True, True
            try:
                self._command('resume')
                fresh = self._read()
                if (max(abs(a-b) for a, b in zip(measured_start, fresh['joints_deg'])) > .05
                        or abs(state['gripper_command_raw']-fresh['gripper_command_raw']) > .01):
                    raise R5ExecutionFault('State changed while resuming Cartesian path')
                self.vision_check()
                self._command('policy_trajectory', start_deg=start, points_deg=points,
                              times_s=plan['relative_times_s'], issued_at=self.clock())
                deadline = self.clock()+plan['relative_times_s'][-1]+1
                while True:
                    self.check()
                    current = self._read()
                    if abs(current['gripper_command_raw']-state['gripper_command_raw']) > .01:
                        raise R5ExecutionFault('Gripper changed during Cartesian path')
                    if current.get('policy_trajectory_active') is False:
                        if max(abs(a-b) for a, b in zip(current['command_deg'], points[-1])) > .05:
                            raise R5ExecutionFault('Cartesian path ended before its final target')
                        break
                    if self.clock() > deadline:
                        raise R5ExecutionFault('Cartesian playback did not finish')
                    self.sleep(.02)
                # Stable partial tracking is exposed to the next visual turn;
                # stalls and wrong-direction motion still fail the action.
                final = self._settle(state, target, command_relative=True, min_progress=.4,
                                     reverse_deadband_deg=POLICY_REVERSE_DEADBAND_DEG)
                self._command('pause_hold')
                # Wait through the existing zero-velocity pause profile.
                hold_deadline = self.clock()+1
                while self._read().get('control_state') != 'holding':
                    self.check()
                    if self.clock() > hold_deadline:
                        raise R5ExecutionFault('Cartesian path did not establish hold')
                    self.sleep(.02)
                held = self._read(holding=True)
                if (max(abs(a-b) for a, b in zip(held['command_deg'], final['command_deg'])) > .05
                        or abs(held['gripper_command_raw']-state['gripper_command_raw']) > .01):
                    raise R5ExecutionFault('Hold changed the Cartesian endpoint')
                residual = [measured-requested for measured, requested
                            in zip(held['joints_deg'], points[-1])]
                return {'source_observation_id': args['observation_id'],
                        'submitted_joints_deg': points[-1],
                        'measured_joints_deg': held['joints_deg'],
                        'tracking_residual_deg': residual,
                        'measured_gripper_raw': held['gripper_raw'],
                        'control_state': 'holding',
                        'settle': {'settled': True, 'partial_tracking_accepted': True,
                                   'reverse_deadband_deg': POLICY_REVERSE_DEADBAND_DEG,
                                   'max_abs_residual_deg': max(abs(value) for value in residual)},
                        'grasp_verified': False, 'collision_checked': False}
            except Exception as exc:
                self._fail(exc, request_stop=True)
            finally:
                self.busy = False

    def finish(self, trigger):
        """End a model run without opening, homing, or releasing ownership."""
        if self.busy:
            raise R5ExecutionFault("Cannot finish during an action")
        self.check()
        return {"trigger": trigger, "control_state": "holding", "returned_home": False,
                "operator_handoff_required": True, "grasp_verified": False}

    def return_home(self):
        raise R5ExecutionFault("R5 automatic homing is not deployed; use the finish callback")
