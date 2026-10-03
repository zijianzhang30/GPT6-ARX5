# GPT-Policy R5 deployment status

The goal is physical tennis-ball grasping with GPT-Policy's existing loop,
one R5, Gemini wrist RGB and optional external RGB. This is a partial deployment
adaptation, not a validated autonomous robot deployment.

Latest source update: the default host now binds the original Cartesian catalog,
FrameCalibration, PixelLocalizer, ContinuousIK and Ruckig EefTrajectoryPlanner
to R5. The measured R5 profile is incomplete and the new timed transport is NOT
loaded into the currently running service. See `R5_CARTESIAN_DEPLOYMENT.md`.
The joint-based trial evidence below remains historical; it does not validate
the new Cartesian path or establish a physical grasp.

The deployed workbench supports qualified attended trials with worker protocol 2.
`supervised_policy.py` uses that existing worker without reconnecting or homing.
The approach/correction tools and their limits are documented in
`R5_APPROACH_LOOP.md`; wrist-only testing is documented in `WRIST_ONLY_TRIAL.md`.

## Implemented and tested with fake hardware/provider

- `r5_policy_deployment.run_r5_policy` calls the original upstream `run_loop`.
  It preserves the observe/decide/execute/result sequence and records real
  upstream observation/decision/execution events. No new decision loop is used.
- `R5Cameras` implements snapshot/describe through the existing HTTP camera
  service. JPEGs must decode, sequences advance and device identities remain
  distinct/stable. Images implement the upstream recorder contract. Timestamps
  are host receipts, not sensor exposure times; calibration remains unavailable.
- `R5PolicyBackend` implements state/execute for absolute joint radians and a
  separate raw gripper target. It converts radians to the existing HTTP degrees
  and distinguishes requested, submitted and measured targets. No second SDK,
  CAN connection, initialization, automatic enable or homing is introduced.
- Actions require fresh, unconsumed observation IDs and existing software travel
  limits. After resume, state and action bounds are checked again. Joint/gripper
  settling is followed by fixed-target `pause_hold`; a normal step does not use
  PROTECT. Gripper stalls are not labeled contact or successful grasp.
- Timeouts after submission latch a fault and do not resend the target. The
  existing protective-stop request is attempted only for the same control owner.
  This still has the physical limitations in `STOP_MODE_AUDIT.md`.
- Model completion/budget exhaustion uses a device finish callback, retaining
  hold for operator handoff without opening or homing. Model `completed` is not
  a physical success label. Ownership and heartbeat responsibility remain with
  the embedding host after the model loop returns.

## Intentional hardware-specific differences

The original default tools assume a calibrated metric TCP, calibrated camera
rays and normalized gripper width. Those measurements are not available here.
The R5 tool catalog therefore exposes `move_joints` (six absolute radians),
`move_joint_step`, read-only `check_joint_step`/`observe`,
`set_gripper` (`gripper_raw`, 0..5), `done` and `give_up`. It does not disguise
raw units as normalized opening or enable `move_to`/`locate_point` without
calibration. Existing 2-degree/3-degree-norm and 0.1-raw step limits remain.

## Physical evidence and remaining work

- Empty-gripper stationary enable was observed in
  `analysis/gripper-check-bbd0e9d6c00c/`, with maximum joint drift about 0.525 degrees.
- Powered hold/resume/re-hold was observed in
  `analysis/gripper-check-726ff4b1338f/`, with maximum drift about 0.546 degrees.
  This does not certify holding through faults, communication loss or power loss.
- Incremental opening to raw command 4.8 produced measured feedback about 4.691;
  the operator confirmed opening. Evidence:
  `analysis/live-policy-159299892e2f_unreviewed/`. Raw direction is established;
  metric opening width, contact and grasp force are not calibrated.
- Real GPT trials with both cameras and wrist-only input reached model decisions.
  Trials through `analysis/live-policy-958129a77964_unreviewed/` returned `give_up`
  without model-selected actuator targets. No successful GPT grasp is verified.
- The newer approach/correction logic has offline integration coverage and a
  live model trial in `analysis/live-policy-ead0356cff2c_unreviewed/`, also ending
  with `give_up` before any model-selected motion. Physical
  approach, alignment, closure, lifting and retained-ball evidence remain to be
  established with current scene and direction/clearance evidence.
- Independent camera and heartbeat threads remain ordinary Python supervision,
  not a real-time or safety-rated controller. SDK PROTECT can soften/release
  holding; its limitations remain documented in `STOP_MODE_AUDIT.md`.

`LiveController.snapshot()` now publishes `gripper_command_raw` separately
from `gripper_target_raw`. Execution remains unavailable by default. Explicit
`--supervised-policy` mode requires three seconds of fresh, stable, owned powered
hold before advertising supervised execution. Stop/ownership changes invalidate
that qualification. `fault_fallback_hardware_validated` remains false.

## Control diagnosis update

The downloaded ZIP hash still matches the source recorded in `GPT_POLICY_R5.md`.
The original `runtime.runner.run_loop` remains the decision/execution loop.

- `worker_control.py` validates target generation timestamps before SDK calls,
  rejects targets older than 150 ms or out of order, coalesces valid queued
  targets, and gives queued pause/shutdown priority. The 350 ms worker watchdog
  is checked before dispatch and now latches a fault, preventing automatic
  reactivation by delayed traffic. No SDK gains or mode numbers are changed.
- The worker reports protocol version 2 and its fault reason; the live policy
  backend requires version 2. Controller and worker must be deployed together.
- Backend fault cancellation and target submission share a lock, following the
  upstream `MotionControl` pattern. A command already in progress may finish;
  no further command can follow the latched stop. This is not instantaneous
  physical cancellation or a substitute for an atomic server-side owner check.
- `SupervisedCameras` owns capture and preserves per-batch image metadata.
  Capture stalls cannot block the separate heartbeat/fault monitor. Model
  completion keeps the supervisor alive for handoff; exceptional exit closes
  it and requests the existing protection mode only for its own enabled arm.
- `gripper_check.py --mode stationary --supported-empty-gripper` is a separate
  five-second enable diagnostic. It sends no extra target after enable, checks
  joint displacement and final stability, and checks gripper drift. Enable
  still energizes all axes and initializes position references. Exit requests
  PROTECT, so supported empty hardware and an on-site operator are required.
  Passing this check does not validate `pause_hold`, fault fallback or grasping.

These worker/supervisor changes have been deployed to the running service.
The previous 0.525-degree diagnostic abort is not proof of its physical cause;
the current diagnostic threshold is approximately 1.719 degrees. Inspection of
the SDK setters did not establish a mode-transition race as the cause, so their
order and the vendor library were not changed speculatively.

## Upstream changes (local evaluation copy only)

- `runtime/runner.py`: optional device `finish_fn` and `fail_on_state_error`.
  Default X5 behavior is unchanged. R5 fails on missing state rather than
  retrying forever or feeding an old state to the model.
- `motion/__init__.py`: lazy trajectory exports. Importing the generic loop and
  trajectory error types no longer requires Ruckig for an HTTP-backed robot.
  Actual trajectory planner use still requires the real Ruckig dependency.
- `harness/codex.py`: close the spawned model process if initialization fails.
  The local shadow runner additionally bounds startup with a 15-second wait
  deadline and each decision with a 25-second wait deadline.

The original ZIP is unchanged. Earlier statements that every extracted upstream
file is unmodified are superseded by this explicit local patch list.

## Verification

```bash
python3 -m pytest -q tests/test_r5_policy_backend.py tests/test_r5_policy_deployment.py
python3 -m pytest -q tests
```

Tests drive the real upstream loop and recorder with fake camera frames,
feedback, command transport and decisions. They do not import the native SDK,
access CAN, call a real model or establish physical grasp capability.
