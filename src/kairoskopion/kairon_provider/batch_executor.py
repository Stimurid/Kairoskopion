[Reading 253 lines from start (total: 253 lines, 0 remaining)]

"""Executable qualification slice for ARTIKL.KAIRON batch cells.

This module closes the gap between a durable BatchQualificationPlan and an
observed per-cell Kairon transition proposal. It remains qualification-only:
no manuscript materialization, no target refresh, and no semantic adoption.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from ..schema import ArticleModel
from .batch import BatchArticleInput, BatchCell, BatchTargetInput
from .batch_pressure import derive_batch_target_pressure
from .batch_runtime import BatchRunStore
from .models import KaironTransitionDecision, TargetPressurePack
from .storage import TargetWorldStore
from .source_completeness import SourceCompletenessReport, project_verified_reference_count
from .transition import propose_transition


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def _pressure_pack_id(cell: BatchCell, pack: TargetPressurePack) -> str:
    payload = "|".join(
        [
            cell.cell_id,
            pack.target_id,
            pack.snapshot_id,
            *sorted(item.pressure_id for item in pack.items),
            *sorted(pack.unknowns),
        ]
    )
    return "kpp_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


@dataclass
class BatchCellQualificationReceipt:
    batch_id: str
    cell_id: str
    article_id: str
    article_state_id: str
    target_id: str
    target_snapshot_id: str
    status: str
    pressure_pack_id: str | None = None
    pressure_pack: dict[str, Any] | None = None
    transition_decision_id: str | None = None
    transition_decision: dict[str, Any] | None = None
    evidence_debt: list[str] = field(default_factory=list)
    author_decision_required: bool = False
    evidence_refs: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BatchQualificationReceiptStore:
    """Atomic durable receipt store, one latest receipt per batch cell."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "batch_receipts"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, cell_id: str) -> Path:
        return self.root / f"{_digest(cell_id)}.json"

    def put(self, receipt: BatchCellQualificationReceipt) -> BatchCellQualificationReceipt:
        _atomic_json(self._path(receipt.cell_id), receipt.to_dict())
        return receipt

    def get(self, cell_id: str) -> BatchCellQualificationReceipt | None:
        path = self._path(cell_id)
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("cell_id") != cell_id:
            return None
        return BatchCellQualificationReceipt(**raw)

    def list_for_batch(self, batch_id: str) -> list[BatchCellQualificationReceipt]:
        out: list[BatchCellQualificationReceipt] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue
            if raw.get("batch_id") != batch_id:
                continue
            out.append(BatchCellQualificationReceipt(**raw))
        return out


def _qualification_status(decision: KaironTransitionDecision) -> str:
    if decision.author_decision_required:
        return "blocked_author"
    if decision.primary_transition == "HOLD":
        return "evidence_hold"
    return "qualification_complete"


def qualify_batch_cell(
    *,
    cell: BatchCell,
    article_input: BatchArticleInput,
    article: ArticleModel,
    target: BatchTargetInput,
    target_world_store: TargetWorldStore,
    current_year: int | None = None,
) -> BatchCellQualificationReceipt:
    """Observe one article x frozen-target cell through Kairon B5."""

    if article_input.article_id != cell.article_id:
        raise ValueError("article input does not match claimed batch cell")
    if article_input.artikl_state.state_id != cell.article_state_id:
        raise ValueError("article state does not match claimed batch cell")
    if target.target_id != cell.target_id:
        raise ValueError("target input does not match claimed batch cell")
    if target.snapshot_id != cell.target_snapshot_id:
        raise ValueError("target snapshot does not match claimed batch cell")

    snapshot = target_world_store.get(cell.target_snapshot_id)
    if snapshot is None:
        raise KeyError(f"target snapshot not found: {cell.target_snapshot_id}")

    pack = derive_batch_target_pressure(
        article_input=article_input,
        article=article,
        target=target,
        snapshot=snapshot,
        current_year=current_year,
    )
    call_id = f"kaironbatch:{cell.batch_id}:{cell.cell_id}"
    decision = propose_transition(
        call_id=call_id,
        pressure_pack=pack,
        protected_core=article_input.protected_core,
        allowed_change_classes=article_input.allowed_change_classes,
    )
    pack_id = _pressure_pack_id(cell, pack)
    debt = list(dict.fromkeys([
        *list(pack.unknowns or []),
        *list(decision.blocking_evidence_debt or []),
    ]))

    return BatchCellQualificationReceipt(
        batch_id=cell.batch_id,
        cell_id=cell.cell_id,
        article_id=cell.article_id,
        article_state_id=cell.article_state_id,
        target_id=cell.target_id,
        target_snapshot_id=cell.target_snapshot_id,
        status=_qualification_status(decision),
        pressure_pack_id=pack_id,
        pressure_pack=pack.to_dict(),
        transition_decision_id=decision.decision_id,
        transition_decision=decision.to_dict(),
        evidence_debt=debt,
        author_decision_required=decision.author_decision_required,
        evidence_refs=list(decision.evidence_refs or []),
    )


def run_batch_qualification_slice(
    *,
    batch_id: str,
    batch_store: BatchRunStore,
    receipt_store: BatchQualificationReceiptStore,
    target_world_store: TargetWorldStore,
    article_inputs: dict[str, BatchArticleInput],
    article_models: dict[str, ArticleModel],
    target_inputs: dict[str, BatchTargetInput],
    source_completeness_reports: dict[str, SourceCompletenessReport] | None = None,
    manuscript_revisions: dict[str, str] | None = None,
    limit: int | None = None,
    current_year: int | None = None,
) -> list[BatchCellQualificationReceipt]:
    """Claim and qualify one resumable scheduler slice."""

    claimed = batch_store.claim_cells(batch_id, limit=limit)
    receipts: list[BatchCellQualificationReceipt] = []

    for cell in claimed:
        try:
            article_input = article_inputs[cell.article_id]
            article = article_models[cell.article_id]
            if source_completeness_reports and cell.article_id in source_completeness_reports:
                if not manuscript_revisions or cell.article_id not in manuscript_revisions:
                    raise ValueError("source completeness projection requires current manuscript revision")
                article = project_verified_reference_count(
                    article,
                    source_completeness_reports[cell.article_id],
                    current_manuscript_revision=manuscript_revisions[cell.article_id],
                )
            target = target_inputs[cell.target_id]
            receipt = qualify_batch_cell(
                cell=cell,
                article_input=article_input,
                article=article,
                target=target,
                target_world_store=target_world_store,
                current_year=current_year,
            )
            receipt_store.put(receipt)
            batch_store.update_cell(
                batch_id=batch_id,
                cell_id=cell.cell_id,
                status=receipt.status,
                pressure_pack_id=receipt.pressure_pack_id,
                transition_decision_id=receipt.transition_decision_id,
                evidence_debt=receipt.evidence_debt,
                author_decision_required=receipt.author_decision_required,
            )
        except Exception as exc:
            receipt = BatchCellQualificationReceipt(
                batch_id=cell.batch_id,
                cell_id=cell.cell_id,
                article_id=cell.article_id,
                article_state_id=cell.article_state_id,
                target_id=cell.target_id,
                target_snapshot_id=cell.target_snapshot_id,
                status="failed",
                errors=[f"{type(exc).__name__}: {exc}"],
            )
            receipt_store.put(receipt)
            batch_store.update_cell(
                batch_id=batch_id,
                cell_id=cell.cell_id,
                status="failed",
            )
        receipts.append(receipt)

    return receipts