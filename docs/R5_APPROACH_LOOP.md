# R5 approach and correction loop

This describes the legacy `--policy-interface joint` diagnostic mode. The default
now uses the original Cartesian tools; see `R5_CARTESIAN_DEPLOYMENT.md`.

The R5 adapter retains the original GPT-Policy `runtime.runner.run_loop`.
The policy now has the following options between fresh camera/state observations:

| Tool | Effect |
| --- | --- |
| `observe` | Read another fresh observation without an actuator target. |
| `check_joint_step` | Preview six relative joint increments in radians against numeric limits and remaining budgets. No motion or budget debit. |
| `move_joint_step` | Convert those increments from the latest observed measured pose to an absolute target, recheck current state, execute, settle, and hold. |
| `move_joints` | Existing absolute joint radians tool. |
| `set_gripper` | Existing separate raw gripper target. |
| `done` / `give_up` | Finish while retaining hold for operator handoff. |

The instructions follow the upstream sequence: approach and align, observe actual
results, correct, close separately, then lift and verify retention. A rejected
numeric preview or uncertainty about the eventual grasp alone does not establish
impossibility. The model can consider supported safe alternatives. Missing
direction/clearance evidence, hardware faults and exhausted budgets still block
motion; no minimum number of physical attempts is required.

Every successful arm action reports its source observation and measured joint
delta. `state.visual_feedback` reports a wrist colour/shape ball candidate. With
one unclipped candidate in consecutive observations and a matching settled arm
action, it reports pixel displacement, apparent diameter ratio and measured joint
changes. A predominantly single-joint change can produce a local response
candidate that explicitly requires visual confirmation. No identity tracking,
depth, contact, table height, TCP calibration or successful approach is implied.
Camera changes, stale frames, missing/ambiguous candidates, unexpected pose drift,
read-only tools and rejected actions do not establish an action-response sample.

The original URDF remains visualization data. This change does not expose
unvalidated metric TCP movement or copy X5 camera calibration to the R5.

## Historical reference

`r5_tennis_wrist_policy_context.json` includes the verified gripper-opening
evidence and two reviewed wrist images from
`recordings/20260924T135243_10d933b7b83a/`. The associated measured J2 change was
approximately +3.344 degrees, with J4 also changing +0.109 degrees. The ball
candidate shifted from [484.4, 227.2] to [488.85, 199.26] pixels. This is an old
teleoperation example, not a successful grasp, current clearance, or transferable
calibration; its motion is not replayed. Full provenance and timestamps are in
`analysis/reviewed-j2-visual-reference.json`.

## Attended trial

With the existing workbench connected in supervised mode and an operator present:

```bash
python3 supervised_policy.py --supported-supervision --policy-interface joint --camera-mode wrist \
  --max-decisions 10 --task '抓取网球' \
  --input-json r5_tennis_wrist_policy_context.json
```

All existing motion budgets remain: 2 degrees per joint per step, 3 degrees step
norm, 10 accepted actions, 10 degrees session excursion, 30 degrees cumulative
joint travel and 1.0 raw cumulative gripper travel. Preview/observe use decision
turns but do not reset those budgets. These are attended trial limits; a full
approach and grasp may exceed them. They are not automatically enlarged or reset.

Offline tests cover preview rejection/recovery, unchanged budgets, revalidation
after preview, relative-target anchoring, measured-result linkage, ambiguous
visual feedback, and the real upstream loop with fake hardware/provider. A
passing test is not evidence of a physical grasp.

## Verification on 2026-09-25

Full regression: 198 tests and 79 subtests passed. Live trial
`analysis/live-policy-ead0356cff2c_unreviewed/` used `gpt-6-astra`, wrist-only
images and the reviewed historical reference. The live observation included
`visual_feedback` (ball candidate center [319.44, 186.14] pixels). The first
decision remained `give_up`: the model did not consider historical J2 pixel
motion sufficient evidence of current approach direction or table clearance,
and had no verified lateral alignment direction. No model-selected actuator
target was submitted. The host received `stop` after that decision.

The software correction loop is implemented; physical grasping remains
unverified. Further repetitions of the same scene/prompt do not supply the
missing current direction and clearance evidence.
