"""
app/evaluation/timing.py

Minimal stage-latency tracker. Not a profiler — just wall-clock timing per
named stage (routing, retrieval, rerank, generation), accumulated into a
dict, so an eval run can report where time actually goes. Kept as a plain
context manager rather than a decorator so it works equally well wrapping
a single line or a multi-line block, and doesn't require the timed code to
be its own function.
"""

from __future__ import annotations

import time
from contextlib import contextmanager


class StageTimer:
    def __init__(self):
        self.timings_ms: dict[str, float] = {}

    @contextmanager
    def track(self, stage_name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            # Accumulate rather than overwrite — a stage name might be
            # entered more than once (e.g. "retrieval" across a loop), and
            # silently dropping earlier time would understate real cost.
            self.timings_ms[stage_name] = self.timings_ms.get(stage_name, 0.0) + elapsed_ms

    @property
    def total_ms(self) -> float:
        return sum(self.timings_ms.values())
