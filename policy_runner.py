#!/usr/bin/env python3
"""Run the upstream GPT-Policy decision session on R5 observations, without motion.

This completes the model-side integration, not the unresolved physical executor.
Neither mode enables, homes, stops, or commands the arm.
"""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

from policy_adapter import ROOT, R5PolicyAdapter, ReadOnlyWorkbench


UPSTREAM = ROOT / "vendor" / "GPT-Policy-main"


def upstream_config():
    source = str(UPSTREAM / "src")
    if source not in sys.path:
        sys.path.insert(0, source)
    from gpt_policy.harness.config import named_agent_config
    return named_agent_config("codex", UPSTREAM / "configs")


def new_agent(config):
    from gpt_policy.harness.providers.codex import CodexSession
    return CodexSession(config, config.model, False, 85)


def run_decisions(adapter, factory, turns=1, emit=lambda result: None):
    """Check real observations before constructing a provider; never replay targets."""
    if type(turns) is not int or not 1 <= turns <= 10:
        raise ValueError("turns must be an integer from 1 to 10")
    from gpt_policy.harness.waiting import monitor_health

    result = {"status": "preflight", "executed": False, "execution_available": False}
    agent = None
    previous = None
    try:
        observation = adapter.observe()
        if not observation["proposal_ready"]:
            result.update(status="blocked", blockers=observation["blockers"])
            return result
        with monitor_health(None, deadline=time.monotonic() + 15):
            agent = factory()
            agent.start(adapter.agent_context())
        for index in range(turns):
            # Provider startup and earlier decisions can invalidate old frames.
            observation = adapter.observe()
            if not observation["proposal_ready"]:
                result.update(status="blocked", blockers=observation["blockers"])
                break
            started = time.monotonic()
            with monitor_health(None, deadline=started + 25):
                decision = agent.decide(adapter.agent_turn(observation, previous))
            # Also check providers which return without polling the wait hook.
            if time.monotonic() - started >= 25:
                raise TimeoutError("Decision exceeded 25 seconds; no proposal dispatched")
            normalized = ({k: v for k, v in decision.items() if k != "_wire"}
                          if isinstance(decision, dict) else decision)
            previous = adapter.handle(normalized)
            result = {"status": "shadow_decision", "turn": index + 1,
                      "executed": False, "execution_available": False,
                      "decision": normalized, "result": previous}
            emit(result)
            # No automatic retry/reset of rejected decisions or hardware faults.
            if not previous.get("accepted", previous.get("proposal_ready", False)):
                result["status"] = "blocked"
                break
    except KeyboardInterrupt:
        result = {"status": "interrupted", "executed": False, "execution_available": False}
    except Exception as exc:
        # Provider exceptions can contain transport details: don't persist credentials.
        result = {"status": "error", "error_type": type(exc).__name__,
                  "executed": False, "execution_available": False}
    finally:
        if agent is not None:
            try:
                agent.close()
            except Exception as exc:
                result.update(status="error", cleanup_error_type=type(exc).__name__)
        adapter._save("session-result.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "decide"))
    parser.add_argument("--url", default="http://127.0.0.1:8768")
    parser.add_argument("--turns", type=int, choices=range(1, 11), default=1)
    parser.add_argument("--task", default="Pick up the tennis ball.")
    parser.add_argument("--output", type=Path,
                        default=ROOT / "analysis" / ("gpt-session-" + uuid.uuid4().hex[:12]))
    args = parser.parse_args(argv)
    config = upstream_config()
    adapter = R5PolicyAdapter(ReadOnlyWorkbench(args.url), args.output, args.task)
    adapter._save("session-config.json", {
        "provider": "codex", "model": config.model, "effort": config.effort,
        "live_image_window": config.live_image_window, "turns": args.turns,
        "mode": args.mode, "execution_available": False,
        "physical_blockers": ["Powered pause/hold not validated or deployed",
                              "Fault/communication/power-loss fallback unresolved",
                              "No validated GPT physical execution backend"],
    })
    if args.mode == "preflight":
        observation = adapter.observe()
        result = {"status": "observation_ready" if observation["proposal_ready"] else "blocked",
                  "blockers": observation["blockers"], "executed": False,
                  "execution_available": False, "model_called": False}
        adapter._save("session-result.json", result)
    else:
        print("Sending both camera images and robot state to the configured Codex model; "
              "proposals only, no hardware execution.", file=sys.stderr, flush=True)
        result = run_decisions(adapter, lambda: new_agent(config), args.turns,
                               lambda value: print(json.dumps(value), flush=True))
    print(json.dumps({**result, "directory": str(adapter.directory)}), flush=True)
    return 0 if result["status"] in ("observation_ready", "shadow_decision") else 2


if __name__ == "__main__":
    sys.exit(main())
