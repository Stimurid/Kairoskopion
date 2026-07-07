"""Per-session LLM call logging with FIFO rotation.

Each API session (login→logout or server restart) gets its own log file.
Logs are JSONL: one JSON object per LLM call with request/response/timing.
FIFO rotation keeps the last N session files (default 50).

Log directory: {data_dir}/logs/llm_sessions/
File naming: {timestamp}_{session_id}.jsonl
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MAX_SESSION_FILES = 50
_LOG_DIR_ENV = "KAIROSKOPION_LOG_DIR"
_DATA_DIR_ENV = "KAIROSKOPION_DATA_DIR"


def _default_log_dir() -> Path:
    log_dir = os.environ.get(_LOG_DIR_ENV)
    if log_dir:
        return Path(log_dir) / "llm_sessions"
    data_dir = os.environ.get(_DATA_DIR_ENV, ".kairoskopion")
    return Path(data_dir) / "logs" / "llm_sessions"


def _rotate_fifo(log_dir: Path, max_files: int = MAX_SESSION_FILES) -> int:
    """Delete oldest session log files to keep at most max_files. Returns count deleted."""
    if not log_dir.is_dir():
        return 0
    files = sorted(log_dir.glob("*.jsonl"), key=lambda f: f.stat().st_mtime)
    to_delete = max(0, len(files) - max_files)
    deleted = 0
    for f in files[:to_delete]:
        try:
            f.unlink()
            deleted += 1
        except OSError:
            pass
    return deleted


class LLMSessionLog:
    """Append-only JSONL log for one session's LLM calls."""

    def __init__(
        self,
        session_id: str = "default",
        log_dir: Path | None = None,
        max_files: int = MAX_SESSION_FILES,
    ) -> None:
        self._session_id = session_id
        self._log_dir = log_dir or _default_log_dir()
        self._max_files = max_files
        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._path = self._log_dir / f"{ts}_{session_id}.jsonl"
        _rotate_fifo(self._log_dir, self._max_files)

    @property
    def path(self) -> Path:
        return self._path

    def log_call(
        self,
        *,
        agent_role: str = "",
        model: str = "",
        messages_preview: str = "",
        response_preview: str = "",
        latency_ms: float = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        parse_status: str = "",
        error_code: str = "",
        error_message: str = "",
        fallback_model: str = "",
        attempt: int = 1,
        extra: dict[str, Any] | None = None,
    ) -> None:
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "session": self._session_id,
            "agent_role": agent_role,
            "model": model,
            "latency_ms": round(latency_ms, 1),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "parse_status": parse_status,
            "attempt": attempt,
        }
        if messages_preview:
            record["messages_preview"] = messages_preview[:500]
        if response_preview:
            record["response_preview"] = response_preview[:500]
        if error_code:
            record["error_code"] = error_code
        if error_message:
            record["error_message"] = error_message[:300]
        if fallback_model:
            record["fallback_model"] = fallback_model
        if extra:
            record["extra"] = extra
        try:
            with open(self._path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError as e:
            logger.warning("Failed to write LLM session log: %s", e)

    def log_error(
        self,
        *,
        agent_role: str = "",
        model: str = "",
        error_code: str,
        error_message: str,
        attempt: int = 1,
        latency_ms: float = 0,
    ) -> None:
        self.log_call(
            agent_role=agent_role,
            model=model,
            error_code=error_code,
            error_message=error_message,
            attempt=attempt,
            latency_ms=latency_ms,
            parse_status="error",
        )


# Global session log — initialized on first access.
_global_log: LLMSessionLog | None = None


def get_session_log(session_id: str = "api") -> LLMSessionLog:
    global _global_log
    if _global_log is None:
        _global_log = LLMSessionLog(session_id=session_id)
    return _global_log


def reset_session_log(session_id: str = "api") -> LLMSessionLog:
    """Start a new session log (e.g. on server restart)."""
    global _global_log
    _global_log = LLMSessionLog(session_id=session_id)
    return _global_log
