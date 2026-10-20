"""Isolated, single-writer LOKI R0 event ledger.

This is a development sidecar, NOT the canonical Factory/Indago/WhiteCrow store.
It cannot submit, edit manuscripts, or claim production multi-writer safety.
"""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Any


ZERO_HASH = "0" * 64
_PRIVATE_KEYS = frozenset({
    "raw_manuscript", "manuscript_text", "email_body", "source_body",
    "password", "api_key", "oauth_token", "secret",
})


def _canonical(data: Any) -> str:
    return json.dumps(data, sort_keys=True, ensure_ascii=False,
                      allow_nan=False, separators=(",", ":"))


def _guard_payload(data: Any) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in _PRIVATE_KEYS:
                raise ValueError(f"raw protected value forbidden in LOKI ledger: {key}")
            _guard_payload(value)
    elif isinstance(data, (list, tuple)):
        for value in data:
            _guard_payload(value)


class LokiLedger:
    """Append-only hash chain with idempotent events; one writer only.

    For a concurrent deployment, use the canonical Factory's transactional
    journal rather than this deliberately bounded file implementation.
    """

    def __init__(self, path: str | Path, *, write_enabled: bool = False) -> None:
        self.path = Path(path)
        self.write_enabled = write_enabled

    def read(self) -> tuple[dict[str, Any], ...]:
        if not self.path.exists():
            return ()
        history = []
        previous = ZERO_HASH
        seen = set()
        with self.path.open("r", encoding="utf-8") as f:
            for index, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                except (ValueError, TypeError) as exc:
                    raise ValueError(f"ledger line {index} corrupted") from exc
                if not isinstance(record, dict):
                    raise ValueError(f"ledger line {index} is not an event")
                event_hash = record.get("event_hash", "")
                body = {k: v for k, v in record.items() if k != "event_hash"}
                computed = sha256(_canonical(body).encode("utf-8")).hexdigest()
                if body.get("previous_hash") != previous or computed != event_hash:
                    raise ValueError(f"ledger line {index}: hash-chain mismatch")
                if not isinstance(body.get("event_id"), str) or not body["event_id"]:
                    raise ValueError(f"ledger line {index}: missing event ID")
                if body["event_id"] in seen:
                    raise ValueError(f"ledger line {index}: duplicate event ID")
                seen.add(body["event_id"])
                _guard_payload(body.get("payload"))
                history.append(record)
                previous = event_hash
        return tuple(history)

    def append(self, event_id: str, event_type: str, payload: dict[str, Any]) -> bool:
        """Return False for identical replay; refuse collisions and corrupt history."""
        if not self.write_enabled:
            raise PermissionError("LOKI sidecar is read-only unless explicitly enabled")
        if not event_id or not event_type or not isinstance(payload, dict):
            raise ValueError("event ID/type and dictionary payload required")
        _guard_payload(payload)
        _canonical(payload)  # Reject non-JSON values before any append.
        history = self.read()
        for existing in history:
            if existing["event_id"] == event_id:
                if (existing["event_type"] == event_type
                        and existing["payload"] == payload):
                    return False
                raise ValueError("event ID collision with different content")
        body = {
            "event_id": event_id,
            "event_type": event_type,
            "payload": payload,
            "previous_hash": history[-1]["event_hash"] if history else ZERO_HASH,
        }
        row = dict(body)
        row["event_hash"] = sha256(_canonical(body).encode("utf-8")).hexdigest()
        # No concurrent writer or Factory journal is permitted on this file.
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as f:
            f.write(_canonical(row) + "\n")
            f.flush()
            os.fsync(f.fileno())
        # Fail closed if a write did not survive or chain was corrupted.
        if self.read()[-1]["event_hash"] != row["event_hash"]:
            raise OSError("LOKI append was not durable")
        return True
