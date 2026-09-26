"""Shared immutable exchange catalog for Kairoskopion TargetWorlds."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

STATUS_RANK = {
    "PROD_ACCEPTED": 60,
    "PROD_OBSERVED": 50,
    "QUALIFIED_DEV": 40,
    "PROVIDER_OBSERVED": 30,
    "STAGING": 20,
    "PROVISIONAL": 10,
    "HISTORICAL": 0,
}

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _digest(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()
def _safe_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def summarize_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    corpus = snapshot.get("corpus_manifest") or {}
    models = snapshot.get("target_models") or {}
    return {
        "snapshot_id": snapshot.get("snapshot_id"),
        "target_id": snapshot.get("target_id"),
        "parent_snapshot_id": snapshot.get("parent_snapshot_id"),
        "provider_commit": snapshot.get("provider_commit"),
        "created_at": snapshot.get("created_at"),
        "corpus_size": len(corpus.get("artifacts") or []),
        "editor_profile_count": len(snapshot.get("editor_profiles") or []),
        "article_model_count": len(models.get("article_models") or []),
        "formal_rule_count": len(snapshot.get("canonical_target_rules") or {}),
        "evidence_ref_count": len(snapshot.get("evidence_refs") or []),
        "confidence": models.get("confidence"),
        "freshness": snapshot.get("freshness") or {},
        "model_capabilities": [
            k for k in ("genre_patterns","argument_patterns","method_patterns",
                        "citation_patterns","register_patterns","novelty_patterns",
                        "article_models")
            if models.get(k)
        ],
    }

class TargetWorldCatalog:
    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "target_world_catalog"
        self.packages = self.root / "packages"
        self.root.mkdir(parents=True, exist_ok=True)
        self.packages.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"

    def _load_index(self) -> dict[str, Any]:
        if not self.index_path.is_file():
            return {"schema_version": "targetworld-catalog-v1", "entries": []}
        return json.loads(self.index_path.read_text(encoding="utf-8"))

    def _save_index(self, data: dict[str, Any]) -> None:
        tmp = self.index_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.index_path)

    def ingest(self, snapshot: dict[str, Any], *, origin: str,
               status: str = "PROVIDER_OBSERVED", source_ref: str | None = None,
               display_name: str | None = None) -> dict[str, Any]:
        if not snapshot.get("snapshot_id") or not snapshot.get("target_id"):
            raise ValueError("snapshot_id and target_id are required")
        if status not in STATUS_RANK:
            raise ValueError(f"unsupported catalog status: {status}")
        digest = _digest(snapshot)
        package_id = f"{snapshot['snapshot_id']}@{digest[:16]}"
        package_path = self.packages / f"{_safe_id(package_id)}.json"
        package = {
            "schema_version": "targetworld-exchange-v1",
            "package_id": package_id,
            "content_digest": digest,
            "observed_at": _now(),
            "origin": origin,
            "status": status,
            "source_ref": source_ref,
            "display_name": display_name or snapshot["target_id"],
            "snapshot": snapshot,
        }
        if not package_path.exists():
            package_path.write_text(
                json.dumps(package, ensure_ascii=False, indent=2), encoding="utf-8"
            )

        index = self._load_index()
        entries = list(index.get("entries") or [])
        found = next((e for e in entries if e.get("package_id") == package_id), None)
        summary = summarize_snapshot(snapshot)
        entry = {
            **summary,
            "package_id": package_id,
            "content_digest": digest,
            "origin": origin,
            "origins": [origin],
            "status": status,
            "status_rank": STATUS_RANK[status],
            "source_ref": source_ref,
            "source_refs": [source_ref] if source_ref else [],
            "display_name": display_name or snapshot["target_id"],
            "observed_at": package["observed_at"],
        }
        if found is None:
            entries.append(entry)
        else:
            found["origins"] = sorted(set((found.get("origins") or [found.get("origin")]) + [origin]) - {None})
            found["source_refs"] = sorted(set((found.get("source_refs") or []) + ([source_ref] if source_ref else [])))
            if STATUS_RANK[status] > int(found.get("status_rank") or -1):
                found["status"] = status
                found["status_rank"] = STATUS_RANK[status]
                found["origin"] = origin
                found["source_ref"] = source_ref
            found.update(summary)
            found["observed_at"] = package["observed_at"]
            entry = found
        entries.sort(key=lambda e: (
            e.get("target_id") or "",
            -(e.get("status_rank") or 0),
            e.get("created_at") or "",
        ))
        index["entries"] = entries
        index["updated_at"] = _now()
        self._save_index(index)
        return entry

    def list_entries(self, target_id: str | None = None) -> list[dict[str, Any]]:
        entries = list(self._load_index().get("entries") or [])
        if target_id:
            entries = [e for e in entries if e.get("target_id") == target_id]
        return entries

    def get_package(self, package_id: str) -> dict[str, Any] | None:
        path = self.packages / f"{_safe_id(package_id)}.json"
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if data.get("package_id") == package_id else None
    def best_for_target(self, target_id: str,
                        allowed_statuses: set[str] | None = None) -> dict[str, Any] | None:
        entries = self.list_entries(target_id)
        if allowed_statuses is not None:
            entries = [e for e in entries if e.get("status") in allowed_statuses]
        if not entries:
            return None
        entries.sort(key=lambda e: (
            e.get("status_rank") or 0,
            e.get("created_at") or "",
            e.get("observed_at") or "",
        ), reverse=True)
        return entries[0]

    def import_package(self, package: dict[str, Any]) -> dict[str, Any]:
        snapshot = package.get("snapshot")
        if not isinstance(snapshot, dict):
            raise ValueError("exchange package must include snapshot")
        claimed = package.get("content_digest")
        actual = _digest(snapshot)
        if claimed and claimed != actual:
            raise ValueError("exchange package content_digest mismatch")
        return self.ingest(
            snapshot,
            origin=str(package.get("origin") or "ARTIKL_CHAT"),
            status=str(package.get("status") or "PROVISIONAL"),
            source_ref=package.get("source_ref"),
            display_name=package.get("display_name"),
        )