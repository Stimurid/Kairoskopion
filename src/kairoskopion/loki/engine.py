"""Deterministic LOKI R0 game-hacking core. No network, no mutable Field or send."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable

from .domain import (
    Decision, EvidenceKind, GameHypothesis, GameModel, MoveKind,
    OutcomeEvidence, ProbeKind, ProbeRecord, StrategicMove, StrategyPolicy,
)


@dataclass(frozen=True, slots=True)
class ProbeRanking:
    probe_id: str
    differentiated_pairs: int
    cost: float
    risk: int
    reversible: bool


def _check_game(game: GameModel, objects: Iterable[object]) -> None:
    for obj in objects:
        if getattr(obj, "game_id", None) != game.game_id:
            raise ValueError("cross-game object rejected")


def discrimination_score(probe: ProbeRecord, hypotheses: tuple[GameHypothesis, ...]) -> int:
    """Count PRE-REGISTERED hypothesis pairs with different observable predictions.

    This is experimental design, not a probability or causal estimate.
    Missing/UNKNOWN predictions cannot distinguish anything.
    """
    if hypotheses:
        if len({h.game_id for h in hypotheses} | {probe.game_id}) != 1:
            raise ValueError("cross-game predictions rejected")
    known_h = {h.hypothesis_id for h in hypotheses}
    if len(known_h) != len(hypotheses):
        raise ValueError("duplicate hypotheses")
    predictions = dict(probe.predictions)
    if not set(predictions).issubset(known_h):
        raise ValueError("probe contains undeclared hypothesis")
    return sum(
        1 for a, b in combinations(hypotheses, 2)
        if predictions.get(a.hypothesis_id, "UNKNOWN") != "UNKNOWN"
        and predictions.get(b.hypothesis_id, "UNKNOWN") != "UNKNOWN"
        and predictions[a.hypothesis_id] != predictions[b.hypothesis_id]
    )


def rank_discriminating_probes(
    game: GameModel,
    hypotheses: tuple[GameHypothesis, ...],
    probes: tuple[ProbeRecord, ...],
) -> tuple[ProbeRanking, ...]:
    """Pareto frontier: discriminability up, cost/risk down, reversibility up."""
    _check_game(game, (*hypotheses, *probes))
    if len({p.probe_id for p in probes}) != len(probes):
        raise ValueError("duplicate probe IDs")
    candidates: list[ProbeRanking] = []
    for probe in probes:
        if not probe.observation_possible:
            continue
        if probe.kind is ProbeKind.AUTHORIZED_REAL_ACTION and not probe.access_approved:
            continue  # Designed experiment does not authorize external action.
        score = discrimination_score(probe, hypotheses)
        if score < 1:
            continue
        candidates.append(ProbeRanking(
            probe_id=probe.probe_id, differentiated_pairs=score,
            cost=probe.cost, risk=probe.risk, reversible=probe.reversible,
        ))

    def dominates(a: ProbeRanking, b: ProbeRanking) -> bool:
        better_or_equal = (
            a.differentiated_pairs >= b.differentiated_pairs
            and a.cost <= b.cost
            and a.risk <= b.risk
            and int(a.reversible) >= int(b.reversible)
        )
        strictly = (
            a.differentiated_pairs > b.differentiated_pairs
            or a.cost < b.cost or a.risk < b.risk
            or (a.reversible and not b.reversible)
        )
        return better_or_equal and strictly

    nondominated = [
        p for p in candidates if not any(dominates(q, p) for q in candidates if q != p)
    ]
    return tuple(sorted(nondominated, key=lambda x:
                        (-x.differentiated_pairs, x.cost, x.risk,
                         not x.reversible, x.probe_id)))


def assess_observation(
    probe: ProbeRecord,
    hypotheses: tuple[GameHypothesis, ...],
    evidence: OutcomeEvidence,
) -> dict[str, str]:
    """Categorical consistency, never automatic truth or causal attribution."""
    if probe.game_id != evidence.game_id or probe.probe_id != evidence.probe_id:
        raise ValueError("observation attached to another game or probe")
    if probe.fingerprint != evidence.probe_fingerprint:
        raise ValueError("post-hoc changed probe predictions: fingerprint mismatch")
    if len({h.hypothesis_id for h in hypotheses}) != len(hypotheses):
        raise ValueError("duplicate hypothesis IDs")
    if any(h.game_id != probe.game_id for h in hypotheses):
        raise ValueError("cross-game hypothesis")
    if evidence.kind in {
        EvidenceKind.SIMULATION, EvidenceKind.TEST_FIXTURE, EvidenceKind.NEGATIVE_SEARCH
    }:
        status = "NOT_REAL_GAME_EVIDENCE"
    elif not evidence.is_verified_real:
        status = "INDETERMINATE"
    else:
        status = ""
    predictions = dict(probe.predictions)
    return {
        h.hypothesis_id: (
            status or
            ("NOT_TESTED" if h.hypothesis_id not in predictions
             else "CONSISTENT" if predictions[h.hypothesis_id] == evidence.outcome
             else "INCONSISTENT")
        )
        for h in hypotheses
    }


def _verified_real_evidence(
    ids: tuple[str, ...], evidence: dict[str, OutcomeEvidence], game_id: str
) -> bool:
    return bool(ids) and all(
        e_id in evidence
        and evidence[e_id].game_id == game_id
        and evidence[e_id].is_verified_real
        for e_id in ids
    )


def _advancement(game: GameModel, move: StrategicMove) -> tuple[int, ...] | None:
    impacts = dict(move.objective_impacts)
    if set(impacts) != set(game.objective_ids):
        return None
    return tuple(impacts[g] for g in game.objective_ids)


def _pareto(game: GameModel, moves: tuple[StrategicMove, ...]) -> tuple[StrategicMove, ...]:
    vectors = {m.move_id: _advancement(game, m) for m in moves}
    if any(v is None for v in vectors.values()):
        return ()

    def dominates(a: StrategicMove, b: StrategicMove) -> bool:
        va, vb = vectors[a.move_id], vectors[b.move_id]
        assert va is not None and vb is not None
        return all(x >= y for x, y in zip(va, vb)) and any(
            x > y for x, y in zip(va, vb)
        )
    return tuple(sorted(
        (m for m in moves if not any(dominates(other, m)
                                   for other in moves if other.move_id != m.move_id)),
        key=lambda m: m.move_id,
    ))


def recommend_strategy(
    game: GameModel,
    moves: tuple[StrategicMove, ...],
    evidence: tuple[OutcomeEvidence, ...],
    *,
    return_condition: str = "",
) -> StrategyPolicy:
    """Evidence-bounded advisory policy, never approval to execute a move.

    A DO_NOT_PLAY needs independent real evidence against *every* proposed
    move and a scientific residue/re-entry path. Unknown does not mean blocked.
    """
    _check_game(game, (*moves, *evidence))
    if len({m.move_id for m in moves}) != len(moves):
        raise ValueError("duplicate move IDs")
    if len({e.evidence_id for e in evidence}) != len(evidence):
        raise ValueError("duplicate evidence IDs")
    by_id = {e.evidence_id: e for e in evidence}

    def policy(decision: Decision, reason: str,
               chosen: tuple[str, ...] = (), alternatives: tuple[str, ...] = (),
               refs: tuple[str, ...] = ()) -> StrategyPolicy:
        return StrategyPolicy(
            game_id=game.game_id, decision=decision, selected_move_ids=chosen,
            alternative_move_ids=alternatives, reasoning=reason,
            supporting_evidence_ids=refs,
            preserved_field_ref=game.protected_field_ref,
            return_condition=return_condition if decision is Decision.DO_NOT_PLAY else "",
        )

    if not moves:
        return policy(Decision.ABSTAIN, "No actions have been enumerated; the game is unknown.")
    available = tuple(m for m in moves if m.eligible is True and not m.protected_core_loss)
    unknown = any(m.eligible is None for m in moves)
    if not available:
        if unknown:
            return policy(Decision.ABSTAIN, "At least one move remains unqualified.")
        if not game.protected_field_ref or not return_condition:
            return policy(Decision.ABSTAIN, "Exit needs protected field and re-entry condition.")
        if not all(_verified_real_evidence(m.evidence_ids, by_id, game.game_id)
                   for m in moves):
            return policy(Decision.ABSTAIN,
                          "Cannot infer DO_NOT_PLAY from unverifiable or simulated blocks.")
        refs = tuple(sorted({x for m in moves for x in m.evidence_ids}))
        return policy(Decision.DO_NOT_PLAY,
                      "All proposed moves are evidence-backed blocked; keep scientific residue.",
                      refs=refs)

    # Unknown eligibility of other moves may conceal a superior strategy.
    if unknown:
        return policy(Decision.ABSTAIN, "Unqualified moves prevent a complete strategy comparison.",
                      alternatives=tuple(m.move_id for m in available))
    if any(not _verified_real_evidence(m.evidence_ids, by_id, game.game_id)
           for m in available):
        return policy(Decision.ABSTAIN, "A proposed winning move lacks verified real grounds.",
                      alternatives=tuple(m.move_id for m in available))
    frontier = _pareto(game, available)
    if not frontier:
        return policy(Decision.ABSTAIN, "Objective axes are incomplete or incompatible.")
    if len(frontier) != 1:
        return policy(Decision.ABSTAIN,
                      "Multiple Pareto-optimal strategies; owner must resolve trade-off.",
                      alternatives=tuple(m.move_id for m in frontier))
    best = frontier[0]
    mapping = {
        MoveKind.SWITCH_TARGET: Decision.SWITCH_TARGET,
        MoveKind.BRANCH: Decision.BRANCH,
        MoveKind.REOPEN_FIELD: Decision.REOPEN_FIELD,
    }
    return policy(
        mapping.get(best.kind, Decision.CONTINUE),
        "Single supported non-dominated candidate. Requires owner action gate.",
        chosen=(best.move_id,),
        alternatives=tuple(m.move_id for m in moves if m.move_id != best.move_id),
        refs=best.evidence_ids,
    )
