"""Adversarial tests for the MAI-batch Trimurti phase scheduler.

These tests exercise:
* Happy path for 10+ routes reaching READY_FOR_AUTHOR_REWORK.
* Per-route independence (one route's hold/failure does not affect others).
* Phase advancement idempotency (same event hash on repeat).
* Typed phase checkpoints and named refusal codes.
* Adversarial guards:
    - Fake fulltext (raw_kind=fulltext without manuscript pointer/hash).
    - Same manuscript on two exclusive venues (dual-exclusive).
    - Generic editor address claimed as a CFP response (route type confusion).
    - Unapproved scientific promotion (general_promotion route_type).
* Idempotent restart: re-running the plan yields identical hashes/state.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kairoskopion.kairon_provider import (
    CHECKPOINT_STATUS_COMPLETED,
    CHECKPOINT_STATUS_FAILED,
    CHECKPOINT_STATUS_HOLD,
    CHECKPOINT_STATUS_IN_PROGRESS,
    CHECKPOINT_STATUS_PENDING,
    PHASE_ORDER,
    PhaseName,
    REFUSAL_CHALLENGE_HTML,
    REFUSAL_DUAL_EXCLUSIVE,
    REFUSAL_FAKE_FULLTEXT,
    REFUSAL_PROMOTION_UNAPPROVED,
    REFUSAL_ROUTE_TYPE_CONFUSION,
    RouteStatus,
    TrimurtiBatchPlan,
    TrimurtiBatchSpec,
    TrimurtiPlanStore,
    advance_phase,
    build_fixture_w12,
    build_run_receipt,
    build_trimurti_plan,
    claim_routes,
    compute_route_event_hash,
    plan_summary,
)
from kairoskopion.kairon_provider.trimurti_scheduler import (
    REFUSAL_DIRECT_PROMOTION,
    REFUSAL_EMPTY_EVIDENCE,
    REFUSAL_EMPTY_SCHOLARLY_EVIDENCE,
    REFUSAL_MISSING_FROZEN_TARGET,
    REFUSAL_STALE_REPLAY,
    REFUSAL_TERMINAL_PRECONDITION,
    _advance_checkpoints,
    _detect_route_conflicts,
)


def _frozen_targets_covering_all() -> list[dict]:
    """A frozen VenueTarget binding that matches every route_type.

    Tests that drive routes all the way to READY_FOR_AUTHOR_REWORK must
    supply this (or an equivalent binding) — the terminal gate refuses
    promotion for any route with no frozen venue target bound.
    """

    return [{"target_id": "target:fixture-frozen", "snapshot_id": "snap:fixture-frozen"}]


def _evidence_for(route_id: str, phase: PhaseName) -> list[str]:
    return [f"evidence:{route_id}:{phase.value}:provider=fixture-probe"]


def _records_with_fakes(*, fake_fulltext: bool = False, route_type: str | None = None, raw_kind: str | None = None, route_kind: str = "regular", manuscript_hash: str | None = None, exclusive_venue_class: str = "none", source_kind: str = "FIXTURE_NOT_REAL_DATA"):
    records, receipt = build_fixture_w12()
    out = []
    for record in records:
        new = record
        if fake_fulltext:
            new = _mutate_record(record, raw_kind="fulltext", manuscript_pointer=None, manuscript_hash=None)
        if route_type is not None:
            new = _mutate_record(new, route_type=route_type)
        if raw_kind is not None and not fake_fulltext:
            new = _mutate_record(new, raw_kind=raw_kind)
        if route_kind != "regular":
            new = _mutate_record(new, route_kind=route_kind)
        if manuscript_hash is not None:
            new = _mutate_record(new, manuscript_hash=manuscript_hash)
        if exclusive_venue_class != "none":
            new = _mutate_record(new, exclusive_venue_class=exclusive_venue_class)
        if source_kind != "FIXTURE_NOT_REAL_DATA":
            new = _mutate_record(new, source_kind=source_kind)
        out.append(new)
    return out, receipt


def _mutate_record(record, **overrides):
    from dataclasses import replace
    return replace(record, **overrides)


def test_build_plan_from_fixture_routes_retains_shape():
    records, receipt = build_fixture_w12()
    spec = TrimurtiBatchSpec(batch_id="batch:happy", concurrency_limit=3)
    plan = build_trimurti_plan(batch_id="batch:happy", w12_records=records, spec=spec)
    assert len(plan.routes) == 53
    assert receipt.records_count == 53
    assert receipt.seed_family_count == 6
    assert receipt.meaning_version_count == 27
    assert plan.spec.concurrency_limit == 3
    for route in plan.routes:
        assert route.status == RouteStatus.PENDING.value
        assert route.current_phase == PhaseName.SOURCE_EVIDENCE.value
        assert set(route.phase_checkpoints.keys()) == {p.value for p in PHASE_ORDER}


def test_ten_routes_reach_ready_for_author_rework():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:ready",
        w12_records=records[:10],
        spec=TrimurtiBatchSpec(batch_id="batch:ready", concurrency_limit=2),
        frozen_targets=_frozen_targets_covering_all(),
    )

    for route in plan.routes:
        for phase in PHASE_ORDER:
            advance_phase(
                plan,
                route_id=route.route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_COMPLETED,
                notes=[f"{phase.value} ok"],
                evidence_refs=[f"src:{route.route_id}:{phase.value}"],
            )
    summary = plan_summary(plan)
    assert summary["ready_for_author_rework"] == 10
    assert summary["hold_count"] == 0
    assert summary["failed_count"] == 0
    assert plan.status == "ready_for_author_rework"
    for route in plan.routes:
        assert route.status == RouteStatus.READY_FOR_AUTHOR_REWORK.value
        for phase in PHASE_ORDER:
            checkpoint = route.phase_checkpoints[phase.value]
            assert checkpoint.status == CHECKPOINT_STATUS_COMPLETED
            assert checkpoint.event_hash is not None
            assert checkpoint.completed_at is not None


def test_per_route_hold_does_not_block_other_routes():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:hold",
        w12_records=records[:5],
        frozen_targets=_frozen_targets_covering_all(),
    )
    failing_route = plan.routes[2]
    good_routes = [r for r in plan.routes if r.route_id != failing_route.route_id]

    advance_phase(
        plan,
        route_id=failing_route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_HOLD,
        notes=["source empty"],
    )
    for route in good_routes:
        for phase in PHASE_ORDER:
            advance_phase(
                plan,
                route_id=route.route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_COMPLETED,
                notes=["ok"],
                evidence_refs=_evidence_for(route.route_id, phase),
            )
    summary = plan_summary(plan)
    assert summary["hold_count"] == 1
    assert summary["ready_for_author_rework"] == 4
    assert summary["failed_count"] == 0
    assert failing_route.status == RouteStatus.HOLD.value
    assert failing_route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].status == CHECKPOINT_STATUS_HOLD


def test_per_route_failure_does_not_block_other_routes():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:fail",
        w12_records=records[:6],
        frozen_targets=_frozen_targets_covering_all(),
    )
    target = plan.routes[3]

    advance_phase(
        plan,
        route_id=target.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_FAILED,
        notes=["schema invalid"],
    )
    for route in plan.routes:
        if route.route_id == target.route_id:
            continue
        for phase in PHASE_ORDER:
            advance_phase(
                plan,
                route_id=route.route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_COMPLETED,
                evidence_refs=_evidence_for(route.route_id, phase),
            )

    summary = plan_summary(plan)
    assert summary["failed_count"] == 1
    assert summary["ready_for_author_rework"] == 5
    assert target.status == RouteStatus.FAILED.value
    assert any("schema invalid" in n for n in target.hold_failures)


def test_phase_advancement_is_idempotent():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:idem", w12_records=records[:2])

    first = advance_phase(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        notes=["first run"],
        evidence_refs=["ref:1", "ref:2"],
    )
    second = advance_phase(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        notes=["first run"],
        evidence_refs=["ref:1", "ref:2"],
    )
    assert first.last_event_hash == second.last_event_hash
    assert (
        first.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash
        == second.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash
    )


def test_compute_route_event_hash_is_deterministic():
    h1 = compute_route_event_hash(
        route_id="r1", phase=PhaseName.SOURCE_EVIDENCE.value, status="completed"
    )
    h2 = compute_route_event_hash(
        route_id="r1", phase=PhaseName.SOURCE_EVIDENCE.value, status="completed"
    )
    assert h1 == h2
    assert h1.startswith("tev_")
    assert len(h1) == 4 + 16


def test_fake_fulltext_routes_are_marked_refused():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(
            record,
            raw_kind="fulltext",
            manuscript_pointer=None,
            manuscript_hash=None,
        )
        for record in records
    ]
    plan = build_trimurti_plan(batch_id="batch:fake", w12_records=mutated)
    refused = [r for r in plan.routes if REFUSAL_FAKE_FULLTEXT in r.refusal_codes]
    assert len(refused) == len(mutated)


def test_fake_fulltext_routes_cannot_advance_past_source_evidence():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, raw_kind="fulltext", manuscript_pointer=None, manuscript_hash=None)
        for record in records[:1]
    ]
    plan = build_trimurti_plan(batch_id="batch:fake-advance", w12_records=mutated)
    target = plan.routes[0]
    with pytest.raises(ValueError, match="refusal codes"):
        advance_phase(
            plan,
            route_id=target.route_id,
            phase=PhaseName.SCHOLARLY_CHALLENGE,
            status=CHECKPOINT_STATUS_COMPLETED,
        )


def test_dual_exclusive_venues_share_same_manuscript_rejected():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(
            records[0],
            route_kind="exclusive",
            manuscript_hash="manuscript:001",
            exclusive_venue_class="exclusive",
        ),
        _mutate_record(
            records[1],
            route_kind="exclusive",
            manuscript_hash="manuscript:001",
            exclusive_venue_class="exclusive",
        ),
    ]
    plan = build_trimurti_plan(batch_id="batch:dual-exclusive", w12_records=mutated)
    codes = [r.refusal_codes for r in plan.routes]
    assert all(REFUSAL_DUAL_EXCLUSIVE in c for c in codes)


def test_route_type_confusion_generic_editor_address_rejected():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, route_type="generic_editor_address")
        for record in records[:3]
    ]
    plan = build_trimurti_plan(batch_id="batch:typeconf", w12_records=mutated)
    for route in plan.routes:
        assert REFUSAL_ROUTE_TYPE_CONFUSION in route.refusal_codes


def test_generic_promotion_route_is_rejected():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, route_type="general_promotion")
        for record in records[:2]
    ]
    plan = build_trimurti_plan(batch_id="batch:promo", w12_records=mutated)
    for route in plan.routes:
        assert REFUSAL_PROMOTION_UNAPPROVED in route.refusal_codes


def test_challenge_html_raw_kind_rejected():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, raw_kind="challenge_html") for record in records[:1]
    ]
    plan = build_trimurti_plan(batch_id="batch:challenge", w12_records=mutated)
    assert REFUSAL_CHALLENGE_HTML in plan.routes[0].refusal_codes


def test_claim_routes_skips_refused_routes():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, raw_kind="fulltext", manuscript_pointer=None, manuscript_hash=None)
        if i == 0
        else record
        for i, record in enumerate(records[:5])
    ]
    plan = build_trimurti_plan(batch_id="batch:claim", w12_records=mutated)
    claimed = claim_routes(plan, limit=10)
    assert len(claimed) == 4
    assert all(REFUSAL_FAKE_FULLTEXT not in r.refusal_codes for r in claimed)
    assert plan.status == "running"


def test_claim_routes_respects_concurrency_limit():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:limit",
        w12_records=records[:12],
        spec=TrimurtiBatchSpec(batch_id="batch:limit", concurrency_limit=3),
    )
    claimed = claim_routes(plan)
    assert len(claimed) == 3
    assert all(r.status == RouteStatus.IN_PROGRESS.value for r in claimed)


def test_run_receipt_includes_event_hashes():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:receipt", w12_records=records[:2])
    for route in plan.routes:
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SOURCE_EVIDENCE,
            status=CHECKPOINT_STATUS_COMPLETED,
            notes=["ok"],
            evidence_refs=_evidence_for(route.route_id, PhaseName.SOURCE_EVIDENCE),
        )
    receipt = build_run_receipt(plan)
    assert receipt.batch_id == "batch:receipt"
    assert len(receipt.route_event_hashes) == 2
    assert receipt.completed_count == 0
    assert receipt.ready_count == 0
    for route_id, hash_ in receipt.route_event_hashes.items():
        assert hash_.startswith("tev_")


def test_plan_store_round_trip(tmp_path: Path):
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:store",
        w12_records=records[:5],
        spec=TrimurtiBatchSpec(batch_id="batch:store", concurrency_limit=2),
    )
    store = TrimurtiPlanStore(tmp_path)
    store.put(plan)
    restored = store.get("batch:store")
    assert restored is not None
    assert restored.spec.concurrency_limit == 2
    assert len(restored.routes) == 5
    assert restored.routes[0].route_id == plan.routes[0].route_id


def test_idempotent_restart_produces_same_state_hashes(tmp_path: Path):
    records, _ = build_fixture_w12()
    plan_a = build_trimurti_plan(
        batch_id="batch:restart",
        w12_records=records[:4],
        frozen_targets=_frozen_targets_covering_all(),
    )
    plan_b = build_trimurti_plan(
        batch_id="batch:restart",
        w12_records=records[:4],
        frozen_targets=_frozen_targets_covering_all(),
    )
    for plan in (plan_a, plan_b):
        for route in plan.routes:
            for phase in PHASE_ORDER:
                advance_phase(
                    plan,
                    route_id=route.route_id,
                    phase=phase,
                    status=CHECKPOINT_STATUS_COMPLETED,
                    notes=["deterministic"],
                    evidence_refs=["ref:stable"],
                )

    for route_a, route_b in zip(plan_a.routes, plan_b.routes):
        assert route_a.route_id == route_b.route_id
        assert route_a.last_event_hash == route_b.last_event_hash
        for phase in PHASE_ORDER:
            assert (
                route_a.phase_checkpoints[phase.value].event_hash
                == route_b.phase_checkpoints[phase.value].event_hash
            )


def test_partial_failure_yields_blocked_partial_status():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:partial",
        w12_records=records[:6],
        frozen_targets=_frozen_targets_covering_all(),
    )
    advance_phase(
        plan,
        route_id=plan.routes[0].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_FAILED,
    )
    advance_phase(
        plan,
        route_id=plan.routes[1].route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_HOLD,
    )
    for route in plan.routes[2:]:
        for phase in PHASE_ORDER:
            advance_phase(
                plan,
                route_id=route.route_id,
                phase=phase,
                status=CHECKPOINT_STATUS_COMPLETED,
                evidence_refs=_evidence_for(route.route_id, phase),
            )
    summary = plan_summary(plan)
    assert summary["ready_for_author_rework"] == 4
    assert summary["failed_count"] == 1
    assert summary["hold_count"] == 1
    assert plan.status == "blocked_partial"


def test_advance_unknown_phase_raises():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:bad-phase", w12_records=records[:1])
    with pytest.raises(ValueError, match="unknown phase"):
        advance_phase(
            plan,
            route_id=plan.routes[0].route_id,
            phase="not_a_phase",
            status=CHECKPOINT_STATUS_COMPLETED,
        )


def test_advance_unknown_route_raises():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:bad-route", w12_records=records[:1])
    with pytest.raises(KeyError, match="route_id not in plan"):
        advance_phase(
            plan,
            route_id="route:missing",
            phase=PhaseName.SOURCE_EVIDENCE,
            status=CHECKPOINT_STATUS_COMPLETED,
        )


def test_phase_checkpoints_are_typed():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:typed", w12_records=records[:1])
    route = plan.routes[0]
    for phase in PHASE_ORDER:
        cp = route.phase_checkpoints[phase.value]
        assert cp.phase == phase.value
        assert cp.status in {
            CHECKPOINT_STATUS_PENDING,
            CHECKPOINT_STATUS_IN_PROGRESS,
            CHECKPOINT_STATUS_COMPLETED,
            CHECKPOINT_STATUS_HOLD,
            CHECKPOINT_STATUS_FAILED,
        }


def test_concurrent_double_advance_keeps_state_consistent(tmp_path: Path):
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:concurrent", w12_records=records[:3])
    claimed = claim_routes(plan, limit=3)
    assert len(claimed) == 3
    for route in claimed:
        cp = route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value]
        assert cp.status == CHECKPOINT_STATUS_IN_PROGRESS
        assert route.status == RouteStatus.IN_PROGRESS.value
    store = TrimurtiPlanStore(tmp_path)
    store.put(plan)
    reloaded = store.get("batch:concurrent")
    assert reloaded is not None
    for route in reloaded.routes:
        cp = route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value]
        assert cp.status == CHECKPOINT_STATUS_IN_PROGRESS


def test_plan_summary_counts_refusal_codes():
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, route_type="general_promotion")
        if i % 2 == 0
        else record
        for i, record in enumerate(records[:4])
    ]
    plan = build_trimurti_plan(batch_id="batch:summary", w12_records=mutated)
    summary = plan_summary(plan)
    assert summary["by_refusal_code"][REFUSAL_PROMOTION_UNAPPROVED] == 2


def test_refusal_codes_survive_reload(tmp_path: Path):
    records, _ = build_fixture_w12()
    mutated = [
        _mutate_record(record, route_type="general_promotion")
        for record in records[:3]
    ]
    plan = build_trimurti_plan(batch_id="batch:reload-refusal", w12_records=mutated)
    store = TrimurtiPlanStore(tmp_path)
    store.put(plan)
    reloaded = store.get("batch:reload-refusal")
    assert reloaded is not None
    for route in reloaded.routes:
        assert REFUSAL_PROMOTION_UNAPPROVED in route.refusal_codes


def test_hold_then_resume_advances_to_completed():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:resume",
        w12_records=records[:1],
        frozen_targets=_frozen_targets_covering_all(),
    )
    route = plan.routes[0]
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_HOLD,
        notes=["pending external task"],
    )
    assert route.status == RouteStatus.HOLD.value
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        notes=["external task completed"],
        evidence_refs=_evidence_for(route.route_id, PhaseName.SOURCE_EVIDENCE),
    )
    for phase in list(PHASE_ORDER)[1:]:
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=phase,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=_evidence_for(route.route_id, phase),
        )
    assert route.status == RouteStatus.READY_FOR_AUTHOR_REWORK.value


# ---------------------------------------------------------------------------
# HEAD-TRIMURTI P0 fix (2026-10-20): semantic fail-open regression guards.
#
# Reproduces and closes the regression from GitHub issue #45:
#   advance_phase(plan, route_id=FIRST_REAL_ROUTE,
#                 phase="ready_for_author_rework", status="completed",
#                 evidence_refs=[])
#   previously returned READY while source_evidence=PENDING and qa=PENDING,
#   and scholarly_challenge could be "completed" with no evidence.
# ---------------------------------------------------------------------------


def test_probe_direct_jump_to_terminal_with_empty_evidence_is_blocked():
    """Exact regression shape from issue #45: must no longer go READY."""

    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:probe-regression",
        w12_records=records[:1],
        frozen_targets=_frozen_targets_covering_all(),
    )
    first_real_route = plan.routes[0]
    assert first_real_route.status == RouteStatus.PENDING.value
    assert first_real_route.current_phase == PhaseName.SOURCE_EVIDENCE.value

    with pytest.raises(ValueError, match=REFUSAL_DIRECT_PROMOTION):
        advance_phase(
            plan,
            route_id=first_real_route.route_id,
            phase="ready_for_author_rework",
            status="completed",
            evidence_refs=[],
        )

    assert first_real_route.status == RouteStatus.PENDING.value
    assert first_real_route.current_phase == PhaseName.SOURCE_EVIDENCE.value
    assert (
        first_real_route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].status
        == CHECKPOINT_STATUS_PENDING
    )
    assert (
        first_real_route.phase_checkpoints[PhaseName.QA.value].status
        == CHECKPOINT_STATUS_PENDING
    )


def test_direct_jump_several_phases_ahead_is_blocked_direct_promotion():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:jump", w12_records=records[:1])
    route = plan.routes[0]
    with pytest.raises(ValueError, match=REFUSAL_DIRECT_PROMOTION):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.EDITORIAL_PACKET,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:1"],
        )
    assert route.current_phase == PhaseName.SOURCE_EVIDENCE.value


def test_scholarly_challenge_completed_with_empty_evidence_is_blocked():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:empty-scholarly", w12_records=records[:1])
    route = plan.routes[0]
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:source"],
    )
    with pytest.raises(ValueError, match=REFUSAL_EMPTY_SCHOLARLY_EVIDENCE):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SCHOLARLY_CHALLENGE,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=[],
        )
    assert route.current_phase == PhaseName.SCHOLARLY_CHALLENGE.value
    assert (
        route.phase_checkpoints[PhaseName.SCHOLARLY_CHALLENGE.value].status
        == CHECKPOINT_STATUS_PENDING
    )


def test_whitespace_only_evidence_refs_are_treated_as_empty():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:whitespace-evidence", w12_records=records[:1])
    route = plan.routes[0]
    with pytest.raises(ValueError, match=REFUSAL_EMPTY_EVIDENCE):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SOURCE_EVIDENCE,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["   ", ""],
        )


def test_empty_editorial_packet_evidence_is_blocked_before_terminal():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:empty-packet",
        w12_records=records[:1],
        frozen_targets=_frozen_targets_covering_all(),
    )
    route = plan.routes[0]
    for phase in list(PHASE_ORDER)[:5]:
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=phase,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=_evidence_for(route.route_id, phase),
        )
    assert route.current_phase == PhaseName.EDITORIAL_PACKET.value
    with pytest.raises(ValueError, match=REFUSAL_EMPTY_EVIDENCE):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.EDITORIAL_PACKET,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=[],
        )


def test_missing_frozen_venue_target_blocks_terminal_promotion():
    """All 7 prior phases genuinely completed with evidence, but no frozen
    VenueTarget was ever bound (build_trimurti_plan called with no
    frozen_targets) — terminal promotion must still be refused."""

    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:no-frozen-target", w12_records=records[:1])
    route = plan.routes[0]
    assert route.frozen_target_id is None
    for phase in list(PHASE_ORDER)[:-1]:
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=phase,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=_evidence_for(route.route_id, phase),
        )
    assert route.current_phase == PhaseName.READY_FOR_AUTHOR_REWORK.value
    with pytest.raises(ValueError, match=REFUSAL_MISSING_FROZEN_TARGET):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.READY_FOR_AUTHOR_REWORK,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:editorial-packet-digest:sha256:deadbeef"],
        )
    assert route.status != RouteStatus.READY_FOR_AUTHOR_REWORK.value


def test_stale_phase_replay_with_changed_evidence_is_rejected():
    """Re-submitting an already-completed phase with different evidence
    must not be silently accepted (no last-write-wins on history), and
    must never regress route.current_phase backward."""

    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:stale-replay", w12_records=records[:1])
    route = plan.routes[0]
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:source:v1"],
    )
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SCHOLARLY_CHALLENGE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:challenge:v1"],
    )
    assert route.current_phase == PhaseName.VENUE_QUALIFICATION.value

    with pytest.raises(ValueError, match=REFUSAL_STALE_REPLAY):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SOURCE_EVIDENCE,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:source:v2-different"],
        )
    # Stale rejection must not regress current_phase.
    assert route.current_phase == PhaseName.VENUE_QUALIFICATION.value
    assert route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].evidence_refs == [
        "ev:source:v1"
    ]


def test_identical_replay_of_completed_phase_is_idempotent_no_op():
    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:identical-replay", w12_records=records[:1])
    route = plan.routes[0]
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:source:v1"],
    )
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SCHOLARLY_CHALLENGE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:challenge:v1"],
    )
    before_hash = route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash
    # Byte-identical replay of the already-completed earlier phase: allowed,
    # reasserts the same receipt, does not touch current_phase.
    advance_phase(
        plan,
        route_id=route.route_id,
        phase=PhaseName.SOURCE_EVIDENCE,
        status=CHECKPOINT_STATUS_COMPLETED,
        evidence_refs=["ev:source:v1"],
    )
    assert route.current_phase == PhaseName.VENUE_QUALIFICATION.value
    assert route.phase_checkpoints[PhaseName.SOURCE_EVIDENCE.value].event_hash == before_hash


def test_derived_sheet_snapshot_source_gets_no_evidence_exemption():
    """A route sourced from the authorized-but-derived W12 sheet snapshot
    (not the fixture, not a full-bytes real import) must still pass
    through the same evidence/order gate — source_kind alone is never
    treated as scholarly acceptance."""

    records, _ = build_fixture_w12()
    mutated = [_mutate_record(records[0], source_kind="DERIVED_SHEET_SNAPSHOT")]
    plan = build_trimurti_plan(batch_id="batch:derived-sheet", w12_records=mutated)
    route = plan.routes[0]
    assert route.source_kind == "DERIVED_SHEET_SNAPSHOT"

    with pytest.raises(ValueError, match=REFUSAL_DIRECT_PROMOTION):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.READY_FOR_AUTHOR_REWORK,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:anything"],
        )

    with pytest.raises(ValueError, match=REFUSAL_EMPTY_SCHOLARLY_EVIDENCE):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SOURCE_EVIDENCE,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:source"],
        )
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.SCHOLARLY_CHALLENGE,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=[],
        )


def test_hold_resume_phase_cannot_be_skipped_either():
    """A HOLD can only be recorded against the route's current phase —
    it cannot be used to mark a future phase as blocked out of order."""

    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(batch_id="batch:hold-order", w12_records=records[:1])
    route = plan.routes[0]
    with pytest.raises(ValueError, match=REFUSAL_DIRECT_PROMOTION):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.QA,
            status=CHECKPOINT_STATUS_HOLD,
            notes=["out of order hold attempt"],
        )


def test_terminal_precondition_rechecked_even_if_checkpoints_hand_edited(tmp_path: Path):
    """Defense-in-depth: even if a stored plan on disk has a dangling
    'completed' checkpoint with empty evidence (e.g. hand-edited JSON),
    the terminal gate re-validates from the stored checkpoints rather
    than trusting route.current_phase alone."""

    records, _ = build_fixture_w12()
    plan = build_trimurti_plan(
        batch_id="batch:hand-edited",
        w12_records=records[:1],
        frozen_targets=_frozen_targets_covering_all(),
    )
    route = plan.routes[0]
    for phase in list(PHASE_ORDER)[:-1]:
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=phase,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=_evidence_for(route.route_id, phase),
        )
    # Simulate corruption: wipe the QA checkpoint's evidence after the fact.
    route.phase_checkpoints[PhaseName.QA.value].evidence_refs = []
    with pytest.raises(ValueError, match=REFUSAL_TERMINAL_PRECONDITION + "|" + REFUSAL_EMPTY_EVIDENCE):
        advance_phase(
            plan,
            route_id=route.route_id,
            phase=PhaseName.READY_FOR_AUTHOR_REWORK,
            status=CHECKPOINT_STATUS_COMPLETED,
            evidence_refs=["ev:final-receipt"],
        )