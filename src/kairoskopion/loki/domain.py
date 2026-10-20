"""LOKI R0: typed, side-effect-free contracts for studying bounded games.

All pointers refer to existing source/field/venue/editorial owners. This module
owns no manuscripts, journal events, external submissions or canonical Field.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import json
from math import isfinite


class ProbeKind(StrEnum):
    PASSIVE_ANALYSIS = "PASSIVE_ANALYSIS"
    OFFLINE_EXPERIMENT = "OFFLINE_EXPERIMENT"
    SIMULATION = "SIMULATION"
    AUTHORIZED_REAL_ACTION = "AUTHORIZED_REAL_ACTION"


class EvidenceKind(StrEnum):
    PUBLIC_SOURCE = "PUBLIC_SOURCE"
    PRIVATE_SOURCE = "PRIVATE_SOURCE"
    EXTERNAL_EDITORIAL_RECEIPT = "EXTERNAL_EDITORIAL_RECEIPT"
    EXPERIMENT_TRACE = "EXPERIMENT_TRACE"
    SIMULATION = "SIMULATION"
    NEGATIVE_SEARCH = "NEGATIVE_SEARCH"
    TEST_FIXTURE = "TEST_FIXTURE"


class Verification(StrEnum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTORY = "CONTRADICTORY"


class Decision(StrEnum):
    CONTINUE = "CONTINUE"
    SWITCH_TARGET = "SWITCH_TARGET"
    BRANCH = "BRANCH"
    REOPEN_FIELD = "REOPEN_FIELD"
    DEFER = "DEFER"
    DO_NOT_PLAY = "DO_NOT_PLAY"
    ABSTAIN = "ABSTAIN"


class MoveKind(StrEnum):
    CONTINUE = "CONTINUE"
    SWITCH_TARGET = "SWITCH_TARGET"
    BRANCH = "BRANCH"
    REOPEN_FIELD = "REOPEN_FIELD"
    COLLABORATION = "COLLABORATION"
    RESEARCH = "RESEARCH"


REAL_EVIDENCE_KINDS = frozenset({
    EvidenceKind.PUBLIC_SOURCE,
    EvidenceKind.PRIVATE_SOURCE,
    EvidenceKind.EXTERNAL_EDITORIAL_RECEIPT,
    EvidenceKind.EXPERIMENT_TRACE,
})


def _present(value: str, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _unique(values: tuple[str, ...], name: str) -> None:
    if not isinstance(values, tuple) or any(
        not isinstance(v, str) or not v.strip() for v in values
    ):
        raise ValueError(f"{name} must be an immutable tuple of nonempty strings")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must contain unique IDs")


def _enum_instance(value: object, cls: type, name: str) -> None:
    if not isinstance(value, cls):
        raise ValueError(f"{name} must be a typed {cls.__name__}, not a raw string")


def _tuple_pairs(value: object, name: str) -> None:
    if not isinstance(value, tuple) or any(
        not isinstance(item, tuple) or len(item) != 2 for item in value
    ):
        raise ValueError(f"{name} must be an immutable tuple of pairs")


@dataclass(frozen=True, slots=True)
class GameModel:
    game_id: str
    scope_ref: str
    objective_ids: tuple[str, ...]
    protected_field_ref: str = ""
    explicit_rule_refs: tuple[str, ...] = ()
    inferred_rule_hypothesis_ids: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    source_revisions: tuple[str, ...] = ()
    version: int = 1

    def __post_init__(self) -> None:
        _present(self.game_id, "game_id")
        _present(self.scope_ref, "scope_ref")
        if not self.objective_ids:
            raise ValueError("owner objective_ids required; no invented utility")
        _unique(self.objective_ids, "objective_ids")
        for name in ("explicit_rule_refs", "inferred_rule_hypothesis_ids",
                     "unknowns", "source_revisions"):
            _unique(getattr(self, name), name)
        if type(self.version) is not int or self.version < 1:
            raise ValueError("version must be a positive integer")


@dataclass(frozen=True, slots=True)
class GameHypothesis:
    hypothesis_id: str
    game_id: str
    proposition: str
    mechanism: str
    rival_ids: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field in ("hypothesis_id", "game_id", "proposition", "mechanism"):
            _present(getattr(self, field), field)
        _unique(self.rival_ids, "rival_ids")
        _unique(self.source_refs, "source_refs")
        if self.hypothesis_id in self.rival_ids:
            raise ValueError("hypothesis cannot be its own rival")


@dataclass(frozen=True, slots=True)
class ProbeRecord:
    probe_id: str
    game_id: str
    kind: ProbeKind
    # Frozen, pre-registered predictions: (hypothesis_id, observable outcome ID).
    predictions: tuple[tuple[str, str], ...]
    cost: float
    risk: int = 0  # 0 = lowest risk, larger = higher risk.
    reversible: bool = True
    observation_possible: bool = True
    access_approved: bool = False  # Required even to propose an external probe.
    controls: tuple[str, ...] = ()
    confounders: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _present(self.probe_id, "probe_id")
        _present(self.game_id, "game_id")
        _enum_instance(self.kind, ProbeKind, "kind")
        _tuple_pairs(self.predictions, "predictions")
        for name in ("reversible", "observation_possible", "access_approved"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        for name in ("controls", "confounders", "source_refs"):
            _unique(getattr(self, name), name)
        if isinstance(self.cost, bool) or not isinstance(self.cost, (int, float)):
            raise ValueError("cost must be a real nonnegative number")
        if not isfinite(self.cost) or self.cost < 0:
            raise ValueError("cost must be finite and nonnegative")
        if type(self.risk) is not int or self.risk < 0:
            raise ValueError("risk must be a nonnegative integer")
        _unique(tuple(h for h, _ in self.predictions), "prediction hypothesis IDs")
        for h, outcome in self.predictions:
            _present(h, "predicted hypothesis ID")
            _present(outcome, "predicted observable outcome")

    @property
    def fingerprint(self) -> str:
        """Immutable pre-registration fingerprint (not an outcome or authority proof)."""
        from dataclasses import asdict
        serialized = json.dumps(asdict(self), sort_keys=True, ensure_ascii=False,
                                separators=(",", ":"), allow_nan=False)
        return sha256(serialized.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class OutcomeEvidence:
    evidence_id: str
    game_id: str
    probe_id: str
    probe_fingerprint: str
    outcome: str
    kind: EvidenceKind
    verification: Verification
    source_ref: str
    source_revision: str = ""
    observed_at: str = ""
    negative_search_scope: str = ""

    def __post_init__(self) -> None:
        for field in ("evidence_id", "game_id", "probe_id", "probe_fingerprint",
                      "outcome", "source_ref"):
            _present(getattr(self, field), field)
        _enum_instance(self.kind, EvidenceKind, "kind")
        _enum_instance(self.verification, Verification, "verification")
        if self.kind is EvidenceKind.NEGATIVE_SEARCH and not self.negative_search_scope:
            raise ValueError("negative search must report its searched scope")

    @property
    def is_verified_real(self) -> bool:
        return self.kind in REAL_EVIDENCE_KINDS and self.verification is Verification.VERIFIED


@dataclass(frozen=True, slots=True)
class StrategicMove:
    move_id: str
    game_id: str
    kind: MoveKind
    # Advancement relative to named OWNER goals, not a fabricated global score.
    objective_impacts: tuple[tuple[str, int], ...]
    eligible: bool | None  # True: available; False: blocked; None: unknown.
    evidence_ids: tuple[str, ...] = ()
    protected_core_loss: bool = False
    rationale: str = ""

    def __post_init__(self) -> None:
        _present(self.move_id, "move_id")
        _present(self.game_id, "game_id")
        _enum_instance(self.kind, MoveKind, "kind")
        _tuple_pairs(self.objective_impacts, "objective_impacts")
        _unique(self.evidence_ids, "evidence_ids")
        if self.eligible is not None and type(self.eligible) is not bool:
            raise ValueError("eligible must be True, False, or None")
        if type(self.protected_core_loss) is not bool:
            raise ValueError("protected_core_loss must be boolean")
        _unique(tuple(k for k, _ in self.objective_impacts), "objective impact IDs")
        for key, value in self.objective_impacts:
            _present(key, "objective impact key")
            if not isinstance(value, int) or isinstance(value, bool):
                raise ValueError("impacts must be signed integer owner-goal advancements")


@dataclass(frozen=True, slots=True)
class StrategyPolicy:
    game_id: str
    decision: Decision
    selected_move_ids: tuple[str, ...]
    alternative_move_ids: tuple[str, ...]
    reasoning: str
    supporting_evidence_ids: tuple[str, ...] = ()
    preserved_field_ref: str = ""
    return_condition: str = ""
    # No path from policy evaluation to send/submit or scientific acceptance.
    human_approval_required: bool = True
    executable_action: bool = False

    def __post_init__(self) -> None:
        _present(self.game_id, "game_id")
        _present(self.reasoning, "reasoning")
        _enum_instance(self.decision, Decision, "decision")
        for name in ("selected_move_ids", "alternative_move_ids", "supporting_evidence_ids"):
            _unique(getattr(self, name), name)
        if type(self.human_approval_required) is not bool or type(self.executable_action) is not bool:
            raise ValueError("approval/action fields must be boolean")
        if not self.human_approval_required or self.executable_action:
            raise ValueError("LOKI R0 policies are advisory; external actions require owner")
        if self.decision is Decision.DO_NOT_PLAY:
            _present(self.preserved_field_ref, "preserved_field_ref")
            _present(self.return_condition, "return_condition")
