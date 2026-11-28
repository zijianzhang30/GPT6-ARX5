#!/usr/bin/env python3
"""Copy the three Workbench journals for one ASPIRE review run."""

import argparse
import json
import math
from pathlib import Path
import subprocess


WORKBENCH_UNITS = ('arx5-record-workbench.service', 'arx5-left-workbench.service',
                   'arx5-right-workbench.service')


def collect(run):
    with (run/'events.jsonl').open(encoding='utf-8') as stream:
        first = json.loads(next(stream, '{}'))
        if first.get('event') != 'review_session_started':
            raise ValueError('Expected an ASPIRE run with a review_session_started event')
        last = first
        for line in stream:
            try:
                last = json.loads(line)
            except json.JSONDecodeError:
                if line.endswith('\n'):
                    raise
                break  # The review host may have been stopped mid-write.
    since = math.floor(first['at_s'])
    until = math.ceil(last['at_s'])
    command = ['journalctl', '--user', '--no-pager', '--output=short-iso-precise',
               f'--since=@{since}', f'--until=@{until}']
    for unit in WORKBENCH_UNITS:
        command.extend(('--unit', unit))
    journal = subprocess.run(command, capture_output=True, check=True, timeout=30).stdout
    destination = run/'workbench-journal.log'
    temporary = run/'workbench-journal.tmp'
    temporary.write_bytes(journal)
    temporary.replace(destination)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path, help='Directory containing this run’s events.jsonl')
    args = parser.parse_args()
    try:
        print(collect(args.run.resolve()))
    except (OSError, KeyError, ValueError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()
