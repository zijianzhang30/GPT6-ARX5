# Wrist-only supervised trial

`supervised_policy.py --camera-mode wrist` acquires only the Gemini wrist
camera (`left`). Wrist-only is now the default. Camera freshness, device identity,
independent heartbeats, action limits and stop handling still apply.

Use `r5_tennis_wrist_context.json` for the reviewed opening-direction evidence
with historical wrist images only. The original two-camera manifest also has
external reference images, so it is not suitable for a strictly wrist-only run.

```bash
python3 supervised_policy.py --supported-supervision --policy-interface joint --camera-mode wrist \
  --max-decisions 10 --task '抓取网球' \
  --input-json r5_tennis_wrist_context.json
```

The existing live workbench must already be connected in supervised policy
mode, with an on-site operator. This command enables the existing worker after
preflight; it does not reconnect or home. Normal model completion retains powered
hold until the operator sends `stop` or stops through the workbench.

This recorded trial used the legacy joint interface. The new default Cartesian
interface and its measured calibration requirements are documented in
`R5_CARTESIAN_DEPLOYMENT.md`.

On 2026-09-25, the real `gpt-6-astra` trial was recorded at
`analysis/live-policy-958129a77964_unreviewed/`. Its only live frame was
`frames/step-00000-left.jpg`. The first decision was `give_up`, with zero
execution results: the model could see the ball ahead/left of the fingers but
could not establish fingertip/table clearance or a safe approach from the
uncalibrated monocular view. The host then received `stop`. No grasp was verified.

The camera/deployment/supervisor/preparation tests passed (24 tests), including
the original loop with an unavailable external camera and a wrist camera fault
that remains latched. These software checks do not establish grasp capability.
