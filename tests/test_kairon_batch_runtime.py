import pytest

from kairoskopion.kairon_provider import ArtiklStatePointer
from kairoskopion.kairon_provider.batch import (
    BatchArticleInput,
    BatchTargetInput,
    LocalFirstAuditReceipt,
    build_batch_qualification_plan,
)
from kairoskopion.kairon_provider.batch_runtime import (
    BATCH_STAGE_ORDER,
    BatchRunStore,
    advance_cell_stage,
    advance_work_item,
    build_resume_work_items,
    initialize_batch_run,
)


def _article(article_id: str) -> BatchArticleInput:
    return BatchArticleInput(
        article_id=article_id,
        artikl_state=ArtiklStatePointer(
            state_id=f"state:{article_id}",
            state_type="MANUSCRIPT",
            authority="ARTIKL",
        ),
        protected_core=[f"core:{article_id}"],
        allowed_change_classes=["LOCAL_EXPOSITION", "ARTICLE_VARIANT_BRANCH"],
    )


def _target(target_id: str, snapshot_id: str) -> BatchTargetInput:
    receipt = LocalFirstAuditReceipt(
        target_id=target_id,
        checked_discipline_registry=True,
        checked_venue_registry=True,
        checked_target_world_store=True,
        checked_venue_memory=True,
        local_hits=[f"local:{target_id}"],
        status="complete",
    )
    return BatchTargetInput(
        target_id=target_id,
        snapshot_id=snapshot_id,
        academic_world_path=["world:international", f"venue:{target_id}"],
        local_first_receipt=receipt,
    )


def _plan():
    return build_batch_qualification_plan(
        batch_id="batch:pilot",
        articles=[_article("P06"), _article("P07"), _article("F17")],
        targets=[
            _target("pt", "targetworld:pt:frozen"),
            _target("techne", "targetworld:techne:frozen"),
            _target("vphil", "targetworld:vphil:frozen"),
        ],
    )


def test_initialize_and_resume_coalesces_target_level_work():
    plan = _plan()
    state = initialize_batch_run(plan)

    items = build_resume_work_items(plan, state)
    assert len(items) == 3
    assert {i.stage for i in items} == {"LOCAL_RESOLUTION"}
    assert all(i.coalesced for i in items)
    assert sorted(len(i.cell_ids) for i in items) == [3, 3, 3]

    for item in items:
        advance_work_item(plan, state, item)

    items = build_resume_work_items(plan, state)
    assert len(items) == 3
    assert {i.stage for i in items} == {"TARGET_READY"}
    assert all(i.coalesced for i in items)
    assert sorted(len(i.cell_ids) for i in items) == [3, 3, 3]


def test_article_specific_work_is_not_coalesced_after_target_ready():
    plan = _plan()
    state = initialize_batch_run(plan)
    for item in build_resume_work_items(plan, state):
        advance_work_item(plan, state, item)
    for item in build_resume_work_items(plan, state):
        advance_work_item(plan, state, item)

    items = build_resume_work_items(plan, state)
    assert len(items) == 9
    assert {i.stage for i in items} == {"PRESSURE_READY"}
    assert all(len(i.cell_ids) == 1 for i in items)
    assert all(not i.coalesced for i in items)


def test_store_roundtrip_and_resume_skips_completed_stages(tmp_path):
    plan = _plan()
    store = BatchRunStore(tmp_path)
    state = initialize_batch_run(plan, store=store)

    first = sorted(state.cell_states)[0]
    advance_cell_stage(
        state,
        cell_id=first,
        stage="LOCAL_RESOLUTION",
        evidence_refs=["registry:hit"],
        store=store,
    )
    advance_cell_stage(
        state,
        cell_id=first,
        stage="TARGET_READY",
        evidence_refs=["snapshot:frozen"],
        store=store,
    )

    loaded = initialize_batch_run(plan, store=store)
    assert loaded.cell_states[first].next_stage() == "PRESSURE_READY"
    assert loaded.cell_states[first].stage_evidence["TARGET_READY"] == ["snapshot:frozen"]


def test_out_of_order_stage_is_rejected():
    plan = _plan()
    state = initialize_batch_run(plan)
    first = sorted(state.cell_states)[0]
    with pytest.raises(ValueError, match="out-of-order"):
        advance_cell_stage(state, cell_id=first, stage="TARGET_READY")


def test_completed_stage_is_idempotent_and_merges_evidence():
    plan = _plan()
    state = initialize_batch_run(plan)
    first = sorted(state.cell_states)[0]
    advance_cell_stage(
        state,
        cell_id=first,
        stage="LOCAL_RESOLUTION",
        evidence_refs=["a"],
    )
    advance_cell_stage(
        state,
        cell_id=first,
        stage="LOCAL_RESOLUTION",
        evidence_refs=["a", "b"],
    )
    assert state.cell_states[first].stage_evidence["LOCAL_RESOLUTION"] == ["a", "b"]


def test_blocked_cell_stops_resume_for_that_cell():
    plan = _plan()
    state = initialize_batch_run(plan)
    first = sorted(state.cell_states)[0]
    advance_cell_stage(
        state,
        cell_id=first,
        stage="LOCAL_RESOLUTION",
        status="blocked",
        blocked_reason="author decision required",
    )
    assert state.cell_states[first].next_stage() is None
    assert state.status == "partial"
    pending_ids = {
        cid
        for item in build_resume_work_items(plan, state)
        for cid in item.cell_ids
    }
    assert first not in pending_ids


def test_plan_drift_is_rejected_on_resume(tmp_path):
    plan = _plan()
    store = BatchRunStore(tmp_path)
    initialize_batch_run(plan, store=store)
    drifted = build_batch_qualification_plan(
        batch_id="batch:pilot",
        articles=[_article("P06"), _article("P07"), _article("F17")],
        targets=[_target("pt", "targetworld:pt:changed")],
    )
    with pytest.raises(ValueError, match="fingerprint"):
        initialize_batch_run(drifted, store=store)


def test_full_stage_progression_completes_batch():
    plan = build_batch_qualification_plan(
        batch_id="batch:one",
        articles=[_article("P06")],
        targets=[_target("pt", "targetworld:pt:frozen")],
    )
    state = initialize_batch_run(plan)
    cell_id = plan.cells[0].cell_id
    for stage in BATCH_STAGE_ORDER:
        advance_cell_stage(state, cell_id=cell_id, stage=stage)
    assert state.cell_states[cell_id].complete
    assert state.status == "complete"
    assert build_resume_work_items(plan, state) == []