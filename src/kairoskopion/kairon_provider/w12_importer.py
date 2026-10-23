"""Real W12 importer/adapter for the MAI-batch pre-author gate.

This module loads MAI W12 route records from authorized source bytes. If real
bytes are unavailable, it returns a ``BLOCKED_PERMISSION`` receipt with the
exact permission failure recorded. Fixture records are clearly labelled
``FIXTURE_NOT_REAL_DATA`` and never claim to be authoritative.

The importer is intentionally read-only. It never edits the canonical W12
table; it only projects a deterministic, stable view into the durable
batch route plan. Stable IDs derive from the SHA-256 of the source bytes
plus the seed/meaning/route triple, so identical real bytes always yield
identical route IDs across cold executions.

W12 source-of-truth shape (preserved, never collapsed):
- 6 seed families
- 27 meaning versions
- 53 routes (route packages, not necessarily 53 distinct manuscripts)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Iterable


W12_FIRST_BYTES_FINGERPRINT_SIZE = 4096
W12_EXPECTED_SEED_FAMILIES = 6
W12_EXPECTED_MEANING_VERSIONS = 27
W12_EXPECTED_ROUTES = 53


SOURCE_KIND_REAL = "REAL_AUTHORIZED_BYTES"
SOURCE_KIND_FIXTURE = "FIXTURE_NOT_REAL_DATA"
SOURCE_KIND_BLOCKED = "BLOCKED_PERMISSION"


ROUTE_TYPE_GENERIC_PROMO = "general_promotion"
ROUTE_TYPE_GENERIC_EDITOR = "generic_editor_address"
ROUTE_TYPE_EDITORIAL_PITCH = "editorial_pitch"
ROUTE_TYPE_RESPOND_CFP = "cfp_response"
ROUTE_TYPE_TARGETED_TARGET = "targeted_target"

ROUTE_KIND_REGULAR = "regular"
ROUTE_KIND_EXCLUSIVE = "exclusive"
ROUTE_KIND_AMBASSADOR = "ambassador"

RAW_KIND_FULLTEXT = "fulltext"
RAW_KIND_METADATA = "metadata"
RAW_KIND_CHALLENGE_HTML = "challenge_html"
RAW_KIND_AMBASSADOR = "ambassador_pack"

EXCLUSIVE_VENUE_NONE = "none"
EXCLUSIVE_VENUE_DUAL = "dual_exclusive"


@dataclass
class W12Record:
    """One route package from the W12 source bytes.

    ``route_id`` is a stable SHA-256[:16] derived from the source bytes and
    the seed/meaning triple; identical bytes always yield identical IDs.
    """

    record_id: str
    route_id: str
    seed_family_id: str
    meaning_version_id: str
    seed_label: str
    meaning_version_label: str
    route_type: str
    route_kind: str
    raw_kind: str
    exclusive_venue_class: str
    source_kind: str
    source_first_bytes_sha256: str
    source_full_sha256: str
    manuscript_pointer: str | None = None
    manuscript_hash: str | None = None
    route_label: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class W12ImportReceipt:
    """Receipt describing exactly how the W12 table was loaded.

    A receipt is the authoritative machine-readable signal that downstream
    code can rely on. ``source_kind`` is one of:
    ``REAL_AUTHORIZED_BYTES`` | ``FIXTURE_NOT_REAL_DATA`` | ``BLOCKED_PERMISSION``.
    """

    status: str
    source_kind: str
    source_path: str | None = None
    source_full_sha256: str | None = None
    source_first_bytes_sha256: str | None = None
    source_byte_count: int = 0
    records_count: int = 0
    seed_family_count: int = 0
    meaning_version_count: int = 0
    blocked_reason: str | None = None
    permission_failure: str | None = None
    authorization_env_var: str | None = None
    shape_warnings: list[str] = field(default_factory=list)
    loaded_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class W12ImportError:
    code: str
    message: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _first_bytes_fingerprint(data: bytes) -> str:
    sample = data[:W12_FIRST_BYTES_FINGERPRINT_SIZE]
    return _digest_bytes(sample)


def _slug(value: str) -> str:
    return "".join(ch if ch.isalnum() else "_" for ch in value).strip("_")[:48]


def _record_id(
    *,
    source_full_sha256: str,
    seed_family_id: str,
    meaning_version_id: str,
    route_label: str,
    route_index: int,
) -> str:
    payload = "|".join(
        [
            source_full_sha256,
            seed_family_id,
            meaning_version_id,
            str(route_index),
            route_label,
        ]
    )
    return "w12_" + _digest_string(payload)[:16]


def _route_id(
    *,
    source_full_sha256: str,
    seed_family_id: str,
    meaning_version_id: str,
    route_label: str,
    route_index: int,
) -> str:
    payload = "|".join(
        [
            "route",
            source_full_sha256,
            seed_family_id,
            meaning_version_id,
            route_label,
            str(route_index),
        ]
    )
    return "route_" + _digest_string(payload)[:16]


def _stable_seed_id(source_full_sha256: str, label: str) -> str:
    return "seed_" + _digest_string("|".join(["seed", source_full_sha256, label]))[:16]


def _stable_meaning_id(source_full_sha256: str, label: str) -> str:
    return "meaning_" + _digest_string("|".join(["meaning", source_full_sha256, label]))[:16]


def _coerce_records(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        for key in ("routes", "records", "w12"):
            if key in raw and isinstance(raw[key], list):
                return [r for r in raw[key] if isinstance(r, dict)]
        return [raw]
    return []


def _build_records(
    *,
    raw_records: list[dict[str, Any]],
    source_full_sha256: str,
    source_first_bytes_sha256: str,
    source_kind: str,
) -> list[W12Record]:
    out: list[W12Record] = []
    for index, raw in enumerate(raw_records):
        seed_label = str(raw.get("seed_family") or raw.get("seed") or f"seed-{index // 8}")
        meaning_label = str(
            raw.get("meaning_version")
            or raw.get("meaning")
            or f"meaning-{index % 27}"
        )
        seed_family_id = str(
            raw.get("seed_family_id") or _stable_seed_id(source_full_sha256, seed_label)
        )
        meaning_version_id = str(
            raw.get("meaning_version_id")
            or _stable_meaning_id(source_full_sha256, meaning_label)
        )
        route_label = str(
            raw.get("route_label")
            or raw.get("title")
            or raw.get("name")
            or f"route-{index}"
        )
        route_type = str(raw.get("route_type") or ROUTE_TYPE_TARGETED_TARGET)
        route_kind = str(raw.get("route_kind") or ROUTE_KIND_REGULAR)
        raw_kind = str(raw.get("raw_kind") or RAW_KIND_METADATA)
        exclusive_venue_class = str(
            raw.get("exclusive_venue_class") or EXCLUSIVE_VENUE_NONE
        )
        manuscript_pointer = (
            str(raw["manuscript_pointer"])
            if isinstance(raw, dict) and raw.get("manuscript_pointer")
            else None
        )
        manuscript_hash = (
            str(raw["manuscript_hash"]) if raw.get("manuscript_hash") else None
        )
        notes = list(raw.get("notes") or [])

        record_id = _record_id(
            source_full_sha256=source_full_sha256,
            seed_family_id=seed_family_id,
            meaning_version_id=meaning_version_id,
            route_label=route_label,
            route_index=index,
        )
        route_id = _route_id(
            source_full_sha256=source_full_sha256,
            seed_family_id=seed_family_id,
            meaning_version_id=meaning_version_id,
            route_label=route_label,
            route_index=index,
        )

        out.append(
            W12Record(
                record_id=record_id,
                route_id=route_id,
                seed_family_id=seed_family_id,
                meaning_version_id=meaning_version_id,
                seed_label=seed_label,
                meaning_version_label=meaning_label,
                route_type=route_type,
                route_kind=route_kind,
                raw_kind=raw_kind,
                exclusive_venue_class=exclusive_venue_class,
                source_kind=source_kind,
                source_first_bytes_sha256=source_first_bytes_sha256,
                source_full_sha256=source_full_sha256,
                manuscript_pointer=manuscript_pointer,
                manuscript_hash=manuscript_hash,
                route_label=route_label,
                notes=notes,
            )
        )
    return out


def _shape_warnings(records: list[W12Record]) -> list[str]:
    seeds = {r.seed_family_id for r in records}
    meanings = {r.meaning_version_id for r in records}
    warnings: list[str] = []
    if len(records) != W12_EXPECTED_ROUTES:
        warnings.append(
            f"route_count={len(records)} differs from expected "
            f"{W12_EXPECTED_ROUTES}; treating W12 shape as advisory"
        )
    if len(seeds) != W12_EXPECTED_SEED_FAMILIES:
        warnings.append(
            f"seed_family_count={len(seeds)} differs from expected "
            f"{W12_EXPECTED_SEED_FAMILIES}"
        )
    if len(meanings) != W12_EXPECTED_MEANING_VERSIONS:
        warnings.append(
            f"meaning_version_count={len(meanings)} differs from expected "
            f"{W12_EXPECTED_MEANING_VERSIONS}"
        )
    return warnings


def _blocked_receipt(
    *,
    reason: str,
    permission_failure: str,
    authorization_env_var: str,
    source_path: str | None = None,
    notes: Iterable[str] = (),
) -> tuple[list[W12Record], W12ImportReceipt]:
    receipt = W12ImportReceipt(
        status=SOURCE_KIND_BLOCKED,
        source_kind=SOURCE_KIND_BLOCKED,
        source_path=source_path,
        blocked_reason=reason,
        permission_failure=permission_failure,
        authorization_env_var=authorization_env_var,
        records_count=0,
        seed_family_count=0,
        meaning_version_count=0,
        notes=list(notes),
    )
    return [], receipt


def discover_w12_source(
    *,
    env_var: str = "MAI_W12_AUTHORIZED_PATH",
    fallback_path: str | Path | None = None,
) -> W12ImportReceipt:
    """Probe the environment for an authorized W12 source.

    Real bytes are only loaded if the env var points to a readable file.
    If no real bytes are available, a ``BLOCKED_PERMISSION`` receipt is
    returned with the exact failure code, and no records are synthesized.
    """

    authorized = os.environ.get(env_var) or (
        str(fallback_path) if fallback_path else None
    )
    if not authorized:
        return _blocked_receipt(
            reason="no_authorized_source",
            permission_failure=(
                f"{env_var} not set and no fallback path provided"
            ),
            authorization_env_var=env_var,
        )[1]
    path = Path(authorized)
    if not path.exists():
        return _blocked_receipt(
            reason="authorized_path_missing",
            permission_failure=f"authorized path does not exist: {path}",
            authorization_env_var=env_var,
            source_path=str(path),
        )[1]
    if not path.is_file():
        return _blocked_receipt(
            reason="authorized_path_not_file",
            permission_failure=f"authorized path is not a regular file: {path}",
            authorization_env_var=env_var,
            source_path=str(path),
        )[1]
    try:
        with path.open("rb") as fh:
            data = fh.read()
    except OSError as exc:
        return _blocked_receipt(
            reason="authorized_path_unreadable",
            permission_failure=f"OSError reading {path}: {exc}",
            authorization_env_var=env_var,
            source_path=str(path),
        )[1]

    receipt = W12ImportReceipt(
        status=SOURCE_KIND_REAL,
        source_kind=SOURCE_KIND_REAL,
        source_path=str(path),
        source_full_sha256=_digest_bytes(data),
        source_first_bytes_sha256=_first_bytes_fingerprint(data),
        source_byte_count=len(data),
    )
    return receipt


def load_w12(
    source_path: str | Path,
    *,
    source_kind: str = SOURCE_KIND_REAL,
) -> tuple[list[W12Record], W12ImportReceipt]:
    """Load W12 records from a specific source path with kind label.

    Use ``source_kind=SOURCE_KIND_FIXTURE`` for test data; the returned
    records are clearly labelled ``FIXTURE_NOT_REAL_DATA`` so downstream
    code cannot mistake them for authoritative bytes.
    """

    path = Path(source_path)
    if not path.is_file():
        records, receipt = _blocked_receipt(
            reason="source_path_not_file",
            permission_failure=f"source path is not a file: {path}",
            authorization_env_var="inline",
            source_path=str(path),
        )
        return records, receipt

    try:
        with path.open("rb") as fh:
            data = fh.read()
    except OSError as exc:
        records, receipt = _blocked_receipt(
            reason="source_path_unreadable",
            permission_failure=f"OSError reading {path}: {exc}",
            authorization_env_var="inline",
            source_path=str(path),
        )
        return records, receipt

    if not data:
        records, receipt = _blocked_receipt(
            reason="source_path_empty",
            permission_failure=f"source file is empty: {path}",
            authorization_env_var="inline",
            source_path=str(path),
        )
        return records, receipt

    full_sha = _digest_bytes(data)
    first_sha = _first_bytes_fingerprint(data)

    try:
        decoded = data.decode("utf-8")
    except UnicodeDecodeError:
        records, receipt = _blocked_receipt(
            reason="source_not_utf8_text",
            permission_failure="source bytes are not UTF-8 text",
            authorization_env_var="inline",
            source_path=str(path),
        )
        return records, receipt

    raw_records: list[dict[str, Any]] = []
    parse_errors: list[str] = []
    for line_number, line in enumerate(decoded.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            raw_records.append(json.loads(stripped))
        except json.JSONDecodeError as exc:
            parse_errors.append(f"line {line_number}: {exc.msg}")

    if not raw_records:
        try:
            decoded_object = json.loads(decoded)
            raw_records = _coerce_records(decoded_object)
        except json.JSONDecodeError as exc:
            records, receipt = _blocked_receipt(
                reason="source_unparseable_json",
                permission_failure=f"JSON decode failed: {exc.msg}",
                authorization_env_var="inline",
                source_path=str(path),
            )
            return records, receipt

    records = _build_records(
        raw_records=raw_records,
        source_full_sha256=full_sha,
        source_first_bytes_sha256=first_sha,
        source_kind=source_kind,
    )

    seeds = {r.seed_family_id for r in records}
    meanings = {r.meaning_version_id for r in records}

    receipt = W12ImportReceipt(
        status=source_kind,
        source_kind=source_kind,
        source_path=str(path),
        source_full_sha256=full_sha,
        source_first_bytes_sha256=first_sha,
        source_byte_count=len(data),
        records_count=len(records),
        seed_family_count=len(seeds),
        meaning_version_count=len(meanings),
        shape_warnings=_shape_warnings(records),
        notes=parse_errors,
    )
    return records, receipt


def build_fixture_w12(
    *,
    seed_count: int = W12_EXPECTED_SEED_FAMILIES,
    meaning_count: int = W12_EXPECTED_MEANING_VERSIONS,
    route_count: int = W12_EXPECTED_ROUTES,
    fingerprint_seed: str = "fixture-mai-w12",
) -> tuple[list[W12Record], W12ImportReceipt]:
    """Build an explicitly-labelled fixture W12 corpus for offline tests.

    The fixture is fully deterministic and uses ``FIXTURE_NOT_REAL_DATA`` as
    its ``source_kind``. Stable IDs derive from a synthetic SHA-256 of the
    fingerprint seed string so the fixture can never be mistaken for real
    authorized bytes.
    """

    full_sha = _digest_string(fingerprint_seed)
    first_sha = _digest_string(fingerprint_seed + ":first")

    raw_records: list[dict[str, Any]] = []
    seeds = [f"SEED-{i+1:02d}" for i in range(seed_count)]
    meanings = [f"MV-{i+1:03d}" for i in range(meaning_count)]
    for i in range(route_count):
        seed = seeds[i % len(seeds)]
        meaning = meanings[i % len(meanings)]
        route_type = ROUTE_TYPE_TARGETED_TARGET
        route_kind = ROUTE_KIND_REGULAR
        raw_kind = RAW_KIND_FULLTEXT
        exclusive_venue_class = EXCLUSIVE_VENUE_NONE
        if i % 11 == 0 and i > 0:
            route_kind = ROUTE_KIND_EXCLUSIVE
        if i % 9 == 0:
            raw_kind = RAW_KIND_METADATA
        raw_records.append(
            {
                "seed_family": seed,
                "meaning_version": meaning,
                "route_label": f"Route {i+1:03d}",
                "route_type": route_type,
                "route_kind": route_kind,
                "raw_kind": raw_kind,
                "exclusive_venue_class": exclusive_venue_class,
                "manuscript_pointer": f"manuscript://fixture/{i+1:03d}",
                "notes": ["deterministic fixture"],
            }
        )

    records = _build_records(
        raw_records=raw_records,
        source_full_sha256=full_sha,
        source_first_bytes_sha256=first_sha,
        source_kind=SOURCE_KIND_FIXTURE,
    )
    seeds_set = {r.seed_family_id for r in records}
    meanings_set = {r.meaning_version_id for r in records}
    receipt = W12ImportReceipt(
        status=SOURCE_KIND_FIXTURE,
        source_kind=SOURCE_KIND_FIXTURE,
        source_path=None,
        source_full_sha256=full_sha,
        source_first_bytes_sha256=first_sha,
        source_byte_count=len(fingerprint_seed),
        records_count=len(records),
        seed_family_count=len(seeds_set),
        meaning_version_count=len(meanings_set),
        shape_warnings=_shape_warnings(records),
        notes=["fixture-only; not authorized real bytes"],
    )
    return records, receipt


def route_event_hash(
    *,
    record: W12Record,
    phase: str,
    status: str,
    extra: Iterable[str] = (),
) -> str:
    """Deterministic SHA-256[:16] over a route's event payload.

    Used by the Trimurti scheduler to make phase transitions idempotent
    and reproducible across cold executions.
    """

    payload = "|".join(
        [
            record.route_id,
            record.seed_family_id,
            record.meaning_version_id,
            phase,
            status,
            *(str(x) for x in extra),
        ]
    )
    return "tev_" + _digest_string(payload)[:16]