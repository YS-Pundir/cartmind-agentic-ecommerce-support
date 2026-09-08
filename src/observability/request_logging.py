"""
Structured request logging.

This is intentionally a separate module from src/logging_config.py (which
sets up your general application logging - e.g. the tenacity
`before_sleep_log(logger, ...)` retry warnings emitted in
src/agent/nodes.py). This file has one job: write exactly one JSON-Lines
entry per inbound API request, with a trace id and timing, to its own
log file/logger so it never mixes with retry/app logs and vice versa.

PII handling
------------
Whatever text is logged (request_text / response_text) is passed through
the *same* `mask_pii()` guardrail that src/agent/nodes.py already applies
to user input before it reaches the model (see classify_intent()). That
means any fixed-format PII field mask_pii knows how to mask never reaches
disk in the clear here - masking happens once, log and model see the same
masked value. If masking itself fails, we redact the whole field rather
than fall back to logging the raw text.

Usage
-----
    from src.observability.request_logging import log_request

    with log_request("/api/chat", thread_id=thread_id, request_text=req.message) as ctx:
        answer = run_agent(...)
        ctx["response_text"] = answer

One line is written when the `with` block exits, whether it raised or not.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Optional

from src.guardrails.pii import mask_pii

# ---------------------------------------------------------------------
# Where the JSONL file lives. Uses src/config.request_log_loc if you add
# one; otherwise falls back to ./logs/requests.jsonl next to wherever the
# process runs from.
# ---------------------------------------------------------------------
try:
    from src.config import request_log_loc as _REQUEST_LOG_FILE  # type: ignore
except ImportError:
    _REQUEST_LOG_FILE = Path("logs")/"agent_run"/"requests.jsonl"

_REQUEST_LOG_FILE = Path(_REQUEST_LOG_FILE)
_REQUEST_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# Dedicated logger, isolated from the root/app logger set up in
# src/logging_config.py, so retry warnings never land in this file and
# these request lines never land in the general app log.
_logger = logging.getLogger("request_audit")
_logger.setLevel(logging.INFO)
_logger.propagate = False

if not _logger.handlers:
    _handler = logging.FileHandler(_REQUEST_LOG_FILE, encoding="utf-8")
    # We build the full JSON line ourselves - the handler shouldn't add
    # its own timestamp/level prefix in front of it.
    _handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(_handler)


def _safe_mask(value: Optional[str]) -> Optional[str]:
    """Mask text the same way classify_intent() masks user input.

    A failure in the masking guardrail itself must never result in raw
    text being written to disk, so on error we redact entirely instead
    of falling back to the unmasked value.
    """
    if value is None:
        return None
    try:
        return mask_pii(value)
    except Exception:
        logging.getLogger(__name__).exception(
            "PII masking failed while writing request log entry"
        )
        return "<redacted:masking_failed>"


def new_trace_id() -> str:
    return uuid.uuid4().hex


@contextmanager
def log_request(
    endpoint: str,
    *,
    thread_id: Optional[str] = None,
    request_text: Optional[str] = None,
    trace_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
):
    """Context manager emitting exactly one JSON-Lines entry per request.

    Yields a mutable `ctx` dict. Set ctx["response_text"] before the block
    exits if you want the (masked) response logged too. If the block
    raises, status/error are recorded automatically and the exception is
    re-raised unchanged; if you catch and handle an error yourself inside
    the block (e.g. to return a JSONResponse), set ctx["status"] = "error"
    and ctx["error"] = "..." manually before returning.
    """
    trace_id = trace_id or new_trace_id()
    start = time.perf_counter()
    ctx: dict[str, Any] = {"response_text": None, "status": "ok", "error": None}
    try:
        yield ctx
    except Exception as exc:
        ctx["status"] = "error"
        ctx["error"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        entry = {
            "trace_id": trace_id,
            "endpoint": endpoint,
            "thread_id": thread_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "duration_ms": duration_ms,
            "status": ctx["status"],
            "request_text": _safe_mask(request_text),
            "response_text": _safe_mask(ctx["response_text"]),
        }
        if ctx["error"]:
            entry["error"] = ctx["error"]
        if extra:
            entry.update(extra)
        _logger.info(json.dumps(entry, ensure_ascii=False))
