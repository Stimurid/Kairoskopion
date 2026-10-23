"""Stage-operation driver for the MAI-batch Trimurti pre-author gate.

This module sits between the existing ``trimurti_scheduler`` state machine
and the per-phase real operations that must actually be performed.

The trimurti scheduler accepts ``evidence_refs`` as input and stamps them
into a phase checkpoint. That is necessary, but it leaves a loophole: a
free-form string like ``src:fake`` or ``arbitrary:text:0`` can be recorded
as an operation receipt. This module closes that loophole by:

* Requiring every ``evidence_ref`` to parse as a strictly-typed
  ``EvidenceRef`` triple of ``(kind, sha256[:16], source_kind)``.
* Requiring every checkpoint completion to carry an ``OperationDigest``
  documenting who did what: provider, command, input/output SHA-256,
  started/finished timestamps and a result fingerprint.
* Rejecting stub strings such as ``src:fake``, empty values, and
  whitespace-only entries — they can never reach
  ``CHECKPOINT_STATUS_COMPLETED``.
* Giving each Trimurti phase a typed ``StageAdapter`` so the per-phase
  operation is explicit and adapter-swappable, instead of letting the
  scheduler silently accept evidence supplied from outside.

The driver is deliberately the thin glue layer: every real WhiteCrow /
Indago / Kairon operation owns its own source-root, command line, and
diagnostic path. This module's job is to make the gate observable and
honest, not to invent new facts about the world. When a real source
root is not available, the adapter must return ``StageResult.HOLD`` with
an explicit refusal code; never a fabricated ``completed``.

Roadmap (deferred beyond this slice):

* Real Indago/WhiteCrow adapters (only stubs exist here).
* Real Kairon journal-world challenge adapter (awaiting an authorized
  source root).
* Real scholarly_opposition adapter (awaiting a verified citation set
  pointer).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import re
from typing import Any, Iterable, Protocol

from .trimurti_scheduler import (
    CHECKPOINT_STATUS_COMPLETED,
    CHECKPOINT_STATUS_FAILED,
    CHECKPOINT_STATUS_HOLD,
    CHECKPOINT_TERMINAL_STATUSES,
    PHASE_ORDER,
    PhaseName,
    REFUSAL_EMPTY_EVIDENCE,
    REFUSAL_EMPTY_SCHOLARLY_EVIDENCE,
    REFUSAL_STALE_REPLAY,
    RouteRecord,
    TrimurtiBatchPlan,
    advance_phase,
    compute_route_event_hash,
)
from .w12_importer import (
    SOURCE_KIND_BLOCKED,
    SOURCE_KIND_FIXTURE,
    SOURCE_KIND_REAL,
    W12Record,
)


# ---------------------------------------------------------------------------
# Module-level constants and refusal codes.
# ---------------------------------------------------------------------------

# Evidence-ref contract: a parseable evidence_ref is `kind:<sha16>:<source_kind>`.
EVIDENCE_REF_PATTERN = re.compile(
    r"^(?P<kind>[a-z][a-z0-9_]{1,32}):(?P<sha>[0-9a-f]{16,64}):(?P<source_kind>"
    + "|".join(re.escape(k) for k in (SOURCE_KIND_REAL, SOURCE_KIND_FIXTURE, SOURCE_KIND_BLOCKED))
    + r")$"
)

# A placeholder/stub evidence_ref is anything that matches a `src:` prefix
# without a real SHA-256 digest. The exact strings flagged here are the
# ones that have been used historically as placeholders; the contract
# itself forbids any string that does not parse via EVIDENCE_REF_PATTERN.
EVIDENCE_REF_FORBIDDEN_LITERALS: frozenset[str] = frozenset(
    {
        "src:fake",
        "src:placeholder",
        "src:none",
        "src:unknown",
        "evidence:placeholder",
        "evidence:fake",
        "",
    }
)

# Refusal codes this module owns. Trimurti scheduler codes are kept
# separate so a downgrade of upstream policy never silently erases this
# module's per-stage guard.
REFUSAL_EVIDENCE_REF_INVALID = "EVIDENCE_REF_FORMAT_INVALID"
REFUSAL_EVIDENCE_REF_STUB = "EVIDENCE_REF_STUB_REJECTED"
REFUSAL_NEEDS_REAL_OPERATION_ADAPTER = "REAL_OPERATION_ADAPTER_REQUIRED"
REFUSAL_SOURCE_BYTES_MISSING = "SOURCE_BYTES_PERMISSION_OR_PATH_FAILED"
REFUSAL_OPERATION_DIGEST_MISSING = "OPERATION_DIGEST_REQUIRED"


# Phases that this driver knows how to execute with a real adapter stub.
# All other phases require explicit REAL adapter implementation; today
# every entry below returns HOLD with REFUSAL_NEEDS_REAL_OPERATION_ADAPTER
# unless the operator points the source_root at verified bytes.
_PHASES_WITH_REAL_ADAPTER: frozenset[str] = frozenset(
    {
        PhaseName.SOURCE_EVIDENCE.value,
        PhaseName.SCHOLARLY_CHALLENGE.value,
    }
)


# ---------------------------------------------------------------------------
# Helpers.
# ---------------------------------------------------------------------------


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Evidence-ref contract.
# ---------------------------------------------------------------------------


@dataclass
class EvidenceRef:
    """Strictly typed evidence_ref triple.

    Free-form strings like ``src:fake`` are not valid EvidenceRefs; they
    must be rejected by ``parse_evidence_ref`` so that no operation
    receipt can be silently faked into a phase checkpoint.
    """

    kind: str
    sha256_short: str
    source_kind: str

    def __post_init__(self) -> None:
        if not self.kind or not self.sha256_short or not self.source_kind:
            raise ValueError("EvidenceRef fields must be non-empty")
        if self.source_kind not in {SOURCE_KIND_REAL, SOURCE_KIND_FIXTURE, SOURCE_KIND_BLOCKED}:
            raise ValueError(
                f"invalid source_kind for EvidenceRef: {self.source_kind!r} "
                "(expected REAL_AUTHORIZED_BYTES | FIXTURE_NOT_REAL_DATA | BLOCKED_PERMISSION)"
            )
        if not re.fullmatch(r"[0-9a-f]{16,64}", self.sha256_short):
            raise ValueError(
                f"invalid sha256_short: {self.sha256_short!r} "
                "(must be lowercase hex, 16..64 chars)"
            )

    @property
    def canonical(self) -> str:
        return f"{self.kind}:{self.sha256_short}:{self.source_kind}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def parse_evidence_ref(value: Any) -> EvidenceRef:
    """Parse a string into an EvidenceRef, or raise ValueError.

    Anything that does not match ``kind:<sha16>:<source_kind>`` is
    rejected. ``src:fake`` and the other stub literals in
    ``EVIDENCE_REF_FORBIDDEN_LITERALS`` are explicitly rejected with
    REFUSAL_EVIDENCE_REF_STUB regardless of whether they happen to match
    the regex shape.
    """

    if not isinstance(value, str):
        raise ValueError(
            f"{REFUSAL_EVIDENCE_REF_INVALID}: evidence_ref must be str, "
            f"got {type(value).__name__}"
        )
    stripped = value.strip()
    if not stripped or stripped in EVIDENCE_REF_FORBIDDEN_LITERALS:
        raise ValueError(
            f"{REFUSAL_EVIDENCE_REF_STUB}: evidence_ref {value!r} is a "
            "stub/placeholder; it cannot be promoted to a real operation "
            "receipt"
        )
    match = EVIDENCE_REF_PATTERN.match(stripped)
    if not match:
        raise ValueError(
            f"{REFUSAL_EVIDENCE_REF_INVALID}: evidence_ref {value!r} does "
            "not match kind:<sha16>:<source_kind> contract"
        )
    return EvidenceRef(
        kind=match.group("kind"),
        sha256_short=match.group("sha"),
        source_kind=match.group("source_kind"),
    )


def parse_evidence_refs(values: Iterable[Any]) -> list[EvidenceRef]:
    """Strictly parse every value; no partial success is permitted."""

    out: list[EvidenceRef] = []
    errors: list[str] = []
    for v in values:
        try:
            out.append(parse_evidence_ref(v))
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError("; ".join(errors))
    return out


def is_valid_evidence_ref(value: Any) -> bool:
    try:
        parse_evidence_ref(value)
    except ValueError:
        return False
    return True


def validate_evidence_refs_for_phase(
    phase: PhaseName | str, refs: list[EvidenceRef]
) -> tuple[bool, list[str]]:
    """Phase-specific guard on a *parsed* list of EvidenceRefs.

    Returns ``(ok, errors)``. Even with valid format, an empty list is a
    hard failure (this is the upstream
    ``REFUSAL_EMPTY_EVIDENCE``/``REFUSAL_EMPTY_SCHOLARLY_EVIDENCE``
    invariant re-expressed at the evidence-ref layer).
    """

    errors: list[str] = []
    if not refs:
        empty_code = (
            REFUSAL_EMPTY_SCHOLARLY_EVIDENCE
            if phase == PhaseName.SCHOLARLY_CHALLENGE.value
            else REFUSAL_EMPTY_EVIDENCE
        )
        errors.append(
            f"{empty_code}: no valid evidence_refs after validation"
        )
        return False, errors
    # Per-phase source_kind discipline:
    if phase == PhaseName.SOURCE_EVIDENCE.value:
        for ref in refs:
            if ref.source_kind not in {SOURCE_KIND_REAL, SOURCE_KIND_FIXTURE}:
                errors.append(
                    f"source_evidence evidence_ref must be REAL or "
                    f"FIXTURE, got {ref.source_kind!r}"
                )
    elif phase == PhaseName.SCHOLARLY_CHALLENGE.value:
        for ref in refs:
            if ref.source_kind != SOURCE_KIND_REAL:
                errors.append(
                    f"scholarly_challenge evidence_ref must be "
                    f"REAL_AUTHORIZED_BYTES (fixture cannot count as "
                    f"scholarly opposition); got {ref.source_kind!r}"
                )
    return not errors, errors


# ---------------------------------------------------------------------------
# Operation digest.
# ---------------------------------------------------------------------------


@dataclass
class OperationDigest:
    """Receipt describing one actual stage operation invocation.

    This is the audit anchor for every phase completion: a CHECKPOINT
    cannot be promoted to COMPLETED without a non-null OperationDigest
    whose provider, command, input/output SHA-256, and result fingerprint
    are recorded. Without a digest the evidence is just a string, which
    is exactly the promotion loophole this module exists to close.
    """

    provider: str
    command: str
    input_sha256: str
    output_sha256: str
    result_fingerprint: str
    started_at: str
    finished_at: str
    input_bytes: int = 0
    output_bytes: int = 0
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.provider or not self.command:
            raise ValueError("OperationDigest provider and command must be non-empty")
        if not re.fullmatch(r"[0-9a-f]{64}", self.input_sha256):
            raise ValueError(
                f"invalid input_sha256: {self.input_sha256!r} (must be lowercase hex64)"
            )
        if not re.fullmatch(r"[0-9a-f]{64}", self.output_sha256):
            raise ValueError(
                f"invalid output_sha256: {self.output_sha256!r} (must be lowercase hex64)"
            )
        if not re.fullmatch(r"[0-9a-f]{16,64}", self.result_fingerprint):
            raise ValueError(
                f"invalid result_fingerprint: {self.result_fingerprint!r} "
                "(must be lowercase hex, 16..64 chars)"
            )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def make_operation_digest(
    *,
    provider: str,
    command: str,
    input_bytes: bytes,
    output_bytes: bytes,
    started_at: str | None = None,
    finished_at: str | None = None,
    notes: Iterable[str] = (),
) -> OperationDigest:
    """Convenience builder that hashes the bytes for you."""

    start = started_at or _now()
    end = finished_at or _now()
    input_sha = _digest_bytes(input_bytes)
    output_sha = _digest_bytes(output_bytes)
    fingerprint = _digest_string("|".join([provider, command, input_sha, output_sha]))[:32]
    return OperationDigest(
        provider=provider,
        command=command,
        input_sha256=input_sha,
        output_sha256=output_sha,
        result_fingerprint=fingerprint,
        started_at=start,
        finished_at=end,
        input_bytes=len(input_bytes),
        output_bytes=len(output_bytes),
        notes=list(notes),
    )


# ---------------------------------------------------------------------------
# Stage result and adapter protocol.
# ---------------------------------------------------------------------------


@dataclass
class StageResult:
    """What a StageAdapter yields for one (route, phase) call.

    The driver consumes this and decides whether to advance the trimurti
    scheduler to COMPLETED, HOLD, or FAILED — never to silently promote.
    """

    status: str
    evidence_refs: list[EvidenceRef] = field(default_factory=list)
    refusal_code: str | None = None
    refusal_text: str | None = None
    operation_digest: OperationDigest | None = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in {
            CHECKPOINT_STATUS_COMPLETED,
            CHECKPOINT_STATUS_HOLD,
            CHECKPOINT_STATUS_FAILED,
        }:
            raise ValueError(
                f"invalid StageResult.status: {self.status!r} "
                "(expected completed | hold | failed)"
            )
        if self.status == CHECKPOINT_STATUS_COMPLETED:
            if not self.evidence_refs:
                raise ValueError(
                    f"{REFUSAL_EVIDENCE_REF_INVALID}: StageResult.status=completed "
                    "requires non-empty evidence_refs"
                )
            if self.operation_digest is None:
                raise ValueError(
                    f"{REFUSAL_OPERATION_DIGEST_MISSING}: StageResult.status=completed "
                    "requires a non-null OperationDigest"
                )

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "evidence_refs": [ref.to_dict() for ref in self.evidence_refs],
            "refusal_code": self.refusal_code,
            "refusal_text": self.refusal_text,
            "operation_digest": (
                self.operation_digest.to_dict() if self.operation_digest is not None else None
            ),
            "notes": list(self.notes),
        }


class StageAdapter(Protocol):
    """Per-phase stage operation. ``execute`` is the only required entry."""

    def execute(
        self,
        *,
        route: RouteRecord,
        w12_record: W12Record,
        phase: PhaseName,
        source_root: "SourceRoot | None",
    ) -> StageResult:
        ...

    @property
    def provider_name(self) -> str:
        ...


# ---------------------------------------------------------------------------
# Source root: a thin wrapper around authorized bytes + receipt.
# ---------------------------------------------------------------------------


@dataclass
class SourceRoot:
    """Concrete bytes + provenance for an authorized source root.

    The class is read-only by design: we never mutate the source.
    Pointing ``SourceRoot(path=...)`` at a non-existent / unreadable /
    non-UTF-8 file yields ``status=SOURCE_KIND_BLOCKED`` so the driver
    can promote nothing without explicit permission.
    """

    path: str
    source_kind: str
    full_sha256: str
    first_bytes_sha256: str
    byte_count: int
    blocked_reason: str | None = None
    permission_failure: str | None = None

    @classmethod
    def from_path(cls, path: str | "Path") -> "SourceRoot":
        from pathlib import Path as _Path

        p = _Path(path)
        if not p.is_file():
            return cls(
                path=str(p),
                source_kind=SOURCE_KIND_BLOCKED,
                full_sha256="",
                first_bytes_sha256="",
                byte_count=0,
                blocked_reason="source_path_not_file",
                permission_failure=f"source path is not a file: {p}",
            )
        try:
            data = p.read_bytes()
        except OSError as exc:
            return cls(
                path=str(p),
                source_kind=SOURCE_KIND_BLOCKED,
                full_sha256="",
                first_bytes_sha256="",
                byte_count=0,
                blocked_reason="authorized_path_unreadable",
                permission_failure=f"OSError reading {p}: {exc}",
            )
        if not data:
            return cls(
                path=str(p),
                source_kind=SOURCE_KIND_BLOCKED,
                full_sha256="",
                first_bytes_sha256="",
                byte_count=0,
                blocked_reason="source_path_empty",
                permission_failure=f"source file is empty: {p}",
            )
        return cls(
            path=str(p),
            source_kind=SOURCE_KIND_REAL,
            full_sha256=_digest_bytes(data),
            first_bytes_sha256=_digest_bytes(data[:4096]),
            byte_count=len(data),
        )

    @classmethod
    def fixture_only(cls, marker: str) -> "SourceRoot":
        """Synthetic source root for fixture-mode tests.

        The marker is hashed so each call gets a distinct root; the
        resulting SourceRoot is honestly labelled
        ``FIXTURE_NOT_REAL_DATA`` and never counts as scholarly source.
        """

        sha = _digest_string(marker)
        return cls(
            path=None,  # type: ignore[arg-type]
            source_kind=SOURCE_KIND_FIXTURE,
            full_sha256=sha,
            first_bytes_sha256=_digest_string(sha + ":first"),
            byte_count=0,
        )

    @property
    def is_real(self) -> bool:
        return self.source_kind == SOURCE_KIND_REAL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Concrete adapters.
# ---------------------------------------------------------------------------


class SourceBytesStageAdapter:
    """SOURCE_EVIDENCE stage adapter that verifies the W12 source bytes.

    This is the only adapter that can produce COMPLETED on a non-stub
    source. It does NOT perform any external fetch; it reads the local
    authorized source file (if available), verifies that the route's
    source_full_sha256 matches, and yields:

    * ``COMPLETED`` with REAL evidence_refs on a verified REAL source,
    * ``HOLD`` with REFUSAL_SOURCE_BYTES_MISSING on a BLOCKED source root,
    * ``HOLD`` with REFUSAL_NEEDS_REAL_OPERATION_ADAPTER on FIXTURE mode
      (fixture cannot stand as real scientific source — see
      CLAUDE.md "no fake references" rule).
    """

    PROVIDER = "kairoskopion.stage_operation.SourceBytesStageAdapter"

    @property
    def provider_name(self) -> str:
        return self.PROVIDER

    def execute(
        self,
        *,
        route: RouteRecord,
        w12_record: W12Record,
        phase: PhaseName,
        source_root: SourceRoot | None,
    ) -> StageResult:
        if phase != PhaseName.SOURCE_EVIDENCE:
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
                refusal_text=(
                    f"SourceBytesStageAdapter cannot execute phase "
                    f"{phase.value!r}"
                ),
                notes=[f"provider={self.provider_name}"],
            )

        if source_root is None:
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_SOURCE_BYTES_MISSING,
                refusal_text=(
                    "no SourceRoot was provided for SOURCE_EVIDENCE; "
                    "operator must point at authorized W12 bytes"
                ),
                notes=[
                    f"route_id={route.route_id}",
                    f"w12_source_kind={w12_record.source_kind}",
                ],
            )

        if source_root.source_kind == SOURCE_KIND_BLOCKED:
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_SOURCE_BYTES_MISSING,
                refusal_text=(
                    f"source_root BLOCKED: {source_root.blocked_reason!r} — "
                    f"{source_root.permission_failure!r}"
                ),
                notes=[
                    f"route_id={route.route_id}",
                    f"source_root_path={source_root.path}",
                ],
            )

        if source_root.source_kind == SOURCE_KIND_FIXTURE:
            # Fixture bytes are an honest label, but cannot stand as
            # real scholarly source. Always HOLD.
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
                refusal_text=(
                    "fixture source_root can never satisfy "
                    "SOURCE_EVIDENCE; operation requires a REAL_AUTHORIZED_BYTES root"
                ),
                notes=[
                    f"route_id={route.route_id}",
                    f"source_root_kind={source_root.source_kind}",
                ],
            )

        # REAL source. Verify the route's source bytes match the root.
        if (
            w12_record.source_full_sha256
            and w12_record.source_full_sha256 != source_root.full_sha256
        ):
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_SOURCE_BYTES_MISSING,
                refusal_text=(
                    f"route source_full_sha256 "
                    f"{w12_record.source_full_sha256!r} does not match "
                    f"source_root.full_sha256 {source_root.full_sha256!r}; "
                    "cannot verify provenance"
                ),
                notes=[
                    f"route_id={route.route_id}",
                    f"source_root_path={source_root.path}",
                ],
            )

        # Build evidence_ref + digest. The evidence_ref claims the route's
        # source_full_sha256 with kind=`w12_source` and source_kind=`REAL`.
        evidence = EvidenceRef(
            kind="w12_source",
            sha256_short=w12_record.source_full_sha256[:32]
            if w12_record.source_full_sha256
            else source_root.full_sha256[:32],
            source_kind=SOURCE_KIND_REAL,
        )
        command = json.dumps(
            {
                "provider": self.provider_name,
                "phase": phase.value,
                "route_id": route.route_id,
                "source_path": source_root.path,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        # The "output" of SOURCE_EVIDENCE is the verification receipt:
        output_payload = json.dumps(
            {
                "verified": True,
                "route_id": route.route_id,
                "source_full_sha256": source_root.full_sha256,
                "source_first_bytes_sha256": source_root.first_bytes_sha256,
                "byte_count": source_root.byte_count,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        digest = make_operation_digest(
            provider=self.provider_name,
            command=command,
            input_bytes=command.encode("utf-8"),
            output_bytes=output_payload.encode("utf-8"),
        )
        return StageResult(
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=[evidence],
            refusal_code=None,
            refusal_text=None,
            operation_digest=digest,
            notes=[
                f"route_id={route.route_id}",
                f"source_root_byte_count={source_root.byte_count}",
            ],
        )


class ScholarlyChallengeStageAdapter:
    """SCHOLARLY_CHALLENGE stage adapter placeholder.

    A genuine scholarly-challenge adapter must consume a verified
    citation set pointer (real prior-art corpus) and produce at least
    one reproducible counterargument or an explicit negative result.
    Until such an adapter is supplied, this class exists so any driver
    call lands in a typed HOLD with an explicit refusal code, never a
    fabricated COMPLETED.
    """

    PROVIDER = "kairoskopion.stage_operation.ScholarlyChallengeStageAdapter"

    @property
    def provider_name(self) -> str:
        return self.PROVIDER

    def execute(
        self,
        *,
        route: RouteRecord,
        w12_record: W12Record,
        phase: PhaseName,
        source_root: SourceRoot | None,
    ) -> StageResult:
        if phase != PhaseName.SCHOLARLY_CHALLENGE:
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
                refusal_text=(
                    f"ScholarlyChallengeStageAdapter cannot execute phase "
                    f"{phase.value!r}"
                ),
                notes=[f"provider={self.provider_name}"],
            )
        # Scholarly challenge requires REAL_AUTHORIZED_BYTES (the prior
        # art corpus), not fixture. We don't have such a corpus in this
        # slice; refuse and let the route land on HOLD.
        if source_root is None or source_root.source_kind != SOURCE_KIND_REAL:
            return StageResult(
                status=CHECKPOINT_STATUS_HOLD,
                refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
                refusal_text=(
                    "scholarly_challenge requires a verified citation-set "
                    "SourceRoot with REAL_AUTHORIZED_BYTES; this slice "
                    "does not implement the art/opposition corpus "
                    "adapter (deferred to a follow-up issue). Marking HOLD "
                    "rather than fabricating a completed result."
                ),
                notes=[
                    f"provider={self.provider_name}",
                    f"route_id={route.route_id}",
                    f"source_root_kind={source_root.source_kind if source_root else 'None'}",
                ],
            )
        # Even with a REAL SourceRoot, this stub adapter refuses by
        # default — a real challenge needs explicit adapter wiring.
        return StageResult(
            status=CHECKPOINT_STATUS_HOLD,
            refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
            refusal_text=(
                "scholarly_challenge adapter is a stub; route marked HOLD "
                "until a real prior-art corpus is wired into this driver"
            ),
            notes=[f"provider={self.provider_name}"],
        )


# ---------------------------------------------------------------------------
# drive_stage: the thin glue layer.
# ---------------------------------------------------------------------------


def drive_stage(
    plan: TrimurtiBatchPlan,
    *,
    route_id: str,
    phase: PhaseName | str,
    adapter: StageAdapter,
    w12_record: W12Record | None = None,
    source_root: SourceRoot | None = None,
) -> tuple[RouteRecord, StageResult]:
    """Run ``adapter.execute`` for one (route, phase) and stamp the result.

    Returns ``(route, stage_result)``. The caller can inspect the
    ``stage_result`` to see what really happened — refusal code,
    evidence refs, operation digest — even when the scheduler's
    ``RouteStatus`` is a generic HOLD or COMPLETED.
    """

    phase_value = phase.value if isinstance(phase, PhaseName) else phase
    if phase_value not in {p.value for p in PHASE_ORDER}:
        raise ValueError(f"unknown phase: {phase_value!r}")
    route = _lookup_route(plan, route_id)
    if phase_value not in _PHASES_WITH_REAL_ADAPTER:
        result = StageResult(
            status=CHECKPOINT_STATUS_HOLD,
            refusal_code=REFUSAL_NEEDS_REAL_OPERATION_ADAPTER,
            refusal_text=(
                f"phase {phase_value!r} has no real adapter wired into "
                "this driver; cannot yield COMPLETED"
            ),
            notes=[f"provider={adapter.provider_name}"],
        )
        # Do not write a HOLD onto a future checkpoint: the state machine
        # requires every preceding phase to be completed first.
        current = route.current_phase
        record_phase = current if PHASE_ORDER.index(PhaseName(phase_value)) > PHASE_ORDER.index(PhaseName(current)) else phase_value
        result.notes.append(f"requested_unsupported_phase={phase_value}")
        _apply_result(plan, route_id=route_id, phase=record_phase, result=result)
        return _lookup_route(plan, route_id), result

    if w12_record is None:
        result = StageResult(
            status=CHECKPOINT_STATUS_HOLD,
            refusal_code=REFUSAL_SOURCE_BYTES_MISSING,
            refusal_text=(
                "drive_stage called without a W12Record; cannot verify "
                "route provenance"
            ),
            notes=[f"provider={adapter.provider_name}"],
        )
        _apply_result(plan, route_id=route_id, phase=phase_value, result=result)
        return _lookup_route(plan, route_id), result

    # Already completed stages can be replayed only against identical
    # authenticated source bytes. Reusing stored receipts keeps the event
    # hash and the original operation timestamps unchanged.
    route = _lookup_route(plan, route_id)
    existing = route.phase_checkpoints[phase_value]
    if existing.status == CHECKPOINT_STATUS_COMPLETED:
        if phase_value != PhaseName.SOURCE_EVIDENCE.value or not isinstance(adapter, SourceBytesStageAdapter):
            raise ValueError("STAGE_REPLAY_REQUIRES_CERTIFIED_ADAPTER")
        if (source_root is None or not source_root.is_real
                or source_root.full_sha256 != w12_record.source_full_sha256):
            raise ValueError("STAGE_REPLAY_SOURCE_DRIFT")
        refs = parse_evidence_refs(existing.evidence_refs)
        if not refs or any(ref.sha256_short != source_root.full_sha256[:len(ref.sha256_short)] for ref in refs):
            raise ValueError("STAGE_REPLAY_EVIDENCE_DRIFT")
        saved = next((v[len("operation_digest="):] for v in existing.notes
                      if v.startswith("operation_digest=")), None)
        if not saved:
            raise ValueError("STAGE_REPLAY_MISSING_DIGEST")
        digest = OperationDigest(**json.loads(saved))
        return route, StageResult(
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=refs, operation_digest=digest,
            notes=list(existing.notes),
        )
    result = adapter.execute(
        route=route,
        w12_record=w12_record,
        phase=PhaseName(phase_value),
        source_root=source_root,
    )
    _apply_result(plan, route_id=route_id, phase=phase_value, result=result)
    return _lookup_route(plan, route_id), result


def _apply_result(
    plan: TrimurtiBatchPlan,
    *,
    route_id: str,
    phase: str,
    result: StageResult,
) -> None:
    """Translate StageResult into advance_phase-compatible arguments."""

    if result.status not in CHECKPOINT_TERMINAL_STATUSES:
        # Adapters must yield terminal statuses; defensive guard.
        raise ValueError(
            f"adapter yielded non-terminal status {result.status!r} for "
            f"route {route_id} phase {phase!r}"
        )

    evidence_strings = [ref.canonical for ref in result.evidence_refs]
    notes: list[str] = list(result.notes)
    if result.refusal_code:
        notes.append(f"refusal_code={result.refusal_code}")
    if result.refusal_text:
        notes.append(f"refusal_text={result.refusal_text}")
    if result.operation_digest is not None:
        notes.append(
            "operation_digest=" + json.dumps(result.operation_digest.to_dict(), sort_keys=True)
        )

    try:
        advance_phase(
            plan,
            route_id=route_id,
            phase=phase,
            status=result.status,
            notes=notes,
            evidence_refs=evidence_strings,
        )
    except ValueError as exc:
        # Map upstream empty-evidence rejections back into a clean HOLD on
        # the route so we never raise past the driver.
        message = str(exc)
        if REFUSAL_EMPTY_EVIDENCE in message or REFUSAL_EMPTY_SCHOLARLY_EVIDENCE in message:
            advance_phase(
                plan,
                route_id=route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_HOLD,
                notes=notes + [f"upstream_caught={exc}"],
                evidence_refs=[],
            )
            return
        if REFUSAL_STALE_REPLAY in message:
            advance_phase(
                plan,
                route_id=route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_HOLD,
                notes=notes + [f"upstream_caught={exc}"],
                evidence_refs=[],
            )
            return
        raise


def _lookup_route(plan: TrimurtiBatchPlan, route_id: str) -> RouteRecord:
    for route in plan.routes:
        if route.route_id == route_id:
            return route
    raise KeyError(f"route_id not in plan: {route_id}")


# ---------------------------------------------------------------------------
# Batch-first stage-op driver for SOURCE_EVIDENCE across many routes.
# ---------------------------------------------------------------------------


def run_batch_first_source_evidence(
    plan: TrimurtiBatchPlan,
    *,
    records_by_route_id: dict[str, W12Record],
    source_root: SourceRoot | None,
    adapter: StageAdapter | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Drive SOURCE_EVIDENCE across up to ``limit`` pending routes.

    Returns a compact machine-readable summary suitable for a CLI
    runner or a CI comment. The summary is *honest by construction*:
    every route that lands in COMPLETED has both an OperationDigest and
    parseable EvidenceRefs; every HOLD has a refusal_code.
    """

    chosen_adapter: StageAdapter = adapter or SourceBytesStageAdapter()
    if limit is None:
        limit = plan.spec.concurrency_limit

    claimed: list[RouteRecord] = []
    for route in plan.routes:
        if route.status != "pending" or route.current_phase != PhaseName.SOURCE_EVIDENCE.value:
            continue
        if route.refusal_codes:
            continue
        checkpoint = route.phase_checkpoints.get(PhaseName.SOURCE_EVIDENCE.value)
        if checkpoint and checkpoint.status == CHECKPOINT_STATUS_COMPLETED:
            continue
        claimed.append(route)
        if len(claimed) >= limit:
            break

    results: list[dict[str, Any]] = []
    for route in claimed:
        record = records_by_route_id.get(route.route_id)
        _, stage = drive_stage(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SOURCE_EVIDENCE,
            adapter=chosen_adapter,
            w12_record=record,
            source_root=source_root,
        )
        results.append(
            {
                "route_id": route.route_id,
                "stage_status": stage.status,
                "refusal_code": stage.refusal_code,
                "evidence_refs": [ref.canonical for ref in stage.evidence_refs],
                "has_operation_digest": stage.operation_digest is not None,
            }
        )

    by_status = {status: 0 for status in CHECKPOINT_TERMINAL_STATUSES}
    for result in results:
        by_status[result["stage_status"]] = by_status.get(result["stage_status"], 0) + 1

    return {
        "schema": "TRIMURTI_STAGE_OPERATION_BATCH_FIRST_v1",
        "batch_id": plan.batch_id,
        "phase": PhaseName.SOURCE_EVIDENCE.value,
        "adapter_provider": chosen_adapter.provider_name,
        "source_root_kind": source_root.source_kind if source_root else None,
        "source_root_path": getattr(source_root, "path", None) if source_root else None,
        "requested": len(claimed),
        "by_status": by_status,
        "results": results,
        "no_external_send": True,
    }


# Re-export so external callers can compose.
__all__ = [
    "EVIDENCE_REF_FORBIDDEN_LITERALS",
    "EVIDENCE_REF_PATTERN",
    "EvidenceRef",
    "OperationDigest",
    "REFUSAL_EVIDENCE_REF_INVALID",
    "REFUSAL_EVIDENCE_REF_STUB",
    "REFUSAL_NEEDS_REAL_OPERATION_ADAPTER",
    "REFUSAL_OPERATION_DIGEST_MISSING",
    "REFUSAL_SOURCE_BYTES_MISSING",
    "ScholarlyChallengeStageAdapter",
    "SourceBytesStageAdapter",
    "SourceRoot",
    "StageAdapter",
    "StageResult",
    "drive_stage",
    "is_valid_evidence_ref",
    "make_operation_digest",
    "parse_evidence_ref",
    "parse_evidence_refs",
    "run_batch_first_source_evidence",
    "validate_evidence_refs_for_phase",
]


# Silence "imported but unused" for symbols only re-exported by __all__.
_ = (compute_route_event_hash,)
