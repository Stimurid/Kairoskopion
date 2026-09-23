"""Durable academic-world memory and resumable Kairon batch runtime helpers.

This layer is intentionally scheduler-light: it proves local-first lookup,
persists the publication-world graph and batch cell state, and exposes pending
cells for an execution worker. It does not adopt semantic transitions or mutate
frozen TargetWorld snapshots.
"""

from __future__ import annotations

from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import Any

from .batch import (
    AcademicWorldNode,
    BatchCell,
    BatchQualificationPlan,
    BatchQualificationSpec,
    LocalFirstAuditReceipt,
)
from .storage import TargetWorldStore
from ..registry.services import RegistryHub
from ..services.discipline_registry.loader import load_default_registry
from ..services.venue_memory import VenueMemoryRegistry


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(path)


class AcademicWorldStore:
    """Durable graph store under KAIROSKOPION_DATA_DIR.

    Nodes are addressable by stable node_id. Updating a node replaces its
    current materialization but preserves provenance supplied by the caller.
    Frozen TargetWorld evidence remains in TargetWorldStore and is never
    overwritten by this store.
    """

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "academic_world"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, node_id: str) -> Path:
        return self.root / f"{_digest(node_id)}.json"

    def put(self, node: AcademicWorldNode) -> AcademicWorldNode:
        _atomic_json(self._path(node.node_id), node.to_dict())
        return node

    def get(self, node_id: str) -> AcademicWorldNode | None:
        path = self._path(node_id)
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("node_id") != node_id:
            return None
        return AcademicWorldNode(**raw)

    def list_nodes(self, node_type: str | None = None) -> list[AcademicWorldNode]:
        out: list[AcademicWorldNode] = []
        for path in sorted(self.root.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                node = AcademicWorldNode(**raw)
            except Exception:
                continue
            if node_type is None or node.node_type == node_type:
                out.append(node)
        return out

    def children_of(self, parent_id: str) -> list[AcademicWorldNode]:
        return [n for n in self.list_nodes() if parent_id in n.parent_ids]

    def validate_path(self, node_ids: list[str]) -> list[str]:
        errors: list[str] = []
        previous: AcademicWorldNode | None = None
        for node_id in node_ids:
            node = self.get(node_id)
            if node is None:
                errors.append(f"missing node: {node_id}")
                previous = None
                continue
            if previous is not None and node.parent_ids:
                if previous.node_id not in node.parent_ids and previous.node_id not in node.adjacent_ids:
                    errors.append(
                        f"unlinked path edge: {previous.node_id} -> {node.node_id}"
                    )
            previous = node
        return errors


class BatchRunStore:
    """Atomic durable batch plan/cell store with resume primitives."""

    def __init__(self, root: str | Path):
        self.root = Path(root) / "kairon_provider" / "batches"
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, batch_id: str) -> Path:
        return self.root / f"{_digest(batch_id)}.json"

    def put(self, plan: BatchQualificationPlan) -> BatchQualificationPlan:
        _atomic_json(self._path(plan.batch_id), plan.to_dict())
        return plan

    def get(self, batch_id: str) -> BatchQualificationPlan | None:
        path = self._path(batch_id)
        if not path.is_file():
            return None
        raw = json.loads(path.read_text(encoding="utf-8"))
        if raw.get("batch_id") != batch_id:
            return None
        spec_raw = raw.get("spec")
        spec = BatchQualificationSpec(**spec_raw) if isinstance(spec_raw, dict) else None
        cells = []
        for item in raw.get("cells") or []:
            item = dict(item)
            receipt = item.get("local_first_receipt")
            if isinstance(receipt, dict):
                item["local_first_receipt"] = LocalFirstAuditReceipt(**receipt)
            cells.append(BatchCell(**item))
        return BatchQualificationPlan(
            batch_id=raw["batch_id"],
            article_ids=list(raw.get("article_ids") or []),
            target_ids=list(raw.get("target_ids") or []),
            cells=cells,
            snapshot_reuse=dict(raw.get("snapshot_reuse") or {}),
            spec=spec,
            status=raw.get("status") or "planned",
        )

    def update_cell(
        self,
        *,
        batch_id: str,
        cell_id: str,
        status: str,
        pressure_pack_id: str | None = None,
        transition_decision_id: str | None = None,
        target_variant_pointer: str | None = None,
        round_trip_ref: str | None = None,
        evidence_debt: list[str] | None = None,
        author_decision_required: bool | None = None,
    ) -> BatchCell:
        plan = self.get(batch_id)
        if plan is None:
            raise KeyError(f"batch not found: {batch_id}")
        found = None
        for cell in plan.cells:
            if cell.cell_id != cell_id:
                continue
            cell.status = status
            if pressure_pack_id is not None:
                cell.pressure_pack_id = pressure_pack_id
            if transition_decision_id is not None:
                cell.transition_decision_id = transition_decision_id
            if target_variant_pointer is not None:
                cell.target_variant_pointer = target_variant_pointer
            if round_trip_ref is not None:
                cell.round_trip_ref = round_trip_ref
            if evidence_debt is not None:
                cell.evidence_debt = list(evidence_debt)
            if author_decision_required is not None:
                cell.author_decision_required = author_decision_required
            found = cell
            break
        if found is None:
            raise KeyError(f"cell not found: {cell_id}")
        terminal = {"complete", "blocked_author", "failed", "abandoned"}
        if plan.cells and all(c.status in terminal for c in plan.cells):
            plan.status = "complete"
        elif any(c.status not in ("pending", "planned") for c in plan.cells):
            plan.status = "running"
        self.put(plan)
        return found

    def pending_cells(self, batch_id: str, limit: int | None = None) -> list[BatchCell]:
        plan = self.get(batch_id)
        if plan is None:
            raise KeyError(f"batch not found: {batch_id}")
        out = [c for c in plan.cells if c.status in ("pending", "planned", "retry")]
        if limit is not None:
            return out[: max(0, limit)]
        return out


    def claim_cells(self, batch_id: str, limit: int | None = None) -> list[BatchCell]:
        """Claim resumable cells for one qualification scheduler worker."""
        plan = self.get(batch_id)
        if plan is None:
            raise KeyError(f"batch not found: {batch_id}")
        cap = limit
        if cap is None and plan.spec is not None:
            cap = plan.spec.concurrency_limit
        if cap is None:
            cap = 1
        candidates = [
            c for c in plan.cells if c.status in ("pending", "planned", "retry")
        ][: max(0, cap)]
        for cell in candidates:
            cell.status = "in_progress"
        if candidates:
            plan.status = "running"
            self.put(plan)
        return candidates

    def recover_inflight(self, batch_id: str) -> int:
        """Make cells abandoned by an interrupted worker resumable."""
        plan = self.get(batch_id)
        if plan is None:
            raise KeyError(f"batch not found: {batch_id}")
        recovered = 0
        for cell in plan.cells:
            if cell.status == "in_progress":
                cell.status = "retry"
                recovered += 1
        if recovered:
            plan.status = "running"
            self.put(plan)
        return recovered


def probe_local_first(
    *,
    target_id: str,
    data_root: str | Path,
    discipline_query: str | None = None,
    venue_query: str | None = None,
    issn: str | None = None,
) -> LocalFirstAuditReceipt:
    """Check durable local knowledge without creating network work.

    This function has no external adapters. A caller may mark an external
    discovery only after this receipt exists and validates.
    """

    root = Path(data_root)
    layer_hits: dict[str, list[str]] = {
        "discipline_registry": [],
        "venue_registry": [],
        "target_world_store": [],
        "venue_memory": [],
    }

    # 1. Disciplinary landscape: repository seed/live registry.
    discipline_registry = load_default_registry()
    if discipline_query:
        matches = discipline_registry.candidates_keyword(
            discipline_query, region="auto", limit=12
        )
        layer_hits["discipline_registry"] = [
            f"discipline:{m.discipline_id}" for m in matches
        ]

    # 2. Durable runtime venue registry.
    hub = RegistryHub(data_dir=root / "registry")
    venue_matches = []
    if issn:
        for rec in hub.venues().list_all():
            if rec.issn == issn or rec.eissn == issn:
                venue_matches.append(rec)
    elif venue_query:
        venue_matches = hub.venues().search(venue_query, limit=20)
    layer_hits["venue_registry"] = [f"venue:{r.venue_id}" for r in venue_matches]

    # 3. Frozen TargetWorld snapshots.
    tw_store = TargetWorldStore(root)
    for snapshot_id in tw_store.list_ids():
        data = tw_store.get(snapshot_id)
        if data and str(data.get("target_id")) == target_id:
            layer_hits["target_world_store"].append(f"targetworld:{snapshot_id}")

    # 4. Cross-session VenueMemory.
    vm = VenueMemoryRegistry(root)
    memory = vm.lookup(issn=issn, name=venue_query) if (issn or venue_query) else None
    if memory is not None:
        layer_hits["venue_memory"].append(
            f"venue_memory:{memory.venue_memory_id}"
        )

    hits = []
    for values in layer_hits.values():
        hits.extend(values)
    target_level_hit = any(
        layer_hits[key]
        for key in ("venue_registry", "target_world_store", "venue_memory")
    )
    if target_level_hit:
        status = "target_local_hit"
    elif layer_hits["discipline_registry"]:
        status = "context_only_hit"
    else:
        status = "local_miss"

    return LocalFirstAuditReceipt(
        target_id=target_id,
        checked_discipline_registry=True,
        checked_venue_registry=True,
        checked_target_world_store=True,
        checked_venue_memory=True,
        local_hits=list(dict.fromkeys(hits)),
        layer_hits=layer_hits,
        external_discovery_used=False,
        status=status,
    )


def authorize_external_discovery(
    receipt: LocalFirstAuditReceipt,
    *,
    external_task_refs: list[str],
) -> LocalFirstAuditReceipt:
    """Return a receipt that proves network work followed local lookup."""

    updated = replace(
        receipt,
        external_discovery_used=True,
        external_task_refs=list(external_task_refs),
        status="external_authorized",
    )
    updated.validate()
    return updated