"""LOKI R0 synthetic contract tests — NOT evidence of a real editorial outcome."""
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
import json

import pytest

from kairoskopion.loki import (
    Decision, EvidenceKind, GameHypothesis, GameModel, LokiLedger, MoveKind,
    OutcomeEvidence, ProbeKind, ProbeRecord, StrategicMove, Verification,
    assess_observation, discrimination_score, rank_discriminating_probes,
    recommend_strategy,
)


def game(**overrides):
    args = dict(game_id="GAME:MAI:fixture", scope_ref="JOURNAL:fixture",
                objective_ids=("scientific_integrity", "author_value"),
                protected_field_ref="FIELD:fixture")
    args.update(overrides)
    return GameModel(**args)


def hypotheses():
    g = game().game_id
    return (
        GameHypothesis("H:SCOPE", g, "scope exclusion", "topic rule"),
        GameHypothesis("H:METHOD", g, "method not sufficient", "method regime"),
        GameHypothesis("H:GENRE", g, "genre mismatch", "rhetorical regime"),
    )


def probe(**overrides):
    args = dict(probe_id="P:1", game_id=game().game_id,
                kind=ProbeKind.PASSIVE_ANALYSIS,
                predictions=(("H:SCOPE", "excluded"), ("H:METHOD", "allowed"),
                             ("H:GENRE", "allowed")),
                cost=1.0)
    args.update(overrides)
    return ProbeRecord(**args)


def observation(p=None, **overrides):
    p = p or probe()
    args = dict(evidence_id="E:1", game_id=p.game_id, probe_id=p.probe_id,
                probe_fingerprint=p.fingerprint, outcome="allowed",
                kind=EvidenceKind.PUBLIC_SOURCE,
                verification=Verification.VERIFIED,
                source_ref="fixture://publisher-policy-v1", observed_at="2026-10-20")
    args.update(overrides)
    return OutcomeEvidence(**args)


def move(mid="M:1", **overrides):
    args = dict(move_id=mid, game_id=game().game_id,
                kind=MoveKind.CONTINUE,
                objective_impacts=(("scientific_integrity", 1), ("author_value", 1)),
                eligible=True, evidence_ids=("E:1",))
    args.update(overrides)
    return StrategicMove(**args)


def test_exactly_six_public_domain_types_and_inert_policy():
    g, h, p, e, m = game(), hypotheses()[0], probe(), observation(), move()
    assert all((g.game_id, h.hypothesis_id, p.probe_id, e.evidence_id, m.move_id))
    policy = recommend_strategy(g, (m,), (e,))
    assert policy.decision is Decision.CONTINUE
    assert policy.selected_move_ids == ("M:1",)
    assert policy.human_approval_required and not policy.executable_action


def test_frozen_contracts_and_unique_objectives():
    with pytest.raises(FrozenInstanceError):
        game().scope_ref = "changed"
    with pytest.raises(ValueError, match="unique"):
        game(objective_ids=("speed", "speed"))
    with pytest.raises(ValueError, match="objective_ids"):
        game(objective_ids=())


def test_probe_predictions_are_frozen_and_fingerprint_changes_on_rewrite():
    p = probe()
    assert p.fingerprint == probe().fingerprint
    with pytest.raises(FrozenInstanceError):
        p.predictions = ()
    modified = replace(p, predictions=(("H:SCOPE", "allowed"), ("H:METHOD", "allowed")))
    assert modified.fingerprint != p.fingerprint


def test_discriminating_probe_selection_with_forbidden_external_probe():
    g, hs = game(), hypotheses()
    a = probe(probe_id="A", predictions=(("H:SCOPE", "same"),
                                          ("H:METHOD", "same"),
                                          ("H:GENRE", "same")), cost=0.1)
    b = probe(probe_id="B", predictions=(("H:SCOPE", "one"),
                                          ("H:METHOD", "two"),
                                          ("H:GENRE", "two")), cost=2.0)
    c = probe(probe_id="C", predictions=(("H:SCOPE", "one"),
                                          ("H:METHOD", "two"),
                                          ("H:GENRE", "three")), cost=0.01,
              kind=ProbeKind.AUTHORIZED_REAL_ACTION, access_approved=False)
    assert discrimination_score(a, hs) == 0
    assert discrimination_score(b, hs) == 2
    assert discrimination_score(c, hs) == 3
    ranked = rank_discriminating_probes(g, hs, (a, b, c))
    assert tuple(r.probe_id for r in ranked) == ("B",)


def test_probe_pareto_does_not_collapse_cost_and_discrimination():
    g, hs = game(), hypotheses()
    cheap = probe(probe_id="CHEAP", predictions=(("H:SCOPE", "x"),
                                                 ("H:METHOD", "y"),
                                                 ("H:GENRE", "y")), cost=0.5)
    informative = probe(probe_id="INFORMATIVE",
                        predictions=(("H:SCOPE", "x"), ("H:METHOD", "y"),
                                     ("H:GENRE", "z")), cost=2.0)
    dominated = probe(probe_id="DOMINATED", predictions=cheap.predictions, cost=5.0)
    assert {r.probe_id for r in rank_discriminating_probes(
        g, hs, (cheap, informative, dominated)
    )} == {"CHEAP", "INFORMATIVE"}


def test_unknown_predictions_and_invalid_hypothesis_ids():
    p = probe(predictions=(("H:SCOPE", "UNKNOWN"),
                           ("H:METHOD", "outcome"),
                           ("H:GENRE", "outcome")))
    assert discrimination_score(p, hypotheses()) == 0
    with pytest.raises(ValueError, match="undeclared"):
        discrimination_score(probe(predictions=(("H:BOGUS", "x"),)), hypotheses())


def test_observation_is_consistency_not_causation():
    statuses = assess_observation(probe(), hypotheses(), observation())
    assert statuses == {
        "H:SCOPE": "INCONSISTENT", "H:METHOD": "CONSISTENT",
        "H:GENRE": "CONSISTENT",
    }


def test_simulation_and_fixture_cannot_update_real_game():
    for kind in (EvidenceKind.SIMULATION, EvidenceKind.TEST_FIXTURE):
        statuses = assess_observation(
            probe(), hypotheses(), observation(kind=kind)
        )
        assert set(statuses.values()) == {"NOT_REAL_GAME_EVIDENCE"}


def test_negative_search_alone_does_not_disprove_hypotheses():
    ev = observation(kind=EvidenceKind.NEGATIVE_SEARCH,
                     negative_search_scope="one restricted index")
    assert set(assess_observation(probe(), hypotheses(), ev).values()) == {
        "NOT_REAL_GAME_EVIDENCE"
    }
    with pytest.raises(ValueError, match="scope"):
        observation(kind=EvidenceKind.NEGATIVE_SEARCH)


def test_partial_and_unverified_remain_indeterminate():
    for status in (Verification.PARTIAL, Verification.UNVERIFIED,
                   Verification.CONTRADICTORY):
        results = assess_observation(probe(), hypotheses(),
                                     observation(verification=status))
        assert set(results.values()) == {"INDETERMINATE"}


def test_post_hoc_prediction_mutation_cannot_claim_pre_registered_observation():
    p = probe()
    modified = replace(p, predictions=(("H:SCOPE", "new"),
                                       ("H:METHOD", "allowed")))
    with pytest.raises(ValueError, match="fingerprint"):
        assess_observation(modified, hypotheses(), observation(p=p))


def test_cross_game_sources_and_predictions_fail():
    with pytest.raises(ValueError, match="cross-game"):
        rank_discriminating_probes(game(),
                                  hypotheses(), (probe(game_id="OTHER"),))
    with pytest.raises(ValueError, match="cross-game"):
        recommend_strategy(game(), (move(),),
                           (observation(game_id="DIFFERENT"),))


def test_do_not_play_is_first_class_with_verified_blocks_and_reentry():
    m1 = move("M:1", eligible=False)
    m2 = move("M:2", eligible=False)
    result = recommend_strategy(game(), (m1, m2), (observation(),),
                                return_condition="Recheck on official scope change")
    assert result.decision is Decision.DO_NOT_PLAY
    assert result.supporting_evidence_ids == ("E:1",)
    assert result.preserved_field_ref == "FIELD:fixture"
    assert result.return_condition.startswith("Recheck")
    assert not result.executable_action


def test_simulated_or_unverified_block_cannot_justify_exit():
    blocked = move(eligible=False)
    for ev in (observation(kind=EvidenceKind.SIMULATION),
               observation(verification=Verification.UNVERIFIED)):
        policy = recommend_strategy(game(), (blocked,), (ev,),
                                    return_condition="Another issue")
        assert policy.decision is Decision.ABSTAIN


def test_unknown_move_is_not_equivalent_to_a_blocked_move():
    known_block = move("M:1", eligible=False)
    unknown = move("M:2", eligible=None)
    result = recommend_strategy(game(), (known_block, unknown),
                                (observation(),), return_condition="Some future test")
    assert result.decision is Decision.ABSTAIN


def test_missing_exit_reentry_or_field_residue_prevents_exit():
    blocked = move(eligible=False)
    result = recommend_strategy(game(), (blocked,), (observation(),))
    assert result.decision is Decision.ABSTAIN
    no_field = game(protected_field_ref="")
    assert recommend_strategy(no_field, (blocked,), (observation(),),
                              return_condition="Try later").decision is Decision.ABSTAIN


def test_supported_dominant_target_switch_and_author_gate():
    other = move("M:1", objective_impacts=(
        ("scientific_integrity", 0), ("author_value", 0)))
    target = move("M:2", kind=MoveKind.SWITCH_TARGET, objective_impacts=(
        ("scientific_integrity", 2), ("author_value", 1)))
    result = recommend_strategy(game(), (other, target), (observation(),))
    assert result.decision is Decision.SWITCH_TARGET
    assert result.selected_move_ids == ("M:2",)
    assert result.human_approval_required
    assert not result.executable_action


def test_pareto_conflict_needs_owner_not_fabricated_scalar_weights():
    integrity = move("M:I", objective_impacts=(
        ("scientific_integrity", 2), ("author_value", 0)))
    author = move("M:A", objective_impacts=(
        ("scientific_integrity", 0), ("author_value", 2)))
    policy = recommend_strategy(game(), (integrity, author), (observation(),))
    assert policy.decision is Decision.ABSTAIN
    assert set(policy.alternative_move_ids) == {"M:I", "M:A"}


def test_incomplete_goal_axes_or_no_moves_is_abstain():
    incomplete = move(objective_impacts=(("scientific_integrity", 2),))
    assert recommend_strategy(game(), (incomplete,), (observation(),)).decision is Decision.ABSTAIN
    assert recommend_strategy(game(), (), (observation(),)).decision is Decision.ABSTAIN


def test_good_move_without_real_evidence_cannot_be_called_winning():
    assert recommend_strategy(game(), (move(),),
                              (observation(kind=EvidenceKind.TEST_FIXTURE),)).decision is Decision.ABSTAIN


def test_protected_core_loss_is_not_silently_accepted():
    lossy = move(eligible=True, protected_core_loss=True)
    result = recommend_strategy(game(), (lossy,), (observation(),),
                                return_condition="Review core preservation")
    assert result.decision is Decision.DO_NOT_PLAY
    assert not result.executable_action


def test_evidence_requires_source_pointer_even_on_synthetic_cases():
    with pytest.raises(ValueError, match="source_ref"):
        observation(source_ref="")


def test_duplicate_probes_or_moves_fail():
    with pytest.raises(ValueError, match="duplicate probe"):
        rank_discriminating_probes(game(), hypotheses(), (probe(), probe()))
    with pytest.raises(ValueError, match="duplicate move"):
        recommend_strategy(game(), (move(), move()), (observation(),))


def test_ledger_is_read_only_by_default(tmp_path: Path):
    ledger = LokiLedger(tmp_path / "trace.jsonl")
    assert ledger.read() == ()
    with pytest.raises(PermissionError):
        ledger.append("evt:1", "ProbeDesigned", {"probe_id": "P:1"})


def test_ledger_append_idempotency_cold_resume_and_hash_chain(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    writer = LokiLedger(path, write_enabled=True)
    assert writer.append("evt:1", "ProbeDesigned", {"probe_id": "P:1"})
    assert not writer.append("evt:1", "ProbeDesigned", {"probe_id": "P:1"})
    assert writer.append("evt:2", "EvidenceAdmitted", {"evidence_ref": "E:1"})
    frozen = LokiLedger(path).read()  # Cold read from a distinct object.
    assert len(frozen) == 2
    assert frozen[1]["previous_hash"] == frozen[0]["event_hash"]
    with pytest.raises(ValueError, match="collision"):
        writer.append("evt:1", "ProbeDesigned", {"probe_id": "P:other"})


def test_ledger_detects_tampering_before_append(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    store = LokiLedger(path, write_enabled=True)
    store.append("evt:1", "ProbeDesigned", {"value": "original"})
    raw = path.read_text(encoding="utf-8")
    path.write_text(raw.replace("original", "tampered"), encoding="utf-8")
    with pytest.raises(ValueError, match="hash-chain"):
        LokiLedger(path).read()
    with pytest.raises(ValueError, match="hash-chain"):
        store.append("evt:2", "EvidenceAdmitted", {"value": "after corruption"})


def test_ledger_rejects_embedded_private_raw_text(tmp_path: Path):
    writer = LokiLedger(tmp_path / "trace.jsonl", write_enabled=True)
    with pytest.raises(ValueError, match="protected"):
        writer.append("evt:bad", "Evidence", {
            "source_id": "safe-ref",
            "nested": {"email_body": "private editorial letter"},
        })
    assert writer.read() == ()


def test_ledger_rejects_invalid_json_payload_without_write(tmp_path: Path):
    path = tmp_path / "trace.jsonl"
    store = LokiLedger(path, write_enabled=True)
    with pytest.raises(TypeError):
        store.append("evt:bad", "Evidence", {"opaque": object()})
    assert not path.exists()


def test_external_action_probe_requires_explicit_authorization_for_ranking():
    unapproved = probe(kind=ProbeKind.AUTHORIZED_REAL_ACTION,
                       access_approved=False)
    approved = replace(unapproved, access_approved=True)
    assert rank_discriminating_probes(game(), hypotheses(), (unapproved,)) == ()
    assert len(rank_discriminating_probes(game(), hypotheses(), (approved,))) == 1
    # This planner NEVER executes either probe: permission here only admits design.


def test_negative_evidence_and_immutable_source_ref_not_a_send():
    p = probe()
    ev = observation(p, kind=EvidenceKind.TEST_FIXTURE,
                     source_ref="fixture://never-sent")
    assert not ev.is_verified_real
    assert ev.probe_fingerprint == p.fingerprint
    assert not recommend_strategy(game(), (move(),), (ev,)).executable_action


def test_raw_string_enums_cannot_bypass_probe_authority():
    with pytest.raises(ValueError, match="kind"):
        probe(kind="AUTHORIZED_REAL_ACTION", access_approved=False)
    with pytest.raises(ValueError, match="boolean"):
        probe(kind=ProbeKind.AUTHORIZED_REAL_ACTION, access_approved="yes")


def test_mutable_predictions_cannot_rewrite_preregistration():
    with pytest.raises(ValueError, match="immutable"):
        probe(predictions=[("H:SCOPE", "old"), ("H:METHOD", "new")])


def test_evidence_requires_typed_kind_and_verification():
    with pytest.raises(ValueError, match="kind"):
        observation(kind="SIMULATION")
    with pytest.raises(ValueError, match="verification"):
        observation(verification="VERIFIED")


def test_raw_eligibility_and_move_kind_are_rejected():
    with pytest.raises(ValueError, match="eligible"):
        move(eligible="false")
    with pytest.raises(ValueError, match="kind"):
        move(kind="CONTINUE")


def test_strategy_policy_cannot_be_created_from_untyped_decision():
    from kairoskopion.loki import StrategyPolicy

    with pytest.raises(ValueError, match="decision"):
        StrategyPolicy(game_id=game().game_id, decision="CONTINUE",
                       selected_move_ids=(), alternative_move_ids=(),
                       reasoning="Untyped decision")
    with pytest.raises(ValueError, match="boolean"):
        StrategyPolicy(game_id=game().game_id, decision=Decision.ABSTAIN,
                       selected_move_ids=(), alternative_move_ids=(),
                       reasoning="Bad execution bit", executable_action="yes")


def test_domain_lists_are_not_immutable_tuples():
    with pytest.raises(ValueError, match="immutable"):
        game(objective_ids=["quality"])
    with pytest.raises(ValueError, match="immutable"):
        GameHypothesis("H:X", game().game_id, "proposition",
                       "mechanism", rival_ids=["H:Y"])
