# R5 stop-mode audit, 2026-09-25

Read-only investigation. No SDK object was constructed, no process was attached,
no motor command was issued, and no controller code was changed for this audit.
This establishes software behavior, not physical brake certification.

## Pinned binary and API

Inspected binary:
`vendor/R5-master/py/ARX_R5_python/bimanual/api/arx_r5_src/libarx_r5_src.so`

SHA-256:
`30239795532e0d440842405f02092c85f95b5f4b0813c2bdf95b22d89960fa18`

The shipped `InterfacesThread.hpp` enumerates SOFT=0, GO_HOME=1, PROTECT=2,
G_COMPENSATION=3, END_CONTROL=4 and POSITION_CONTROL=5. The shipped Python
wrapper `single_arm.py` maps `protect_mode()` to 2 and
`gravity_compensation()` to 3. These are separate operations.

`robot_worker.py` currently requests state 2 for pause, shutdown, active command
timeout, CAN timeout and SDK errors. `live_control.py` routes the website stop
and disconnect through that path. Normal powered pause is not yet deployed.

## What PROTECT sends

Static disassembly: `ControllerBase::stateProtect`, address 0x15349e,
ending before 0x15374a. It invokes the five-double motor packing virtual method.
DWARF confirms that virtual slot 3 is `packMotorMsg(double, double, double,
double, double)`. The definition parameter names for both MotorType1 and
MotorType2 are, in order:

```text
k_p, k_d, position, velocity, torque
```

Parameter-name evidence: DWARF definition DIEs around 0x4404d3 and 0x4472c5;
the corresponding function addresses are 0x1bba52 and 0x1bc788.

The PROTECT calls set all inputs except k_d to zero. Constant references and
joint-index loops establish the following pre-encoding values:

| SDK joint | k_p | k_d | Position | Velocity | Feedforward torque |
| --- | --- | --- | --- | --- | --- |
| J1 | 0 | 1 | 0 | 0 | 0 |
| J2, J3 | 0 | 5 | 0 | 0 | 0 |
| J4 | 0 | 2 | 0 | 0 | 0 |
| J5, J6 | 0 | 1 | 0 | 0 | 0 |

The relevant double constants are at 0x1c0300 (1), 0x1c0310 (2), and 0x1c0370
(5); `.rodata` has the same virtual-address/file-offset mapping here.
These are SDK control parameters, not calibrated physical damping coefficients.

The routine subsequently copies measured joint positions into internal target
storage. That bookkeeping does not turn the transmitted zero-k_p commands into
position holding. It ends by calling `CatchSoft()` at 0x155636, which sends
all five parameters as zero to motor index 6 (the gripper).

Conclusion: this host-side protection command is damping/soft behavior, not a
request to maintain joint positions and gripping force. It does not establish
anything about a separate brake or drive behavior after power/communication loss.

## Gravity compensation is not a direct replacement

`stateGravityCompensation()` starts at 0x15374a and ends before 0x1538ea.
Its normal branch sends a feedforward torque vector with zero position and
velocity gains, updates internal target storage and calls `CatchSoft()` as well.
It checks torque limits and can fall back to `stateProtect()` on failure.

Consequently, replacing state 2 with state 3 is not a verified position-hold or
gripper-hold fix. Payload/model accuracy and drive fault behavior still matter.
Do not bypass the SDK fault path or retune these binary constants to force a hold.

## Recorded post-stop motion

Source: local `recordings/<episode>/timeline.jsonl`. Rows were sorted by `t_ns`.
For accepted stop requests, compare the last valid measured sample within 150 ms
before the request with the last recorded disabled sample within one second
after it. The selected recordings end shortly after stop, so these are short
windows, not complete stopping-distance or settling measurements.

| Episode | Stop request, seconds | Last after-stop sample, seconds | Delta J3 | Delta J4 |
| --- | --- | --- | --- | --- |
| 20260924T145652_08f81a0ff6cf | 5.044707 | 5.212722 | -2.710 deg | -2.361 deg |
| 20260924T151143_1b53282ec423 | 5.045002 | 5.212450 | -1.727 deg | -1.355 deg |
| 20260924T152451_55f3f8e924ae | 44.999740 | 45.141977 | -2.732 deg | -2.339 deg |

In the first example the pre-stop sample is at 5.012512 s; J3 changes from
4.513444 to 1.803225 degrees and J4 from -10.917538 to -13.278106 degrees.
The first disabled sample already has the same J3/J4 values as the pre-stop
sample, so the measured change continues while the controller reports disabled.
Both selected endpoint samples have empty error arrays, with reported feedback
ages of 21 and 19 ms. These are HTTP-recorded feedback receipt times, not exact
motor sampling times or physical stop application times.

These observations support lack of position holding after stop. They do not
prove power was lost or distinguish gravity, residual motion, cable force,
external contact and encoder/control effects in every case. No deliberate
power-loss or communication-loss experiment was performed in this audit.

## Work needed for GPT grasping

1. Separate a normal powered pause/model-thinking interval from fault protection.
   A validated local control loop must own the held target independently of model
   latency. Existing `pause_hold` is an offline prototype, not deployed hardware
   behavior; see `PAUSE_HOLD.md`.
2. Establish manufacturer-supported behavior for communication loss, drive fault
   and power loss, including whether this exact physical arm has brakes and what
   support/containment is required. The local API/binary is insufficient to
   certify those mechanisms.
3. Perform an appropriately supported, supervised empty-gripper validation of
   pause, tracking, gripper retention and operator handoff. Do not intentionally
   disconnect an unsupported powered arm to test it.
4. Complete the actual GPT decision-session/live-backend integration. The
   current adapter is a tested observation/shadow contract, not a working
   autonomous physical-grasp deployment.
5. Only then validate approach, alignment, closure and lift with fresh images
   and measured feedback. A numeric proposal or model completion message is not
   proof of a successful grasp.

The objective remains GPT-controlled physical grasping. This audit narrows a
concrete control-layer blocker; it does not claim the overall task is complete.
