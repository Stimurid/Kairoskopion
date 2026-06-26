"""JSONL registry for Kairoskopion entities.

Each registry is a single ``.jsonl`` file.  Append-only by default;
read returns all records; list returns entity IDs.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_DEFAULT_DIR = Path("registry")


def _registry_path(name: str, base_dir: Path | str | None = None) -> Path:
    base = Path(base_dir) if base_dir else _DEFAULT_DIR
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{name}.jsonl"


def append(name: str, record: dict[str, Any], *, base_dir: Path | str | None = None) -> Path:
    """Append one JSON record to a named registry file.  Returns the file path."""
    path = _registry_path(name, base_dir)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")
    return path


def read_all(name: str, *, base_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """Read all records from a named registry."""
    path = _registry_path(name, base_dir)
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def list_ids(name: str, id_field: str = "id", *, base_dir: Path | str | None = None) -> list[str]:
    """Return all values of *id_field* from a named registry."""
    records = read_all(name, base_dir=base_dir)
    ids: list[str] = []
    for r in records:
        for key in (id_field, f"{name}_id", "entity_id"):
            if key in r:
                ids.append(r[key])
                break
    return ids


def find_by_id(
    name: str,
    entity_id: str,
    id_field: str = "id",
    *,
    base_dir: Path | str | None = None,
) -> dict[str, Any] | None:
    """Return the first record whose ID matches *entity_id*, or None."""
    for r in read_all(name, base_dir=base_dir):
        for key in (id_field, f"{name}_id", "entity_id"):
            if r.get(key) == entity_id:
                return r
    return None


def registry_exists(name: str, *, base_dir: Path | str | None = None) -> bool:
    return _registry_path(name, base_dir).exists()
