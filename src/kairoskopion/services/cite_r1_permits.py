"""TRM-CITE-001 R1 source-reader permit registry.

A permit is a per-work-order, operator-authored, JSON-Lines file that records
exactly which source witness a downstream provider is allowed to acquire.  It
is the only path from a request to a recorded OBSERVED return.  Without a
permit, a work order returns BLOCKED with a typed reason — there is no
implicit trust of a URL or file.

The permit file is intentionally restrictive:

- One JSON object per work_order_id, written by an operator with a stable
  ``authorized_by`` label (typically ``OWNER_AUTHORITY_<date>``).
- The mode is FIXTURE (local cached witness file) or LIVE (URL); LIVE only
  resolves if the URL host is in the allowlist passed to the provider.  URLs
  are never fetched through shell commands, custom transports, or any path
  that could be used to circumvent publisher authentication.
- The expected_locator and expected_passage anchor the witness text so a
  mismatch produces EVIDENCE_MISMATCH_BLOCKED, not a false OBSERVED.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SCHEMA = "trm-cite-r1-permit-v1"

# Hosts that an operator may pre-authorize for a real, observable source.
# Anything not in this set is treated as LIVE_NOT_PERMITTED and forces BLOCKED.
DEFAULT_ALLOWED_HOSTS: frozenset[str] = frozenset({
    "unicaen.fr",                     # Presses universitaires de Caen
    "puc.unicaen.fr",
    "link.springer.com",              # Springer open-access (Springer+ for OA journals)
    "springeropen.com",
})

_FIXTURE_MODES = {"FIXTURE"}
_LIVE_MODES = {"LIVE"}
_KNOWN_MODES = _FIXTURE_MODES | _LIVE_MODES


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


@dataclasses.dataclass(frozen=True)
class Permit:
    """One authorized read of one source for one work order."""

    work_order_id: str
    # One approved source may support several investigations, but each task
    # must be explicitly permitted. Sharing a Z0 child is not carte blanche.
    allowed_task_ids: tuple[str, ...]
    provider: str
    authorized_by: str
    mode: str
    work_id: str
    edition_id: str
    witness_id: str
    license: str
    expected_locator: str
    expected_passage: str
    citation_mode: str = "QUOTE"
    read_depth: str = "ANCHORED_PASSAGE"
    source_kind: str = "SOURCE_NEEDS_INDEPENDENT_REVIEW"
    access: str = "READABILITY_NOT_CERTIFIED"
    # Witness provenance cannot be inferred from a fixture path or a source URL.
    witness_class: str = "SYNTHETIC_TEST"
    witness_sha256: str = ""
    observed_at: str | None = None
    notes: str | None = None
    fixture_path: str | None = None
    live_url: str | None = None
    issued_at: str = dataclasses.field(default_factory=_now_iso)
    permit_id: str = ""

    def __post_init__(self) -> None:
        _require(bool(self.work_order_id), "permit.work_order_id is required")
        object.__setattr__(self, "allowed_task_ids", tuple(self.allowed_task_ids))
        _require(bool(self.allowed_task_ids) and
                 len(self.allowed_task_ids) == len(set(self.allowed_task_ids)),
                 "Permit must list unique allowed_task_ids")
        _require(bool(self.provider), "permit.provider is required")
        _require(bool(self.authorized_by), "permit.authorized_by is required")
        _require(self.mode in _KNOWN_MODES, f"permit.mode must be FIXTURE or LIVE; got {self.mode!r}")
        _require(self.citation_mode in {"QUOTE", "PARAPHRASE", "UNKNOWN"},
                 f"permit.citation_mode must be QUOTE, PARAPHRASE, or UNKNOWN; got {self.citation_mode!r}")
        _require(self.read_depth in {"ANCHORED_PASSAGE", "FULL_BOOK", "SECTION_TEXT",
                                    "PUBLISHER_ABSTRACT", "SEARCH_RESULT"},
                 f"permit.read_depth not allowed: {self.read_depth!r}")
        _require(bool(self.work_id) and bool(self.edition_id) and bool(self.witness_id),
                 "permit work/edition/witness ids are required")
        _require(bool(self.expected_locator),
                 "permit.expected_locator is required")
        _require(bool(self.expected_passage),
                 "permit.expected_passage is required")
        _require(self.witness_class in {
            "SYNTHETIC_TEST", "MANUAL_WEB_OBSERVED", "LIVE_AUTHORIZED_SOURCE_READ"
        }, "Unknown witness_class")
        _require(re.fullmatch(r"[0-9a-fA-F]{64}", self.witness_sha256 or "") is not None,
                 "permit.witness_sha256 must be a pinned 64-char digest")
        if self.mode == "FIXTURE":
            _require(self.witness_class in {"SYNTHETIC_TEST", "MANUAL_WEB_OBSERVED"},
                     "FIXTURE must not claim LIVE_AUTHORIZED_SOURCE_READ")
            _require(bool(self.observed_at), "FIXTURE must contain original observed_at")
            observed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
            _require(observed.tzinfo is not None, "FIXTURE observed_at requires timezone")
            _require(bool(self.fixture_path),
                     "FIXTURE permit must declare fixture_path")
            _require(re.fullmatch(r"[A-Za-z0-9_.-]{1,180}", self.fixture_path) is not None,
                     "FIXTURE path must be one safe filename, not a directory or traversal")
            _require(self.live_url is None, "FIXTURE permit must not declare live_url")
        else:
            _require(self.witness_class == "LIVE_AUTHORIZED_SOURCE_READ",
                     "LIVE permit requires LIVE_AUTHORIZED_SOURCE_READ")
            _require(bool(self.live_url),
                     "LIVE permit must declare live_url")
            _require(self.fixture_path is None,
                     "LIVE permit must not declare fixture_path")
        if not self.permit_id:
            object.__setattr__(
                self, "permit_id",
                "permit_" + _sha(
                    (self.work_order_id + "|" + self.authorized_by + "|" +
                     self.work_id + "|" + self.edition_id + "|" +
                     self.witness_id + "|" + self.expected_locator + "|" +
                     self.expected_passage + "|" + self.witness_sha256 + "|" +
                     self.witness_class + "|" +
                     ",".join(sorted(self.allowed_task_ids))).encode()
                )[:24],
            )

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}


def load_permits(directory: Path) -> dict[str, Permit]:
    """Load every JSON permit file in ``directory``.

    Filenames must be ``<work_order_id>.json``.  Files that fail to parse or
    validate raise ``ValueError`` so a partial registry is never silently
    trusted.
    """
    directory = Path(directory)
    if not directory.exists():
        return {}
    out: dict[str, Permit] = {}
    seen_ids: set[str] = set()
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(data, dict):
            raise ValueError(f"permit {path} is not an object")
        if data.get("schema") != SCHEMA:
            raise ValueError(
                f"permit {path} has wrong schema: {data.get('schema')!r} != {SCHEMA!r}"
            )
        work_order_id = str(data.get("work_order_id") or path.stem)
        if work_order_id in seen_ids:
            raise ValueError(f"duplicate permit for {work_order_id}")
        seen_ids.add(work_order_id)
        payload = {k: v for k, v in data.items() if k != "schema"}
        out[work_order_id] = Permit(**payload)
    return out


def save_permit(directory: Path, permit: Permit) -> Path:
    """Persist one permit as ``<work_order_id>.json`` using exclusive create.

    The filename is intentionally the work_order_id so an operator cannot
    accidentally rename a permit to a different request.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {"schema": SCHEMA, **permit.to_dict()},
        sort_keys=True, ensure_ascii=False, indent=2,
    ) + "\n"
    target = directory / (permit.work_order_id + ".json")
    if target.exists():
        if target.read_text(encoding="utf-8") != payload:
            raise RuntimeError("permit already exists with different content: " + str(target))
        return target
    with target.open("xb") as stream:
        stream.write(payload.encode("utf-8"))
    return target


def validate_permit_against_hosts(
    permit: Permit, allowed_hosts: frozenset[str]
) -> tuple[bool, str | None]:
    """Return (allowed, reason).  ``allowed`` is True iff permitted to fetch.

    A FIXTURE permit only checks format.  A LIVE permit also requires that
    the URL host is in the allowlist.  Publishers with subscription, DRMed
    URLs, or anything not in the allowlist always returns False with a typed
    reason that the reader must surface as a BLOCKED reason.
    """
    if permit.mode == "FIXTURE":
        return True, None
    if not permit.live_url:
        return False, "LIVE permit has no URL"
    parsed = urlparse(permit.live_url)
    if parsed.scheme != "https":
        return False, "Only HTTPS public-source reads are permitted"
    host = parsed.hostname or ""
    if not host:
        return False, "URL host could not be parsed"
    if not any(host == h or host.endswith("." + h) for h in allowed_hosts):
        return False, f"host {host} is not in the allowed source list"
    return True, None


def normalize_locator(locator: str) -> str:
    """Fold whitespace and case so a permit locator survives minor reformatting."""
    return re.sub(r"\s+", " ", locator.strip()).casefold()


def locator_matches(expected: str, declared: str) -> bool:
    return normalize_locator(expected) == normalize_locator(declared)
