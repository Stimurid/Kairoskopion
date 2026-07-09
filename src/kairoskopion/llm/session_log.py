"""Provider diagnostic log — per-process JSONL for operator debugging.

Each backend process (API server lifecycle, CLI invocation, test run)
gets its own log file. Logs are JSONL: one JSON object per provider
attempt with request/response/timing. This is NOT the authoritative
PipelineRun trace — it supplements the agent-layer LLMAttemptMetadata.

FIFO rotation keeps the last N process files (default 50).
Size rotation caps individual files (default 10 MB).

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

MAX_PROCESS_FILES = 50
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
_LOG_DIR_ENV = "KAIROSKOPION_LOG_DIR"
_DATA_DIR_ENV = "KAIROSKOPION_DATA_DIR"
_MAX_FILES_ENV = "KAIROSKOPION_LLM_LOG_MAX_FILES"
_MAX_BYTES_ENV = "KAIROSKOPION_LLM_LOG_MAX_BYTES"


def _default_log_dir() -> Path:
    log_dir = os.environ.get(_LOG_DIR_ENV)
    if log_dir:
        return Path(log_dir) / "llm_sessions"
    data_dir = os.environ.get(_DATA_DIR_ENV, ".kairoskopion")
    return Path(data_dir) / "logs" / "llm_sessions"


def _rotate_fifo(log_dir: Path, max_files: int = MAX_PROCESS_FILES) -> int:
    """Delete oldest process log files to keep at most max_files. Returns count deleted."""
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
    """Append-only JSONL provider diagnostic log for one process.

    Terminology: "session" here means one backend process lifecycle,
    NOT a user session, login session, or PipelineRun.
    """

    def __init__(
        self,
        session_id: str = "default",
        log_dir: Path | None = None,
        max_files: int | None = None,
        max_bytes: int | None = None,
    ) -> None:
        self._session_id = session_id
        self._log_dir = log_dir or _default_log_dir()

        if max_files is None:
            env_mf = os.environ.get(_MAX_FILES_ENV, "")
            self._max_files = int(env_mf) if env_mf.isdigit() else MAX_PROCESS_FILES
        else:
            self._max_files = max_files

        if max_bytes is None:
            env_mb = os.environ.get(_MAX_BYTES_ENV, "")
            self._max_bytes = int(env_mb) if env_mb.isdigit() else DEFAULT_MAX_BYTES
        else:
            self._max_bytes = max_bytes

        self._log_dir.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        self._path = self._log_dir / f"{ts}_{session_id}.jsonl"
        self._file_index = 0
        _rotate_fifo(self._log_dir, self._max_files)

    @property
    def path(self) -> Path:
        return self._path

    @property
    def max_bytes(self) -> int:
        return self._max_bytes

    def _rotate_if_needed(self) -> None:
        """Rotate to a new file if current file exceeds max_bytes."""
        if self._max_bytes <= 0:
            return
        try:
            if self._path.exists() and self._path.stat().st_size >= self._max_bytes:
                self._file_index += 1
                ts = time.strftime("%Y%m%d_%H%M%S")
                self._path = self._log_dir / f"{ts}_{self._session_id}_{self._file_index}.jsonl"
                _rotate_fifo(self._log_dir, self._max_files)
        except OSError:
            pass

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
        self._rotate_if_needed()
        record = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "process_file": self._session_id,
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
            logger.warning("Failed to write provider diagnostic log: %s", e)

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


# Global process log — initialized on first access.
_global_log: LLMSessionLog | None = None


def get_session_log(session_id: str = "api") -> LLMSessionLog:
    global _global_log
    if _global_log is None:
        _global_log = LLMSessionLog(session_id=session_id)
    return _global_log


def reset_session_log(session_id: str = "api") -> LLMSessionLog:
    """Start a new process log (e.g. on server restart)."""
    global _global_log
    _global_log = LLMSessionLog(session_id=session_id)
    return _global_log
