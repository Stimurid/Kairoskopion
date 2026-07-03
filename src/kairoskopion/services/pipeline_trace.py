"""Pipeline trace models and storage — PipelineRun, PipelineNode, PromptRunRecord.

Durable trace for the ManuscriptVenueFitPipeline and replay engine.
Every pipeline execution creates a PipelineRun with PipelineNode records
for each stage. LLM-capable stages also get PromptRunRecord entries.
"""
from __future__ import annotations

import dataclasses as dc
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..ids import generate_id


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# PipelineRun
# ---------------------------------------------------------------------------

@dc.dataclass
class PipelineRun:
    run_id: str = dc.field(default_factory=lambda: generate_id("prun"))
    case_id: str | None = None
    input_article_ref: str | None = None
    trigger: str = "upload"
    status: str = "pending"
    base_run_id: str | None = None
    prompt_override_ids: list[str] = dc.field(default_factory=list)
    started_at: str = dc.field(default_factory=_now)
    completed_at: str | None = None
    node_ids: list[str] = dc.field(default_factory=list)
    final_artifact_refs: list[str] = dc.field(default_factory=list)
    gates_summary: dict[str, Any] = dc.field(default_factory=dict)
    diagnostics: list[str] = dc.field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dc.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineRun:
        valid = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ---------------------------------------------------------------------------
# PipelineNode
# ---------------------------------------------------------------------------

@dc.dataclass
class PipelineNode:
    node_id: str = dc.field(default_factory=lambda: generate_id("pnode"))
    run_id: str = ""
    stage_id: str = ""
    stage_label: str = ""
    order_index: int = 0
    producer_type: str = "deterministic"
    service_or_agent: str = ""
    prompt_family_id: str | None = None
    prompt_version_hash: str | None = None
    prompt_override_id: str | None = None
    model_role: str | None = None
    provider_status: str | None = None
    parse_status: str | None = None
    input_artifact_refs: list[str] = dc.field(default_factory=list)
    output_artifact_refs: list[str] = dc.field(default_factory=list)
    evidence_refs: list[str] = dc.field(default_factory=list)
    gate_results: dict[str, Any] = dc.field(default_factory=dict)
    status: str = "pending"
    rerunnable: bool = True
    downstream_node_ids: list[str] = dc.field(default_factory=list)
    diagnostics: list[str] = dc.field(default_factory=list)
    started_at: str | None = None
    completed_at: str | None = None
    output_hash: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dc.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PipelineNode:
        valid = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ---------------------------------------------------------------------------
# PromptRunRecord
# ---------------------------------------------------------------------------

@dc.dataclass
class PromptRunRecord:
    prompt_run_id: str = dc.field(default_factory=lambda: generate_id("prr"))
    node_id: str = ""
    prompt_family_id: str = ""
    prompt_version_hash: str = ""
    prompt_override_id: str | None = None
    rendered_system_prompt: str = ""
    rendered_user_prompt: str = ""
    input_context_summary: str = ""
    input_artifact_refs: list[str] = dc.field(default_factory=list)
    provider_status: str | None = None
    response_status: str | None = None
    response_excerpt_or_ref: str | None = None
    parsed_output_ref: str | None = None
    diagnostics: list[str] = dc.field(default_factory=list)
    created_at: str = dc.field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dc.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptRunRecord:
        valid = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


# ---------------------------------------------------------------------------
# PipelineTraceStore — in-memory with JSONL persistence
# ---------------------------------------------------------------------------

class PipelineTraceStore:
    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir
        self._runs: dict[str, PipelineRun] = {}
        self._nodes: dict[str, PipelineNode] = {}
        self._prompt_records: dict[str, PromptRunRecord] = {}
        if data_dir:
            data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        if not self._data_dir:
            return
        for path, store, cls in [
            (self._data_dir / "pipeline_runs.jsonl", self._runs, PipelineRun),
            (self._data_dir / "pipeline_nodes.jsonl", self._nodes, PipelineNode),
            (self._data_dir / "prompt_run_records.jsonl", self._prompt_records, PromptRunRecord),
        ]:
            if path.exists():
                for line in path.read_text(encoding="utf-8").strip().split("\n"):
                    if not line.strip():
                        continue
                    obj = cls.from_dict(json.loads(line))
                    id_field = dc.fields(cls)[0].name
                    store[getattr(obj, id_field)] = obj

    def _persist(self, record: Any, filename: str) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / filename
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    # -- runs ---------------------------------------------------------------

    def save_run(self, run: PipelineRun) -> PipelineRun:
        self._runs[run.run_id] = run
        self._persist(run, "pipeline_runs.jsonl")
        return run

    def get_run(self, run_id: str) -> PipelineRun | None:
        return self._runs.get(run_id)

    def list_runs(self, case_id: str | None = None) -> list[PipelineRun]:
        if case_id:
            return [r for r in self._runs.values() if r.case_id == case_id]
        return list(self._runs.values())

    # -- nodes --------------------------------------------------------------

    def save_node(self, node: PipelineNode) -> PipelineNode:
        self._nodes[node.node_id] = node
        self._persist(node, "pipeline_nodes.jsonl")
        return node

    def get_node(self, node_id: str) -> PipelineNode | None:
        return self._nodes.get(node_id)

    def list_nodes(self, run_id: str) -> list[PipelineNode]:
        nodes = [n for n in self._nodes.values() if n.run_id == run_id]
        return sorted(nodes, key=lambda n: n.order_index)

    # -- prompt records -----------------------------------------------------

    def save_prompt_record(self, rec: PromptRunRecord) -> PromptRunRecord:
        self._prompt_records[rec.prompt_run_id] = rec
        self._persist(rec, "prompt_run_records.jsonl")
        return rec

    def get_prompt_record(self, prompt_run_id: str) -> PromptRunRecord | None:
        return self._prompt_records.get(prompt_run_id)

    def get_prompt_records_for_node(self, node_id: str) -> list[PromptRunRecord]:
        return [r for r in self._prompt_records.values() if r.node_id == node_id]
