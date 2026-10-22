"""
app/core/logging_config.py

Configures Python's standard logging module for the whole app — called
once at startup (app/main.py). Deliberately plain key=value formatting to
stdout rather than a logging framework/library: this is a single-process
FastAPI app, not a distributed system, and stdout is what Docker/any
container platform already captures without extra configuration.

Log points are added where they carry real operational signal — a routing
decision, a hallucinated citation, ingestion volume, an upstream failure —
not blanket "entering function X" noise that just adds volume without
adding anything a reader could act on.
"""

from __future__ import annotations

import logging

from app.core.config import settings


def configure_logging() -> None:
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s level=%(levelname)s logger=%(name)s msg=%(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        # basicConfig() is a no-op if the root logger already has handlers
        # (e.g. pytest, uvicorn, or a prior call already configured it) —
        # force=True makes this call actually take effect every time,
        # rather than the log level silently failing to apply.
        force=True,
    )
    # Quiet down noisy third-party loggers unless we're actually debugging
    # at DEBUG level — httpx logs every request at INFO by default, which
    # would drown out the app's own log lines otherwise.
    if level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
