"""LOKI game-reverse-engineering R0 sidecar.

The public API is advisory and inert: no live Factory writes, reviewer
simulation as truth, email submission, Field mutation, or production mount.
"""
from .domain import (
    Decision,
    EvidenceKind,
    GameHypothesis,
    GameModel,
    MoveKind,
    OutcomeEvidence,
    ProbeKind,
    ProbeRecord,
    StrategicMove,
    StrategyPolicy,
    Verification,
)
from .engine import (
    ProbeRanking,
    assess_observation,
    discrimination_score,
    rank_discriminating_probes,
    recommend_strategy,
)
from .ledger import LokiLedger

__all__ = [
    "Decision", "EvidenceKind", "GameHypothesis", "GameModel", "MoveKind",
    "OutcomeEvidence", "ProbeKind", "ProbeRecord", "StrategicMove",
    "StrategyPolicy", "Verification", "ProbeRanking", "assess_observation",
    "discrimination_score", "rank_discriminating_probes", "recommend_strategy",
    "LokiLedger",
]
