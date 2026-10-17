#!/usr/bin/env python3
"""Offline Codex usage and ARX command accounting. Never connects to hardware."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path


TOKEN_FIELDS = (
    'input_tokens', 'cached_input_tokens', 'cache_write_input_tokens',
    'output_tokens', 'reasoning_output_tokens', 'total_tokens',
)
NOTES = [
    'Window is inclusive and selected by record timestamp, not request start time.',
    'Model responses are local token_usage_record entries deduplicated by response_id; '
    'this is not a verified count of server requests or billed attempts.',
    'Top-level tool calls are deduplicated by call_id (or id). Nested calls inside '
    'functions.exec are not inferred from code and remain unknown.',
    'Robot requests, host commands, model responses and tool calls overlap; do not add them.',
    'Cached input is part of input; reasoning output is part of output. '
    'Repeated context is counted on every request.',
    'Noncached input includes cache writes; ordinary input excludes both reads and writes.',
    'Cumulative token_count snapshots are not summed or substituted for per-response usage.',
    'Missing usage fields remain null. Missing usage records do not prove zero model requests.',
    'Host durations include planning, execution, settling and capture; '
    'they are not pure motion or model inference time.',
    'No message text, internal reasoning, tool arguments, tool outputs or credentials are exported.',
]


def timestamp(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return datetime.fromtimestamp(value, timezone.utc)
    parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        raise ValueError('Timestamps must include a timezone')
    return parsed.astimezone(timezone.utc)


def iso(value):
    return value.isoformat().replace('+00:00', 'Z')


def read_jsonl(path, diagnostics, label):
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise ValueError('Expected object')
            except (ValueError, TypeError):
                diagnostics[label + '_invalid_json_lines'] += 1
                continue
            yield event


def number(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def normalize_usage(usage):
    """Accept flat Codex fields and nested Responses API usage field names."""
    details = usage.get('input_tokens_details') or {}
    output_details = usage.get('output_tokens_details') or {}
    result = {key: number(usage.get(key)) for key in TOKEN_FIELDS}
    for name, nested, key in (
        ('cached_input_tokens', details, 'cached_tokens'),
        ('cache_write_input_tokens', details, 'cache_write_tokens'),
        ('reasoning_output_tokens', output_details, 'reasoning_tokens'),
    ):
        if result[name] is None:
            result[name] = number(nested.get(key))
    inp, out, total = (result[k] for k in ('input_tokens', 'output_tokens', 'total_tokens'))
    if inp is not None and out is not None:
        if total is None:
            result['total_tokens'] = inp + out
        elif total != inp + out:
            raise ValueError('Usage total does not equal input plus output')
    cached, written = result['cached_input_tokens'], result['cache_write_input_tokens']
    reasoning = result['reasoning_output_tokens']
    if inp is not None and cached is not None and cached > inp:
        raise ValueError('Cached input exceeds input')
    if inp is not None and written is not None and written + (cached or 0) > inp:
        raise ValueError('Cache reads plus writes exceed input')
    if out is not None and reasoning is not None and reasoning > out:
        raise ValueError('Reasoning tokens exceed output')
    return result


def remember(rows, key, row, compared_fields, diagnostics, label):
    if not key:
        diagnostics[label + '_missing_id'] += 1
        return
    if key in rows:
        if any(rows[key][field] != row[field] for field in compared_fields):
            raise ValueError('Conflicting duplicate ' + label + ' ID; reconcile the source records')
        diagnostics[label + '_duplicate_records'] += 1
        return
    rows[key] = row


def collect(session_logs, start, end, robot_events=None, task_end=None):
    start, end = timestamp(start), timestamp(end)
    task_end = timestamp(task_end) if task_end is not None else None
    if end < start or (task_end is not None and not start <= task_end <= end):
        raise ValueError('Invalid execution window or task-end boundary')
    responses, calls, diagnostics = {}, {}, Counter()
    for path in session_logs:
        for event in read_jsonl(path, diagnostics, 'session'):
            try:
                at = timestamp(event['timestamp'])
            except (KeyError, ValueError, TypeError, OverflowError):
                diagnostics['session_invalid_timestamps'] += 1
                continue
            if not start <= at <= end:
                continue
            payload = event.get('payload') or {}
            if not isinstance(payload, dict):
                diagnostics['session_invalid_payloads'] += 1
                continue
            kind, subtype = event.get('type'), payload.get('type')
            if kind == 'token_usage_record':
                if not isinstance(payload.get('usage'), dict):
                    diagnostics['response_missing_usage'] += 1
                    continue
                row = {'timestamp': iso(at), 'response_id': payload.get('response_id'),
                       'usage': normalize_usage(payload['usage'])}
                remember(responses, row['response_id'], row, ['usage'], diagnostics, 'response')
            if kind == 'response_item' and subtype in ('function_call', 'custom_tool_call'):
                key = payload.get('call_id') or payload.get('id')
                row = {'timestamp': iso(at), 'call_id': key,
                       'name': payload.get('name'), 'type': subtype}
                remember(calls, key, row, ['name', 'type'], diagnostics, 'tool_call')
            if subtype == 'token_count':
                diagnostics['cumulative_snapshots_ignored'] += 1

    totals = {}
    missing = {}
    for field in TOKEN_FIELDS:
        values = [r['usage'][field] for r in responses.values()]
        missing[field] = sum(v is None for v in values)
        totals[field] = sum(values) if values and not missing[field] else None
    inp, cached, written = (totals[k] for k in
                            ('input_tokens', 'cached_input_tokens', 'cache_write_input_tokens'))
    totals['uncached_input_tokens'] = inp - cached if inp is not None and cached is not None else None
    totals['ordinary_input_tokens'] = (inp - cached - written
                                      if all(v is not None for v in (inp, cached, written)) else None)
    robot = None
    if robot_events is not None:
        requests, host, outcomes = Counter(), Counter(), Counter()
        request_count = internal_targets = task_count = after_task_count = 0
        host_duration = 0.0
        host_durations_complete = True
        for event in read_jsonl(robot_events, diagnostics, 'robot'):
            try:
                at = timestamp(event.get('at_s', event.get('timestamp')))
            except (ValueError, TypeError, OverflowError):
                diagnostics['robot_invalid_timestamps'] += 1
                continue
            if not start <= at <= end:
                continue
            kind = event.get('event')
            if kind == 'request':
                request_count += 1
                requests[str(event.get('tool', 'unknown'))] += 1
                if task_end is not None:
                    if at <= task_end:
                        task_count += 1
                    else:
                        after_task_count += 1
            elif kind == 'review_command_finished':
                host[str(event.get('command', 'unknown'))] += 1
                outcomes[str(event.get('outcome', 'unknown'))] += 1
                duration = event.get('command_wall_s')
                if isinstance(duration, (int, float)) and not isinstance(duration, bool) and duration >= 0:
                    host_duration += duration
                else:
                    host_durations_complete = False
            elif kind == 'gripper_preparation_target':
                internal_targets += 1
        robot = {
            'json_requests': request_count, 'json_requests_by_tool': dict(requests),
            'task_json_requests': task_count if task_end else None,
            'after_task_json_requests': after_task_count if task_end else None,
            'host_finished_commands': sum(host.values()), 'host_commands_by_name': dict(host),
            'host_outcomes': dict(outcomes),
            'host_command_wall_s': host_duration if host_durations_complete else None,
            'empty_gripper_internal_targets': internal_targets,
        }
    summary = {
        'schema_version': 1, 'window_start_utc': iso(start), 'window_end_utc': iso(end),
        'task_end_utc': iso(task_end) if task_end else None,
        'wall_elapsed_s': (end-start).total_seconds(),
        'unique_model_response_records': len(responses),
        'top_level_tool_calls': len(calls),
        'tool_calls_by_name': dict(Counter(str(r['name']) for r in calls.values())),
        'nested_tool_calls': None, 'token_totals': totals,
        'missing_usage_fields_by_record': missing, 'diagnostics': dict(diagnostics),
        'robot': robot, 'pure_server_inference_s': None, 'server_ttft_s': None,
        'model_generation_tokens_per_s': None, 'actual_billed_cost': None,
        'notes': NOTES,
    }
    return summary, list(responses.values()), list(calls.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-log', type=Path, action='append', required=True,
                        help='Codex rollout JSONL; repeat for multiple session files')
    parser.add_argument('--start', required=True, help='Inclusive ISO 8601 timestamp with timezone')
    parser.add_argument('--end', required=True, help='Inclusive ISO 8601 timestamp with timezone')
    parser.add_argument('--robot-events', type=Path, help='Optional single ARX events.jsonl file')
    parser.add_argument('--task-end', help='Optional boundary separating task from subsequent cleanup')
    parser.add_argument('--output', type=Path, required=True, help='Directory for new summary files')
    args = parser.parse_args()
    targets = [args.output / n for n in ('USAGE_SUMMARY.json', 'response_usage.jsonl', 'tool_calls.jsonl')]
    if any(p.exists() for p in targets):
        parser.error('Output files already exist; choose a new directory to preserve frozen records')
    try:
        summary, responses, calls = collect(args.session_log, args.start, args.end,
                                            args.robot_events, args.task_end)
    except (ValueError, OSError) as exc:
        parser.error(str(exc))
    args.output.mkdir(parents=True, exist_ok=True)
    targets[0].write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    for path, rows in zip(targets[1:], (responses, calls)):
        path.write_text(''.join(json.dumps(r, ensure_ascii=False)+'\n' for r in rows), encoding='utf-8')
    print(json.dumps({'summary': str(targets[0]),
                      'responses': summary['unique_model_response_records'],
                      'top_level_tool_calls': summary['top_level_tool_calls'],
                      'token_totals': summary['token_totals']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
