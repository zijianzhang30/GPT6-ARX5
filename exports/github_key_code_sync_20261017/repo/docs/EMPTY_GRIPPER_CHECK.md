# Supported empty-gripper check, 2026-09-25

## Separate stationary-enable diagnostic

The new `--mode stationary` isolates enabling from an opening command:

```bash
python3 gripper_check.py --mode stationary --supported-empty-gripper
```

This is a physical diagnostic requiring supported empty hardware and on-site
supervision. It enables all axes at 10 percent speed, retains their initial
references, observes for five seconds, then requests the existing PROTECT mode.
No additional joint or gripper target is submitted. PROTECT may allow sag and
release the gripper; do not use the flag as a substitute for mechanical support.

The diagnostic checks the existing 1.719-degree displacement envelope, gripper
drift within 0.03 raw units, and final joint stability within 0.1 degrees over
at least 0.5 seconds. A valid initial gripper reference is still required. The
result `stationary_enable_observed` is distinct from a powered-pause test or
grasp success; `hold_validated` remains false. This new check has only been
tested with fake feedback, including near-open-limit, gripper drift and joint
oscillation cases. It has not been run on the physical arm in this update.

The existing `--mode open` remains the default and still requires room for its
0.1-raw-unit opening step after the enable reference is initialized.

## Diagnostic threshold revision

Following the user's request to use GPT-Policy settings, future runs use
`degrees(0.03)` (approximately 1.719 degrees) instead of 0.5 degrees for the
empty-gripper check's joint displacement envelope. This borrows upstream's
default position settling tolerance; it does NOT reproduce upstream's complete
position/velocity/consecutive-sample settling test. Upstream's separate tracking
fault limit is 0.12 radians (6.875 degrees). The R5 controller's existing
3-degree tracking lead cap is unchanged. Neither number is a collision limit.
The old 0.525-degree event alone would no longer trip this diagnostic envelope.
Tests cover that event, both signed boundaries and an out-of-range opening.
This revision does not enable the autonomous backend, deploy the hold prototype,
change gripper limits, or constitute a new physical test. The historical test
below used the old threshold.

User authorized an empty-gripper opening check and confirmed mechanical support.
This was a bounded manual acceptance check, not a GPT grasp or a test of the
undeployed powered pause-and-hold path. No SDK was reconnected or homed.

## Recorded outcome

Evidence: `analysis/gripper-check-b771f647d493/events.jsonl` and before/after JPEGs.

- Initial feedback: 0.1361866 raw; initial gripper reference: 0.2361866 raw.
- Requested target: 0.3361866 raw, a 0.1 raw-unit reference increase.
- The existing controller was enabled at 10 percent speed. The target request
  contained only `gripper_raw`; six-joint references remained unchanged in the
  recorded active snapshots. Enabling nevertheless activates all six joints.
- The check aborted on maximum observed joint displacement of 0.525 degrees,
  exceeding its 0.5-degree diagnostic threshold. That threshold is a test
  criterion, not a proven physical collision/safety limit or proof of damage.
- PROTECT was requested and the service acknowledged disabled control. That
  acknowledgment does not prove physical immobility or keep the gripper stiff.
- No gripper feedback increase was recorded before the abort. No successful
  opening, powered hold or grasp was established. No automatic retry occurred.

Before the abort, the saved samples show J3 changing 0.797766 -> 0.950762 degrees
and J4 changing -11.289101 -> -11.070535 degrees with unchanged command angles.
The original check validated before logging each sample, so the exact violating
sample was not saved. The reason records the maximum magnitude but cannot
identify the triggering joint retrospectively. Logging now saves each inspected
sample before validation and reports the specific joint for any future check.

## Subsequent manual intervention

The user reported physically opening the gripper by hand while control was
disabled. Later read-only observations `analysis/gpt-session-15e3d4157d79/` and
`analysis/gpt-session-7d7379db5bde/` show gripper feedback 5.2075229, the retained
reference 0.3361866, disabled control, no owner and an empty SDK error list.
Post-intervention changes must not be labeled automatic motion or automatically
attributed to this test. The exact timing of the manual movement is not logged.

The adapter blocks movement at that feedback because its validated envelope is
0..5. This does not prove an encoder fault, damage or a true physical endpoint.
Commands and passive feedback limits must be established separately.

## SDK and adapter findings

Read-only disassembly of the pinned native SDK confirms that
`ControllerThread::getJointPositons()` (0x16103e) returns each stored position
minus the initialization offset. `setCatch(double)` (0x161654) writes the seventh
target channel without a physical-width conversion in that setter. Neither
method establishes that the feedback after passive manual movement must be in
the application's 0..5 command interval.

`LiveController.command('enable')` previously clipped feedback + 0.1 into 0..5.
This could silently change the initial reference after a manual displacement.
The code now rejects invalid/unrepresentable initial references without enabling
or mutating the previous target. This is rejection, not calibrated recovery.
The running service was not restarted; source changes are not hot-deployed.

No gains, SDK modes, heartbeat watchdogs, joint limits or command ranges were
loosened. The root cause of the enable-time displacement remains unresolved;
these data do not distinguish controller mode transition, gravity compensation,
cable forces, compliance or external contact. Vendor-supported stationary-enable
behavior and a supervised recovery/calibration procedure are still required
before resuming autonomous grasp tests.
