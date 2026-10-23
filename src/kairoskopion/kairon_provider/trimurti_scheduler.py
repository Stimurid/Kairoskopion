"""Deterministic, resumable MAI-batch Trimurti scheduler.

The scheduler is an additive layer on top of the existing
``kairon_provider/batch`` qualification grid. It does NOT replace or
re-author the existing Kairon batch qualification; rather it adds a
typed per-route phase tracker that can carry 10-50 route jobs through
seven pre-author checkpoints and into ``READY_FOR_AUTHOR_REWORK``.

The scheduler is intentionally scheduler-light:

* Phase advancement is **idempotent**: re-applying the same phase+status
  pair with identical evidence produces an identical event hash.
* Per-route state is independent. A hold/fail on one route never blocks
  or invalidates the others.
* Terminal states are explicit and separated:
  - ``READY_FOR_AUTHOR_REWORK`` is the goal of this slice
  - ``READY_FOR_APPROVAL`` and ``READY_FOR_HUMAN_SEND`` remain
    downstream and are deliberately not produced by this slice
* All storage is atomic JSON via ``.tmp`` + replace, matching the
  existing JSONL/durable pattern.

Adversarial guards enforced here (with documented reason codes):
* ``FAKE_FULLTEXT_REJECTED`` — raw_kind=fulltext without a manuscript hash.
* ``DUAL_EXCLUSIVE_VENUES_REJECTED`` — same manuscript (manuscript_hash)
  attached to two exclusive routes.
* ``ROUTE_TYPE_CONFUSION_REJECTED`` — generic editor address claimed
  as a CFP response.
* ``PROMOTION_UNAPPROVED`` — route_type=general_promotion that bypasses
  editorial_packet + QA phases.
* ``BLOCKED_DIRECT_PROMOTION`` — a phase advance targets a phase ahead
  of the route's ``current_phase`` (skipping checkpoints).
* ``BLOCKED_EMPTY_EVIDENCE`` / ``BLOCKED_EMPTY_SCHOLARLY_EVIDENCE`` — a
  ``completed`` checkpoint was submitted with no non-blank
  ``evidence_refs``.
* ``STALE_PHASE_REPLAY_REJECTED`` — a checkpoint already recorded as
  ``completed`` was resubmitted with different status/evidence/notes
  (history is append-only; use a new checkpoint phase or an explicit
  operator override, never a silent overwrite).
* ``FROZEN_VENUE_TARGET_MISSING`` / ``TERMINAL_PRECONDITION_NOT_MET`` —
  ``ready_for_author_rework`` was attempted without every prior phase
  independently completed with evidence and a frozen venue target bound.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from .w12_importer import (
    RAW_KIND_CHALLENGE_HTML,
    RAW_KIND_FULLTEXT,
    ROUTE_TYPE_GENERIC_EDITOR,
    ROUTE_TYPE_GENERIC_PROMO,
    W12Record,
)


class PhaseName(str, Enum):
    SOURCE_EVIDENCE = "source_evidence"
    SCHOLARLY_CHALLENGE = "scholarly_challenge"
    VENUE_QUALIFICATION = "venue_qualification"
    ROUTE_POLICY = "route_policy"
    TARGET_VARIANT = "target_variant"
    EDITORIAL_PACKET = "editorial_packet"
    QA = "qa"
    READY_FOR_AUTHOR_REWORK = "ready_for_author_rework"


PHASE_ORDER: tuple[PhaseName, ...] = (
    PhaseName.SOURCE_EVIDENCE,
    PhaseName.SCHOLARLY_CHALLENGE,
    PhaseName.VENUE_QUALIFICATION,
    PhaseName.ROUTE_POLICY,
    PhaseName.TARGET_VARIANT,
    PhaseName.EDITORIAL_PACKET,
    PhaseName.QA,
    PhaseName.READY_FOR_AUTHOR_REWORK,
)


class RouteStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    HOLD = "hold"
    FAILED = "failed"
    REJECTED = "rejected"
    READY_FOR_AUTHOR_REWORK = "ready_for_author_rework"
    READY_FOR_APPROVAL = "ready_for_approval"
    READY_FOR_HUMAN_SEND = "ready_for_human_send"


TERMINAL_ROUTE_STATUSES: frozenset[str] = frozenset(
    {
        RouteStatus.READY_FOR_AUTHOR_REWORK.value,
        RouteStatus.READY_FOR_APPROVAL.value,
        RouteStatus.READY_FOR_HUMAN_SEND.value,
        RouteStatus.HOLD.value,
        RouteStatus.FAILED.value,
        RouteStatus.REJECTED.value,
    }
)


CHECKPOINT_STATUS_PENDING = "pending"
CHECKPOINT_STATUS_IN_PROGRESS = "in_progress"
CHECKPOINT_STATUS_COMPLETED = "completed"
CHECKPOINT_STATUS_HOLD = "hold"
CHECKPOINT_STATUS_FAILED = "failed"

CHECKPOINT_TERMINAL_STATUSES: frozenset[str] = frozenset(
    {
        CHECKPOINT_STATUS_COMPLETED,
        CHECKPOINT_STATUS_HOLD,
        CHECKPOINT_STATUS_FAILED,
    }
)


REFUSAL_FAKE_FULLTEXT = "FAKE_FULLTEXT_REJECTED"
REFUSAL_DUAL_EXCLUSIVE = "DUAL_EXCLUSIVE_VENUES_REJECTED"
REFUSAL_ROUTE_TYPE_CONFUSION = "ROUTE_TYPE_CONFUSION_REJECTED"
REFUSAL_PROMOTION_UNAPPROVED = "PROMOTION_UNAPPROVED"
REFUSAL_CHALLENGE_HTML = "CHALLENGE_HTML_NOT_FULLTEXT"

# Phase-gate refusal codes (HEAD-TRIMURTI P0 fail-open fix, 2026-10-20).
REFUSAL_DIRECT_PROMOTION = "BLOCKED_DIRECT_PROMOTION"
REFUSAL_EMPTY_EVIDENCE = "BLOCKED_EMPTY_EVIDENCE"
REFUSAL_EMPTY_SCHOLARLY_EVIDENCE = "BLOCKED_EMPTY_SCHOLARLY_EVIDENCE"
REFUSAL_STALE_REPLAY = "STALE_PHASE_REPLAY_REJECTED"
REFUSAL_MISSING_FROZEN_TARGET = "FROZEN_VENUE_TARGET_MISSING"
REFUSAL_TERMINAL_PRECONDITION = "TERMINAL_PRECONDITION_NOT_MET"


@dataclass
class PhaseCheckpoint:
    phase: str
    status: str = CHECKPOINT_STATUS_PENDING
    notes: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    completed_at: str | None = None
    event_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RouteRecord:
    """One route's typed phase checkpoint ledger."""

    route_id: str
    seed_family_id: str
    meaning_version_id: str
    seed_label: str
    meaning_version_label: str
    route_label: str
    route_type: str
    route_kind: str
    raw_kind: str
    exclusive_venue_class: str
    manuscript_pointer: str | None = None
    manuscript_hash: str | None = None
    frozen_target_id: str | None = None
    frozen_target_snapshot_id: str | None = None
    status: str = RouteStatus.PENDING.value
    current_phase: str = PhaseName.SOURCE_EVIDENCE.value
    phase_checkpoints: dict[str, PhaseCheckpoint] = field(default_factory=dict)
    last_event_hash: str | None = None
    hold_failures: list[str] = field(default_factory=list)
    refusal_codes: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    source_kind: str = "FIXTURE_NOT_REAL_DATA"
    source_first_bytes_sha256: str | None = None
    source_full_sha256: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class TrimurtiBatchSpec:
    batch_id: str
    concurrency_limit: int = 4
    author_rework_enabled: bool = False
    notes: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.batch_id.strip():
            raise ValueError("batch_id must be non-empty")
        if self.concurrency_limit < 1:
            raise ValueError("concurrency_limit must be >= 1")


@dataclass
class TrimurtiBatchPlan:
    batch_id: str
    routes: list[RouteRecord]
    spec: TrimurtiBatchSpec
    status: str = "planned"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "spec": asdict(self.spec),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "routes": [r.to_dict() for r in self.routes],
        }


@dataclass
class TrimurtiRunReceipt:
    run_id: str
    batch_id: str
    route_event_hashes: dict[str, str]
    completed_count: int
    hold_count: int
    failed_count: int
    ready_count: int
    run_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _digest_string(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_checkpoints(route: RouteRecord) -> None:
    """Make sure the route has a checkpoint entry for every phase."""

    for phase in PHASE_ORDER:
        key = phase.value
        if key not in route.phase_checkpoints:
            route.phase_checkpoints[key] = PhaseCheckpoint(phase=key)


def _default_checkpoints() -> dict[str, PhaseCheckpoint]:
    return {
        phase.value: PhaseCheckpoint(phase=phase.value) for phase in PHASE_ORDER
    }


def _route_from_w12(record: W12Record, *, frozen_target_id: str | None = None, frozen_target_snapshot_id: str | None = None) -> RouteRecord:
    route = RouteRecord(
        route_id=record.route_id,
        seed_family_id=record.seed_family_id,
        meaning_version_id=record.meaning_version_id,
        seed_label=record.seed_label,
        meaning_version_label=record.meaning_version_label,
        route_label=record.route_label or record.route_id,
        route_type=record.route_type,
        route_kind=record.route_kind,
        raw_kind=record.raw_kind,
        exclusive_venue_class=record.exclusive_venue_class,
        manuscript_pointer=record.manuscript_pointer,
        manuscript_hash=record.manuscript_hash,
        frozen_target_id=frozen_target_id,
        frozen_target_snapshot_id=frozen_target_snapshot_id,
        phase_checkpoints=_default_checkpoints(),
        source_kind=record.source_kind,
        source_first_bytes_sha256=record.source_first_bytes_sha256,
        source_full_sha256=record.source_full_sha256,
    )
    return route


def _detect_route_conflicts(routes: list[RouteRecord]) -> list[tuple[str, str]]:
    """Return (route_id, refusal_code) for routes that violate platform rules.

    The conflicts are recorded on the route (refusal_codes) so an operator
    sees an immediate, per-route explanation. Re-running this check on the
    same plan must produce the same result (idempotent).
    """

    manuscript_to_exclusives: dict[str, list[RouteRecord]] = {}
    conflicts: list[tuple[str, str]] = []

    for route in routes:
        route.refusal_codes = []
        if (
            route.raw_kind == RAW_KIND_FULLTEXT
            and not route.manuscript_hash
            and not route.manuscript_pointer
        ):
            route.refusal_codes.append(REFUSAL_FAKE_FULLTEXT)
            conflicts.append((route.route_id, REFUSAL_FAKE_FULLTEXT))
        if route.raw_kind == RAW_KIND_CHALLENGE_HTML:
            route.refusal_codes.append(REFUSAL_CHALLENGE_HTML)
            conflicts.append((route.route_id, REFUSAL_CHALLENGE_HTML))
        if route.route_type == ROUTE_TYPE_GENERIC_EDITOR:
            route.refusal_codes.append(REFUSAL_ROUTE_TYPE_CONFUSION)
            conflicts.append((route.route_id, REFUSAL_ROUTE_TYPE_CONFUSION))
        if route.route_type == ROUTE_TYPE_GENERIC_PROMO:
            route.refusal_codes.append(REFUSAL_PROMOTION_UNAPPROVED)
            conflicts.append((route.route_id, REFUSAL_PROMOTION_UNAPPROVED))
        if route.route_kind == "exclusive" and route.manuscript_hash:
            manuscript_to_exclusives.setdefault(route.manuscript_hash, []).append(route)

    for ms_hash, group in manuscript_to_exclusives.items():
        if len(group) > 1:
            for route in group:
                if REFUSAL_DUAL_EXCLUSIVE not in route.refusal_codes:
                    route.refusal_codes.append(REFUSAL_DUAL_EXCLUSIVE)
                    conflicts.append((route.route_id, REFUSAL_DUAL_EXCLUSIVE))

    return conflicts


def build_trimurti_plan(
    *,
    batch_id: str,
    w12_records: list[W12Record],
    spec: TrimurtiBatchSpec | None = None,
    frozen_targets: list[dict[str, Any]] | None = None,
) -> TrimurtiBatchPlan:
    """Build a Trimurti batch plan from a list of W12 records.

    ``frozen_targets`` is a list of ``{"target_id": ..., "snapshot_id": ...}``
    objects. Each route is bound to the FIRST frozen target that matches its
    academic path; if no frozen target matches, ``frozen_target_id`` and
    ``frozen_target_snapshot_id`` remain None and the route will be flagged
    with a hold when it reaches ``venue_qualification``.
    """

    if not batch_id.strip():
        raise ValueError("batch_id must be non-empty")
    if not w12_records:
        raise ValueError("w12_records must be non-empty")
    if spec is not None and spec.batch_id != batch_id:
        raise ValueError("spec.batch_id must match batch_id")

    if spec is None:
        spec = TrimurtiBatchSpec(batch_id=batch_id)

    frozen_targets = list(frozen_targets or [])

    routes: list[RouteRecord] = []
    for index, record in enumerate(w12_records):
        frozen_target_id = None
        frozen_target_snapshot_id = None
        for target in frozen_targets:
            if not isinstance(target, dict):
                continue
            target_id = str(target.get("target_id") or "")
            if not target_id:
                continue
            target_route_types = target.get("applies_route_types")
            if target_route_types and record.route_type not in target_route_types:
                continue
            frozen_target_id = target_id
            frozen_target_snapshot_id = str(target.get("snapshot_id") or "")
            break
        route = _route_from_w12(
            record,
            frozen_target_id=frozen_target_id,
            frozen_target_snapshot_id=frozen_target_snapshot_id,
        )
        routes.append(route)

    _detect_route_conflicts(routes)

    plan = TrimurtiBatchPlan(
        batch_id=batch_id,
        routes=routes,
        spec=spec,
        status="planned",
    )
    return plan


def compute_route_event_hash(
    *,
    route_id: str,
    phase: str,
    status: str,
    extra: Iterable[str] = (),
) -> str:
    """Stable SHA-256[:16] over a route's transition event."""

    payload = "|".join([route_id, phase, status, *(str(x) for x in extra)])
    return "tev_" + _digest_string(payload)[:16]


def next_phase(current: PhaseName) -> PhaseName | None:
    """Return the next phase in the canonical order, or None if terminal."""

    idx = PHASE_ORDER.index(current)
    if idx + 1 >= len(PHASE_ORDER):
        return None
    return PHASE_ORDER[idx + 1]


def claim_routes(plan: TrimurtiBatchPlan, *, limit: int | None = None) -> list[RouteRecord]:
    """Claim pending routes for a single scheduler worker.

    Pending = status=pending and current_phase=SOURCE_EVIDENCE and the
    route has no refusal codes. Claimed routes transition to
    ``RouteStatus.IN_PROGRESS`` and their SOURCE_EVIDENCE checkpoint
    moves to ``in_progress``. The plan status flips to ``running`` if any
    routes were claimed.
    """

    if limit is None:
        limit = plan.spec.concurrency_limit

    candidates: list[RouteRecord] = []
    for route in plan.routes:
        if route.status != RouteStatus.PENDING.value:
            continue
        if route.refusal_codes:
            continue
        if route.phase_checkpoints.get(PhaseName.SOURCE_EVIDENCE.value) is None:
            _ensure_checkpoints(route)
        checkpoint = route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value]
        if checkpoint.status not in (CHECKPOINT_STATUS_PENDING, CHECKPOINT_STATUS_FAILED, CHECKPOINT_STATUS_HOLD):
            continue
        candidates.append(route)

    claimed = candidates[: max(0, limit)]
    for route in claimed:
        route.status = RouteStatus.IN_PROGRESS.value
        checkpoint = route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value]
        checkpoint.status = CHECKPOINT_STATUS_IN_PROGRESS
    if claimed:
        plan.status = "running"
        plan.updated_at = _now()
    return claimed


def _advance_checkpoints(
    route: RouteRecord,
    *,
    phase: PhaseName,
    status: str,
    notes: Iterable[str],
    evidence_refs: Iterable[str],
) -> PhaseCheckpoint:
    if status not in {CHECKPOINT_STATUS_COMPLETED, CHECKPOINT_STATUS_HOLD, CHECKPOINT_STATUS_FAILED}:
        raise ValueError(f"unsupported checkpoint status: {status}")
    _ensure_checkpoints(route)
    checkpoint = route.phase_checkpoints[phase.value]
    checkpoint.status = status
    checkpoint.notes = list(dict.fromkeys([*checkpoint.notes, *notes]))
    checkpoint.evidence_refs = list(dict.fromkeys([*checkpoint.evidence_refs, *evidence_refs]))
    if status in CHECKPOINT_TERMINAL_STATUSES:
        checkpoint.completed_at = _now()
    event_hash = compute_route_event_hash(
        route_id=route.route_id,
        phase=phase.value,
        status=status,
        extra=[*checkpoint.evidence_refs, *checkpoint.notes],
    )
    checkpoint.event_hash = event_hash
    route.last_event_hash = event_hash
    return checkpoint


def _has_real_evidence(evidence_refs: list[str]) -> bool:
    """Reject empty/whitespace-only evidence — not an operation receipt."""

    return any(str(ref).strip() for ref in evidence_refs)


def _empty_evidence_code(phase_value: str) -> str:
    if phase_value == PhaseName.SCHOLARLY_CHALLENGE.value:
        return REFUSAL_EMPTY_SCHOLARLY_EVIDENCE
    return REFUSAL_EMPTY_EVIDENCE


def _validate_terminal_preconditions(route: RouteRecord) -> None:
    """Defense-in-depth gate for the READY_FOR_AUTHOR_REWORK transition.

    Order enforcement in ``advance_phase`` already makes it impossible to
    reach this phase without completing every prior checkpoint in order,
    but this re-checks the stored state explicitly (and checks the
    frozen venue target binding, which order enforcement cannot see) so
    a corrupted/hand-edited plan on disk cannot silently promote.
    """

    for phase in PHASE_ORDER:
        if phase == PhaseName.READY_FOR_AUTHOR_REWORK:
            continue
        checkpoint = route.phase_checkpoints.get(phase.value)
        if checkpoint is None or checkpoint.status != CHECKPOINT_STATUS_COMPLETED:
            raise ValueError(
                f"{REFUSAL_TERMINAL_PRECONDITION}: route {route.route_id} phase "
                f"{phase.value} is {checkpoint.status if checkpoint else 'missing'!r}, "
                "not completed; cannot promote to ready_for_author_rework"
            )
        if not _has_real_evidence(checkpoint.evidence_refs):
            raise ValueError(
                f"{_empty_evidence_code(phase.value)}: route {route.route_id} phase "
                f"{phase.value} has no evidence_refs on record; cannot promote to "
                "ready_for_author_rework"
            )
    if not route.frozen_target_id or not route.frozen_target_snapshot_id:
        raise ValueError(
            f"{REFUSAL_MISSING_FROZEN_TARGET}: route {route.route_id} has no frozen "
            "VenueTarget (frozen_target_id/frozen_target_snapshot_id) bound; cannot "
            "promote to ready_for_author_rework"
        )


def advance_phase(
    plan: TrimurtiBatchPlan,
    *,
    route_id: str,
    phase: str | PhaseName,
    status: str,
    notes: Iterable[str] = (),
    evidence_refs: Iterable[str] = (),
) -> RouteRecord:
    """Advance one route through a phase checkpoint.

    The advance is **idempotent**: re-running with identical inputs
    produces an identical event hash. Refusal codes from the build step
    are respected: a route with any refusal code cannot progress beyond
    SOURCE_EVIDENCE until the operator clears the refusal.

    Strictly ordered: a phase can only be advanced when it is the
    route's current phase (``BLOCKED_DIRECT_PROMOTION`` otherwise — no
    jumping straight to a terminal or any other downstream phase from a
    pending/hold/failed state). A ``completed`` checkpoint always
    requires non-blank ``evidence_refs`` (``BLOCKED_EMPTY_EVIDENCE`` /
    ``BLOCKED_EMPTY_SCHOLARLY_EVIDENCE`` otherwise) — a note string alone
    is never accepted as an operation receipt. Replaying a phase that is
    already recorded as ``completed`` with different status/evidence is
    rejected (``STALE_PHASE_REPLAY_REJECTED``) rather than silently
    overwritten or silently ignored; replaying with byte-identical
    inputs is a no-op that reasserts the existing event hash.
    """

    phase_value = phase.value if isinstance(phase, PhaseName) else phase
    if phase_value not in {p.value for p in PHASE_ORDER}:
        raise ValueError(f"unknown phase: {phase_value!r}")
    phase_enum = PhaseName(phase_value)

    if status not in {CHECKPOINT_STATUS_COMPLETED, CHECKPOINT_STATUS_HOLD, CHECKPOINT_STATUS_FAILED}:
        raise ValueError(f"unsupported checkpoint status: {status!r}")

    notes_list = [str(n) for n in notes]
    evidence_list = [str(e) for e in evidence_refs]

    for route in plan.routes:
        if route.route_id != route_id:
            continue
        if route.refusal_codes and phase_value != PhaseName.SOURCE_EVIDENCE.value:
            raise ValueError(
                f"route {route_id} has refusal codes {route.refusal_codes}; "
                "operator must clear before advancing past source_evidence"
            )

        _ensure_checkpoints(route)
        current_idx = PHASE_ORDER.index(PhaseName(route.current_phase))
        target_idx = PHASE_ORDER.index(phase_enum)
        existing_checkpoint = route.phase_checkpoints[phase_value]

        if target_idx > current_idx:
            raise ValueError(
                f"{REFUSAL_DIRECT_PROMOTION}: route {route_id} cannot advance to "
                f"phase {phase_value!r} while current_phase is "
                f"{route.current_phase!r}; phases must complete in strict order"
            )

        if status == CHECKPOINT_STATUS_COMPLETED and not _has_real_evidence(evidence_list):
            raise ValueError(
                f"{_empty_evidence_code(phase_value)}: phase {phase_value!r} for "
                f"route {route_id} requires non-empty evidence_refs to be marked "
                "completed; a note string alone is not an operation receipt"
            )

        if existing_checkpoint.status == CHECKPOINT_STATUS_COMPLETED:
            # History for this phase is already settled. A byte-identical
            # replay reasserts the same receipt (idempotent restart); any
            # other input is a silent-overwrite attempt and is rejected.
            merged_evidence = list(dict.fromkeys([*existing_checkpoint.evidence_refs, *evidence_list]))
            merged_notes = list(dict.fromkeys([*existing_checkpoint.notes, *notes_list]))
            is_identical_replay = (
                status == existing_checkpoint.status
                and merged_evidence == existing_checkpoint.evidence_refs
                and merged_notes == existing_checkpoint.notes
            )
            if not is_identical_replay:
                raise ValueError(
                    f"{REFUSAL_STALE_REPLAY}: route {route_id} phase {phase_value!r} "
                    "is already completed with different evidence/notes on record; "
                    "idempotent replay must be byte-identical, not a silent overwrite"
                )
            if target_idx < current_idx:
                # Already-passed phase: reassert its own checkpoint only,
                # never regress route.status/current_phase.
                _advance_checkpoints(
                    route, phase=phase_enum, status=status,
                    notes=notes_list, evidence_refs=evidence_list,
                )
                _refresh_plan_status(plan)
                plan.updated_at = _now()
                return route
            # target_idx == current_idx and already completed (terminal
            # phase re-affirmation): fall through to the normal path below,
            # which will re-derive the identical terminal state.

        if status == CHECKPOINT_STATUS_COMPLETED:
            if phase_value == PhaseName.READY_FOR_AUTHOR_REWORK.value:
                _validate_terminal_preconditions(route)
                route.status = RouteStatus.READY_FOR_AUTHOR_REWORK.value
                route.current_phase = PhaseName.READY_FOR_AUTHOR_REWORK.value
            else:
                nxt = next_phase(phase_enum)
                if nxt is None:
                    raise ValueError(f"phase {phase_value!r} has no successor")
                route.current_phase = nxt.value
        elif status == CHECKPOINT_STATUS_HOLD:
            route.status = RouteStatus.HOLD.value
            route.hold_failures = list(dict.fromkeys([*route.hold_failures, *notes_list]))
        elif status == CHECKPOINT_STATUS_FAILED:
            route.status = RouteStatus.FAILED.value
            route.hold_failures = list(dict.fromkeys([*route.hold_failures, *notes_list]))

        _advance_checkpoints(
            route,
            phase=phase_enum,
            status=status,
            notes=notes_list,
            evidence_refs=evidence_list,
        )

        _refresh_plan_status(plan)
        plan.updated_at = _now()
        return route

    raise KeyError(f"route_id not in plan: {route_id}")


def _refresh_plan_status(plan: TrimurtiBatchPlan) -> None:
    statuses = {route.status for route in plan.routes}
    if statuses == {RouteStatus.READY_FOR_AUTHOR_REWORK.value}:
        plan.status = "ready_for_author_rework"
        return
    if RouteStatus.PENDING.value in statuses:
        plan.status = "planned"
        return
    if RouteStatus.IN_PROGRESS.value in statuses:
        plan.status = "running"
        return
    if {RouteStatus.HOLD.value, RouteStatus.FAILED.value, RouteStatus.REJECTED.value} & statuses:
        plan.status = "blocked_partial"
        return
    plan.status = "complete"


def plan_summary(plan: TrimurtiBatchPlan) -> dict[str, Any]:
    """Compact machine-readable summary of the plan's current state."""

    summary: dict[str, Any] = {
        "batch_id": plan.batch_id,
        "route_count": len(plan.routes),
        "status": plan.status,
        "by_status": {},
        "by_phase": {},
        "by_refusal_code": {},
        "ready_for_author_rework": 0,
        "hold_count": 0,
        "failed_count": 0,
        "terminal_route_count": 0,
    }
    for route in plan.routes:
        summary["by_status"][route.status] = summary["by_status"].get(route.status, 0) + 1
        summary["by_phase"][route.current_phase] = summary["by_phase"].get(route.current_phase, 0) + 1
        for code in route.refusal_codes:
            summary["by_refusal_code"][code] = summary["by_refusal_code"].get(code, 0) + 1
        if route.status == RouteStatus.READY_FOR_AUTHOR_REWORK.value:
            summary["ready_for_author_rework"] += 1
        if route.status == RouteStatus.HOLD.value:
            summary["hold_count"] += 1
        if route.status == RouteStatus.FAILED.value:
            summary["failed_count"] += 1
        if route.status in TERMINAL_ROUTE_STATUSES:
            summary["terminal_route_count"] += 1
    return summary


def build_run_receipt(
    plan: TrimurtiBatchPlan,
    *,
    run_id: str | None = None,
) -> TrimurtiRunReceipt:
    """Build a receipt summarising the current per-route event hashes."""

    hashes: dict[str, str] = {}
    for route in plan.routes:
        if route.last_event_hash:
            hashes[route.route_id] = route.last_event_hash
    completed = sum(1 for r in plan.routes if r.status == RouteStatus.COMPLETED.value)
    hold = sum(1 for r in plan.routes if r.status == RouteStatus.HOLD.value)
    failed = sum(1 for r in plan.routes if r.status == RouteStatus.FAILED.value)
    ready = sum(
        1 for r in plan.routes if r.status == RouteStatus.READY_FOR_AUTHOR_REWORK.value
    )
    return TrimurtiRunReceipt(
        run_id=run_id or ("trimurti_" + _digest_string(plan.batch_id + _now())[:16]),
        batch_id=plan.batch_id,
        route_event_hashes=hashes,
        completed_count=completed,
        hold_count=hold,
        failed_count=failed,
        ready_count=ready,
    )


class TrimurtiPlanStore:
    """Atomic durable plan store, mirroring BatchRunStore conventions."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "trimurti"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, batch_id: str) -> Path:
        digest = _digest_string(batch_id)
        return self.root / f"{digest}.json"

    def _atomic_write(self, path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(path)

    def _route_from_dict(self, raw: dict[str, Any]) -> RouteRecord:
        checkpoints: dict[str, PhaseCheckpoint] = {}
        for key, value in (raw.get("phase_checkpoints") or {}).items():
            checkpoints[key] = PhaseCheckpoint(**value) if isinstance(value, dict) else PhaseCheckpoint(phase=key)
        raw2 = dict(raw)
        raw2["phase_checkpoints"] = checkpoints
        return RouteRecord(**raw2)

    def put(self, plan: TrimurtiBatchPlan) -> TrimurtiBatchPlan:
        self._atomic_write(self._path(plan.batch_id), plan.to_dict())
        return plan

    def get(self, batch_id: str) -> TrimurtiBatchPlan | None:
        path = self._path(batch_id)
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("batch_id") != batch_id:
            return None
        spec_raw = raw.get("spec") or {}
        spec = TrimurtiBatchSpec(**spec_raw)
        routes = [self._route_from_dict(r) for r in (raw.get("routes") or [])]
        return TrimurtiBatchPlan(
            batch_id=raw["batch_id"],
            routes=routes,
            spec=spec,
            status=raw.get("status", "planned"),
            created_at=raw.get("created_at") or _now(),
            updated_at=raw.get("updated_at") or _now(),
        )


__all__ = [
    "PHASE_ORDER",
    "PhaseCheckpoint",
    "PhaseName",
    "REFUSAL_CHALLENGE_HTML",
    "REFUSAL_DUAL_EXCLUSIVE",
    "REFUSAL_FAKE_FULLTEXT",
    "REFUSAL_PROMOTION_UNAPPROVED",
    "REFUSAL_ROUTE_TYPE_CONFUSION",
    "RouteRecord",
    "RouteStatus",
    "TERMINAL_ROUTE_STATUSES",
    "TrimurtiBatchPlan",
    "TrimurtiBatchSpec",
    "TrimurtiPlanStore",
    "TrimurtiRunReceipt",
    "advance_phase",
    "build_run_receipt",
    "build_trimurti_plan",
    "claim_routes",
    "compute_route_event_hash",
    "next_phase",
    "plan_summary",
]