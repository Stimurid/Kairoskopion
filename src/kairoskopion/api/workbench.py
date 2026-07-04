"""P11 Prompt Pipeline Workbench API routes.

Mounted at /api/ in the main app. Provides endpoints for:
- Prompt family listing and inspection
- Pipeline run traces
- Prompt override CRUD
- Pipeline replay (rerun_all, rerun_stage, rerun_from_stage)
- Run diffing
- Correction candidates
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..services.pipeline_replay import (
    PIPELINE_STAGES,
    diff_runs,
    execute_replay_run,
    plan_rerun_all,
    plan_rerun_from_stage,
    plan_rerun_stage,
    scaffold_replay_run,
)
from ..services.pipeline_trace import (
    PipelineNode,
    PipelineRun,
    PipelineTraceStore,
    PromptRunRecord,
)
from ..services.prompt_override import (
    PromptOverride,
    PromptOverrideStore,
    PromptPatchCandidate,
)
from ..services.prompt_registry import PromptRegistry
from ..llm.config import LLMConfig
from ..llm.openai_compat import OpenAICompatProvider

router = APIRouter(tags=["workbench"])


def _get_llm_provider() -> OpenAICompatProvider | None:
    """Construct LLM provider from env config, if available."""
    cfg = LLMConfig.from_env()
    if cfg is None:
        return None
    if not cfg.api_key:
        return None
    return OpenAICompatProvider(cfg)

# --- Singletons (initialized on first import) ---

_data_dir = Path(os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion")

_prompt_registry: PromptRegistry | None = None
_trace_store: PipelineTraceStore | None = None
_override_store: PromptOverrideStore | None = None


def _get_prompt_registry() -> PromptRegistry:
    global _prompt_registry
    if _prompt_registry is None:
        _prompt_registry = PromptRegistry()
    return _prompt_registry


def _get_trace_store() -> PipelineTraceStore:
    global _trace_store
    if _trace_store is None:
        _trace_store = PipelineTraceStore(data_dir=_data_dir / "pipeline_traces")
    return _trace_store


def _get_override_store() -> PromptOverrideStore:
    global _override_store
    if _override_store is None:
        _override_store = PromptOverrideStore(data_dir=_data_dir / "prompt_overrides")
    return _override_store


# ---------------------------------------------------------------------------
# Prompt Family endpoints
# ---------------------------------------------------------------------------

@router.get("/prompts")
def list_prompts():
    reg = _get_prompt_registry()
    return [info.to_dict() for info in reg.list_all()]


@router.get("/prompts/{prompt_id}")
def get_prompt(prompt_id: str):
    reg = _get_prompt_registry()
    info = reg.get(prompt_id)
    if not info:
        raise HTTPException(404, f"Prompt family '{prompt_id}' not found")
    return info.to_dict()


# ---------------------------------------------------------------------------
# Pipeline stages (static definition)
# ---------------------------------------------------------------------------

@router.get("/pipeline-stages")
def list_pipeline_stages():
    return PIPELINE_STAGES


# ---------------------------------------------------------------------------
# Pipeline run trace endpoints
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/pipeline-runs")
def list_pipeline_runs(case_id: str):
    store = _get_trace_store()
    runs = store.list_runs(case_id)
    return [r.to_dict() for r in runs]


@router.get("/cases/{case_id}/pipeline-runs/{run_id}")
def get_pipeline_run(case_id: str, run_id: str):
    store = _get_trace_store()
    run = store.get_run(run_id)
    if not run or run.case_id != case_id:
        raise HTTPException(404, "Run not found")
    return run.to_dict()


@router.get("/cases/{case_id}/pipeline-runs/{run_id}/nodes")
def list_pipeline_nodes(case_id: str, run_id: str):
    store = _get_trace_store()
    run = store.get_run(run_id)
    if not run or run.case_id != case_id:
        raise HTTPException(404, "Run not found")
    nodes = store.list_nodes(run_id)
    return [n.to_dict() for n in nodes]


@router.get("/cases/{case_id}/pipeline-runs/{run_id}/nodes/{node_id}")
def get_pipeline_node(case_id: str, run_id: str, node_id: str):
    store = _get_trace_store()
    node = store.get_node(node_id)
    if not node or node.run_id != run_id:
        raise HTTPException(404, "Node not found")
    return node.to_dict()


@router.get("/cases/{case_id}/pipeline-runs/{run_id}/nodes/{node_id}/prompt")
def get_node_prompt(case_id: str, run_id: str, node_id: str):
    store = _get_trace_store()
    records = store.get_prompt_records_for_node(node_id)
    if not records:
        raise HTTPException(404, "No prompt records for this node")
    return [r.to_dict() for r in records]


# ---------------------------------------------------------------------------
# Prompt override endpoints
# ---------------------------------------------------------------------------

class CreateOverrideRequest(BaseModel):
    base_prompt_family_id: str
    edited_system_prompt: str | None = None
    edited_user_template: str | None = None
    notes: str = ""


class UpdateOverrideRequest(BaseModel):
    status: str | None = None
    edited_system_prompt: str | None = None
    edited_user_template: str | None = None
    notes: str | None = None


@router.post("/cases/{case_id}/prompt-overrides")
def create_prompt_override(case_id: str, req: CreateOverrideRequest):
    reg = _get_prompt_registry()
    if not reg.get(req.base_prompt_family_id):
        raise HTTPException(404, f"Prompt family '{req.base_prompt_family_id}' not found")

    version_hash = reg.get_version_hash(req.base_prompt_family_id) or ""
    ovr = PromptOverride(
        case_id=case_id,
        base_prompt_family_id=req.base_prompt_family_id,
        base_prompt_version_hash=version_hash,
        edited_system_prompt=req.edited_system_prompt,
        edited_user_template=req.edited_user_template,
        notes=req.notes,
    )
    store = _get_override_store()
    store.save_override(ovr)
    return ovr.to_dict()


@router.get("/cases/{case_id}/prompt-overrides")
def list_prompt_overrides(case_id: str):
    store = _get_override_store()
    return [o.to_dict() for o in store.list_overrides(case_id)]


@router.patch("/cases/{case_id}/prompt-overrides/{override_id}")
def update_prompt_override(case_id: str, override_id: str, req: UpdateOverrideRequest):
    store = _get_override_store()
    ovr = store.get_override(override_id)
    if not ovr or ovr.case_id != case_id:
        raise HTTPException(404, "Override not found")
    if req.status is not None:
        ovr.status = req.status
    if req.edited_system_prompt is not None:
        ovr.edited_system_prompt = req.edited_system_prompt
    if req.edited_user_template is not None:
        ovr.edited_user_template = req.edited_user_template
    if req.notes is not None:
        ovr.notes = req.notes
    return ovr.to_dict()


# ---------------------------------------------------------------------------
# Rerun endpoints
# ---------------------------------------------------------------------------

class RerunRequest(BaseModel):
    prompt_override_ids: list[str] = Field(default_factory=list)


class RerunStageRequest(BaseModel):
    stage_id: str
    prompt_override_ids: list[str] = Field(default_factory=list)
    base_run_id: str | None = None
    manuscript_text: str | None = None


class RerunFromStageRequest(BaseModel):
    stage_id: str
    prompt_override_ids: list[str] = Field(default_factory=list)
    base_run_id: str | None = None
    manuscript_text: str | None = None


@router.post("/cases/{case_id}/rerun")
def rerun_pipeline(case_id: str, req: RerunRequest):
    store = _get_trace_store()
    override_store = _get_override_store()
    prompt_reg = _get_prompt_registry()
    plan = plan_rerun_all(overrides=req.prompt_override_ids)
    outcome = execute_replay_run(
        plan,
        case_id=case_id,
        trace_store=store,
        override_store=override_store,
        prompt_registry=prompt_reg,
    )
    run = outcome["run"]
    resp = run.to_dict()
    resp["execution_status"] = outcome.get("status", "scaffold_only")
    return resp


@router.post("/cases/{case_id}/rerun-stage")
def rerun_single_stage(case_id: str, req: RerunStageRequest):
    from ..services.pipeline_replay import get_stage_index
    if get_stage_index(req.stage_id) is None:
        raise HTTPException(400, f"Unknown stage: {req.stage_id}")
    store = _get_trace_store()
    override_store = _get_override_store()
    prompt_reg = _get_prompt_registry()
    plan = plan_rerun_stage(
        req.stage_id,
        overrides=req.prompt_override_ids,
        base_run_id=req.base_run_id,
    )
    provider = _get_llm_provider() if req.manuscript_text else None
    outcome = execute_replay_run(
        plan, case_id=case_id, trace_store=store,
        override_store=override_store,
        prompt_registry=prompt_reg,
        llm_provider=provider,
        manuscript_text=req.manuscript_text,
    )
    run = outcome["run"]
    resp = run.to_dict()
    resp["execution_status"] = outcome.get("status", "scaffold_only")
    if "unsupported_stages" in outcome:
        resp["unsupported_stages"] = outcome["unsupported_stages"]
    return resp


@router.post("/cases/{case_id}/rerun-from-stage")
def rerun_from_stage(case_id: str, req: RerunFromStageRequest):
    from ..services.pipeline_replay import get_stage_index
    if get_stage_index(req.stage_id) is None:
        raise HTTPException(400, f"Unknown stage: {req.stage_id}")
    store = _get_trace_store()
    override_store = _get_override_store()
    prompt_reg = _get_prompt_registry()
    plan = plan_rerun_from_stage(
        req.stage_id,
        overrides=req.prompt_override_ids,
        base_run_id=req.base_run_id,
    )
    provider = _get_llm_provider() if req.manuscript_text else None
    outcome = execute_replay_run(
        plan, case_id=case_id, trace_store=store,
        override_store=override_store,
        prompt_registry=prompt_reg,
        llm_provider=provider,
        manuscript_text=req.manuscript_text,
    )
    run = outcome["run"]
    resp = run.to_dict()
    resp["execution_status"] = outcome.get("status", "scaffold_only")
    if "unsupported_stages" in outcome:
        resp["unsupported_stages"] = outcome["unsupported_stages"]
    return resp


# ---------------------------------------------------------------------------
# Pipeline diff
# ---------------------------------------------------------------------------

@router.get("/cases/{case_id}/pipeline-diff")
def pipeline_diff(case_id: str, run_a: str, run_b: str):
    store = _get_trace_store()
    ra = store.get_run(run_a)
    rb = store.get_run(run_b)
    if not ra or not rb:
        raise HTTPException(404, "One or both runs not found")
    diffs = diff_runs(store, run_a, run_b)
    return [
        {"stage_id": d.stage_id, "field": d.field,
         "run_a": d.run_a_value, "run_b": d.run_b_value, "changed": d.changed}
        for d in diffs
    ]


# ---------------------------------------------------------------------------
# Correction candidates
# ---------------------------------------------------------------------------

class CorrectionRequest(BaseModel):
    node_id: str
    correction_type: str
    user_note: str
    affected_prompt_family_id: str
    proposed_change: str | None = None


@router.post("/cases/{case_id}/corrections")
def create_correction(case_id: str, req: CorrectionRequest):
    store = _get_override_store()
    corr = PromptPatchCandidate(
        case_id=case_id,
        node_id=req.node_id,
        correction_type=req.correction_type,
        user_note=req.user_note,
        affected_prompt_family_id=req.affected_prompt_family_id,
        proposed_change=req.proposed_change,
    )
    store.save_correction(corr)
    return corr.to_dict()
