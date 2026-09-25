[Reading 213 lines from start (total: 213 lines, 0 remaining)]

from pathlib import Path

from kairoskopion.kairon_provider import (
    ArtiklStatePointer,
    BatchArticleInput,
    BatchQualificationReceiptStore,
    BatchQualificationSpec,
    BatchTargetInput,
    LocalFirstAuditReceipt,
    SourceCompletenessReport,
    build_batch_qualification_plan,
    run_batch_qualification_slice,
)
from kairoskopion.kairon_provider.batch_runtime import BatchRunStore
from kairoskopion.kairon_provider.storage import TargetWorldStore
from kairoskopion.schema import ArticleModel


def _article(article_id: str, language: str = "ru") -> tuple[BatchArticleInput, ArticleModel]:
    inp = BatchArticleInput(
        article_id=article_id,
        artikl_state=ArtiklStatePointer(
            state_id=f"state:{article_id}",
            state_type="MANUSCRIPT",
            authority="ARTIKL",
        ),
        protected_core=[f"core:{article_id}"],
        allowed_change_classes=["LOCAL_EXPOSITION", "ARTICLE_VARIANT_BRANCH"],
        academic_world_path_hints=[
            ["world:anglophone", "discipline:philosophy-of-technology"]
        ],
    )
    model = ArticleModel(
        title_current=f"Article {article_id}",
        language=language,
        genre_current="conceptual_article",
        method_status="declared",
        method_description="conceptual philosophical reconstruction",
        reference_count=20,
    )
    return inp, model


def _target(target_id: str, snapshot_id: str) -> BatchTargetInput:
    return BatchTargetInput(
        target_id=target_id,
        snapshot_id=snapshot_id,
        academic_world_path=[
            "world:anglophone",
            "discipline:philosophy-of-technology",
            f"venue:{target_id}",
        ],
        local_first_receipt=LocalFirstAuditReceipt(
            target_id=target_id,
            checked_academic_world_store=True,
            checked_discipline_registry=True,
            checked_venue_registry=True,
            checked_target_world_store=True,
            checked_venue_memory=True,
            status="target_local_hit",
        ),
    )


def _snapshot(target_id: str, snapshot_id: str) -> dict:
    return {
        "snapshot_id": snapshot_id,
        "target_id": target_id,
        "evidence_refs": ["source:target"],
        "corpus_manifest": {
            "artifacts": [
                {"year": 2026, "title": "Recent article", "source_ref": "w1"},
                {"year": 2025, "title": "Recent article 2", "source_ref": "w2"},
            ]
        },
        "target_models": {
            "genre_patterns": [{"label": "conceptual_article", "share": 0.5}],
            "method_patterns": [{"label": "conceptual", "share": 0.5}],
            "citation_patterns": {"median_reference_count": 18},
            "language_patterns": {"en": 0.9},
            "limitations": [],
        },
    }


def test_scheduler_slice_qualifies_cells_and_persists_receipts(tmp_path: Path):
    a1, m1 = _article("A1", language="en")
    a2, m2 = _article("A2", language="en")
    target = _target("pt", "targetworld:pt:1")
    plan = build_batch_qualification_plan(
        batch_id="batch:exec",
        articles=[a1, a2],
        targets=[target],
        spec=BatchQualificationSpec(batch_id="batch:exec", concurrency_limit=1),
    )
    batch_store = BatchRunStore(tmp_path)
    batch_store.put(plan)
    tw = TargetWorldStore(tmp_path)
    tw.put(_snapshot("pt", "targetworld:pt:1"))
    receipts = BatchQualificationReceiptStore(tmp_path)

    first = run_batch_qualification_slice(
        batch_id="batch:exec",
        batch_store=batch_store,
        receipt_store=receipts,
        target_world_store=tw,
        article_inputs={"A1": a1, "A2": a2},
        article_models={"A1": m1, "A2": m2},
        target_inputs={"pt": target},
        current_year=2026,
    )
    assert len(first) == 1
    assert first[0].status == "qualification_complete"
    assert first[0].transition_decision["primary_transition"] == "KEEP"
    assert len(batch_store.pending_cells("batch:exec")) == 1

    second = run_batch_qualification_slice(
        batch_id="batch:exec",
        batch_store=batch_store,
        receipt_store=receipts,
        target_world_store=tw,
        article_inputs={"A1": a1, "A2": a2},
        article_models={"A1": m1, "A2": m2},
        target_inputs={"pt": target},
        current_year=2026,
    )
    assert len(second) == 1
    assert len(receipts.list_for_batch("batch:exec")) == 2
    assert batch_store.get("batch:exec").status == "complete"


def test_russian_article_gets_branch_proposal_against_english_corpus(tmp_path: Path):
    article_input, article = _article("A1", language="ru")
    target = _target("pt", "targetworld:pt:1")
    plan = build_batch_qualification_plan(
        batch_id="batch:branch",
        articles=[article_input],
        targets=[target],
    )
    batch_store = BatchRunStore(tmp_path)
    batch_store.put(plan)
    tw = TargetWorldStore(tmp_path)
    tw.put(_snapshot("pt", "targetworld:pt:1"))
    receipts = BatchQualificationReceiptStore(tmp_path)

    result = run_batch_qualification_slice(
        batch_id="batch:branch",
        batch_store=batch_store,
        receipt_store=receipts,
        target_world_store=tw,
        article_inputs={"A1": article_input},
        article_models={"A1": article},
        target_inputs={"pt": target},
        current_year=2026,
    )[0]

    assert result.status == "qualification_complete"
    assert result.transition_decision["primary_transition"] == "BRANCH"
    assert "target:corpus:language:english_realization" in {
        x["pressure_id"] for x in result.pressure_pack["items"]
    }


def test_missing_snapshot_is_durable_failed_receipt(tmp_path: Path):
    article_input, article = _article("A1", language="en")
    target = _target("missing", "targetworld:missing:1")
    plan = build_batch_qualification_plan(
        batch_id="batch:missing",
        articles=[article_input],
        targets=[target],
    )
    batch_store = BatchRunStore(tmp_path)
    batch_store.put(plan)
    receipts = BatchQualificationReceiptStore(tmp_path)

    result = run_batch_qualification_slice(
        batch_id="batch:missing",
        batch_store=batch_store,
        receipt_store=receipts,
        target_world_store=TargetWorldStore(tmp_path),
        article_inputs={"A1": article_input},
        article_models={"A1": article},
        target_inputs={"missing": target},
    )[0]

    assert result.status == "failed"
    assert "target snapshot not found" in result.errors[0]
    assert receipts.get(result.cell_id).status == "failed"
    assert batch_store.get("batch:missing").status == "complete"


def test_source_completeness_projection_runs_before_pressure_derivation(tmp_path: Path):
    article_input, article = _article("A1", language="en")
    article.reference_count = None
    target = _target("pt", "targetworld:pt:1")
    plan = build_batch_qualification_plan(batch_id="batch:sc", articles=[article_input], targets=[target])
    batch_store = BatchRunStore(tmp_path); batch_store.put(plan)
    tw = TargetWorldStore(tmp_path); tw.put(_snapshot("pt", "targetworld:pt:1"))
    report = SourceCompletenessReport(
        report_id="verified", article_id="A1", manuscript_revision="m1",
        bibliography_status="VERIFIED_COMPLETE", reference_count_status="VERIFIED",
        reference_count=20,
    )
    result = run_batch_qualification_slice(
        batch_id="batch:sc", batch_store=batch_store,
        receipt_store=BatchQualificationReceiptStore(tmp_path),
        target_world_store=tw, article_inputs={"A1": article_input},
        article_models={"A1": article}, target_inputs={"pt": target},
        source_completeness_reports={"A1": report},
        manuscript_revisions={"A1": "m1"}, current_year=2026,
    )[0]
    assert "article:reference_count" not in result.evidence_debt
    assert article.reference_count == 20