#!/usr/bin/env python3
"""One supported, supervised empty-gripper opening check, not a grasp policy.

Uses the existing HTTP worker; no connection, homing, joint target or retries.
Exit requests existing PROTECT (not position hold); mechanical support is required.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import threading
import time
import uuid

from motion_safety import ProposalGuard, finite, vector
from policy_adapter import CAMERAS, read_camera, state_blockers
from visual_control import WorkbenchClient, check_state, validate_action


# Use upstream GPT-Policy's position tolerance as this diagnostic envelope.
# This is not its tracking-fault limit or a calibrated physical safety limit.
JOINT_DRIFT_LIMIT_DEG = math.degrees(.03)


class CameraWatch:
    def __init__(self, client, directory):
        self.client, self.directory = client, directory
        self.devices = None
        self.updated = 0.
        self.failure = None
        self.done = threading.Event()
        self.thread = None

    def capture(self, label=None):
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = {name: pool.submit(read_camera, self.client, key) for name, key in CAMERAS.items()}
            frames = {name: future.result() for name, future in jobs.items()}
        devices = tuple(frames[name][1]["device"] for name in CAMERAS)
        if len(set(devices)) != 2 or self.devices is not None and self.devices != devices:
            raise ValueError("Camera identities changed or are duplicated")
        self.devices = devices
        self.updated = min(meta["received_monotonic_s"] for _, meta in frames.values())
        if label:
            for name, (image, _) in frames.items():
                with (self.directory / f"{label}-{name}.jpg").open("xb") as stream:
                    stream.write(image.data)

    def check(self):
        if self.failure or not 0 <= time.monotonic()-self.updated <= .5:
            raise ValueError(self.failure or "Camera stream is stale")

    def start(self):
        self.capture("before")
        self.check()

        def loop():
            while not self.done.wait(.1):
                try:
                    self.capture()
                except Exception as exc:
                    self.failure = str(exc)
                    return

        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()

    def close(self):
        self.done.set()
        if self.thread:
            self.thread.join(timeout=3)


def verify(client, vision, log, *, mode='open', clock=time.monotonic, sleep=time.sleep):
    if mode not in ('stationary', 'open', 'hold'):
        raise ValueError('Expected stationary, open or hold check')
    active = False
    before = None
    result = {"status": "blocked", "target_sent": False, "stop_confirmed": False,
              "grasp_attempted": False, "hold_validated": False,
              "test_mode": mode,
              "powered_hold_observed": False,
              "joint_drift_limit_deg": JOINT_DRIFT_LIMIT_DEG}

    def inspect(state, initial):
        # Preserve the exact sample that trips a check, not only the prior one.
        log({"event": "inspection", "monotonic_s": clock(), "state": state})
        check_state(state)
        vision.check()
        if state.get("enabled") is not True or state.get("owner") != client.client:
            raise ValueError("Control ownership lost")
        if state.get("mode") != "joint" or state.get("speed") != .1:
            raise ValueError("Control settings changed")
        deltas = [a-b for a, b in zip(state["joints_deg"], initial["joints_deg"])]
        joint = max(range(6), key=lambda i: abs(deltas[i]))
        drift = abs(deltas[joint])
        if drift > JOINT_DRIFT_LIMIT_DEG:
            raise ValueError(f"Non-commanded J{joint+1} drift {deltas[joint]:+.3f} deg "
                             f"exceeds {JOINT_DRIFT_LIMIT_DEG:.3f} deg")
        return drift

    try:
        before = client.state()
        # A newly connected, disabled worker has no previous gripper target.
        # Stationary enable validates the prospective reference separately.
        issues = state_blockers(before, require_gripper_target=mode == 'open')
        if issues:
            raise ValueError("; ".join(issues))
        vision.check()
        if mode == 'hold' and (before.get('hold_available') is not True
                               or before.get('worker_protocol_version') != 2):
            raise ValueError('Hold validation mode and worker protocol 2 are required')
        # Live enable currently initializes its reference to feedback + 0.1.
        initial_reference = before['gripper_raw'] + .1
        if not 0 <= initial_reference <= 5:
            raise ValueError('Initial gripper reference is outside 0..5')
        target = before["gripper_raw"] + .2 if mode == 'open' else None
        guard = ProposalGuard()
        guard.check_state(before, require_gripper_target=mode == 'open')
        if target is not None:
            validate_action(before, {"gripper_raw": target})
            guard.accept(before, {"gripper_raw": target})
        log({"event": "preflight", "state": before, "target_raw": target})
        client.command("settings", mode="joint", speed=.1)
        fresh = client.state()
        if state_blockers(fresh, require_gripper_target=mode == 'open'):
            raise ValueError("Readiness changed before enabling")
        if (max(abs(a-b) for a, b in zip(fresh["joints_deg"], before["joints_deg"])) > .1
                or abs(fresh["gripper_raw"]-before["gripper_raw"]) > .01):
            raise ValueError("Robot changed before enabling")
        vision.check()
        active = True  # An enable timeout does not mean the server rejected it.
        state = client.command("enable")
        max_drift = inspect(state, before)
        fresh = client.state()
        max_drift = max(max_drift, inspect(fresh, before))
        if target is not None:
            validate_action(fresh, {"gripper_raw": target})
            # No joint target is sent: retain the controller's enable-time reference.
            result["target_attempted"] = True
            state = client.command("target", gripper_raw=target)
            result.update(target_sent=True, requested_gripper_raw=target)
            max_drift = max(max_drift, inspect(state, before))
            log({"event": "target_sent", "state": state})
        started = clock()
        deadline = started+5
        samples = []
        joint_samples = []
        held_target = None
        held_gripper = None
        while clock() < deadline:
            if mode == 'hold' and held_target is None and clock()-started >= 1:
                state = client.command('pause_hold')
                max_drift = max(max_drift, inspect(state, before))
                if state.get('control_state') != 'holding':
                    raise ValueError('Stationary pause did not enter holding')
                held_target = state['hold_target_deg'][:]
                held_gripper = state['gripper_command_raw']
                if not vector(held_target) or not finite(held_gripper):
                    raise ValueError('Invalid held arm or gripper reference')
                log({'event': 'hold_entered', 'state': state})
            state = client.command("heartbeat")
            max_drift = max(max_drift, inspect(state, before))
            if held_target is not None:
                if (state.get('control_state') != 'holding'
                        or not vector(state.get('hold_target_deg'))
                        or not vector(state.get('command_deg'))
                        or not finite(state.get('gripper_command_raw'))
                        or max(abs(a-b) for a, b in zip(state['hold_target_deg'], held_target)) > .001
                        or max(abs(a-b) for a, b in zip(state['command_deg'], held_target)) > .05
                        or abs(state['gripper_command_raw']-held_gripper) > .001):
                    raise ValueError('Hold changed the latched arm or gripper command')
            change = state["gripper_raw"]-before["gripper_raw"]
            low, high = (-.03, .2) if mode == 'open' else (-.03, .03)
            if not low <= change <= high:
                raise ValueError("Gripper moved opposite direction or outside test envelope")
            now = clock()
            samples.append((now, state["gripper_raw"]))
            joint_samples.append((now, state['joints_deg'][:]))
            log({"event": "feedback", "monotonic_s": now, "state": state})
            sleep(.05)
        recent = [g for stamp, g in samples if clock()-stamp <= .6]
        response = state["gripper_raw"]-before["gripper_raw"]
        settled = len(recent) >= 5 and max(recent)-min(recent) <= .02
        status = ('response_observed' if settled and response >= .05 else 'inconclusive')
        if mode in ('stationary', 'hold'):
            recent_joints = [(stamp, q) for stamp, q in joint_samples if clock()-stamp <= .65]
            arm_stable = (len(recent_joints) >= 5
                          and recent_joints[-1][0]-recent_joints[0][0] >= .5
                          and max(b[0]-a[0] for a, b in zip(recent_joints, recent_joints[1:])) <= .15
                          and all(max(axis)-min(axis) <= .1
                                  for axis in zip(*(q for _, q in recent_joints))))
            status = ('stationary_enable_observed'
                      if settled and arm_stable and abs(response) <= .03 else 'inconclusive')
            result['joint_feedback_stable'] = arm_stable
            if mode == 'hold' and status == 'stationary_enable_observed':
                resumed = client.command('resume')
                inspect(resumed, before)
                if (resumed.get('control_state') != 'active'
                        or max(abs(a-b) for a, b in zip(resumed['command_deg'], held_target)) > .05
                        or abs(resumed['gripper_command_raw']-held_gripper) > .001):
                    raise ValueError('Resume changed the latched target')
                held_again = client.command('pause_hold')
                inspect(held_again, before)
                if (held_again.get('control_state') != 'holding'
                        or max(abs(a-b) for a, b in zip(held_again['hold_target_deg'], held_target)) > .001):
                    raise ValueError('Second hold did not preserve the target')
                log({'event': 'hold_resumed_and_reentered', 'state': held_again})
                status = 'powered_hold_observed'
                result['powered_hold_observed'] = True
        result.update(status=status,
                      initial_gripper_raw=before["gripper_raw"], final_gripper_raw=state["gripper_raw"],
                      observed_gripper_change_raw=response, max_active_joint_drift_deg=max_drift)
    except Exception as exc:
        result.update(status="aborted", reason=str(exc))
    finally:
        if active:
            try:
                try:
                    state = client.state()
                except Exception:
                    state = None
                if state is not None and state.get("enabled") is False:
                    result["stop_confirmed"] = True
                elif state is None or state.get("owner") == client.client:
                    stopped = client.command("stop")
                    result["stop_confirmed"] = stopped.get("enabled") is False
                else:
                    result["stop_note"] = "Ownership changed; did not stop another controller"
            except Exception as exc:
                result["stop_error"] = str(exc)
            if not result["stop_confirmed"]:
                result["status"] = "stop_unconfirmed"
        log({"event": "result", **result})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--supported-empty-gripper", action="store_true", required=True)
    parser.add_argument('--mode', choices=('stationary', 'open', 'hold'), default='open')
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    args = parser.parse_args()
    directory = Path(__file__).resolve().parent / "analysis" / ("gripper-check-"+uuid.uuid4().hex[:12])
    directory.mkdir(exist_ok=False)
    client = WorkbenchClient(args.url)
    watch = CameraWatch(client, directory)
    with (directory/"events.jsonl").open("x") as stream:
        def log(event):
            stream.write(json.dumps(event, allow_nan=False)+"\n")
            stream.flush()
        try:
            watch.start()
            result = verify(client, watch, log, mode=args.mode)
        finally:
            watch.close()
        try:
            watch.capture("after")
            after = client.state()
            log({"event": "after_stop", "state": after})
        except Exception as exc:
            log({"event": "after_stop_unavailable", "reason": str(exc)})
        print(json.dumps({**result, "directory": str(directory)}), flush=True)
    return 0 if result["status"] in ('response_observed', 'stationary_enable_observed', 'powered_hold_observed') and result["stop_confirmed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
