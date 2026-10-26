"""Read-only science source-pin resolver for the EXISTING Factory case store.

A Factory source-stage receipt and its case ledger can bind exact source bytes.
They cannot establish an independent numerical oracle, authorize a manuscript,
or decide scientific novelty. An expected receipt SHA256 must be supplied by
the owner-controlled runtime from an independently retained checkpoint; it may
NOT come from the model, candidate claim, or this case receipt itself.

No separate factory/store is introduced and no ArticleSeed is written here.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import re
from typing import Any


_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CASE = re.compile(r"[A-Za-z0-9_-]{1,128}\Z")
_MAX_RECEIPT = 256_000
_MAX_LEDGER = 16_000_000
_MAX_SOURCE = 30_000_000
_TEXT_COVERAGE = frozenset({
    "FULL_FETCHED_TEXT_ONLY",
    "STRUCTURAL_TEXT_PROJECTION_COMMENTS_NOT_ACQUIRED",
})


def _read_exact(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Factory pinned file missing or symlinked")
    size = path.stat().st_size
    if not 0 < size <= limit:
        raise ValueError("Factory pinned file size outside policy")
    return path.read_bytes()


def _object(raw: bytes) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        item: dict[str, Any] = {}
        for key, value in pairs:
            if key in item:
                raise ValueError("duplicate Factory JSON field")
            item[key] = value
        return item

    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique_pairs,
            parse_constant=lambda _: (_ for _ in ()).throw(
                ValueError("non-finite Factory JSON")
            ),
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Factory JSON corrupt") from exc
    if not isinstance(value, dict):
        raise ValueError("Factory record must be an object")
    return value


def readback_factory_scientific_source_pin(
    *,
    factory_storage_root: Path | str,
    case_id: str,
    source_id: str,
    source_bytes: bytes,
    owner_expected_stage_receipt_sha256: str,
) -> dict[str, Any]:
    """Derive SOURCE pin from an actual immutable Factory checkpoint.

    The owner-only expected stage receipt SHA is an external trust anchor; a
    matching digest is NOT proof if a caller invents the expected hash itself.
    This returns RAW_SOURCE (eligible for later independent oracle checking)
    or TEXT_PROJECTION (not original-byte science authority). It never returns
    scientific-claim PASS or author approval. The production caller must own
    and protect factory_storage_root + the independent receipt pin.
    """
    if not isinstance(case_id, str) or _CASE.fullmatch(case_id) is None:
        raise ValueError("invalid Factory case ID")
    if not isinstance(source_id, str) or not source_id.strip():
        raise ValueError("Factory source ID is required")
    if (not isinstance(owner_expected_stage_receipt_sha256, str)
            or _SHA.fullmatch(owner_expected_stage_receipt_sha256) is None):
        raise ValueError("owner-pinned Factory stage receipt SHA missing")
    if (not isinstance(source_bytes, bytes)
            or not 0 < len(source_bytes) <= _MAX_SOURCE):
        raise ValueError("actual original source bytes required")

    root = Path(factory_storage_root).resolve()
    stage = _read_exact(
        root / "factory_research_cases" / case_id / "source_stage_receipt.json",
        _MAX_RECEIPT,
    )
    stage_sha = sha256(stage).hexdigest()
    if stage_sha != owner_expected_stage_receipt_sha256:
        raise ValueError("Factory stage receipt differs from independent owner pin")
    receipt = _object(stage)
    if (receipt.get("schema") != "FACTORY_SOURCE_RESEARCH_STAGE_V1"
            or receipt.get("case_id") != case_id
            or receipt.get("article_seed_created") != 0
            or receipt.get("author_approved") is not False
            or receipt.get("world_mutated") is not False
            or receipt.get("external_send") != "DISABLED"):
        raise ValueError("Factory stage authority or case mismatch")

    ledger_bytes = _read_exact(
        root / "talk_corpora" / case_id / "case_ledger.json",
        _MAX_LEDGER,
    )
    ledger_sha = sha256(ledger_bytes).hexdigest()
    if ledger_sha != receipt.get("source_ledger_sha256"):
        raise ValueError("Factory source ledger lost immutable receipt binding")
    ledger = _object(ledger_bytes)
    if (ledger.get("schema") != "TRM074_COLD_CASE_LEDGER_V1"
            or ledger.get("case_id") != case_id
            or ledger.get("publication_send") != "DISALLOWED"):
        raise ValueError("Factory source ledger identity or authority mismatch")
    sources = ledger.get("source_snapshots")
    if not isinstance(sources, list):
        raise ValueError("Factory source ledger missing source inventory")
    found = [s for s in sources if isinstance(s, dict)
             and s.get("source_id") == source_id]
    if len(found) != 1:
        raise ValueError("Factory scientific source not uniquely pinned")
    snapshot = found[0]
    if (snapshot.get("extraction_status") != "extracted"
            or snapshot.get("read_coverage") not in _TEXT_COVERAGE):
        raise ValueError("Factory source reading scope not science eligible")
    content_pin = snapshot.get("content_sha256")
    if not isinstance(content_pin, str) or _SHA.fullmatch(content_pin) is None:
        raise ValueError("Factory content digest not registered")
    raw_pin = snapshot.get("raw_source_sha256")
    if raw_pin is not None and (
        not isinstance(raw_pin, str) or _SHA.fullmatch(raw_pin) is None
    ):
        raise ValueError("Factory raw source digest invalid")

    observed = sha256(source_bytes).hexdigest()
    expected = raw_pin if raw_pin is not None else content_pin
    if observed != expected:
        raise ValueError("Source bytes differ from Factory registered source")
    pin_kind = "RAW_SOURCE" if raw_pin is not None else "TEXT_PROJECTION"
    return {
        "schema": "FACTORY_SCIENTIFIC_SOURCE_PIN_READBACK_V1",
        "case_id": case_id,
        "source_id": source_id,
        "source_sha256": observed,
        "pin_kind": pin_kind,
        "source_stage_receipt_sha256": stage_sha,
        "source_ledger_sha256": ledger_sha,
        "source_snapshot_id": snapshot.get("snapshot_id"),
        "source_coverage": snapshot["read_coverage"],
        "status": "SOURCE_PIN_READBACK_VERIFIED",
        "independent_numerical_oracle": "NOT_VERIFIED",
        "scientific_claim_admitted": False,
        "article_seed_created": False,
        "author_gate": "HOLD",
        "external_send": "DISABLED",
    }
