# Pause-and-hold prototype: offline validation only

This change separates a normal, powered motion pause from the existing SDK
protect request. It is **not a safety-rated stop, brake, or power-loss solution**.
No live service restart, SDK connection, homing, or motor command is required to
run its tests. Hardware pause-and-hold remains disabled by default.

## What is implemented

`Controller` accepts two additional authenticated command actions through the
existing `/api/command` endpoint:

```json
{"action":"pause_hold","client":"existing-owner"}
{"action":"resume","client":"existing-owner"}
```

These commands do not acquire ownership or enable a stopped arm. The current
owner must already have enabled control. During a pause, that owner must continue
to send zero-jog heartbeats within the existing 350 ms lease. A failed or missing
heartbeat still invokes the original stop path; indefinite unattended holding
has not been introduced.

| Controller state | Allowed transition | Meaning |
| --- | --- | --- |
| `disabled` | Explicit `enable` -> `active` | No automatic enable from pause/resume |
| `active` | `pause_hold` -> `pausing` or `holding` | Discard old trajectory and gripper motion |
| `pausing` | Command profile finishes -> `holding` | Bounded command-space deceleration |
| `holding` | Explicit `resume` -> `active` | Accept new commands; never restore old trajectory |
| Any enabled state | Existing stop/fault/lease expiry -> `disabled` | Existing protection behavior, not a physical hold guarantee |

New snapshot fields are `control_state`, `hold_available`, `hold_target_deg`, and
`hold_is_safety_stop` (always false). `holding` describes a controller command
state, not proof that measured joints are stationary. `enabled` remains true
while pausing or holding.

The stop profile starts from the current **commanded** joint position and planner
velocity, rather than jumping the command to a lagging encoder position. It uses
the offline controller's 120 degrees/s^2 deceleration and computes one fixed stop
target. Both the start and stop targets must fit the joint limits. Position is
monotonic along this profile; a profile that cannot fit is rejected and the old
motion is stopped. This is not a Cartesian collision check.

The target is not repeatedly re-latched from feedback. Repeating `pause_hold`
does not restart the profile or chase encoder drift. Motion commands, nonzero
arm/gripper jogs, settings changes, and `enable` are rejected during a pause.
`resume` is accepted only after the command profile has finished. Old motion does
not resume, including old gripper closing targets.

## Live-controller boundary

`LiveController()` reports `hold_available: false`. There is deliberately no
web setting, request field, CLI option, or environment-variable shortcut to
enable hardware pause-and-hold. An `experimental_hold=True` constructor argument
exists for tests using captured messages and simulated feedback; it is not a
hardware approval or a deployment instruction.

The experimental adapter implements:

- Entry/resume checks for fresh joint/CAN feedback (150 ms), ready status, no SDK
  error codes, finite in-range encoder values, and at most 1 degree command lead.
- Continued monitoring during a pause, including the existing 3 degree tracking
  limit. Exceeding it stops the controller; the latched target is not silently
  moved along with the encoder to hide the error.
- Position-target messages through the existing worker; no SDK mode numbers or
  native bindings are changed.
- Cancellation of the pending gripper trajectory by retaining its last issued
  SDK command. This is not calibrated grip-force control.
- Rejection of unsafe pause/resume transitions with the existing protective stop
  when control is active; failure to enter hold does not keep pursuing an old goal.

`robot_worker.py` is unchanged. Its target-command timeout, CAN timeout, fault
handling, shutdown, and `PROTECT` requests remain intact. Temperature limits and
calibrated force/current protections have **not** been invented: the current
interface does not provide validated parameters for those checks.

The current web stop button/keyboard shortcut still uses `stop`. The visual
executor still uses its existing stop on vision/supervision failure and session
exit. This prototype does **not** yet reroute those conditions to holding and
does not resolve observed sag on protective stop or power loss. That rerouting
needs a validated hardware fallback and operator handoff policy first.

## Offline verification

```bash
python3 -m unittest discover -s tests -p test_pause_hold.py -v
python3 -m unittest discover -s tests -v
```

Tests use deterministic simulation, fake feedback, captured worker messages, and
an HTTP workbench with simulation and fake cameras. They do not import or
initialize `robot_worker.py`, open CAN, or address the running control service.
Coverage includes deceleration, fixed targets, encoder drift, gripper latching,
explicit resume, ownership, unsupported live requests, stale feedback, SDK errors,
tracking limits, lease loss, stop/disconnect, and authenticated simulation API
transitions. Passing them is software validation, not real-robot certification.

## Before any hardware deployment

1. Obtain the vendor's documented behavior for protective stop, drive fault,
   communication loss, brakes, and power loss for this exact arm/SDK. Determine
   how to support the load if torque disappears. Do not assume unplugging power
   prevents a fall.
2. Verify payload, tool geometry, workspace/table clearance, and manufacturer
   current/temperature limits. The command profile does not model actual braking
   distance, SDK dynamics, gravity, or collision/contact.
3. Define the operator-takeover and hold-timeout policy and its hardware-backed
   fallback. Retaining heartbeat protections here avoids silently choosing an
   unvalidated indefinite hold policy.
4. Arrange a vendor-approved, mechanically supported, low-energy validation with
   no grasped object. Do not support a powered arm by hand. Measure actual drift,
   following error, settling, and gripper behavior. Fault cases should first be
   injected into mocks, not by disconnecting a loaded physical arm.
5. Only after acceptance, plan a separate deployment and visual-executor/UI
   integration. Restarting/reconnecting the current hardware controller may
   initialize and home the arm; this is not a hot-reload operation.
