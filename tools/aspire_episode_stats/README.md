# ASPIRE System 2 episode statistics

These Python 3 scripts recreate the episode table used in the ASPIRE simulation evaluation. They read existing files and work offline. The ARX real-robot accounting tool is [`collect_experiment_usage.py`](../collect_experiment_usage.py).

## Collect episode timing

Create a local `roster.json` with one entry per valid simulation episode. `trial` is a replicate number independent of the seed. `source` is the episode directory on the machine running the collector. It must contain `result.json` and `effective_config.json`. `episode.jsonl` supplies the native success tick and `system2-tools.jsonl` supplies observation timestamps. The tool trace must record `observation_seq` on the same tick scale as the physics log.

```json
[
  {"task": "L3-01", "trial": 1, "source": "/path/to/simulation/episode"}
]
```

```bash
python3 tools/aspire_episode_stats/collect.py roster.json > episodes.jsonl
```

Reference episodes contribute to the primary totals. Use `"reference": false` for a supplementary episode. For an externally reviewed success, record `"review_success": true` and the independently documented `"regrade_tick"`. The JSON retains the native result and the table marks a regrade with `TRUE*`.

## Assemble the table

```bash
python3 tools/aspire_episode_stats/assemble.py episodes.jsonl \
  --output episode_metrics.json > episode_table.md
```

Pass additional episode JSONL files as positional arguments if the collection was split between machines. To include model telemetry, provide both `--usage-sources usage_sources.json` and `--sessions /path/to/codex/sessions`. The mapping is a JSON array whose entries contain `task`, `trial`, and `session`. The optional fields `turn`, `start` and `end` (inclusive ISO 8601 UTC timestamps), and `scope` narrow or label the attribution. Each session must resolve to exactly one `rollout-*-<session>.jsonl` file. A row marked `†` uses an attributed window or another non-dedicated scope when a scope is supplied.

- **First frame to success** measures wall time between the first fresh public RGB observation and the first fresh public observation recorded at or after the passing tick. A missing passing observation is `null` in JSON and `N/A` in the table.
- **Completed responses** counts unique response IDs with a `token_usage_record`. Total model request attempts, including failed or incomplete requests, are unavailable from this source and remain `—`. Unmapped episodes have no usage totals.
- **Tokens** includes cached tokens in input and reported reasoning tokens in output.

Supply episode data, mappings and Codex rollout files locally. Keep these inputs and any generated reports containing local paths or session metadata out of version control.
