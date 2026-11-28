"""Opt-in monotonic timing for the local Workbench request path."""

from contextlib import contextmanager
from contextvars import ContextVar
import logging
import os
import re
import time
from uuid import uuid4


STAGE_TIMING_ENABLED = os.getenv('R5_WORKBENCH_STAGE_TIMING') == '1'
SLOW_REQUEST_S = .05
LOGGER = logging.getLogger('r5.workbench.timing')
TRACE_HEADER = 'X-R5-Workbench-Trace'
TRACE_ID = ContextVar('workbench_trace_id', default=None)


def new_trace_id():
    return uuid4().hex if STAGE_TIMING_ENABLED else None


def valid_trace_id(trace_id):
    return trace_id if trace_id and re.fullmatch(r'[0-9a-f]{32}', trace_id) else None


def trace_headers():
    trace_id = TRACE_ID.get()
    return {TRACE_HEADER: trace_id} if trace_id else {}


@contextmanager
def trace_request(trace_id):
    token = TRACE_ID.set(valid_trace_id(trace_id))
    try:
        yield
    finally:
        TRACE_ID.reset(token)


@contextmanager
def time_stage(timings, stage):
    if timings is None:
        yield
        return
    started = time.monotonic()
    try:
        yield
    finally:
        timings[stage] = round((time.monotonic() - started) * 1000, 2)


@contextmanager
def log_stages(operation, enabled=True):
    if not (STAGE_TIMING_ENABLED and enabled):
        yield None
        return
    timings = {}
    started = time.monotonic()
    completed = False
    try:
        yield timings
        completed = True
    finally:
        elapsed = time.monotonic() - started
        if elapsed >= SLOW_REQUEST_S or not completed:
            LOGGER.warning('R5 timing %s trace_id=%s start_mono=%.6f total_ms=%.2f completed=%s stages_ms=%s',
                           operation, TRACE_ID.get(), started, elapsed * 1000, completed, timings)
