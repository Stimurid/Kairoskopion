"""Proposal-level transition classifier for ARTIKL.KAIRON.

The engine converts a TargetPressurePack into an explicit transformation-depth
proposal. It never mutates a manuscript and never marks its own proposal as
adopted. Deep identity-sensitive operations require review/author decision.
"""

from __future__ import annotations

from hashlib import sha256
from typing import Iterable

from .models import KaironTransitionDecision, TargetPressurePack


_HINT_MAP: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("evidence_needed", "hold"), ("HOLD",)),
    (("identity_or_reseed_review", "reseed"), ("RESEED",)),
    (("reopen_field",), ("REOPEN_FIELD",)),
    (("split",), ("SPLIT",)),
    (("abandon_target",), ("ABANDON_TARGET",)),
    (("rearchitect_or_branch",), ("BRANCH", "REARCHITECT")),
    (("branch", "target_variant_branch"), ("BRANCH",)),
    (("structural_or_deeper", "structural", "rearchitect"), ("REARCHITECT",)),
    (("local_or_structural",), ("REFRAME",)),
    (("reframe",), ("REFRAME",)),
    (("local", "packaging"), ("LOCAL_ADAPT",)),
    (("none", "keep"), ("KEEP",)),
)

_PRIMARY_PRIORITY = (
    "HOLD",
    "RESEED",
    "REOPEN_FIELD",
    "SPLIT",
    "ABANDON_TARGET",
    "BRANCH",
    "REARCHITECT",
    "REFRAME",
    "LOCAL_ADAPT",
    "KEEP",
)

_DEEP_IDENTITY_REVIEW = {"REARCHITECT", "SPLIT", "RESEED", "REOPEN_FIELD"}
_AUTHOR_DECISION_TRANSITIONS = {"SPLIT", "RESEED", "REOPEN_FIELD", "ABANDON_TARGET"}
_BLOCKING_SEVERITY = {"major", "critical", "blocking", "bad", "high"}


def _ops_for_hint(hint: str) -> list[str]:
    h = (hint or "unknown").strip().lower()
    for aliases, ops in _HINT_MAP:
        if h in aliases:
            return list(ops)
    return ["HOLD"] if h in {"unknown", ""} else ["REFRAME"]


def _unique(xs: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(x for x in xs if x))


def _decision_id(call_id: str, snapshot_id: str, pressure_ids: list[str]) -> str:
    payload = "|".join([call_id, snapshot_id, *sorted(pressure_ids)])
    return "ktr_" + sha256(payload.encode("utf-8")).hexdigest()[:16]


def propose_transition(
    *,
    call_id: str,
    pressure_pack: TargetPressurePack,
    protected_core: list[str] | None = None,
    allowed_change_classes: list[str] | None = None,
) -> KaironTransitionDecision:
    """Classify a pressure pack into a proposal-only Kairon transition.

    Protected core is carried as a governance signal, not semantically
    reinterpreted here. The engine uses explicit pressure depth hints and
    evidence debt. Deep operations are escalated for identity/author review.
    """
    items = list(pressure_pack.items or [])
    pressure_ids = [p.pressure_id for p in items]

    if not items:
        return KaironTransitionDecision(
            decision_id=_decision_id(call_id, pressure_pack.snapshot_id, []),
            call_id=call_id,
            target_id=pressure_pack.target_id,
            snapshot_id=pressure_pack.snapshot_id,
            primary_transition="KEEP",
            required_operations=["KEEP"],
            reasons=["No active target pressure remains on the frozen target snapshot."],
            unknowns=list(pressure_pack.unknowns or []),
        )

    ops: list[str] = []
    reasons: list[str] = []
    evidence_refs: list[str] = []
    blocking_debt: list[str] = []

    for p in items:
        pop = _ops_for_hint(p.transformation_depth_hint)
        ops.extend(pop)
        evidence_refs.extend(p.evidence_refs or [])
        reasons.append(
            f"{p.pressure_id}: {p.dimension} -> {','.join(pop)} "
            f"(severity={p.severity}; {p.observation})"
        )
        if "HOLD" in pop and (p.severity or "").lower() in _BLOCKING_SEVERITY:
            blocking_debt.append(p.pressure_id)

    ops = _unique(ops)
    evidence_refs = _unique(evidence_refs)

    if blocking_debt:
        primary = "HOLD"
    else:
        actionable = [x for x in _PRIMARY_PRIORITY if x != "HOLD" and x in ops]
        primary = actionable[0] if actionable else ("HOLD" if "HOLD" in ops else "REFRAME")

    deep_ops = set(ops) & _DEEP_IDENTITY_REVIEW
    requires_identity_review = bool(deep_ops)

    allowed = {x.upper() for x in (allowed_change_classes or [])}
    author_decision_required = bool(set(ops) & _AUTHOR_DECISION_TRANSITIONS)
    if "REARCHITECT" in ops and "STRUCTURAL_RECONFIGURATION" not in allowed:
        author_decision_required = True
    if protected_core and requires_identity_review:
        author_decision_required = True

    alternatives = [x for x in ops if x != primary and x != "KEEP"]

    return KaironTransitionDecision(
        decision_id=_decision_id(call_id, pressure_pack.snapshot_id, pressure_ids),
        call_id=call_id,
        target_id=pressure_pack.target_id,
        snapshot_id=pressure_pack.snapshot_id,
        primary_transition=primary,
        required_operations=ops,
        alternative_transitions=alternatives,
        pressure_ids=pressure_ids,
        reasons=reasons,
        evidence_refs=evidence_refs,
        blocking_evidence_debt=blocking_debt,
        requires_identity_review=requires_identity_review,
        author_decision_required=author_decision_required,
        adoption_status="PROPOSAL_ONLY",
        authority_boundary="ARTIKL.KAIRON/author",
        unknowns=list(pressure_pack.unknowns or []),
    )