"""Assemble ASPIRE episode metrics and attributed Codex response usage."""

import argparse
from datetime import datetime
import json
from pathlib import Path


TASK_NAMES = {'L1-03': '挂帽', 'L2-01': '双臂拔笔帽', 'L2-02': '抽中间的书',
              'L2-06': '夹取果冻', 'L3-01': '拧瓶盖', 'L3-02': '拧螺母',
              'L3-03': '推转叠书', 'L3-04': '扫三个方块'}


def records(path):
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            yield json.loads(line)


def stamp(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def model_usage(directory, source):
    paths = list(directory.rglob(f"rollout-*-{source['session']}.jsonl"))
    if len(paths) != 1:
        raise ValueError(f"Expected one rollout for session {source['session']}, found {len(paths)}")
    window = (stamp(source['start']), stamp(source['end'])) if source.get('start') else None
    responses = {}
    for row in records(paths[0]):
        if row['type'] != 'token_usage_record':
            continue
        payload = row['payload']
        if source.get('turn') and payload.get('turn_id') != source['turn']:
            continue
        if window and not window[0] <= stamp(row['timestamp']) <= window[1]:
            continue
        identity, usage = payload['response_id'], payload['usage']
        if not identity or (identity in responses and responses[identity] != usage):
            raise ValueError('Invalid or conflicting model response usage record')
        responses[identity] = usage
    if not responses:
        raise ValueError(f"No matching model responses for session {source['session']}")
    return {
        'completed_responses_observed': len(responses),
        'input_tokens': sum(v['input_tokens'] for v in responses.values()),
        'output_tokens': sum(v['output_tokens'] for v in responses.values()),
        'cached_input_tokens': sum(v.get('cached_input_tokens') or 0 for v in responses.values()),
        'model_usage_source': source,
    }


def episode_key(row):
    return row['task'], row['trial']


def assemble(paths, output, *, usage_sources=None, sessions=None):
    rows = [row for path in paths for row in records(path)]
    keys = {episode_key(row) for row in rows}
    if not rows or len(keys) != len(rows):
        raise ValueError('Expected at least one episode and unique (task, trial) pairs')
    usage = {}
    if usage_sources is not None:
        for source in json.loads(usage_sources.read_text(encoding='utf-8')):
            key = episode_key(source)
            if key in usage or key not in keys:
                raise ValueError(f'Duplicate usage source or no matching episode: {key}')
            usage[key] = model_usage(sessions, source)

    for row in rows:
        row.setdefault('regrade_tick', None)
        row.update(task_name=TASK_NAMES.get(row['task'], row['task']), model_requests=None,
                   completed_responses_observed=None, input_tokens=None, output_tokens=None)
        row.update(usage.get(episode_key(row), {}))
    rows.sort(key=episode_key)
    result = {'definition': {
        'scope': 'Episodes listed in the supplied JSON Lines files. Reference episodes contribute to the primary totals.',
        'trial': 'Replicate index, separate from the runtime seed.',
        'wall_time_s': 'Native result.json wall clock including waiting for archive.',
        'first_frame_to_success_s': 'First public RGB observation to the first public observation at or after the native or explicitly reviewed passing tick.',
        'completed_responses_observed': 'Unique response IDs with token_usage_record. Total provider attempts are unavailable.',
        'controller_window': 'An attributed controller interval that may exclude setup and closing activity.',
        'token_scope': 'Input includes cached tokens. Output includes reported reasoning tokens. Missing usage stays missing.',
    }, 'primary_success': sum(row['review_success'] and row['reference'] for row in rows),
       'primary_episodes': sum(row['reference'] for row in rows), 'episodes': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
    print_table(rows)


def print_table(rows):
    print('| Episode | 任务 | 原生成功 | 墙钟耗时(s) | 首帧到达标(s) | 模型调用 | 完成生成 | 输入 token | 输出 token |')
    print('|---|---|---:|---:|---:|---:|---:|---:|---:|')
    for row in rows:
        scope = (row.get('model_usage_source') or {}).get('scope', '')
        tag = '†' if scope and scope != 'dedicated_actor_turn' else ''
        fields = ['—' if row[k] is None else f'{row[k]:,}{tag}'
                  for k in ('completed_responses_observed', 'input_tokens', 'output_tokens')]
        success = 'TRUE*' if row['regrade_tick'] is not None else 'TRUE' if row['review_success'] else 'FALSE'
        elapsed = row['first_frame_to_success_s']
        elapsed_label = f'{elapsed:.3f}' if elapsed is not None else 'N/A'
        label = f"{row['task']}_seed{row['seed']}_r{row['trial']}"
        values = [label, row['task_name'], success, f"{row['wall_time_s']:.3f}", elapsed_label, '—', *fields]
        print('| ' + ' | '.join(values) + ' |')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('episodes', type=Path, nargs='+', help='One or more outputs from collect.py')
    parser.add_argument('--output', type=Path, required=True, help='Destination metrics JSON')
    parser.add_argument('--usage-sources', type=Path, help='Optional JSON array of episode-to-rollout mappings')
    parser.add_argument('--sessions', type=Path, help='Directory containing Codex rollout JSONL files')
    args = parser.parse_args()
    if args.usage_sources and (not args.sessions or not args.sessions.is_dir()):
        parser.error('--usage-sources requires a valid --sessions directory')
    assemble(args.episodes, args.output, usage_sources=args.usage_sources, sessions=args.sessions)


if __name__ == '__main__':
    main()
