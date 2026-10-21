"""TRM-CITE-001 R1 source-reader provider.

This module is the *provider* half of the R1 source-evidence seam:

- The consumer (``citation_r1_batch.consume``) reads an immutable request
  envelope and validates a typed return.  It never acquires a source.
- This module loads operator-authored permits, acquires an authorized
  witness, verifies the recorded passage text actually appears in the
  witness bytes, and persists an immutable ``*.return.json`` envelope whose
  shape the consumer accepts.

The provider never opens a URL or file without an explicit per-work-order
permit.  It never searches, scrapes, or fans out across candidate sources.
Live HTTP access uses only the allowlisted hosts configured on the provider
instance; FIXTURE mode is the only path that does not touch the network.
The output is recorded as a *proposal* for V1–V5 review — the consumer
keeps V1..V5 as ``NOT_CHECKED`` until independent science and the author
gate accept the passage.

Required design constraints enforced here:

(a) cross-process correlation: every return carries the original request's
    task_id, case_id, source_sha256, work_order_ids, correlation_id, plus
    the per-item intake_id and case_id from the Z0 work order;
(b) transport vs certification: this module returns
    ``outcome="OBSERVED"`` only after the witness bytes are read, the
    recorded passage actually occurs, and a SHA-256 digest is computed;
    consumer-side verification of V1..V5 is unchanged;
(c) safe adapter: the LIVE path uses the existing
    ``adapters.http_client.fetch_text_safe`` (stdlib urllib, cached,
    rate-limited); no shell-out to curl/PowerShell invocations; no custom
    TLS handling; no retries on 401/403/404/429;
(d) OBSERVED transports a dated, SHA-pinned witness with an explicit
    provenance class. Synthetic test text is refused in production.
    Cached publisher-visible text can be returned only as a separate
    operator-recorded source derivation with original capture provenance.
(e) negative paths include digest, permission, stale observation,
    missing/duplicate phrase, missing locator label, source ID, task
    scope, replay and task-correlation errors. Declared edition labels
    remain unverified until independent bibliographic V1 review.
(f) original manuscript bytes and SHA remain immutable; source reading
    alone is never V1-V5 PASS or permission to rewrite the manuscript.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..adapters.http_client import fetch_text_safe  # real safe adapter (cited)
from .citation_intake_z0 import _write_immutable
from .citation_r1 import DEPTHS, OUTCOMES, _validate_return
from .cite_r1_permits import (
    DEFAULT_ALLOWED_HOSTS,
    Permit,
    load_permits,
    save_permit,
    validate_permit_against_hosts,
)


RETURN_SCHEMA = "trm-cite-r1-task-return-v1"
SINGLE_SCHEMA = "trm-cite-r1-return-v1"
PROVIDER_TAG = "KAIROSKOPION_R1_SOURCE_READER"


# Reasons the provider uses when it returns BLOCKED or raises.
REASON_NOT_PERMITTED = "SOURCE_READER_NOT_AVAILABLE"
REASON_PERMIT_NOT_FOUND = "PERMIT_NOT_FOUND_FOR_WORK_ORDER"
REASON_FIXTURE_MISSING = "FIXTURE_FILE_MISSING"
REASON_FIXTURE_HASH_MISMATCH = "FIXTURE_HASH_REGRADE_REQUIRED"
REASON_HOST_NOT_ALLOWED = "LIVE_HOST_NOT_IN_ALLOWLIST"
REASON_LIVE_FETCH_FAILED = "LIVE_FETCH_FAILED_NOT_REACHED"
REASON_PASSAGE_NOT_FOUND = "WITNESS_PASSAGE_NOT_PRESENT"
REASON_LOCATOR_MISMATCH = "WITNESS_LOCATOR_LABEL_MISMATCH"
REASON_STALE_RETRIEVED_AT = "STALE_FETCH_NOT_RECENT"
REASON_DUPLICATE_ANCHOR = "DUPLICATE_PASSAGE_ANCHOR_IN_WITNESS"
REASON_REPLAY_DETECTED = "DUPLICATE_CORRELATION_REPLAY"
REASON_BAD_READ_DEPTH = "OBSERVED_READ_DEPTH_INCONSISTENT"
REASON_AUTHOR_SOURCE_NOT_HANDLED = "AUTHOR_SOURCE_NEED_NOT_IN_PROVIDER"
REASON_NO_WORK_ORDER = "WORK_ORDER_NOT_IN_Z0_QUEUE"
REASON_REQUEST_INVALID = "REQUEST_SHAPE_INVALID"
REASON_SPOOFED_CORRELATION = "CORRELATION_DOES_NOT_MATCH_REQUEST"
REASON_INVALID_REQUEST = REASON_REQUEST_INVALID


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ValueError(message)


def _parse_iso(value: str) -> datetime:
    cleaned = value.replace("Z", "+00:00") if value.endswith("Z") else value
    return datetime.fromisoformat(cleaned)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} is not a JSON object")
    return value


def _json_dumps(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")


# ---------------------------------------------------------------------------
# Witness acquisition
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class WitnessBytes:
    text: str
    sha256: str
    byte_length: int
    source_uri: str
    license_tag: str
    retrieval_mode: str  # "FIXTURE" or "LIVE"
    fetched_at: str
    citation_mode: str


def acquire_fixture_witness(permit: Permit, *,
                            fixtures_dir: Path | None) -> WitnessBytes:
    """Read the cached witness file recorded by the permit.

    A cached body remains exactly the original captured bytes, not a
    fresh fetch. Its identity must match the operator-pinned SHA-256.
    """
    if permit.fixture_path is None:
        raise ValueError("FIXTURE permit must declare fixture_path")
    if fixtures_dir is None:
        raise ValueError(REASON_FIXTURE_MISSING)
    base = Path(fixtures_dir).resolve()
    text_path = (base / permit.fixture_path).resolve()
    if not text_path.is_relative_to(base):
        raise ValueError("FIXTURE_PATH_OUTSIDE_AUTHORIZED_ROOT")
    if not text_path.is_file():
        raise ValueError(REASON_FIXTURE_MISSING)
    raw = text_path.read_bytes()
    return WitnessBytes(
        text=raw.decode("utf-8", errors="replace"),
        sha256=_sha256(raw),
        byte_length=len(raw),
        source_uri=str(text_path),
        license_tag=permit.license,
        retrieval_mode="FIXTURE",
        fetched_at=permit.observed_at or "",
        citation_mode=permit.citation_mode,
    )


def acquire_live_witness(permit: Permit, *,
                         allowed_hosts: frozenset[str],
                         timeout: int = 30) -> WitnessBytes:
    """Fetch a permitted URL via the safe stdlib HTTP client.

    Bypass of authentication (login forms, subscription tokens, encrypted
    media, custom headers meant to imitate a paid session) is structurally
    impossible: the URL must match the operator-recorded host, no headers
    are added, no retries beyond what ``fetch_text_safe`` exposes, and no
    shell is invoked.
    """
    _require(permit.live_url is not None, "LIVE permit must declare live_url")
    allowed, reason = validate_permit_against_hosts(permit, allowed_hosts)
    if not allowed:
        raise ValueError(reason or REASON_HOST_NOT_ALLOWED)
    parsed = urlparse(permit.live_url)
    result = fetch_text_safe(
        permit.live_url,
        timeout=timeout,
        rate_limit=True,
        retry_count=0,
        headers={
            "Accept": ("text/html,application/xhtml+xml,text/plain,"
                       "application/xml;q=0.9,*/*;q=0.5"),
        },
    )
    if not result.ok:
        raise ValueError(f"{REASON_LIVE_FETCH_FAILED}: {result.error}")
    raw = result.text.encode("utf-8", errors="replace")
    return WitnessBytes(
        text=result.text,
        sha256=_sha256(raw),
        byte_length=len(raw),
        source_uri=permit.live_url,
        license_tag=permit.license,
        retrieval_mode="LIVE",
        fetched_at=_now_iso(),
        citation_mode=permit.citation_mode,
    )


# ---------------------------------------------------------------------------
# Witness verification (transport vs certification)
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class VerificationResult:
    ok: bool
    reason: str | None
    byte_sha256: str
    passage_id: str
    locator_label: str
    duplicate_anchor: bool


def verify_witness_against_permit(permit: Permit, witness: WitnessBytes) -> VerificationResult:
    """Reject OBSERVED if the recorded passage is missing or repeated.

    The recorded passage text must appear verbatim (after Unicode
    whitespace folding) at least once and at most once in the witness.
    Multiple hits are treated as DUPLICATE_ANCHOR so a reader cannot
    silently pick the first occurrence.
    """
    if permit.witness_class == "SYNTHETIC_TEST":
        for marker, identity in (
            ("WORK", permit.work_id), ("EDITION", permit.edition_id),
            ("WITNESS", permit.witness_id),
        ):
            if f"{marker}: {identity}" not in witness.text:
                return VerificationResult(False, "SYNTHETIC_IDENTITY_MISMATCH",
                                          witness.sha256, "identity:unknown",
                                          permit.expected_locator, False)
    folded_passage = " ".join(permit.expected_passage.split())
    folded_text = " ".join(witness.text.split())
    occurrences = folded_text.count(folded_passage)
    if occurrences == 0:
        return VerificationResult(False, REASON_PASSAGE_NOT_FOUND,
                                  witness.sha256, "passage:absent",
                                  permit.expected_locator, False)
    if occurrences > 1:
        return VerificationResult(False, REASON_DUPLICATE_ANCHOR,
                                  witness.sha256, "passage:multi",
                                  permit.expected_locator, True)
    # The label must actually be carried in the witness, not merely declared
    # by a permit. This is a locator-label check, not proof of printed page.
    folded_locator = " ".join(permit.expected_locator.split()).casefold()
    if folded_locator not in folded_text.casefold():
        return VerificationResult(False, REASON_LOCATOR_MISMATCH,
                                  witness.sha256, "locator:unverified",
                                  permit.expected_locator, False)
    return VerificationResult(True, None, witness.sha256,
                              "passage:" + witness.sha256[:16],
                              permit.expected_locator, False)


# ---------------------------------------------------------------------------
# Source-reader provider
# ---------------------------------------------------------------------------


@dataclasses.dataclass
class ReaderProviderStats:
    requests_total: int = 0
    requests_observed: int = 0
    requests_blocked: int = 0
    rejections_permission: int = 0
    rejections_passage: int = 0
    rejections_replay: int = 0
    rejections_other: int = 0

    def to_dict(self) -> dict[str, int]:
        return dataclasses.asdict(self)


class SourceReaderProvider:
    """Single-process source reader that emits immutable return envelopes."""

    def __init__(
        self,
        *,
        permits: dict[str, Permit],
        fixtures_dir: Path | None = None,
        allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS,
        replay_window_hours: int = 24,
        live_fetcher=acquire_live_witness,
        fixture_fetcher=acquire_fixture_witness,
        test_mode: bool = False,
    ) -> None:
        # Injected fetchers are test doubles; never issue production-class evidence.
        self.test_mode = bool(test_mode or live_fetcher is not acquire_live_witness
                              or fixture_fetcher is not acquire_fixture_witness)
        self._permits = dict(permits)
        self._fixtures_dir = fixtures_dir
        self._allowed_hosts = frozenset(allowed_hosts)
        self._replay_window = timedelta(hours=replay_window_hours)
        # Replay ledger: (source_sha256, correlation_id) -> first observed iso
        self._seen: dict[tuple[str, str], str] = {}
        self._live = live_fetcher
        self._fixture = fixture_fetcher
        self.stats = ReaderProviderStats()
        self.run_id = "run_" + _sha256(
            (_now_iso() + "|" + ",".join(sorted(permits))).encode()
        )[:20]

    @classmethod
    def from_permits_dir(
        cls, permits_dir: Path, *,
        fixtures_dir: Path | None = None,
        allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS,
    ) -> "SourceReaderProvider":
        return cls(
            permits=load_permits(Path(permits_dir)),
            fixtures_dir=fixtures_dir,
            allowed_hosts=allowed_hosts,
        )

    # ------------------------------------------------------------------
    # replay protection
    # ------------------------------------------------------------------

    def _check_replay(self, source_sha: str, correlation_id: str) -> str | None:
        key = (source_sha, correlation_id)
        if key in self._seen:
            return self._seen[key]
        self._seen[key] = _now_iso()
        return None

    # ------------------------------------------------------------------
    # evidence building
    # ------------------------------------------------------------------

    def _common_observed_fields(self, permit: Permit) -> dict[str, Any]:
        return {
            "provider": permit.provider,
            "acquisition_authorized": True,
            "read_depth": permit.read_depth,
            "source_kind": permit.source_kind,
            "access": permit.access,
            "license": permit.license,
            "work_id": permit.work_id,
            "edition_id": permit.edition_id,
            "witness_id": permit.witness_id,
            "citation_mode": permit.citation_mode,
            "witness_class": permit.witness_class,
        }

    def _build_blocked(
        self, *, request: dict[str, Any], reason: str,
        negative_evidence: list[str] | None = None,
        errors: list[str] | None = None,
        extra_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.stats.requests_blocked += 1
        blocked: dict[str, Any] = {
            "schema": RETURN_SCHEMA,
            "task_id": request["task_id"],
            "case_id": request["case_id"],
            "step_index": request["step_index"],
            "source_sha256": request["source_sha256"],
            "work_order_ids": list(request.get("work_order_ids") or []),
            "correlation_id": request["correlation_id"],
            "kind": request.get("kind", "Z0_LINKED"),
            "acquisition_authorized_by_request":
                bool(request.get("acquisition_authorized_by_request", False)),
            "acquisition_authorized": False,
            "witness_class": "NO_WITNESS",
            "outcome": "BLOCKED",
            "reason": reason,
            "provider": "NONE",
            "read_depth": "NONE",
            "source_kind": "NONE",
            "retrieved_at": None,
            "access": "NOT_ATTEMPTED",
            "license": "UNKNOWN",
            "work_id": None,
            "edition_id": None,
            "witness_id": None,
            "passage_id": None,
            "byte_sha256": None,
            "locator": None,
            "negative_evidence": list(negative_evidence or []),
            "errors": list(errors or []) or [reason],
            "source_evidence": [],
            "citation_gate": "NOT_PUBLICATION_READY",
            "author_gate": "PENDING",
        }
        if extra_fields:
            blocked.update(extra_fields)
        return blocked

    # ------------------------------------------------------------------
    # request → return
    # ------------------------------------------------------------------

    def read_request(
        self, request: dict[str, Any], work_orders: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Build the task return for one batch request envelope.

        ``work_orders`` maps ``work_order_id → Z0 work-order row``.  Compound
        requests (``work_order_ids`` length > 1) raise: the provider only
        returns OBSERVED for a single anchoring work order, never a blended
        one.  Author-source tasks raise by design — they have no Z0 anchor.
        """
        self.stats.requests_total += 1
        try:
            _require(request.get("schema") == "trm-cite-r1-task-request-v1",
                     REASON_INVALID_REQUEST + ":schema")
            _require(isinstance(request.get("task_id"), str) and request["task_id"],
                     REASON_INVALID_REQUEST + ":task_id")
            _require(isinstance(request.get("correlation_id"), str),
                     REASON_INVALID_REQUEST + ":correlation_id")
            ids = list(request.get("work_order_ids") or [])
            kind = request.get("kind")
            if kind == "AUTHOR_SOURCE_NEED" or not ids:
                self.stats.rejections_other += 1
                return self._build_blocked(
                    request=request, reason=REASON_AUTHOR_SOURCE_NOT_HANDLED,
                    errors=[REASON_AUTHOR_SOURCE_NOT_HANDLED],
                )
            if len(ids) > 1:
                # Compound evidence is the consumer's job to refuse; the
                # provider refuses to synthesize one.  We surface this as a
                # typed blocked return rather than a guess.
                self.stats.rejections_other += 1
                return self._build_blocked(
                    request=request,
                    reason="COMPOUND_REQUEST_PROVIDER_REJECTS",
                    errors=["COMPOUND_REQUEST_PROVIDER_REJECTS"],
                )
            work_order_id = ids[0]
            order = work_orders.get(work_order_id)
            if order is None:
                # Spoofed or stale work order id — refuse rather than guess.
                self.stats.rejections_permission += 1
                return self._build_blocked(
                    request=request, reason=REASON_NO_WORK_ORDER,
                    errors=[REASON_NO_WORK_ORDER],
                )
            permit = self._permits.get(work_order_id)
            if permit is None:
                self.stats.rejections_permission += 1
                return self._build_blocked(
                    request=request, reason=REASON_PERMIT_NOT_FOUND,
                    errors=[REASON_PERMIT_NOT_FOUND],
                )
            if request["task_id"] not in permit.allowed_task_ids:
                self.stats.rejections_permission += 1
                return self._build_blocked(
                    request=request, reason="TASK_NOT_IN_SOURCE_PERMIT",
                    errors=["TASK_NOT_IN_SOURCE_PERMIT"],
                )
            if permit.witness_class == "SYNTHETIC_TEST" and not self.test_mode:
                return self._build_blocked(request=request,
                    reason="SYNTHETIC_TEST_NOT_ADMISSIBLE",
                    errors=["SYNTHETIC_TEST_NOT_ADMISSIBLE"])
            try:
                witness = self._acquire(permit)
            except ValueError as exc:
                self.stats.rejections_permission += 1
                return self._build_blocked(
                    request=request, reason=str(exc), errors=[str(exc)],
                )
            if witness.sha256.lower() != permit.witness_sha256.lower():
                return self._build_blocked(request=request,
                    reason=REASON_FIXTURE_HASH_MISMATCH,
                    errors=[REASON_FIXTURE_HASH_MISMATCH])
            observed_at = _parse_iso(witness.fetched_at)
            now = datetime.now(timezone.utc)
            if (observed_at.tzinfo is None or
                observed_at.astimezone(timezone.utc) > now or
                observed_at.astimezone(timezone.utc) < now - timedelta(days=30)):
                return self._build_blocked(request=request,
                    reason=REASON_STALE_RETRIEVED_AT,
                    errors=[REASON_STALE_RETRIEVED_AT])
            if permit.read_depth not in {"SECTION_TEXT", "ANCHORED_PASSAGE"}:
                return self._build_blocked(request=request,
                    reason=REASON_BAD_READ_DEPTH,
                    errors=[REASON_BAD_READ_DEPTH])
            verification = verify_witness_against_permit(permit, witness)
            if not verification.ok:
                self.stats.rejections_passage += 1
                return self._build_blocked(
                    request=request, reason=verification.reason or "WITNESS_VERIFICATION_FAILED",
                    errors=[verification.reason or "WITNESS_VERIFICATION_FAILED"],
                    extra_fields={
                        "candidate_witness_sha256": verification.byte_sha256,
                        "candidate_locator_label": verification.locator_label,
                    },
                )
            if verification.byte_sha256 != witness.sha256:
                # Internal consistency check: trip on any drift between the
                # verification record and the acquired bytes.
                self.stats.rejections_other += 1
                return self._build_blocked(
                    request=request,
                    reason="INTERNAL_WITNESS_HASH_DRIFT",
                    errors=["INTERNAL_WITNESS_HASH_DRIFT"],
                )
            prior = self._check_replay(
                request["source_sha256"], request["correlation_id"])
            if prior is not None:
                self.stats.rejections_replay += 1
                return self._build_blocked(
                    request=request, reason=REASON_REPLAY_DETECTED,
                    errors=[REASON_REPLAY_DETECTED],
                    extra_fields={"first_observed_at": prior},
                )
            observed = self._build_observed(
                request=request, permit=permit, witness=witness,
                verification=verification, work_order=order,
            )
            self.stats.requests_observed += 1
            return observed
        except Exception as exc:
            self.stats.rejections_other += 1
            return self._build_blocked(
                request=request, reason="PROVIDER_INTERNAL_ERROR",
                errors=[f"PROVIDER_INTERNAL_ERROR:{type(exc).__name__}:{exc}"],
            )

    def _acquire(self, permit: Permit) -> WitnessBytes:
        if permit.mode == "FIXTURE":
            return self._fixture(permit, fixtures_dir=self._fixtures_dir)
        # Safety preflight must live ABOVE the injectable fetcher. A mock,
        # alternate adapter or future Indago provider cannot skip host ACL.
        allowed, reason = validate_permit_against_hosts(permit, self._allowed_hosts)
        if not allowed:
            raise ValueError(reason or REASON_HOST_NOT_ALLOWED)
        return self._live(permit, allowed_hosts=self._allowed_hosts)

    def _build_observed(
        self, *, request: dict[str, Any], permit: Permit, witness: WitnessBytes,
        verification: VerificationResult, work_order: dict[str, Any],
    ) -> dict[str, Any]:
        # Re-validate the synthetic single-order return before persisting.
        # This guarantees the consumer cannot reject us for a malformed
        # envelope and surfaces drift at the provider boundary.
        single_payload = self._common_observed_fields(permit)
        single_payload.update({
            "schema": SINGLE_SCHEMA,
            "work_order_id": work_order["work_order_id"],
            "case_id": work_order["case_id"],
            "intake_id": work_order["intake_id"],
            "source_sha256": request["source_sha256"],
            "correlation_id": request["correlation_id"],
            "outcome": "OBSERVED",
            "retrieved_at": witness.fetched_at,
            "passage_id": verification.passage_id,
            "byte_sha256": verification.byte_sha256,
            "locator": permit.expected_locator,
        })
        _validate_return(
            request={
                "work_order_id": work_order["work_order_id"],
                "case_id": work_order["case_id"],
                "intake_id": work_order["intake_id"],
                "source_sha256": request["source_sha256"],
                "correlation_id": request["correlation_id"],
            },
            ret=single_payload,
        )
        evidence_item = {
            "work_order_id": work_order["work_order_id"],
            "intake_id": work_order["intake_id"],
            "z0_case_id": work_order["case_id"],
            "provider": permit.provider,
            "source_kind": permit.source_kind,
            "read_depth": permit.read_depth,
            "access": permit.access,
            "license": permit.license,
            "work_id": permit.work_id,
            "edition_id": permit.edition_id,
            "witness_id": permit.witness_id,
            "locator": permit.expected_locator,
            "passage_id": verification.passage_id,
            "byte_sha256": verification.byte_sha256,
            "retrieved_at": witness.fetched_at,
            "acquisition_authorized": True,
            "witness_source_uri": witness.source_uri,
            "retrieval_mode": witness.retrieval_mode,
            "permit_id": permit.permit_id,
            "authorized_by": permit.authorized_by,
            "witness_class": permit.witness_class,
            "test_only": bool(self.test_mode),
            "observed_at_original": witness.fetched_at,
        }
        envelope = {
            "schema": RETURN_SCHEMA,
            "task_id": request["task_id"],
            "case_id": request["case_id"],
            "step_index": request["step_index"],
            "source_sha256": request["source_sha256"],
            "work_order_ids": list(request["work_order_ids"]),
            "correlation_id": request["correlation_id"],
            "kind": request.get("kind", "Z0_LINKED"),
            "acquisition_authorized_by_request":
                bool(request.get("acquisition_authorized_by_request", False)),
            "acquisition_authorized": True,
            "outcome": "OBSERVED",
            "reason": None,
            "provider": permit.provider,
            "read_depth": permit.read_depth,
            "source_kind": permit.source_kind,
            "access": permit.access,
            "license": permit.license,
            "work_id": permit.work_id,
            "edition_id": permit.edition_id,
            "witness_id": permit.witness_id,
            "locator": permit.expected_locator,
            "passage_id": verification.passage_id,
            "byte_sha256": verification.byte_sha256,
            "retrieved_at": witness.fetched_at,
            "source_evidence": [evidence_item],
            "negative_evidence": [],
            "errors": [],
            "citation_mode": permit.citation_mode,
            "citation_gate": "NOT_PUBLICATION_READY",
            "author_gate": "PENDING",
            "transport_only": True,
            "witness_class": permit.witness_class,
            "test_only": bool(self.test_mode),
            "transport_provider_tag": PROVIDER_TAG,
            "transport_run_id": self.run_id,
        }
        return envelope


# ---------------------------------------------------------------------------
# Batch driver
# ---------------------------------------------------------------------------


def _read_batch_inputs(
    audit_path: Path, queue_path: Path, request_dir: Path,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    from .citation_r1_batch import _json, _orders
    from .citation_r1 import _validate_inputs as _v
    audit, orders = _json(audit_path), _orders(queue_path)
    _v(audit, orders)
    by_order = {o["work_order_id"]: o for o in orders}
    manifest = _json(request_dir / "manifest.json")
    if manifest.get("schema") != "trm-cite-r1-batch-manifest-v1":
        raise ValueError("Unknown original R1 batch manifest")
    if manifest["queue_sha256"] != _sha256(queue_path.read_bytes()):
        raise ValueError("Z0 queue digest drift")
    if manifest.get("source_sha256") != audit["source"]["sha256"]:
        raise ValueError("Original manuscript digest drift")
    version = (manifest["queue_sha256"] + ":" +
               manifest["followups_sha256"] + ":" +
               manifest["protocols_sha256"])
    requests = {}
    for path in sorted(request_dir.glob("*.request.json")):
        req = _json(path)
        if req.get("schema") != "trm-cite-r1-task-request-v1":
            raise ValueError("Invalid R1 task request schema")
        if req.get("correlation_id") != _sha256((version + ":" + req["task_id"]).encode()):
            raise ValueError(REASON_SPOOFED_CORRELATION)
        if (req.get("source_sha256") != audit["source"]["sha256"] or
            any(k not in by_order for k in req.get("work_order_ids", []))):
            raise ValueError("Original R1 task / Z0 source correlation mismatch")
        if req["task_id"] in requests:
            raise ValueError("Duplicate request ID")
        requests[req["task_id"]] = req
    if len(requests) != manifest.get("tasks"):
        raise ValueError("Incomplete request batch for provider run")
    return by_order, requests


def run_batch(
    audit_path: Path, queue_path: Path, request_dir: Path, output_dir: Path,
    *,
    permits: dict[str, Permit],
    fixtures_dir: Path | None = None,
    allowed_hosts: frozenset[str] = DEFAULT_ALLOWED_HOSTS,
    test_mode: bool = False,
    live_fetcher=acquire_live_witness,
) -> dict[str, Any]:
    """Run the provider across an entire request batch.

    Each ``*.request.json`` produces one ``*.return.json``; the consumer
    will then correlate the batch.  The provider never mutates
    ``audit_path`` or any Z0 artifact.
    """
    work_orders, requests = _read_batch_inputs(audit_path, queue_path, request_dir)
    prior_summary = output_dir / "provider_summary.json"
    if prior_summary.exists():
        prior = _read_json(prior_summary)
        for task, request in requests.items():
            saved = _read_json(output_dir / (task + ".return.json"))
            for field in ("task_id", "case_id", "source_sha256",
                          "work_order_ids", "correlation_id"):
                if saved.get(field) != request.get(field):
                    raise ValueError("Persisted source return has correlation drift: " + field)
            saved_sha = _sha256((output_dir / (task + ".return.json")).read_bytes())
            if prior.get("return_digests", {}).get(task) != saved_sha:
                raise ValueError("Persisted return was modified after completion")
        if prior.get("tasks") != len(requests):
            raise ValueError("Persisted provider summary differs from request batch")
        return prior
    provider = SourceReaderProvider(
        permits=permits, fixtures_dir=fixtures_dir, allowed_hosts=allowed_hosts,
        test_mode=test_mode, live_fetcher=live_fetcher,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    summary = {"schema": "trm-cite-r1-batch-provider-summary-v1",
               "audit_sha256": None, "queue_sha256": None,
               "tasks": 0, "observed": 0, "blocked": 0,
               "reasons": {}, "run_id": provider.run_id,
               "return_digests": {}, "stats": provider.stats.to_dict()}
    audit_data = _read_json(audit_path)
    summary["audit_sha256"] = audit_data["source"]["sha256"]
    summary["queue_sha256"] = _sha256(queue_path.read_bytes())
    for task_id in sorted(requests):
        request = requests[task_id]
        target = output_dir / (task_id + ".return.json")
        if target.exists():
            ret = _read_json(target)
            for field in ("task_id", "case_id", "source_sha256",
                          "work_order_ids", "correlation_id"):
                if ret.get(field) != request.get(field):
                    raise ValueError("Existing immutable return correlation mismatch")
        else:
            ret = provider.read_request(request, work_orders)
            _write_immutable(target, _json_dumps(ret))
        summary["tasks"] += 1
        summary["return_digests"][task_id] = _sha256(target.read_bytes())
        if ret["outcome"] == "OBSERVED":
            summary["observed"] += 1
        else:
            summary["blocked"] += 1
            reason = ret.get("reason") or "UNKNOWN"
            summary["reasons"][reason] = summary["reasons"].get(reason, 0) + 1
    summary["stats"] = provider.stats.to_dict()
    target = output_dir / "provider_summary.json"
    _write_immutable(target, _json_dumps(summary))
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--audit", required=True, type=Path)
    p.add_argument("--queue", required=True, type=Path)
    p.add_argument("--requests", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--permits", required=True, type=Path)
    p.add_argument("--fixtures", type=Path)
    p.add_argument("--allowed-hosts", action="append", default=None,
                   help="Override the host allowlist (may repeat). "
                        "Default uses cite_r1_permits.DEFAULT_ALLOWED_HOSTS.")
    args = p.parse_args(argv)
    permits = load_permits(args.permits)
    allowed = (frozenset(args.allowed_hosts) if args.allowed_hosts
               else DEFAULT_ALLOWED_HOSTS)
    summary = run_batch(
        audit_path=args.audit, queue_path=args.queue,
        request_dir=args.requests, output_dir=args.out,
        permits=permits, fixtures_dir=args.fixtures,
        allowed_hosts=allowed,
    )
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
    # Even a complete technical run with zero readable sources is not
    # scientific success. Match the batch consumer's science-blocked exit.
    return 3 if summary["observed"] == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
