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
    academic_world_node_from_discipline,
    authorize_external_discovery,
    probe_local_first,
    sync_discipline_registry_to_academic_world,
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
    assert "targetworld:venue-a:frozen" in receipt.local_hits
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




def test_batch_store_claim_and_recover_inflight(tmp_path):
    plan = _plan(tmp_path)
    store = BatchRunStore(tmp_path)
    store.put(plan)
    claimed = store.claim_cells(plan.batch_id)
    assert len(claimed) == 1
    assert store.get(plan.batch_id).cells[0].status == "in_progress"
    assert store.pending_cells(plan.batch_id) == []
    assert store.recover_inflight(plan.batch_id) == 1
    pending = store.pending_cells(plan.batch_id)
    assert len(pending) == 1
    assert pending[0].status == "retry"


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


def test_academic_world_store_reads_seed_and_archives_live_revision(tmp_path):
    seed = tmp_path / "seed.jsonl"
    seed.write_text(
        json.dumps({
            "node_id": "ecology:anglophone",
            "node_type": "REGION_ECOLOGY",
            "names": {"en": "Anglophone publication ecology"},
            "source_status": "routing_scaffold",
        }) + "\n",
        encoding="utf-8",
    )
    store = AcademicWorldStore(tmp_path / "runtime", seed_paths=[seed])
    assert store.get("ecology:anglophone").source_status == "routing_scaffold"
    assert store.search("Anglophone")[0].node_id == "ecology:anglophone"

    store.put(AcademicWorldNode(
        node_id="ecology:anglophone",
        node_type="REGION_ECOLOGY",
        names={"en": "Anglophone publication ecology"},
        source_status="provisional",
        evidence_refs=["source:first"],
    ))
    store.put(AcademicWorldNode(
        node_id="ecology:anglophone",
        node_type="REGION_ECOLOGY",
        names={"en": "Anglophone publication ecology"},
        source_status="provisional",
        evidence_refs=["source:first", "source:second"],
    ))
    history = list((store.history_root).rglob("*.json"))
    assert len(history) == 1
    assert store.get("ecology:anglophone").evidence_refs[-1] == "source:second"


def test_probe_local_first_checks_academic_world_seed(tmp_path):
    receipt = probe_local_first(
        target_id="missing-target",
        data_root=tmp_path,
        academic_world_query="Anglophone",
    )
    assert receipt.checked_academic_world_store is True
    assert receipt.layer_hits["academic_world"]
    assert any("ecology:anglophone" in x for x in receipt.layer_hits["academic_world"])


def test_target_world_refresh_must_create_descendant(tmp_path):
    from kairoskopion.kairon_provider.batch_runtime import persist_target_world_refresh

    store = TargetWorldStore(tmp_path)
    store.put({"snapshot_id": "targetworld:x:1", "target_id": "x"})
    try:
        persist_target_world_refresh(
            store=store,
            parent_snapshot_id="targetworld:x:1",
            refreshed_snapshot={"snapshot_id": "targetworld:x:1", "target_id": "x"},
        )
    except ValueError as exc:
        assert "new descendant" in str(exc)
    else:
        raise AssertionError("refresh should not overwrite a frozen snapshot")

    child = persist_target_world_refresh(
        store=store,
        parent_snapshot_id="targetworld:x:1",
        refreshed_snapshot={"snapshot_id": "targetworld:x:2", "target_id": "x"},
    )
    assert child["lineage"]["parent_snapshot_id"] == "targetworld:x:1"
    assert store.get("targetworld:x:1")["snapshot_id"] == "targetworld:x:1"

def test_probe_local_first_reuses_repository_venue_knowledge(tmp_path: Path):
    repo = tmp_path / "repo"
    data = tmp_path / "runtime"
    (repo / "data" / "registry").mkdir(parents=True)
    (repo / "data" / "registry" / "venues.jsonl").write_text(
        '{"venue_id":"v1","canonical_name":"Known Journal","issn":"1234-5678","source_status":"provisional","review_status":"pending"}\n',
        encoding="utf-8",
    )
    receipt = probe_local_first(
        target_id="known",
        data_root=data,
        venue_query="Known Journal",
        issn="1234-5678",
        repository_root=repo,
    )
    assert receipt.status == "target_local_hit"
    assert receipt.layer_hits["repository_venue_registry"] == ["repo_venue:v1"]


def test_probe_local_first_reuses_repository_harvest_and_evidence_pack(tmp_path: Path):
    repo = tmp_path / "repo"
    data = tmp_path / "runtime"
    harvest = repo / "data" / "seed_registry" / "education" / "p10"
    harvest.mkdir(parents=True)
    (harvest / "provisional_venue_records.jsonl").write_text(
        '{"venue_id":"vh1","canonical_name":"Harvested Higher Education","issn":"1111-2222"}\n',
        encoding="utf-8",
    )
    packs = repo / "data" / "venue_evidence_packs"
    packs.mkdir(parents=True)
    (packs / "local_journal.md").write_text(
        "# Venue Evidence Pack: Local Journal\nISSN 3333-4444\n",
        encoding="utf-8",
    )

    harvested = probe_local_first(
        target_id="he",
        data_root=data,
        venue_query="Harvested Higher Education",
        issn="1111-2222",
        repository_root=repo,
    )
    assert harvested.status == "target_local_hit"
    assert harvested.layer_hits["repository_venue_harvest"] == ["repo_harvest:vh1"]

    packed = probe_local_first(
        target_id="local",
        data_root=data,
        venue_query="Local Journal",
        issn="3333-4444",
        repository_root=repo,
    )
    assert packed.status == "target_local_hit"
    assert packed.layer_hits["venue_evidence_pack"] == [
        "venue_evidence_pack:local_journal.md"
    ]



def test_discipline_projection_preserves_status_and_cross_region_links(tmp_path):
    from kairoskopion.services.discipline_registry.loader import DisciplineRegistry
    from kairoskopion.services.discipline_registry.model import (
        DisciplineModel,
        EvidenceRef,
    )

    ru = DisciplineModel(
        discipline_id="ru-sample",
        display_names={"ru": "Тестовая дисциплина", "en": "Sample discipline"},
        region="ru",
        source_status="llm_draft",
        last_updated="2026-09-25",
        canonical_questions=["Что считается легитимным вопросом?"],
        legitimate_objects=["объект X"],
        adjacent=["ru-neighbor"],
        international_mapping=["intl-sample"],
        evidence_refs=[EvidenceRef(source_type="other", source_id="local-source")],
    )
    registry = DisciplineRegistry([ru])
    store = AcademicWorldStore(tmp_path)
    nodes = sync_discipline_registry_to_academic_world(
        store, discipline_registry=registry
    )
    assert len(nodes) == 1
    node = store.get("discipline:ru-sample")
    assert node is not None
    assert node.parent_ids == ["ecology:ru-post-soviet"]
    assert node.source_status == "llm_draft"
    assert node.review_status == "unreviewed"
    assert "discipline:intl-sample" in node.adjacent_ids
    assert "discipline:ru-neighbor" in node.adjacent_ids
    assert node.canonical_questions == ["Что считается легитимным вопросом?"]
    assert node.provenance["projection_semantics"] == "status_preserving"


def test_discipline_projection_does_not_invent_family_or_school():
    from kairoskopion.services.discipline_registry.model import DisciplineModel

    discipline = DisciplineModel(
        discipline_id="intl-sample",
        display_names={"en": "Sample discipline"},
        region="international",
        source_status="llm_draft",
        last_updated="2026-09-25",
    )
    node = academic_world_node_from_discipline(discipline)
    assert node.node_type == "DISCIPLINE"
    assert node.parent_ids == ["ecology:transregional"]
    assert all("family:" not in x and "school:" not in x for x in node.parent_ids)


def test_probe_projects_repository_discipline_into_academic_world(tmp_path: Path):
    repo = tmp_path / "repo"
    runtime = tmp_path / "runtime"
    seeds = repo / "data" / "disciplinary_landscape" / "seeds"
    seeds.mkdir(parents=True)
    (seeds / "international_seed.jsonl").write_text(
        json.dumps(
            {
                "discipline_id": "intl-test-field",
                "display_names": {"en": "Test Field"},
                "region": "international",
                "source_status": "llm_draft",
                "last_updated": "2026-09-25",
                "aliases": [],
                "evidence_refs": [{"source_type": "other", "source_id": "fixture"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    receipt = probe_local_first(
        target_id="missing-target",
        data_root=runtime,
        academic_world_query="Test Field",
        discipline_query="Test Field",
        repository_root=repo,
    )
    assert "academic_world:discipline:intl-test-field" in receipt.layer_hits[
        "academic_world"
    ]
    graph = AcademicWorldStore(runtime)
    projected = graph.get("discipline:intl-test-field")
    assert projected is not None
    assert projected.source_status == "llm_draft"
    assert projected.parent_ids == ["ecology:transregional"]
