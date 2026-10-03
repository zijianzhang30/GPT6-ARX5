# GPT-Policy / single-R5 adaptation

Status: **observation and shadow proposal integration only**. No physical
execution backend or autonomous grasp is enabled by this change. The existing
web application, SDK process, CAN ownership and stop behavior are unchanged.

Update: the original upstream loop now has a separately tested R5 device backend
and camera/tool adapters, still not enabled for live deployment. See
`R5_DEPLOYMENT_STATUS.md` for implemented components, the local upstream patches
and the remaining model/supervisor/hardware acceptance work. The sections below
describe the earlier read-only/shadow entry points, which remain unchanged.

## Source and compatibility

The user-supplied archive is `/home/tuojing/Downloads/GPT-Policy.zip`, SHA-256:

```text
6a0da6f94eeac65bd8437a183e3de5b8d65dc75de4d4950fd4a1ae45cecd6d00
```

Source, configs, tests and license notices were extracted without modification
to `vendor/GPT-Policy-main/` for local evaluation. Videos, the paper and other
large assets were not copied. No upstream dependencies, drivers or model
sessions were installed/launched. The archive and its source remain unchanged.
The upstream LICENSE permits review/evaluation but has no selected license for
redistribution or commercial use. Do not treat this directory as MIT-licensed.

The supplied repository documents ARX **X5**, via `arx5_interface`, and YAM.
It is not a verified drop-in driver for our R5 vendor SDK. Its policy uses a
vision-language agent and structured tools, not task-specific trained VLA weights.
The adapter implements the upstream `AgentContext`, `AgentTurn`, `ImageInput`
and decision shape without loading its robot, motion planner or main loop.

## Device and unit contract

| Logical input | This setup | Source / units |
| --- | --- | --- |
| Single arm | ARX R5, J1..J6 | Existing workbench GET `/api/state` |
| `left` | Gemini 305 wrist RGB | GET `/api/cameras/gemini/frame.jpg` |
| `top` | Fixed external RGB, not necessarily overhead | GET `/api/cameras/external/frame.jpg` |
| Joint proposals | Six relative increments | Degrees, J1..J6 order |
| Gripper proposals | Separate absolute target | Vendor raw 0..5, not mm or normalized opening |
| `joint_pos_rad` | Derived from finite measured degrees | Radians, otherwise null |
| TCP, metric gripper width, torque | Unvalidated or unavailable | Explicit null, never fabricated |

The current frames are RGB only. Camera intrinsics/extrinsics and fingertip TCP
calibration have not been supplied. `currents` are not calibrated torque.
The existing workbench `pose` is not a validated fingertip TCP. No pixel-to-metre
conversion or depth estimate is made. Numeric joint limits are not workspace,
table-clearance or collision checks.

The HTTP service discovers cameras; this adapter does not open `/dev/video*` or
assume fixed device numbers. Two GETs per camera must show advancing sequence
IDs on the same device. Images must decode as JPEG. Receipt times are recorded;
they are not exposure timestamps or hardware synchronization. At collection
completion both image receipts must be within one second.

## Running the read-only adapter

Prerequisites: Python, Pillow and jsonschema (already available on this machine).
Use the already-running recording proxy on port 8768; do not start another SDK.

```bash
cd /home/tuojing/arx_r5_control
python3 policy_adapter.py protocol
python3 policy_adapter.py observe
python3 policy_adapter.py serve
```

`protocol` prints the model instructions and schemas without HTTP requests.
`observe` saves a new `analysis/policy-<id>/` directory with images, raw feedback,
protocol and append-only `events.jsonl`; exit status 2 means proposal preflight
is blocked, not that a motion was attempted. A healthy read-only preflight exits
0, but does **not** certify safe physical execution. `--output` must name a new
directory; existing runs are never overwritten.

`serve` first emits an observation, then reads one JSON tool selection per stdin
line. It opens no network listener. For example, request another observation:

```json
{"name":"observe","arguments":{}}
```

A model can submit a shadow suggestion with the actual latest observation ID:

```json
{"name":"propose_joint_step","arguments":{"observation_id":"REPLACE_WITH_LATEST_ID","joint_delta_deg":[0,0,2,0,0,0],"note":"Review approach direction; do not execute."}}
```

This is a protocol example, **not a recommended movement for the current scene**.
Gripper suggestions use `propose_gripper` with `observation_id`, `gripper_raw`
and `note`; they cannot be combined with an arm step. Unknown tools or extra
fields are rejected. The dispatcher validates the arguments against the named
tool, not just the outer model-output union schema.

Limits are now tightened through `motion_safety.py`: at most 2 degrees per
joint, 3-degree vector norm, a 2-degree margin inside joint limits, and 0.1 raw
units per gripper proposal. These are software trial limits, not validated
collision, force or braking limits. Both the measured and target angles must
stay outside the soft-limit margin; this interface cannot command a recovery
out of that margin.
Both observation-time and fresh measured joint deltas are checked. The latest
observation must be no older than 30 seconds, unconsumed, and have no blockers.
State is reread before accepting a proposal; significant joint/gripper drift,
changed ownership, invalid telemetry or a new fault rejects it. Every accepted
proposal consumes that observation; it is never queued for later execution.

One adapter session is also limited to 10 accepted proposals, 10 degrees of
per-joint excursion from its first valid measured state, 30 degrees of total
absolute proposed joint travel (summed over all joints), and 1.0 raw unit of
total proposed gripper travel. Reversals count; these are budgets for suggestions,
not a claim of actual executed motion. `observe` cannot reset the anchor or
budgets. Hardware/camera faults, changed device identities or joint limits, and
budget exhaustion latch a fault. Fresh healthy data does not automatically clear
it; inspect the cause before explicitly creating a new session. Creating a new
session is not proof of physical safety. There is no model-visible reset tool.

`software_guard` in observations/results reports the budget and latched reason,
and explicitly marks physical stop validation and collision checking as false.
See `SOFTWARE_MOTION_GUARDS.md` for the legacy visual executor boundary.

`accepted: true` means numeric shadow checks passed. Every result still reports
`executed: false`; the successful result also reports `collision_checked: false`.
This adapter is not a realtime supervisor or a physical safety controller.
Do not forward its saved targets straight to `/api/command`.

## Upstream agent integration boundary

To make the locally evaluated upstream contract types importable:

```bash
export PYTHONPATH=/home/tuojing/arx_r5_control/vendor/GPT-Policy-main/src
```

`adapter.agent_context()` provides the R5-specific instructions, tool schemas
and output schema using upstream's actual `AgentContext` class.
`adapter.agent_turn(observation, previous_result)` supplies the text and actual
JPEG bytes as `AgentTurn` / `ImageInput`, not just paths in a prompt.
An upstream-compatible `AgentSession` can use:

```python
# agent is a separately configured AgentSession; this is not a provider launcher.
agent.start(adapter.agent_context())
try:
    result = adapter.shadow_once(agent)
finally:
    agent.close()
```

`shadow_once` captures fresh observations, refuses to call the agent if preflight
is blocked, requests one decision and runs our shadow dispatcher. `_wire` metadata
from upstream is removed before strict validation. Provider construction is now
available in the runner below. A real model observation call subsequently
succeeded; see `R5_DEPLOYMENT_STATUS.md`. The integration test uses the real upstream
contract classes with a **fake decision provider**, not a live model call.

### Model-session entry point

`policy_runner.py` loads the original `configs/agents/codex.json` and uses the
upstream `CodexSession`, preserving its model, effort and live-image window.
It bypasses upstream main/runtime/hardware constructors and automatic homing.

```bash
python3 policy_runner.py preflight
python3 policy_runner.py decide --turns 1
```

`preflight` reads local state and frames without starting a model. `decide`
starts the model only after successful observation preflight, sends both camera
images and state using existing Codex CLI authentication, and may consume paid
usage. Configuration does not prove account access. The official interface
reference is https://developers.openai.com/codex/app-server .

This is **model-side integration only**, not a live motor executor. Accepted
outputs remain shadow proposals, not actions or proof of a grasp. No `live` mode
or motor-command transport is exposed. Do not replay saved targets manually.
The physical blockers are recorded in `session-config.json`; see
`STOP_MODE_AUDIT.md` for the unresolved stopping/holding behavior.

Every turn receives newly captured images and the preceding tool result. Model
startup never reuses pre-start images. Decisions have a 25-second deadline using
the upstream wait hook and a post-return check; provider initialization and
thread startup have a separate 15-second wait deadline. Rejected outputs or faults end the loop
without automatic retry/reset. Closing a constructed model session sends no
robot command. Session length is 1..10 (default 1), without increasing proposal
budgets. New `analysis/gpt-session-*/` directories contain images, observations,
tool results, `session-config.json` and `session-result.json`. Provider exceptions
record their type instead of potentially sensitive transport details.

Validation on 2026-09-25: `analysis/gpt-session-192ad115667f/` passed real-device
observation preflight with no blockers; no model was called and no motor command
was issued. Automated runner tests use a fake provider with real upstream types.

Do not use upstream `main.py` or `gpt-policy` as the deployment entry point:

- Its default profile is dual-arm X5 plus three cameras; the file named
  `simulated.json` still selects a real ARX backend, not a robot simulator.
- Its ARX constructor sends hold commands. Another SDK must not compete for CAN.
- Terminal decisions, budget exhaustion and first Ctrl+C can return home;
  upstream homing also opens the gripper. None of that is enabled here.
- Its default prompts assume calibrated D405 views, metric TCP targets and a
  normalized gripper. Those assumptions are replaced in this adapter.
- The supplied config also has agent-directory/tool-catalog path resolution
  problems. This integration bypasses those defaults; it does not claim to have
  repaired the upstream CLI.

## Live read-only acceptance on 2026-09-25

Evidence: `analysis/policy-a26c992b25d0/`, observation
`baa1b3e5a38e464197ea8037009a6260-observation.json`.

- Wrist: 848x480, `/dev/video10`, sequence advanced. The image shows the tennis
  ball and open fingers. Global: 640x480, `/dev/video2`, sequence advanced; the
  image shows the ball and arm. This does not establish depth or clearance.
- Both the original 8765 service and the 8768 proxy report `robot_status=fault`,
  six null joint values, `model_ready=false` and repeated SDK error codes
  2/12/22/32/42/52/62. Gripper feedback is about -1.386 raw, outside the contract.
- The current log tail repeatedly reports motors 1..6 offline. The root cause
  (power, wiring, CAN link, device initialization or driver state) is not proven.
  Fresh bus-level RX counters cannot establish valid per-joint feedback.
- The adapter saved both views and blocked proposals. No enable, reset, home,
  gripper or robot target command was sent. No service was restarted.

## Verification and remaining work

```bash
python3 -m pytest -q tests/test_policy_adapter.py
python3 -m pytest -q tests
```

The adapter tests use fake telemetry/cameras and check real upstream contract
compatibility, units, faults, nulls, nonfinite numbers, stale/consumed observations,
frame loss, input schemas, drift, limit checks and absence of command transport.
Existing HTTP regression tests bind ephemeral local ports with simulated arms
and fake cameras; they need local socket permissions, not robot access.

Before a physical grasp:

1. Diagnose and restore valid R5 motor feedback. Reconnection/reinitialization
   can enable/home through the vendor SDK, so it is a separate supervised action.
2. Validate powered pause/hold, operator handoff, communication-loss behavior
   and hardware fallback. See `PAUSE_HOLD.md`: the existing protect request can
   allow sag; software tests and unplugging power do not guarantee holding.
3. Verify gripper direction, raw range, cable slack, payload and collision/table
   clearance. Fixed camera placement alone is not geometric calibration.
4. Configure and verify an actual model session in shadow mode. Convert the
   existing human demonstration explicitly before using it as model context;
   the two repositories' recording formats are not interchangeable.
5. Add a separately reviewed execution backend using the single existing worker,
   fresh-state/camera supervision and verified stopping behavior. Do not remove
   the read-only boundary merely because a shadow proposal looks plausible.
6. Test approach, alignment, closure and lift as separate observed stages; only
   report success after measured/visual evidence of an actual stable grasp.

If the upstream Cartesian/geometric tools are selected later, first establish
R5 kinematics, joint/gripper units, calibrated TCP, camera intrinsics/extrinsics
and the appropriate IK implementation. The image-guided joint-step path here is
an intentional alternative, not a claim that upstream metric tools work without
their required calibration.
