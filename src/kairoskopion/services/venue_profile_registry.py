"""Durable indexed registry for VenueProfilePackage (VF-C2).

The canon §2 + rubric v2 §1 require a cross-session venue model store
so that a second search on a related article reuses what's already in
the registry rather than re-discovering.

This module implements:

- JSONL append-only persistence under
  `${KAIROSKOPION_STORAGE_ROOT}/registries/venue_profile_packages.jsonl`,
- in-memory index by canonical name (lowercased, stripped) and by ISSN
  (any ISSN variant the package carries) and by OpenAlex source id,
- idempotent upsert: a second call with the same identity updates the
  existing record (last write wins per field, append a new line with the
  full updated record),
- lookup-by-anything: name, ISSN, OpenAlex id.

No LLM. No network. Pure storage.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

from ..schema import VenueProfilePackage, _now

logger = logging.getLogger(__name__)


_NAME_NORMALIZE_RE = re.compile(r"[\s\-_/]+")


def _normalize_name(name: str | None) -> str:
    if not name:
        return ""
    return _NAME_NORMALIZE_RE.sub(" ", name.strip().lower()).strip()


def _normalize_issn(issn: str | None) -> str:
    if not issn:
        return ""
    return issn.strip().upper().replace(" ", "")


class VenueProfileRegistry:
    """Indexed JSONL registry for `VenueProfilePackage`."""

    DEFAULT_FILENAME = "venue_profile_packages.jsonl"

    def __init__(self, storage_root: str | Path | None = None) -> None:
        raw = (
            str(storage_root)
            if storage_root
            else os.environ.get("KAIROSKOPION_STORAGE_ROOT", ".kairoskopion")
        )
        self._root = Path(raw)
        self._reg_dir = self._root / "registries"
        self._reg_dir.mkdir(parents=True, exist_ok=True)
        self._path = self._reg_dir / self.DEFAULT_FILENAME
        self._by_name: dict[str, str] = {}  # name -> vpkg_id
        self._by_issn: dict[str, str] = {}  # issn -> vpkg_id
        self._by_openalex: dict[str, str] = {}  # oa_id -> vpkg_id
        self._records: dict[str, VenueProfilePackage] = {}  # vpkg_id -> latest
        self._load()

    # -- internals --

    def _load(self) -> None:
        if not self._path.exists():
            return
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    logger.warning("skipping malformed line in %s", self._path)
                    continue
                try:
                    vpkg = VenueProfilePackage.from_dict(d)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("skipping unreadable VPKG record: %s", exc)
                    continue
                self._records[vpkg.venue_profile_package_id] = vpkg
                self._index_record(vpkg)

    def _index_record(self, vpkg: VenueProfilePackage) -> None:
        vid = vpkg.venue_profile_package_id
        name_key = _normalize_name(vpkg.canonical_name)
        if name_key:
            self._by_name[name_key] = vid
        for issn in vpkg.issns or []:
            ikey = _normalize_issn(issn)
            if ikey:
                self._by_issn[ikey] = vid
        if vpkg.openalex_source_id:
            self._by_openalex[vpkg.openalex_source_id] = vid

    def _append_jsonl(self, vpkg: VenueProfilePackage) -> None:
        line = json.dumps(
            vpkg.to_dict(), ensure_ascii=False, default=str, sort_keys=False
        )
        with self._path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")

    # -- public API --

    def find(
        self,
        *,
        canonical_name: str | None = None,
        issn: str | None = None,
        openalex_source_id: str | None = None,
    ) -> VenueProfilePackage | None:
        """Return the indexed VPKG if any identity matches. None otherwise."""
        if canonical_name:
            vid = self._by_name.get(_normalize_name(canonical_name))
            if vid:
                return self._records.get(vid)
        if issn:
            vid = self._by_issn.get(_normalize_issn(issn))
            if vid:
                return self._records.get(vid)
        if openalex_source_id:
            vid = self._by_openalex.get(openalex_source_id)
            if vid:
                return self._records.get(vid)
        return None

    def upsert(self, vpkg: VenueProfilePackage) -> VenueProfilePackage:
        """Insert or update. Identity-merge by name / ISSN / OpenAlex.

        If a record already exists under any of these keys, the new VPKG's
        id is overwritten to the existing one and the record is treated as
        an update — the file gets a new JSONL line with the merged record;
        on next load that line wins (last write).
        """
        existing = self.find(
            canonical_name=vpkg.canonical_name,
            issn=next(iter(vpkg.issns or []), None),
            openalex_source_id=vpkg.openalex_source_id,
        )
        if existing:
            # Merge: preserve existing id, overwrite identity/sub-ids when
            # the new VPKG has them.
            new_id = existing.venue_profile_package_id
            merged_dict = existing.to_dict()
            for k, v in vpkg.to_dict().items():
                if k in ("venue_profile_package_id", "created_at"):
                    continue
                if v in (None, [], {}, ""):
                    # don't overwrite a known value with empty
                    if not merged_dict.get(k):
                        merged_dict[k] = v
                    continue
                # Merge lists by union (preserve order: existing first)
                if isinstance(v, list) and isinstance(merged_dict.get(k), list):
                    seen = set()
                    out = []
                    for item in (merged_dict.get(k) or []) + v:
                        key = json.dumps(item, sort_keys=True, default=str) if not isinstance(item, str) else item
                        if key not in seen:
                            seen.add(key)
                            out.append(item)
                    merged_dict[k] = out
                else:
                    merged_dict[k] = v
            merged_dict["venue_profile_package_id"] = new_id
            merged_dict["updated_at"] = _now()
            vpkg = VenueProfilePackage.from_dict(merged_dict)
        # Re-index (in case ISSN / openalex_id changed) and write
        self._records[vpkg.venue_profile_package_id] = vpkg
        # Rebuild affected indices: cleanest is full re-index of this record
        self._index_record(vpkg)
        self._append_jsonl(vpkg)
        return vpkg

    def list_all(self) -> list[VenueProfilePackage]:
        return list(self._records.values())

    def count(self) -> int:
        return len(self._records)

    @property
    def path(self) -> Path:
        return self._path
