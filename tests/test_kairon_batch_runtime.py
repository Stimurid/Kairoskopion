import json
from pathlib import Path

from kairoskopion.kairon_provider import ArtiklStatePointer
from kairoskopion.kairon_provider.batch import (
    AcademicWorldNode,
    BatchArticleInput,
    BatchQualificationSpec,
    BatchTargetInput,
    build_batch_qualification_plan,
)
from kairoskopion.kairon_provider.batch_runtime import (
    AcademicWorldStore,
    BatchRunStore,
    authorize_external_discovery,
    probe_local_first,
)
from kairoskopion.kairon_provider.storage import TargetWorldStore


def _plan(tmp_path: Path):
    receipt = probe_local_first(
        target_id="venue-a",
        data_root=tmp_path,
        discipline_query="philosophy technology",
        venue_query="Venue A",
    )
    article = BatchArticleInput(
        article_id="A1",
        artikl_state=ArtiklStatePointer(
            state_id="state:A1", state_type="MANUSCRIPT", authority="ARTIKL"
        ),
    )
    target = BatchTargetInput(
        target_id="venue-a",
        snapshot_id="targetworld:venue-a:1",
        academic_world_path=["world:anglophone", "venue:venue-a"],
        local_first_receipt=receipt,
    )
    spec = BatchQualificationSpec(batch_id="batch:runtime", concurrency_limit=2)
    return build_batch_qualification_plan(
        batch_id=spec.batch_id, articles=[article], targets=[target], spec=spec
    )


def test_academic_world_store_persists_multi_parent_graph(tmp_path):
    store = AcademicWorldStore(tmp_path)
    world = AcademicWorldNode(
        node_id="world:anglophone",
        node_type="REGION_ECOLOGY",
        names={"en": "Anglophone publication ecology"},
        evidence_refs=["source:one"],
        source_status="provisional",
    )
    discipline = AcademicWorldNode(
        node_id="discipline:philosophy-of-technology",
        node_type="DISCIPLINE",
        names={"en": "Philosophy of technology"},
        parent_ids=["world:anglophone"],
        evidence_refs=["source:two"],
        source_status="provisional",
    )
    store.put(world)
    store.put(discipline)
    assert store.get(world.node_id).names["en"].startswith("Anglophone")
    assert [n.node_id for n in store.children_of(world.node_id)] == [discipline.node_id]
    assert store.validate_path([world.node_id, discipline.node_id]) == []


def test_academic_world_store_reports_missing_or_unlinked_path(tmp_path):
    store = AcademicWorldStore(tmp_path)
    store.put(AcademicWorldNode(node_id="world:a", node_type="WORLD"))
    store.put(
        AcademicWorldNode(
            node_id="venue:x", node_type="VENUE", parent_ids=["world:b"]
        )
    )
    errors = store.validate_path(["world:a", "venue:x", "venue:missing"])
    assert any("unlinked path edge" in e for e in errors)
    assert any("missing node" in e for e in errors)


def test_probe_local_first_reuses_frozen_target_world(tmp_path):
    tw = TargetWorldStore(tmp_path)
    tw.put(
        {
            "snapshot_id": "targetworld:venue-a:frozen",
            "target_id": "venue-a",
            "evidence_refs": ["source:venue-a"],
        }
    )
    receipt = probe_local_first(target_id="venue-a", data_root=tmp_path)
    assert receipt.checked_discipline_registry is True
    assert receipt.checked_venue_registry is True
    assert receipt.checked_target_world_store is True
    assert "targetworld:targetworld:venue-a:frozen" in receipt.local_hits
    assert receipt.external_discovery_used is False
    assert receipt.status == "target_local_hit"




def test_probe_local_first_distinguishes_context_from_target_hit(tmp_path):
    receipt = probe_local_first(
        target_id="missing-target",
        data_root=tmp_path,
        discipline_query="philosophy of technology",
        venue_query="Definitely Missing Venue",
    )
    assert receipt.layer_hits["discipline_registry"]
    assert receipt.layer_hits["venue_registry"] == []
    assert receipt.layer_hits["target_world_store"] == []
    assert receipt.status == "context_only_hit"


def test_external_discovery_authorization_requires_completed_local_probe(tmp_path):
    receipt = probe_local_first(target_id="missing", data_root=tmp_path)
    external = authorize_external_discovery(
        receipt, external_task_refs=["task:openalex:1"]
    )
    assert external.external_discovery_used is True
    assert external.external_task_refs == ["task:openalex:1"]
    assert external.status == "external_authorized"


def test_batch_store_resumes_pending_cells(tmp_path):
    plan = _plan(tmp_path)
    store = BatchRunStore(tmp_path)
    store.put(plan)
    restored = store.get(plan.batch_id)
    assert restored is not None
    assert restored.spec.concurrency_limit == 2
    assert len(store.pending_cells(plan.batch_id)) == 1
    cell = restored.cells[0]
    store.update_cell(
        batch_id=plan.batch_id,
        cell_id=cell.cell_id,
        status="complete",
        pressure_pack_id="pack:1",
        transition_decision_id="transition:1",
        round_trip_ref="roundtrip:1",
    )
    assert store.pending_cells(plan.batch_id) == []
    completed = store.get(plan.batch_id)
    assert completed.status == "complete"
    assert completed.cells[0].pressure_pack_id == "pack:1"


def test_batch_spec_id_must_match_plan():
    article = BatchArticleInput(
        article_id="A1",
        artikl_state=ArtiklStatePointer(
            state_id="state:A1", state_type="MANUSCRIPT", authority="ARTIKL"
        ),
    )
    target = BatchTargetInput(target_id="v", snapshot_id="s")
    spec = BatchQualificationSpec(batch_id="batch:other")
    try:
        build_batch_qualification_plan(
            batch_id="batch:this", articles=[article], targets=[target], spec=spec
        )
    except ValueError as exc:
        assert "batch spec batch_id" in str(exc)
    else:
        raise AssertionError("mismatched BatchQualificationSpec should fail")