"""Durable filesystem storage for Kairon provider target-world snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class TargetWorldStore:
    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "target_world"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, snapshot_id: str) -> Path:
        digest = hashlib.sha256(snapshot_id.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def put(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        snapshot_id = str(snapshot["snapshot_id"])
        path = self._path(snapshot_id)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)
        return snapshot

    def get(self, snapshot_id: str) -> dict[str, Any] | None:
        path = self._path(snapshot_id)
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("snapshot_id") != snapshot_id:
            return None
        return data

    def list_ids(self) -> list[str]:
        out = []
        for path in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if data.get("snapshot_id"):
                    out.append(str(data["snapshot_id"]))
            except Exception:
                continue
        return out
