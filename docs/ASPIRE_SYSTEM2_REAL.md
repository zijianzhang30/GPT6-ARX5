# ASPIRE System 2 on the ARX R5

This adapter runs L3-04 with the same observation, action and feedback loop as the
[simulation pilot](https://github.com/LLM4Robot/LLM4Robot-Bench/blob/be281d2487da98ab87f81478a5e59623b8bf8e30/src/harness_v1/aspire/README.md).
The coding agent makes one decision at a time. The MCP bridge translates it into a
command for `tools/held_policy_review.py`. The host uses its existing camera,
observation age, IK, motion budget, tracking and hardware supervision checks.
The branch has been tested with a mock host.

## Connect in observation mode

1. Follow the [current host workflow](../skills/arx-r5-tabletop-tasks/references/common-execution.md)
   for the physical left working arm. Reuse an existing qualified hold through
   the documented handoff where applicable. The MCP client does not launch or
   reconnect the hardware.
2. Create a private, short directory on the ARX machine with mode 0700. Pass
   `--aspire-socket /absolute/private/short/aspire.sock` to the supervised host
   alongside its normal `--working-arm left` arguments. The socket is ready once
   the host reports `ASPIRE System 2 socket`. Use a new path for a new host.
3. Configure the MCP client for **stdio**, using the same machine and OS user.
   The command is `python3` with the following arguments. It uses Python 3.9+
   and the standard library.

   ```text
   /absolute/path/to/GPT6-ARX5/tools/aspire_system2_mcp.py
   --socket
   /absolute/private/short/aspire.sock
   ```

4. Call `r5_task` and `observe`. Confirm the physical arm identities, views
   and feedback. Next, load the [L3-04 task recipe](../skills/arx-r5-tabletop-tasks/references/l3-04-aspire-transfer.md).
   Use the returned camera names `overview`, `left_wrist` and `right_wrist`.

## Attended motion

For a cleared and supervised run, start the existing review host with
`--aspire-allow-motion` and the MCP process with `--allow-motion`. Follow the
host workflow for enabling motion and recording. There is one owner and the
left arm is the only arm selected for MCP motion. Commands submitted over MCP
and the operator's normal terminal use the same host queue.

- `cap_move_to_pose` receives a single target in metres and WXYZ quaternion
  order with `frame: "left_base"`. XYZ refers to the physical left arm's base.
  The adapter converts the quaternion to the ARX tool's XYZW order. Confirm the
  physical TCP and wrist configuration for the station before execution.
- `cap_set_gripper` receives one normalized absolute opening within the
  returned next-opening bounds. See both commanded and measured openings in
  the observation. A gripper position is not force or verified grasp.
- Both require the current `observation_id` and a `note` identifying the visual
  evidence for clearance or contact. Inspect the tool result and new images
  before reusing the latest observation. A manual terminal command invalidates
  the prior MCP observation. The host never automatically retries a timed-out request.
- `review_completed` means the host returned an execution receipt. Inspect the
  measured pose and the reported tracking/settling details. `outcome_unknown`
  calls for checking the host and obtaining a fresh observation before another
  action. A client disconnect keeps the original supervisor in control.
- The current image-guided mode has RGB and nominal TCP feedback. The capability
  graph reports depth backprojection unavailable. A future RGB-D interface
  requires verified depth alignment, camera intrinsics, and the transform to
  the relevant arm base. Existing IK preview checks feasibility; verify actual
  brush, hand and fixture clearance from the station views.

For this sweep, verify that the brush follows a trial lift, then sweep one block
at a time using the observed pan opening. Record the final count after withdrawing
the brush. Follow the task recipe and common workflow for release and return.

## Offline check

```bash
python3 -m unittest discover -s tests -p test_aspire_system2.py -v
```
