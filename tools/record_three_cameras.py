#!/usr/bin/env python3
"""Read-only trial video recording through the running workbench HTTP proxy.

No robot commands, control ownership, camera device opens or service restarts.
Stop with SIGINT/SIGTERM or by creating OUTPUT/STOP. See THREE_CAMERA_RECORDING.md.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import signal
import sys
import threading
import time

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from visual_control import WorkbenchClient

VIEWS = {'top': 'external', 'left': 'gemini', 'right': 'gemini_right'}


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).astimezone().isoformat()


def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
    temporary.replace(path)


def fetch(base, key):
    jpeg, sequence, device = WorkbenchClient(base).camera(key)
    received = time.time()
    frame = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR)
    if frame is None or not sequence or not device:
        raise RuntimeError('Missing image or camera identity')
    return frame, sequence, device, received


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='New trial recording directory')
    parser.add_argument('--base', default='http://127.0.0.1:8768')
    parser.add_argument('--fps', type=int, default=10, choices=range(1, 16))
    parser.add_argument('--segment-seconds', type=int, default=60)
    parser.add_argument('--duration', type=float, help='Optional finite duration in seconds')
    parser.add_argument('--format', choices=('avi', 'mp4'), default='avi',
                        help='AVI/MJPEG or MP4/MPEG-4 Part 2; default preserves existing recordings')
    args = parser.parse_args()
    codec = 'mp4v' if args.format == 'mp4' else 'MJPG'
    if args.segment_seconds < 1 or (args.duration is not None and args.duration <= 0):
        parser.error('Durations must be positive')
    # Prevent accidental duplicate recorders. This lock is unrelated to robot ownership.
    lock_path = Path(__file__).resolve().parents[1] / 'analysis/.three_camera_recording.lock'
    lock_path.parent.mkdir(exist_ok=True)
    lock = lock_path.open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('A three-camera recorder is already running')
    args.output.mkdir(parents=True, exist_ok=False)
    stop = threading.Event()
    reason = ['duration_completed' if args.duration else 'stop_requested']

    def halt(signum, _frame):
        reason[0] = signal.Signals(signum).name
        stop.set()

    signal.signal(signal.SIGINT, halt)
    signal.signal(signal.SIGTERM, halt)
    manifest = {
        'schema_version': 1, 'status': 'starting', 'pid': os.getpid(),
        'base': args.base, 'fps': args.fps, 'segment_seconds': args.segment_seconds,
        'started_at': None, 'ended_at': None, 'views': VIEWS,
        'codec': codec, 'container': args.format.upper(), 'read_only': True,
        'timing_note': 'Shared monotonic sampling grid; HTTP receive timestamps, not hardware exposure synchronization. Missing slots are black frames; duplicate source frames are labeled.',
    }
    atomic_json(args.output / 'manifest.json', manifest)
    stats = {}
    guard = threading.Lock()
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {view: pool.submit(fetch, args.base, key) for view, key in VIEWS.items()}
            initial = {view: future.result() for view, future in futures.items()}
        devices = [v[2] for v in initial.values()]
        if len(set(devices)) != 3:
            raise RuntimeError('Three views do not resolve to three distinct devices')
        origin_mono, origin_wall = time.monotonic(), time.time()
        manifest.update(started_at=iso(origin_wall), started_at_unix_s=origin_wall,
                        status='recording', camera_devices=dict(zip(initial, devices)))

        def worker(view, key):
            writer = None
            try:
                source, _, device, _ = initial[view]
                height, width = source.shape[:2]
                previous = None
                index = 0
                segment_frames = args.fps * args.segment_seconds
                counts = dict(frames=0, fresh_frames=0, duplicate_frames=0,
                              missing_frames=0, request_errors=0, last_error=None,
                              width=width, height=height, last_frame_at=None)
                with (args.output / f'{view}_frames.jsonl').open('x', buffering=1) as timeline:
                    while not stop.is_set():
                        scheduled = index / args.fps
                        if args.duration is not None and scheduled >= args.duration:
                            break
                        if stop.wait(max(0, origin_mono + scheduled - time.monotonic())):
                            break
                        row = dict(index=index, scheduled_unix_s=origin_wall + scheduled,
                                   segment=index // segment_frames, segment_frame=index % segment_frames)
                        frame = None
                        error = None
                        if time.monotonic() - (origin_mono + scheduled) >= 1 / args.fps:
                            error = 'missed_sampling_slot'
                        else:
                            try:
                                frame, seq, current_device, received = fetch(args.base, key)
                                if current_device != device or frame.shape[:2] != (height, width):
                                    raise RuntimeError('Camera device or resolution changed')
                                row.update(received_unix_s=received, sequence=seq, device=current_device)
                                row['status'] = 'duplicate' if seq == previous else 'fresh'
                                previous = seq
                                counts['duplicate_frames' if row['status'] == 'duplicate' else 'fresh_frames'] += 1
                            except Exception as exc:
                                error = str(exc)
                                counts['request_errors'] += 1
                        if error:
                            frame = np.zeros((height, width, 3), dtype=np.uint8)
                            row.update(status='missing', error=error)
                            counts['missing_frames'] += 1
                            counts['last_error'] = error
                        canvas = cv2.copyMakeBorder(frame, 0, 32, 0, 0, cv2.BORDER_CONSTANT)
                        label = f'{view} {iso(origin_wall + scheduled)} #{index} {row["status"]}'
                        cv2.putText(canvas, label, (8, height + 22), cv2.FONT_HERSHEY_SIMPLEX,
                                    .45, (255, 255, 255), 1, cv2.LINE_AA)
                        if index % segment_frames == 0:
                            if writer is not None:
                                writer.release()
                            path = args.output / f'{view}_{row["segment"]:04d}.{args.format}'
                            writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*codec),
                                                     args.fps, (width, height + 32))
                            if not writer.isOpened():
                                raise RuntimeError(f'Cannot open video writer {path}')
                        writer.write(canvas)
                        timeline.write(json.dumps(row) + '\n')
                        counts['frames'] += 1
                        counts['last_frame_at'] = iso(time.time())
                        with guard:
                            stats[view] = counts.copy()
                        index += 1
            except Exception as exc:
                with guard:
                    stats.setdefault(view, {})['fatal_error'] = str(exc)
                reason[0] = 'recorder_error'
                stop.set()
            finally:
                if writer is not None:
                    writer.release()

        threads = [threading.Thread(target=worker, args=(v, k), name=v) for v, k in VIEWS.items()]
        for thread in threads:
            thread.start()
        while any(thread.is_alive() for thread in threads):
            if (args.output / 'STOP').exists():
                reason[0] = 'stop_file'
                stop.set()
            with guard:
                manifest['statistics'] = {v: s.copy() for v, s in stats.items()}
            manifest['heartbeat_at'] = iso(time.time())
            atomic_json(args.output / 'manifest.json', manifest)
            time.sleep(.2)
        for thread in threads:
            thread.join()
        manifest.update(status='failed' if reason[0] == 'recorder_error' else 'completed',
                        stop_reason=reason[0], statistics=stats,
                        elapsed_s=time.monotonic() - origin_mono)
    except Exception as exc:
        manifest.update(status='failed', error=str(exc))
    finally:
        manifest['ended_at'] = iso(time.time())
        atomic_json(args.output / 'manifest.json', manifest)
        print(json.dumps(manifest, ensure_ascii=False), flush=True)
    return 1 if manifest['status'] == 'failed' else 0


if __name__ == '__main__':
    raise SystemExit(main())
