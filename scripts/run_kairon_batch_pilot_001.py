"""Qualification-only real batch pilot: P06/P07/F17 x three venue worlds.

The script exercises the durable batch planner/runtime through B0-B3:
authoritative article inputs, academic-world paths, local-first receipts,
frozen TargetWorld reuse and restart/resume. It intentionally stops before
article-specific pressure generation/materialization.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from kairoskopion.kairon_provider import (
    ArtiklStatePointer,
    BatchArticleInput,
    BatchRunStore,
    BatchTargetInput,
    LocalFirstAuditReceipt,
    advance_work_item,
    build_batch_qualification_plan,
    build_resume_work_items,
    initialize_batch_run,
)
from kairoskopion.kairon_provider.storage import TargetWorldStore


BATCH_ID = "kairon-batch-pilot-001"


def _latest_snapshot(store: TargetWorldStore, target_id: str) -> str:
    hits = []
    for snapshot_id in store.list_ids():
        data = store.get(snapshot_id) or {}
        if data.get("target_id") == target_id:
            hits.append((data.get("created_at") or "", snapshot_id))
    if not hits:
        raise RuntimeError(f"no TargetWorldSnapshot found for {target_id}")
    hits.sort()
    return hits[-1][1]


def _article(
    article_id: str,
    manuscript_pointer: str,
    protected_core: list[str],
) -> BatchArticleInput:
    return BatchArticleInput(
        article_id=article_id,
        artikl_state=ArtiklStatePointer(
            state_id=f"artikl:{article_id}:manuscript",
            state_type="MANUSCRIPT",
            manuscript_pointer=manuscript_pointer,
            authority="ARTIKL",
            source_refs=[manuscript_pointer],
        ),
        protected_core=protected_core,
        mutable_zones=["opening", "register", "genealogy_compression", "target_packaging"],
        allowed_change_classes=[
            "PACKAGING",
            "LOCAL_EXPOSITION",
            "STRUCTURAL_RECONFIGURATION",
        ],
    )


def _receipt(
    target_id: str,
    *,
    local_hits: list[str],
    stale_refs: list[str],
    external_ref: str,
    persisted_ref: str,
) -> LocalFirstAuditReceipt:
    return LocalFirstAuditReceipt(
        target_id=target_id,
        checked_discipline_registry=True,
        checked_venue_registry=True,
        checked_target_world_store=True,
        checked_venue_memory=True,
        local_hits=local_hits,
        stale_local_refs=stale_refs,
        external_discovery_used=True,
        external_task_refs=[external_ref],
        persisted_refs=[persisted_ref],
        status="complete",
    )


def build_plan(data_root: Path):
    target_store = TargetWorldStore(data_root)
    pt_id = _latest_snapshot(target_store, "philosophy_technology_batch_pilot")
    techne_id = _latest_snapshot(target_store, "techne_batch_pilot")
    eps_id = _latest_snapshot(
        target_store, "epistemology_philosophy_science_ru_batch_pilot"
    )

    articles = [
        _article(
            "P06",
            "gdoc:1AmpW5ZV8m_LlDKUSStWtf64SLJ_LrTQap63ZtXDya8U",
            [
                "governed bootstrapping as recursive change of the conditions of cognition",
                "thinking infrastructure is itself part of the changing cognitive system",
                "historical genealogy serves the recursive-infrastructure argument",
            ],
        ),
        _article(
            "P07",
            "gdoc:1RGv3XUErBx77JVIPdfJZTH1MesLcPcrRk-m67n0w-fQ",
            [
                "position/reflexive self-determination is an infrastructural layer of collective augmentation",
                "Engelbart is not reduced to external tools; comparison is operator-level",
                "position is not interchangeable with organizational role",
            ],
        ),
        _article(
            "F17",
            "gdoc:1fSdASFbHfEj8Hj9NSSqnOYbttybHCVSYO4GutGb9fOE",
            [
                "algorithmic processing and interface presentation jointly shape distinguishability of living objects",
                "algorithm and interface remain analytically distinct",
                "epistemic, ontological and normative effects are tracked separately",
            ],
        ),
    ]

    targets = [
        BatchTargetInput(
            target_id="philosophy_technology_batch_pilot",
            snapshot_id=pt_id,
            academic_world_path=[
                "world:anglophone",
                "discipline-family:philosophy",
                "discipline:philosophy-of-technology",
                "venue-family:international-philosophy-of-technology",
                "venue:philosophy-and-technology",
            ],
            local_first_receipt=_receipt(
                "philosophy_technology_batch_pilot",
                local_hits=[
                    "gdoc:P06-Kairon-exercise-001",
                    "targetworld:philosophy_technology:4a125cd4f313",
                ],
                stale_refs=["targetworld:philosophy_technology:4a125cd4f313"],
                external_ref="crossref:issn:2210-5433",
                persisted_ref=pt_id,
            ),
        ),
        BatchTargetInput(
            target_id="techne_batch_pilot",
            snapshot_id=techne_id,
            academic_world_path=[
                "world:anglophone",
                "discipline-family:philosophy",
                "discipline:philosophy-of-technology",
                "venue-family:international-philosophy-of-technology",
                "venue:techne",
            ],
            local_first_receipt=_receipt(
                "techne_batch_pilot",
                local_hits=[
                    "gdoc:P06-Kairon-exercise-001",
                    "targetworld:techne:0823ccebcc43",
                ],
                stale_refs=["targetworld:techne:0823ccebcc43"],
                external_ref="crossref:issn:2691-5928",
                persisted_ref=techne_id,
            ),
        ),
        BatchTargetInput(
            target_id="epistemology_philosophy_science_ru_batch_pilot",
            snapshot_id=eps_id,
            academic_world_path=[
                "world:ru-post-soviet",
                "discipline-family:philosophy",
                "discipline:epistemology-philosophy-of-science",
                "school-tradition-tribe:social-and-digital-epistemology",
                "venue-family:ru-epistemology-philosophy-of-science",
                "venue:epistemology-and-philosophy-of-science",
            ],
            local_first_receipt=_receipt(
                "epistemology_philosophy_science_ru_batch_pilot",
                local_hits=[
                    "repo:data/venue_evidence_packs/epistemologiya_i_filosofiya_nauki_evidence_pack.md",
                    "repo:benchmarks/_operator_notes/mavrinsky_venue_research/ru_cluster_taxonomy.md",
                ],
                stale_refs=[],
                external_ref="crossref:issn:1811-833X",
                persisted_ref=eps_id,
            ),
        ),
    ]
    return build_batch_qualification_plan(
        batch_id=BATCH_ID,
        articles=articles,
        targets=targets,
    )


def main() -> int:
    data_root = Path(
        os.environ.get("KAIRON_BATCH_PILOT_DATA_DIR") or "/tmp/kairo-batch-pilot-data"
    )
    target_store = TargetWorldStore(data_root)
    run_store = BatchRunStore(data_root)
    plan = build_plan(data_root)
    state = initialize_batch_run(plan, store=run_store)

    first_resume = [x.to_dict() for x in build_resume_work_items(plan, state)]

    # Complete reusable target-level stages only. Re-running the script resumes
    # from the first incomplete article-specific stage without rediscovery.
    for stage in ("LOCAL_RESOLUTION", "TARGET_READY"):
        items = [x for x in build_resume_work_items(plan, state) if x.stage == stage]
        for item in items:
            if stage == "TARGET_READY":
                if not item.target_snapshot_id or target_store.get(item.target_snapshot_id) is None:
                    raise RuntimeError(
                        f"frozen snapshot missing for work item {item.target_snapshot_id}"
                    )
                refs = [item.target_snapshot_id]
            else:
                target = next(c for c in plan.cells if c.cell_id == item.cell_ids[0])
                receipt = target.local_first_receipt
                refs = []
                if receipt is not None:
                    refs.extend(receipt.local_hits)
                    refs.extend(receipt.stale_local_refs)
                    refs.extend(receipt.external_task_refs)
                    refs.extend(receipt.persisted_refs)
            advance_work_item(
                plan,
                state,
                item,
                status="complete",
                evidence_refs=list(dict.fromkeys(refs)),
                store=run_store,
            )

    next_items = build_resume_work_items(plan, state)
    if len(plan.cells) != 9:
        raise RuntimeError(f"expected 9 cells, got {len(plan.cells)}")
    if len(next_items) != 9 or {x.stage for x in next_items} != {"PRESSURE_READY"}:
        raise RuntimeError(
            "pilot must resume as nine article-specific PRESSURE_READY cells"
        )

    snapshot_reuse = {
        sid: len(cell_ids) for sid, cell_ids in plan.snapshot_reuse.items()
    }
    summary = {
        "batch_id": plan.batch_id,
        "articles": plan.article_ids,
        "targets": plan.target_ids,
        "cell_count": len(plan.cells),
        "snapshot_reuse": snapshot_reuse,
        "run_status": state.status,
        "first_resume_work_item_count": len(first_resume),
        "next_stage": "PRESSURE_READY",
        "next_work_item_count": len(next_items),
        "resume_is_article_specific": all(len(x.cell_ids) == 1 for x in next_items),
        "run_store_ids": run_store.list_ids(),
        "target_snapshot_ids": target_store.list_ids(),
    }
    receipt_path = data_root / "kairon_provider" / "batch_pilot_001_receipt.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())