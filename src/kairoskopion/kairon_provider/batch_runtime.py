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
from typing import Any, Iterable

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
    """Durable graph store with immutable repository seeds plus live overrides.

    Seed records are search-routing memory. Live records override them by
    node_id. When a live node changes, the previous materialization is archived
    so later passes can reconstruct how the local graph evolved.
    """

    def __init__(
        self,
        root: str | Path,
        *,
        seed_paths: Iterable[str | Path] = (),
    ):
        base = Path(root) / "kairon_provider" / "academic_world"
        self.root = base / "live"
        self.history_root = base / "history"
        self.root.mkdir(parents=True, exist_ok=True)
        self.seed_paths = [Path(x) for x in seed_paths]

    def _path(self, node_id: str) -> Path:
        return self.root / f"{_digest(node_id)}.json"

    def _seed_nodes(self) -> dict[str, AcademicWorldNode]:
        out: dict[str, AcademicWorldNode] = {}
        for path in self.seed_paths:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    node = AcademicWorldNode(**json.loads(line))
                except Exception:
                    continue
                out[node.node_id] = node
        return out

    def put(self, node: AcademicWorldNode) -> AcademicWorldNode:
        path = self._path(node.node_id)
        if path.is_file():
            prior = json.loads(path.read_text(encoding="utf-8"))
            current = node.to_dict()
            if prior != current:
                history_dir = self.history_root / _digest(node.node_id)
                history_dir.mkdir(parents=True, exist_ok=True)
                prior_digest = hashlib.sha256(
                    json.dumps(prior, ensure_ascii=False, sort_keys=True).encode("utf-8")
                ).hexdigest()
                _atomic_json(history_dir / f"{prior_digest}.json", prior)
        _atomic_json(path, node.to_dict())
        return node

    def get(self, node_id: str) -> AcademicWorldNode | None:
        path = self._path(node_id)
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if raw.get("node_id") == node_id:
                return AcademicWorldNode(**raw)
        return self._seed_nodes().get(node_id)

    def list_nodes(self, node_type: str | None = None) -> list[AcademicWorldNode]:
        merged = self._seed_nodes()
        for path in sorted(self.root.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                node = AcademicWorldNode(**raw)
            except Exception:
                continue
            merged[node.node_id] = node
        out = list(merged.values())
        if node_type is not None:
            out = [node for node in out if node.node_type == node_type]
        return out

    def search(self, query: str, limit: int = 20) -> list[AcademicWorldNode]:
        q = (query or "").strip().lower()
        if not q:
            return self.list_nodes()[:limit]
        scored: list[tuple[int, AcademicWorldNode]] = []
        for node in self.list_nodes():
            score = 0
            if q in node.node_id.lower():
                score += 4
            for value in node.names.values():
                if q in value.lower():
                    score += 6
            for value in node.languages + node.institutional_regions:
                if q in value.lower():
                    score += 2
            if score:
                scored.append((score, node))
        scored.sort(key=lambda item: (-item[0], item[1].node_id))
        return [node for _, node in scored[:limit]]

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
        terminal = {"complete", "qualification_complete", "evidence_hold", "blocked_author", "failed", "abandoned"}
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
    academic_world_query: str | None = None,
    discipline_query: str | None = None,
    venue_query: str | None = None,
    issn: str | None = None,
    repository_root: str | Path | None = None,
) -> LocalFirstAuditReceipt:
    """Check durable local knowledge without creating network work.

    This function has no external adapters. A caller may mark an external
    discovery only after this receipt exists and validates.
    """

    root = Path(data_root)
    repo_root = Path(repository_root) if repository_root is not None else Path(__file__).resolve().parents[3]
    layer_hits: dict[str, list[str]] = {
        "academic_world": [],
        "discipline_registry": [],
        "venue_registry": [],
        "repository_venue_registry": [],
        "repository_venue_harvest": [],
        "venue_evidence_pack": [],
        "target_world_store": [],
        "venue_memory": [],
    }

    # 0. Academic-world graph: repository routing seeds + durable live overrides.
    academic_seed_paths = sorted(
        (repo_root / "data" / "academic_world" / "seeds").glob("*.jsonl")
    )
    academic_store = AcademicWorldStore(root, seed_paths=academic_seed_paths)
    if academic_world_query:
        layer_hits["academic_world"] = [
            f"academic_world:{node.node_id}"
            for node in academic_store.search(academic_world_query, limit=20)
        ]

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

    # 2b. Repository venue registry shipped with the current code/data state.
    repo_hub = RegistryHub(data_dir=repo_root / "data" / "registry")
    repo_venue_matches = []
    if issn:
        for rec in repo_hub.venues().list_all():
            if rec.issn == issn or rec.eissn == issn:
                repo_venue_matches.append(rec)
    elif venue_query:
        repo_venue_matches = repo_hub.venues().search(venue_query, limit=20)
    layer_hits["repository_venue_registry"] = [
        f"repo_venue:{r.venue_id}" for r in repo_venue_matches
    ]

    # 2c. Repository harvested provisional venue records.
    q = (venue_query or "").strip().lower()
    for path in sorted((repo_root / "data" / "seed_registry").glob("**/provisional_venue_records.jsonl")):
        try:
            rows = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        except Exception:
            continue
        for row in rows:
            name = str(row.get("canonical_name") or row.get("title") or row.get("name") or "")
            row_issn = str(row.get("issn") or "")
            if (issn and row_issn == issn) or (q and q in name.lower()):
                rid = str(row.get("venue_id") or _digest(name)[:12])
                layer_hits["repository_venue_harvest"].append(
                    f"repo_harvest:{rid}"
                )

    # 2d. Evidence packs are durable local target knowledge too.
    for path in sorted((repo_root / "data" / "venue_evidence_packs").glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        low = text.lower()
        if (issn and issn in text) or (q and q in low):
            layer_hits["venue_evidence_pack"].append(
                f"venue_evidence_pack:{path.name}"
            )

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
        for key in (
            "venue_registry",
            "repository_venue_registry",
            "repository_venue_harvest",
            "venue_evidence_pack",
            "target_world_store",
            "venue_memory",
        )
    )
    if target_level_hit:
        status = "target_local_hit"
    elif layer_hits["academic_world"] or layer_hits["discipline_registry"]:
        status = "context_only_hit"
    else:
        status = "local_miss"

    return LocalFirstAuditReceipt(
        target_id=target_id,
        checked_academic_world_store=True,
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


def persist_target_world_refresh(
    *,
    store: TargetWorldStore,
    parent_snapshot_id: str,
    refreshed_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """Persist refresh as a descendant; a frozen snapshot is never overwritten."""
    parent = store.get(parent_snapshot_id)
    if parent is None:
        raise KeyError(f"parent target snapshot not found: {parent_snapshot_id}")
    child_id = str(refreshed_snapshot.get("snapshot_id") or "")
    if not child_id:
        raise ValueError("refreshed snapshot_id must be non-empty")
    if child_id == parent_snapshot_id:
        raise ValueError("refresh must create a new descendant snapshot_id")
    if store.get(child_id) is not None:
        raise ValueError("refreshed snapshot_id already exists")
    data = dict(refreshed_snapshot)
    lineage = dict(data.get("lineage") or {})
    lineage["parent_snapshot_id"] = parent_snapshot_id
    data["lineage"] = lineage
    store.put(data)
    return data