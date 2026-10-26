"""SYNTHETIC fixture demo of the read-only LOKI R0 API."""
from __future__ import annotations

from dataclasses import asdict
import json

from .domain import GameModel, GameHypothesis, ProbeKind, ProbeRecord
from .engine import rank_discriminating_probes, recommend_strategy


def main() -> int:
    game = GameModel(
        game_id="FIXTURE:GAME", scope_ref="FIXTURE:JOURNAL",
        objective_ids=("scientific_integrity", "author_value"),
        protected_field_ref="FIXTURE:FIELD",
        unknowns=("Real journal source admission has not been run",),
    )
    hypotheses = (
        GameHypothesis("H:SCOPE", game.game_id, "Policy excludes topic", "scope"),
        GameHypothesis("H:METHOD", game.game_id, "Policy permits topic", "method"),
    )
    probe = ProbeRecord(
        "P:READ_POLICY", game.game_id, ProbeKind.PASSIVE_ANALYSIS,
        predictions=(("H:SCOPE", "topic_excluded"),
                     ("H:METHOD", "topic_permitted")),
        cost=1.0, source_refs=("FIXTURE:POLICY",),
    )
    ranked = rank_discriminating_probes(game, hypotheses, (probe,))
    policy = recommend_strategy(game, (), ())  # No real evidence; ABSTAIN.
    print(json.dumps({
        "mode": "SYNTHETIC_FIXTURE_ONLY",
        "game_id": game.game_id,
        "hypotheses": [h.hypothesis_id for h in hypotheses],
        "probe_frontier": [asdict(p) for p in ranked],
        "preregistration_sha256": probe.fingerprint,
        "decision": policy.decision.value,
        "human_approval_required": policy.human_approval_required,
        "real_journal_evidence": False,
        "external_actions_executed": 0,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
