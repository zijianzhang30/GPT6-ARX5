# Software motion guards: not physical fall protection

These checks constrain proposals and the existing supervised visual executor.
They do not add brakes, gravity compensation, collision detection, force control,
or a validated physical stop. No live service restart or motor test was performed
for this change. The GPT-Policy adapter remains GET-only / shadow-only.

## Why small outputs are insufficient

A small commanded step limits intended position change. It does not limit
gravity-driven motion after torque is lost. Even with mains power present,
CAN/USB loss, an SDK fault, a missed 350 ms control lease or worker timeout can
enter the existing PROTECT path. Observed sag on that path is still unresolved.
Software checks cannot guarantee behavior when the computer, transport or drive
is unresponsive. See `PAUSE_HOLD.md` before any physical deployment.

## Implemented checks

`motion_safety.py` centralizes finite telemetry validation and session budgets.
It has no HTTP, CAN, SDK or actuation dependency.

| Limit | Current software trial value |
| --- | --- |
| Per-joint commanded increment | 2 degrees per observed step |
| Combined joint increment | Euclidean norm <= 3 degrees |
| Joint limit margin | 2 degrees inside each lower/upper limit |
| Gripper target increment | 0.1 vendor raw units |
| Session excursion | <= 10 degrees per joint from first valid feedback |
| Sum of absolute proposed joint increments | <= 30 degrees per session |
| Sum of absolute proposed gripper increments | <= 1.0 raw unit per session |
| Accepted proposals/steps | <= 10 per session, including no-ops |
| Joint/CAN feedback age | finite, nonnegative, <= 150 ms |
| Reported following error | finite and <= 3.05 degrees per joint |

Numbers are conservative software trial settings, not measured braking distances,
Cartesian workspace boundaries or manufacturer-certified safety limits. Joint
limits alone cannot keep the fingers, cameras, links or cables off the table.
No uncalibrated current field is treated as torque, temperature or grip force.

Feedback validation rejects missing values, booleans, numeric strings, NaN,
infinities, invalid/reversed limits and missing tracking-limit status. All six
angles and both measured/commanded raw gripper values must be valid. Missing
gripper target feedback is no longer replaced with an invented estimate.

Joint and gripper motion must be separate requests. Extra action fields, including
an attempted per-action speed override, are rejected. A rejected value is not
silently clamped into an apparently accepted action.

## GPT-Policy shadow adapter

`policy_adapter.py` uses a `ProposalGuard` for the entire adapter session.
Successful observations do not reset its anchor, absolute travel budget, or fault.
The budget counts hypothetical suggestions even though they are never executed.
Reversing direction spends more travel budget; it does not refund earlier motion.

Faulted/stale/missing telemetry, camera failure or replacement, changed limits,
soft-limit violations and exhausted budgets lock the session. Restoring healthy
data does not auto-resume it. There is no model reset/enable/stop tool. A new
adapter session must be an explicit action after inspecting the cause, not an
automatic retry loop. Ordinary malformed input or an expired observation can
be rejected without pretending it was a hardware failure.

This layer polls on observation/proposal requests; it is NOT a continuous motor
watchdog and does not supervise motion performed by another controller.

## Existing supervised visual executor

`visual_control.py` shares numeric limits and session budgets but remains a
separate, previously existing experimental execution path. It has not been
invoked in this change and is NOT a workaround for the shadow adapter's lack of
a validated live backend. Existing manual website controls are not wrapped by
this guard; its limits are not automatically applied to manual website commands.

For a later separately validated deployment, the visual executor additionally:

- Keeps its 10% configured speed cap and checks mode, speed and ownership on
  each active heartbeat; unexpected changes abort the session.
- Requires advancing, decodable camera frames with stable, distinct device
  identities. Camera exceptions latch rather than silently auto-recover.
- Rechecks fresh feedback, camera receipt freshness and state drift after
  acquiring control, immediately before submitting a target.
- Treats an enable acknowledgment timeout as potentially accepted by the server;
  cleanup checks ownership and attempts the existing stop instead of assuming
  that nothing was enabled. It does not stop a known new owner.
- Latches apply failures and does not allow the same session to re-enable.
- Rejects invalid/future/nonmonotonic sample timestamps when assessing settling.

The old `stop` behavior is unchanged. On detected problems it still **requests
PROTECT**, not a guaranteed powered hold. An HTTP timeout also means delivery
cannot be established solely from the client; the existing watchdog remains
necessary and is not disabled here. Gripper contact/force and actual grasp success
are not certified by position feedback or joint settling.

## Verification

```bash
python3 -m pytest -q tests/test_motion_safety.py tests/test_policy_adapter.py tests/test_visual_control.py
python3 -m pytest -q tests
```

Faults are injected into fake clients and synthetic telemetry, never into the
physical arm. Coverage includes repeated small steps, reversal travel budgets,
soft margins, camera replacement/recovery, stale and corrupt feedback, speed
changes, acknowledgment loss, pre-send drift, and no target submission on these
failures. Full HTTP regression tests use simulated arms and temporary local
ports, not the running robot service.

Physical execution still requires a reviewed means of preventing uncontrolled
fall/contact, validation of stop/hold and operator handoff, and supervised empty-
gripper tests before attempting a grasp. Do not test loss of power by unplugging
an unsupported powered arm or support it by hand.
