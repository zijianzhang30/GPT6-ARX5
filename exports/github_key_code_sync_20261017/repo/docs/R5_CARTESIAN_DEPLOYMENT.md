# Original GPT-Policy Cartesian deployment on R5

The default `supervised_policy.py` interface is now `cartesian`, with wrist-only
images by default. The old joint tools remain available explicitly through
`--policy-interface joint`; they are diagnostics, not the default grasp policy.

`--cartesian-stage motion` now requires verified robot/TCP geometry only. It
uses the original movement/path-check tools with raw visual observations;
`locate_point` and `set_gripper` are unavailable. `--cartesian-stage vision` adds
calibrated localization but keeps the gripper unchanged. The default `grasp`
stage requires all calibration and exposes the full original catalog. These
are capability gates, not statements of physical deployment or grasp readiness.
No stage bypasses robot-model/TCP validation, transport checks or motion limits.

## Reused upstream modules

- `runtime.runner.run_loop`: original observation/decision/execution cycle.
- `tools.catalog` and `tools.runtime.ToolExecutor`: original `move_to`,
  `move_eef_chunk`, `check_path`, `locate_point`, normalized `set_gripper`, `done`
  and `give_up` interfaces. No model-visible joint-angle tool in this mode.
- `harness.protocol`: original task, persistence, grasp and observation protocol,
  with R5 camera facts, unavailable torque/metric gripper feedback, trial limits,
  and operator handoff stated explicitly.
- `geometry.FrameCalibration`: measured fingertip and camera transforms.
- `vision.PixelLocalizer`: calibrated rays and two-view triangulation, retaining
  its parallax/conditioning checks and explicit unavailable-depth result.
- `motion.ContinuousIK`, `EefTrajectoryPlanner` and Ruckig scalar retiming:
  line/SLERP sampling, per-sample IK and time-only retiming. `R5Solver` binds these
  to the existing R5 URDF solver; it does not construct the vendor hardware SDK.

`CartesianBackend` maps normalized gripper commands through separate measured
command and feedback endpoints. Unknown gripper metres and torque remain null.
The generated joint samples and timestamps go through `policy_trajectory` on the
existing HTTP/worker connection. The server interpolates these timed references,
rejects expired requests, rejects competing targets/jogs, and cancels remaining
samples on pause/stop. A late playback tick stops instead of catching up.
The planned start must agree with both measured and held commanded joints within
0.05 degrees; it cannot jump to a lagging measured pose. Oversized sample counts
are rejected before dense IK allocation.

Existing supervised ownership, feedback freshness, camera checks, worker target
expiry and model-action budgets remain. The entire Cartesian path must fit the
existing 2-degree/joint and 3-degree-norm observed-step envelope. Every path
segment, including reversals, counts toward the 30-degree session travel budget;
one submitted path counts as one action. Timing is bounded to 30 seconds and
10,000 samples; playback does not enlarge any session budget. No IK/path check
is a collision certificate. Completion holds for operator handoff, not home.

## Real parameters still required

`r5_cartesian_profile.json` is intentionally incomplete. It contains no copied
X5 calibration or fabricated R5 measurements. The following data are required:

| Data | Field and convention | How to obtain |
| --- | --- | --- |
| Verified R5 joint model | `kinematics_verified`, `urdf_sha256`, `measurement_record` | Check joint order/sign/zero and measured endpoint motion against the exact URDF; record evidence before marking verified. |
| Fingertip grasp frame | `calibration.link6_from_tcp`, rigid 4x4 transform, metres | Measure/calibrate the grasp point and orientation relative to link6. Tool +z points toward fingertips; +y follows jaw opening, as in upstream. |
| Wrist camera mounting | `calibration.link6_from_camera.left`, camera optical coordinates to link6 | Hand-eye calibration using multiple robot poses and a stationary calibration target; validate on held-out poses. |
| Image projection | `vision.camera_intrinsics.left` 3x3 K; five coefficients `[k1,k2,p1,p2,k3]`; `image_sizes.left` | Obtain the matching camera stream's factory parameters or calibrate at its actual resolution/crop. Do not truncate an incompatible distortion model. |
| Camera identity/setup | `vision.device_ids.left`, `mount_record` | Record the actual device and rigid installation; revalidate after moving the wrist camera. Resolution/device mismatches fail at capture. |
| Gripper endpoints | `gripper.command_closed_raw`, `command_open_raw`, `feedback_closed_raw`, `feedback_open_raw` | Measure the empty-gripper command/feedback endpoints independently. Opening direction alone is insufficient. |

`link6_from_sdk_eef` is identity because this adapter's solver explicitly returns
URDF link6, not the vendor END_CONTROL frame. It is not an assumed fingertip
offset. Camera transforms must be rigid rotations/translations, not arbitrary
finite matrices. Profile flags and records document operator measurements;
software cannot independently certify physical calibration from a JSON file.

If using `--camera-mode both`, also supply top-camera intrinsics/distortion,
image size/device, `vision.top_fixed: true` and
`calibration.base_from_camera.top.left`. A hand-held external camera is not
compatible with fixed extrinsics.

Table position, fingertip and camera-body clearance, and other hidden obstacles
must be measured/checked for the scene. Persistent facts can be supplied through
`scene.safety_notes`; these notes are model context, not automatic collision
geometry. The current adapter does not implement a full collision model.

## Validation and launch

Ruckig 0.19.4 (inside the upstream supported version range) is installed in
`.venv-policy`, which uses the existing system packages. The pinned extra
dependency is in `requirements-policy.txt`.

Configuration-only validation opens neither the robot nor a model session:

```bash
.venv-policy/bin/python supervised_policy.py --check --camera-mode wrist
```

It currently reports missing measured calibration and exits 2. Even a syntactically
complete profile is not proof of physical accuracy or readiness to grasp.

After measurements and deployment/validation of the timed transport:

```bash
.venv-policy/bin/python supervised_policy.py --supported-supervision \
  --camera-mode wrist --task '抓取网球' \
  --calibration-profile r5_cartesian_profile.json
```

The live workbench must advertise `policy_trajectory_protocol: 1`; this is checked
before enabling. The already running workbench has NOT been restarted to load
that interface. Restarting/reconnecting the existing SDK may home the arm, so
source completion does not imply live transport deployment or physical acceptance.

The tests use synthetic transforms explicitly confined to test fixtures. They
exercise the real upstream planner, Ruckig, original tool executor and loop,
including check_path, movement, ray localization, fresh observations, normalized
gripper conversion, path-budget checks and lost-ack stop without resubmission.
No physical movement or real model trial was performed for this Cartesian change.

## Alignment audit: 2026-09-25

The initial configuration-only check reported 11 blockers. These were not 11
independent physical calibrations: model hash/measurement records and camera
identity/mount records document the underlying measurements. The active
workbench still lacks the timed transport; recent live trials explicitly used
the legacy joint interface.

Read-only USB metadata identifies the current wrist device as Orbbec Gemini 305,
VID:PID 2bc5:0840, serial CV2C8610015R, currently exposed at /dev/video10. The
configured RGB stream is 848x480. This identifies the device, not its optical
calibration or mounting pose. The current camera backend captures UVC MJPEG;
it does not retrieve factory intrinsics. pyorbbecsdk is not installed in the
system Python used for this audit. Factory retrieval must match the exact RGB
stream, crop and distortion model; otherwise use a measured calibration target.
The profile currently compares device paths, so stable serial identification is
also an integration improvement before accepting a persistent calibration.

Acquisition and acceptance order:

1. Verify R5 joint order, sign, zero and base axes against the model. Obtain the
   fingertip TCP offset/orientation from the actual finger drawing or measurement.
   Record independent measured endpoint changes; numerical FK/IK agreement alone
   does not validate real hardware.
2. Obtain wrist RGB intrinsics/distortion for the selected stream. Fix the mount,
   then measure link6-to-camera using a known stationary target and multiple
   diverse robot poses. Validate with poses excluded from the fit. A camera
   model name or a photo alone does not supply these transforms.
3. Measure separate empty-gripper command and feedback endpoints, useful jaw
   opening versus command, and a suitable contact/closure procedure for the ball.
   The observed opening direction and approximately 4.8 open command are evidence,
   not a calibrated jaw width or grasp force.
4. Establish table height and clearance for fingers, camera body and arm along
   the intended approach. Supply measured scene facts through safety_notes;
   these notes do not implement automated collision checking.
5. Deploy and validate the timed transport with the existing single worker.
   Confirm start continuity, a small measured translation, camera refresh after
   settling, and interruption behavior before attempting contact.
6. Define and validate a grasp-task motion budget. Existing diagnostic limits
   allow 10 accepted actions, 0.1 raw gripper units per action and 1.0 raw unit
   total travel. The earlier empty opening moved approximately 0.225 to 4.8;
   its reverse alone would require about 46 current-sized actions and exceed
   the total travel budget. This does not establish the closure needed around
   a ball, which is still unmeasured. Merely switching to Cartesian tools cannot
   fix this mismatch. Model-level set_gripper should eventually execute a bounded,
   feedback-monitored internal ramp; keep explicit validated task-wide limits.
   No limits were increased as part of this audit.

Upstream distinctions: move_to/check_path need the robot/TCP geometry, not camera
intrinsics intrinsically. locate_point uses camera geometry; one RGB observation
returns a ray, and two wrist observations require the same stationary feature
and adequate parallax for metric position. Upstream permits absent distortion
coefficients (no correction); our vision stage's mandatory five coefficients
are an adapter choice. Staged capability gates now support verified Cartesian
motion before calibrated localization. Unknown distortion should not silently
be treated as measured zero.

The target remains the original observation/tool/planner loop with measured R5
hardware bindings. Copying X5 transforms, numerical limits or camera values does
not align the physical system. Task input remains "抓取网球"; hardware and scene
facts belong in setup context.

## First stage without a calibration board

```bash
.venv-policy/bin/python supervised_policy.py --check --cartesian-stage motion
```

The real profile currently fails three motion-stage checks: verified robot model,
its measurement record, and physical validation of the estimated fingertip transform. The first two concern one
physical model-validation record; no
camera intrinsics or hand-eye calibration is required for this stage. Hashes
identify files and must not be presented as physical verification.

After the model/TCP and timed transport have been physically validated, an
explicit contact-free validation task is required for a live motion-stage run.
There is no default grasp task or gripper-opening preparation in this stage.
The model receives null normalized opening; transport holds the existing raw
gripper command. The upstream planner's gripper trace likewise contains null
when uncalibrated, never invented normalized readings.

`tools/read_orbbec_factory.py` can query an exact MJPG RGB stream profile through
the official SDK 2.9.3 C ABI without starting streams or importing the robot SDK.
It requires an SDK config using V4L2 with Gemini305 automatic reboot and network
enumeration disabled. Evidence is saved separately and never automatically
applied to the robot profile. Two initial queries (default and V4L2 backends)
returned no enumerated devices on this host, despite the UVC camera being usable.
USB device permissions differ from video-node permissions; factory calibration
has not been acquired. This does not block the motion-only stage.

The operator confirmed unmodified factory fingers. The official Python SDK
manual (downloaded to analysis/r5-factory-geometry/python-sdk.pdf) specifies a
nominal 0-80 mm opening on page 2 and illustrates axes on page 7, but supplies
no complete link6-to-fingertip transform. Neither that range nor the illustrations
establish a measured raw-command-to-width mapping.

The operator subsequently estimated approximately 80 mm from the end mounting
face along the fingers to the fingertips, explicitly distinguishing this from
jaw opening. The real profile records that scalar under hardware_evidence with
unknown measurement uncertainty. At the operator's request, link6_from_tcp now
contains a candidate translation [0.08, 0, 0] in link6 and a proper rotation
mapping tool +Z to link6 +X, tool +Y to link6 +Y, and tool +X to link6 -Z. This
uses the model's J6 +X axis as the assumed finger direction and assumes the
mounting-face center coincides with the link6 origin. These assumptions are
listed in calibration.tcp_validation, with status estimated. The length alone
does not verify them; the profile gate explicitly rejects this estimate for
execution even if the robot-model flag is later marked verified.

The local URDF exactly matches the official repository revision
e87d09c11edb65f6ae672abc7a41fe2277a2f12f. Its SHA256 is now recorded in the real
profile with source provenance. kinematics_verified remains false and
measurement_record remains null. No physical motion or deployment
was performed during this staged-capability change. Validation: 222 project
tests and 79 subtests passed, including original-planner execution with fake
hardware in motion-only mode and rejection of unavailable tools before commands.
