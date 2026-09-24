import pytest

from kairoskopion.kairon_provider import ArtiklStatePointer
from kairoskopion.kairon_provider.batch import (
    AcademicWorldNode,
    BatchArticleInput,
    BatchTargetInput,
    LocalFirstAuditReceipt,
    build_batch_qualification_plan,
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


def _receipt(target_id: str, *, external: bool = False) -> LocalFirstAuditReceipt:
    return LocalFirstAuditReceipt(
        target_id=target_id,
        checked_academic_world_store=True,
        checked_discipline_registry=True,
        checked_venue_registry=True,
        checked_target_world_store=True,
        checked_venue_memory=True,
        local_hits=[f"venue:{target_id}"],
        external_discovery_used=external,
        external_task_refs=[f"task:{target_id}"] if external else [],
        persisted_refs=[f"snapshot:{target_id}"],
        status="complete",
    )


def _target(target_id: str, snapshot_id: str) -> BatchTargetInput:
    return BatchTargetInput(
        target_id=target_id,
        snapshot_id=snapshot_id,
        academic_world_path=[
            "world:anglophone",
            "discipline:philosophy-of-technology",
            f"venue:{target_id}",
        ],
        local_first_receipt=_receipt(target_id),
        provider_commit="provider-test",
    )


def test_batch_plan_builds_full_article_target_cross_product():
    plan = build_batch_qualification_plan(
        batch_id="batch:001",
        articles=[_article("P06"), _article("P07")],
        targets=[
            _target("p-and-t", "targetworld:pt:1"),
            _target("techne", "targetworld:techne:1"),
        ],
    )
    assert len(plan.cells) == 4
    assert len(plan.cells_for_article("P06")) == 2
    assert len(plan.cells_for_target("techne")) == 2
    assert all(cell.status == "pending" for cell in plan.cells)


def test_target_snapshot_is_reused_without_copying_article_state():
    plan = build_batch_qualification_plan(
        batch_id="batch:reuse",
        articles=[_article("A1"), _article("A2")],
        targets=[_target("p-and-t", "targetworld:pt:frozen")],
    )
    cells = plan.cells_for_target("p-and-t")
    assert {c.target_snapshot_id for c in cells} == {"targetworld:pt:frozen"}
    assert {c.article_state_id for c in cells} == {"state:A1", "state:A2"}
    assert len(plan.snapshot_reuse["targetworld:pt:frozen"]) == 2


def test_local_first_receipt_is_preserved_per_cell():
    receipt = _receipt("logos", external=True)
    target = BatchTargetInput(
        target_id="logos",
        snapshot_id="targetworld:logos:1",
        academic_world_path=["world:ru", "venue-family:ru-philosophy", "venue:logos"],
        local_first_receipt=receipt,
    )
    plan = build_batch_qualification_plan(
        batch_id="batch:local-first",
        articles=[_article("A1")],
        targets=[target],
    )
    cell = plan.cells[0]
    assert cell.local_first_receipt is receipt
    assert cell.local_first_receipt.external_discovery_used is True
    assert cell.local_first_receipt.checked_target_world_store is True
    assert cell.academic_world_path[0] == "world:ru"


def test_external_discovery_without_prior_local_checks_is_rejected():
    with pytest.raises(ValueError, match="external discovery requires prior"):
        BatchTargetInput(
            target_id="missing",
            snapshot_id="targetworld:missing:1",
            local_first_receipt=LocalFirstAuditReceipt(
                target_id="missing",
                checked_academic_world_store=True,
                checked_discipline_registry=True,
                checked_venue_registry=False,
                checked_target_world_store=True,
                external_discovery_used=True,
            ),
        )


def test_duplicate_article_or_target_ids_are_rejected():
    with pytest.raises(ValueError, match="duplicate article_id"):
        build_batch_qualification_plan(
            batch_id="batch:dup-a",
            articles=[_article("A1"), _article("A1")],
            targets=[_target("v1", "s1")],
        )

    with pytest.raises(ValueError, match="duplicate target_id"):
        build_batch_qualification_plan(
            batch_id="batch:dup-t",
            articles=[_article("A1")],
            targets=[_target("v1", "s1"), _target("v1", "s2")],
        )


def test_target_requires_frozen_snapshot_reference():
    with pytest.raises(ValueError, match="snapshot_id"):
        BatchTargetInput(target_id="v1", snapshot_id="")


def test_academic_world_node_supports_multi_parent_graph():
    node = AcademicWorldNode(
        node_id="school:postphenomenology",
        node_type="SCHOOL_TRADITION_TRIBE",
        names={"en": "Postphenomenology"},
        parent_ids=[
            "discipline:philosophy-of-technology",
            "discipline:sts",
            "world:anglophone",
        ],
        institutional_regions=["US", "EU"],
        evidence_refs=["source:corpus"],
        source_status="provisional",
    )
    assert len(node.parent_ids) == 3
    assert node.node_type == "SCHOOL_TRADITION_TRIBE"


def test_academic_world_node_rejects_unknown_type():
    with pytest.raises(ValueError, match="unsupported academic-world node_type"):
        AcademicWorldNode(node_id="x", node_type="CIVILIZATION_ESSENCE")


def test_batch_article_rejects_provider_owned_semantic_authority():
    with pytest.raises(ValueError, match="ARTIKL authority"):
        BatchArticleInput(
            article_id="A1",
            artikl_state=ArtiklStatePointer(
                state_id="s1",
                state_type="MANUSCRIPT",
                authority="KAIROSKOPION",
            ),
        )

def test_batch_plan_supports_sparse_article_target_eligibility():
    a1 = _article("A1")
    a2 = _article("A2")
    a1.eligible_target_ids = ["p-and-t"]
    a2.eligible_target_ids = ["techne"]
    plan = build_batch_qualification_plan(
        batch_id="batch:sparse",
        articles=[a1, a2],
        targets=[
            _target("p-and-t", "targetworld:pt:1"),
            _target("techne", "targetworld:techne:1"),
        ],
    )
    assert len(plan.cells) == 2
    assert {(c.article_id, c.target_id) for c in plan.cells} == {
        ("A1", "p-and-t"),
        ("A2", "techne"),
    }


def test_sparse_eligibility_still_reuses_shared_target_when_allowed():
    a1 = _article("A1")
    a2 = _article("A2")
    a1.eligible_target_ids = ["p-and-t"]
    a2.eligible_target_ids = ["p-and-t", "techne"]
    plan = build_batch_qualification_plan(
        batch_id="batch:sparse-reuse",
        articles=[a1, a2],
        targets=[
            _target("p-and-t", "targetworld:pt:shared"),
            _target("techne", "targetworld:techne:1"),
        ],
    )
    assert len(plan.snapshot_reuse["targetworld:pt:shared"]) == 2
    assert len(plan.cells) == 3
