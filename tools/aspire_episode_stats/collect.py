"""Collect ASPIRE System 2 episode timing as JSON Lines."""

import argparse
import json
from pathlib import Path
import re


def records(path):
    if path.is_file():
        with path.open(encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)


def collect(entry):
    path = Path(entry['source'])
    result_path = path / 'result.json'
    result = json.loads(result_path.read_text(encoding='utf-8'))
    if result['task_id'] != entry['task'] or result['evaluation_validity'] != 'valid':
        raise ValueError(f'Task mismatch or invalid evaluation: {result_path}')
    config = json.loads((path / 'effective_config.json').read_text(encoding='utf-8'))
    seed = config['runtime']['seed']
    tick = entry.get('regrade_tick')
    reviewed = entry.get('review_success', result['success'])
    if reviewed != result['success'] and not (reviewed and tick is not None):
        raise ValueError(f'Reviewed outcome differs from native scoring without a regrade tick: {path}')
    if tick is None and result['success']:
        tick = next((row['tick'] for row in records(path / 'episode.jsonl')
                     if row.get('event') == 'physics'
                     and row.get('evaluation', {}).get('status') == 'succeeded'), None)
        if tick is None:
            raise ValueError(f'Native success has no matching physics event: {path}')

    snapshots = []
    for row in records(path / 'system2-tools.jsonl'):
        reply = row.get('result', {})
        obs = reply.get('observation') or {}
        when, seq = obs.get('timestamp_s'), obs.get('observation_seq')
        if (reply.get('image_cameras') and not obs.get('stale') and
                isinstance(when, (int, float)) and when > 1e9 and isinstance(seq, int)):
            snapshots.append((seq, when, row['tool']))
    first = snapshots[0] if snapshots else None
    hit = (next((s for s in snapshots if s[0] >= tick and s[1] >= first[1]), None)
           if tick is not None and first else None)
    elapsed = hit[1] - first[1] if hit else None
    if elapsed is not None and not 0 < elapsed <= result['wall_time_s'] + 1:
        raise ValueError(f'First-frame timing falls outside the episode: {path}')

    files = sorted(p.name for p in path.iterdir() if p.is_file() and
                   re.search('usage|telemetry|controller|actor|manifest', p.name))
    return {
        **entry, 'seed': seed, 'review_success': reviewed, 'reference': entry.get('reference', True),
        'native_result_success': result['success'], 'wall_time_s': result['wall_time_s'],
        'first_frame_to_success_s': elapsed, 'native_first_success_tick': tick,
        'first_frame': first, 'first_success_frame': hit, 'decisions': result.get('decisions'),
        'score_status': result['assessment']['status'], 'sim_time_s': result.get('simulation_time_s'),
        'model_stats_file_candidates': files, 'termination_reason': result.get('termination_reason'),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('roster', type=Path, help='JSON array of episode directories and metadata')
    args = parser.parse_args()
    for entry in json.loads(args.roster.read_text(encoding='utf-8')):
        print(json.dumps(collect(entry), ensure_ascii=False, allow_nan=False))


if __name__ == '__main__':
    main()
