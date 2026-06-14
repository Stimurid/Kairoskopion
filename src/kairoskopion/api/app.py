"""Kairoskopion API — thin FastAPI wrapper over domain services.

Exposes case-oriented endpoints for the publication positioning cockpit.
All heavy logic lives in services/agents/pipelines; this module only
serializes inputs/outputs and manages case state.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import os
import traceback
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .auth import (
    User,
    continue_session as _auth_continue,
    get_current_user,
    logout as _auth_logout,
    me as _auth_me,
    signup as _auth_signup,
)
from .cases import CaseStore, Case, CaseStage

_VERSION = "0.2.0-alpha"

# --- Logging setup ---
_log_dir = os.environ.get("KAIROSKOPION_LOG_DIR")
if _log_dir:
    _log_path = Path(_log_dir)
    _log_path.mkdir(parents=True, exist_ok=True)
    _file_handler = logging.handlers.RotatingFileHandler(
        _log_path / "kairoskopion.log",
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    _file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logging.getLogger("kairoskopion").addHandler(_file_handler)
    logging.getLogger("kairoskopion").setLevel(logging.INFO)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

app = FastAPI(
    title="Kairoskopion",
    version=_VERSION,
    description="Publication positioning cockpit API",
)

_default_origins = ["http://localhost:5173", "http://localhost:3000"]
_env_origins = os.environ.get("KAIROSKOPION_ALLOWED_ORIGINS", "")
_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = CaseStore()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    from ..llm.config import provider_status
    llm = provider_status()
    return {"status": "ok", "version": _VERSION, "llm": llm}


# ---------------------------------------------------------------------------
# Staging soft-auth: signup / continue / me / logout
# ---------------------------------------------------------------------------
# Trust-based identity. No password. No email verification. Acceptable
# only for the small trusted-tester staging group. See
# docs/operations/STAGING_SOFT_AUTH_AND_PERSISTENCE_REPORT.md.

class SignupRequest(BaseModel):
    display_name: str
    email: str | None = None


class ContinueRequest(BaseModel):
    email: str


@app.post("/auth/signup")
def auth_signup(req: SignupRequest):
    if not (req.display_name or "").strip():
        raise HTTPException(400, "display_name_required")
    return _auth_signup(req.display_name, req.email)


@app.post("/auth/continue")
def auth_continue(req: ContinueRequest):
    if not (req.email or "").strip():
        raise HTTPException(400, "email_required")
    return _auth_continue(req.email)


@app.get("/auth/me")
def auth_me(current_user: User = Depends(get_current_user)):
    return _auth_me(current_user)


@app.post("/auth/logout")
def auth_logout(authorization: str | None = Header(default=None)):
    # Idempotent: revoke if present + valid, else no-op.
    if not authorization:
        return {"revoked": False}
    parts = authorization.split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return {"revoked": False}
    return _auth_logout(parts[1].strip())


# Shared dependency: resolves `case_id` to a Case owned by the
# authenticated user, or 404. Cross-tenant access is silent (no
# information leak about whether the case exists for some other user).
def _user_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
) -> Case:
    c = store.get(case_id, user_id=current_user.user_id)
    if not c:
        raise HTTPException(404, f"Case {case_id} not found")
    return c


# ---------------------------------------------------------------------------
# Cases CRUD
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    title: str = ""


@app.get("/cases")
def list_cases(current_user: User = Depends(get_current_user)):
    return [c.summary() for c in store.all(user_id=current_user.user_id)]


@app.post("/cases")
def create_case(
    req: CreateCaseRequest,
    current_user: User = Depends(get_current_user),
):
    case = store.create(title=req.title, user_id=current_user.user_id)
    return case.summary()


@app.get("/cases/{case_id}")
def get_case(case: Case = Depends(_user_case)):
    return case.to_dict()


@app.delete("/cases/{case_id}")
def delete_case(
    case_id: str, current_user: User = Depends(get_current_user),
):
    if not store.delete(case_id, user_id=current_user.user_id):
        raise HTTPException(404, f"Case {case_id} not found")
    return {"deleted": case_id}


# ---------------------------------------------------------------------------
# Intake — accept text, abstract, or file
# ---------------------------------------------------------------------------

class IntakeTextRequest(BaseModel):
    text: str
    input_type: str = "auto"  # auto | article | venue | review_letter
    search_depth: str = "none"  # none | light | deep


@app.post("/cases/{case_id}/intake/text")
def intake_text(req: IntakeTextRequest, case: Case = Depends(_user_case)):
    result = case.intake_text(req.text, req.input_type, req.search_depth)
    store.save(case)
    return result


_SUPPORTED_UPLOAD_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".html", ".htm"}


@app.post("/cases/{case_id}/intake/file")
async def intake_file(
    file: UploadFile = File(...),
    input_type: str = Form("auto"),
    search_depth: str = Form("none"),
    case: Case = Depends(_user_case),
):

    filename = file.filename or "upload"
    suffix = Path(filename).suffix.lower()
    if suffix not in _SUPPORTED_UPLOAD_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type: {suffix}. "
            f"Supported: {', '.join(sorted(_SUPPORTED_UPLOAD_EXTENSIONS))}",
        )

    import tempfile
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        from .source_intake_util import extract_text_from_file

        text, extraction_status, errors = extract_text_from_file(tmp_path)
        if not text:
            raise HTTPException(
                400,
                f"Could not extract text from {filename}: "
                + "; ".join(errors or ["unknown error"]),
            )

        result = case.intake_text(text, input_type, search_depth)
        result["filename"] = filename
        result["extraction_status"] = extraction_status
        store.save(case)
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Venue Investigation
# ---------------------------------------------------------------------------

class InvestigateVenueRequest(BaseModel):
    text: str


@app.post("/cases/{case_id}/investigate-venue")
def investigate_venue(
    req: InvestigateVenueRequest, case: Case = Depends(_user_case),
):
    return case.investigate_venue(req.text)


@app.get("/cases/{case_id}/investigated-venue")
def get_investigated_venue(case: Case = Depends(_user_case)):
    if not case.investigated_venue:
        raise HTTPException(404, "No venue investigated yet")
    result: dict = {"venue": case.investigated_venue.to_dict()}
    if case.publication_regime:
        result["publication_regime"] = case.publication_regime.to_dict()
    return result


# ---------------------------------------------------------------------------
# Article Model
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/article-model")
def get_article_model(case: Case = Depends(_user_case)):
    if not case.article_model:
        raise HTTPException(404, "Article model not built yet")
    return case.article_model.to_dict()


class ConfirmArticleRequest(BaseModel):
    protected_core: list[str] | None = None
    corrections: dict[str, Any] | None = None


@app.post("/cases/{case_id}/article-model/confirm")
def confirm_article_model(
    req: ConfirmArticleRequest, case: Case = Depends(_user_case),
):
    if not case.article_model:
        raise HTTPException(400, "Article model not built yet")
    result = case.confirm_article_model(
        protected_core=req.protected_core,
        corrections=req.corrections,
    )
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Scenario
# ---------------------------------------------------------------------------

class SetScenarioRequest(BaseModel):
    goal: str = ""
    prestige_priority: str = "medium"
    speed_priority: str = "medium"
    apc_max: float | None = None
    deadline: str | None = None
    rewrite_depth_allowed: str = "medium"
    risk_tolerance: str = "medium"
    target_indexing: list[str] = Field(default_factory=list)
    language: str = "en"


@app.post("/cases/{case_id}/scenario")
def set_scenario(
    req: SetScenarioRequest, case: Case = Depends(_user_case),
):
    result = case.set_scenario(req.model_dump())
    store.save(case)
    return result


@app.get("/cases/{case_id}/scenario")
def get_scenario(case: Case = Depends(_user_case)):
    if not case.scenario:
        raise HTTPException(404, "Scenario not set")
    return case.scenario.to_dict()


# ---------------------------------------------------------------------------
# Pathways
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/pathways")
def get_pathways(case: Case = Depends(_user_case)):
    return case.get_pathways()


# ---------------------------------------------------------------------------
# Venue Pool
# ---------------------------------------------------------------------------

@app.post("/cases/{case_id}/discover-venues")
def discover_venues(case: Case = Depends(_user_case)):
    result = case.discover_venues()
    store.save(case)
    return result


@app.get("/cases/{case_id}/venue-pool")
def get_venue_pool(case: Case = Depends(_user_case)):
    return case.get_venue_pool()


# ---------------------------------------------------------------------------
# Selected Venue & Fit
# ---------------------------------------------------------------------------

@app.post("/cases/{case_id}/select-venue/{venue_id}")
def select_venue(venue_id: str, case: Case = Depends(_user_case)):
    result = case.select_venue(venue_id)
    store.save(case)
    return result


@app.get("/cases/{case_id}/fit")
def get_fit(case: Case = Depends(_user_case)):
    return case.get_fit()


@app.get("/cases/{case_id}/mismatch-map")
def get_mismatch_map(case: Case = Depends(_user_case)):
    return case.get_mismatch_map()


# ---------------------------------------------------------------------------
# Adaptation Plan & Decisions
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/adaptation-plan")
def get_adaptation_plan(case: Case = Depends(_user_case)):
    return case.get_adaptation_plan()


class UserDecisionRequest(BaseModel):
    change_id: str
    action: str  # accept | reject | defer
    reason: str = ""


@app.post("/cases/{case_id}/decisions")
def apply_decisions(
    decisions: list[UserDecisionRequest],
    case: Case = Depends(_user_case),
):
    result = case.apply_decisions([d.model_dump() for d in decisions])
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Evidence drill-down
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/evidence/{entity_type}/{field_path}")
def get_evidence(
    entity_type: str, field_path: str,
    case: Case = Depends(_user_case),
):
    return case.get_evidence(entity_type, field_path)


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/quality-gates")
def get_quality_gates(case: Case = Depends(_user_case)):
    return case.get_quality_gates()


# ---------------------------------------------------------------------------
# Dossier
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/dossier")
def get_dossier(case: Case = Depends(_user_case)):
    return case.build_dossier()


# ---------------------------------------------------------------------------
# Decision log
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/decision-log")
def get_decision_log(case: Case = Depends(_user_case)):
    return case.decision_log


# ---------------------------------------------------------------------------
# Agent Map — technical introspection endpoint
# ---------------------------------------------------------------------------

@app.get("/agents/map")
def get_agent_map():
    """Return full agent registry, workflows, and prompt metadata for the UI map."""
    from ..agents.registry import list_agent_specs
    from ..agents.workflows import WORKFLOW_REGISTRY
    from ..agents.prompt_families.catalog import PROMPT_FAMILY_CATALOG
    from ..llm.config import provider_status

    agents = []
    for spec in list_agent_specs():
        d = spec.to_dict() if hasattr(spec, "to_dict") else {
            "role_id": spec.role_id,
            "display_name": spec.display_name,
            "layer": spec.layer,
            "implementation_status": spec.implementation_status,
            "execution_mode": spec.execution_mode,
            "prompt_family_ids": spec.prompt_family_ids,
            "input_contract": spec.input_contract,
            "output_contract": spec.output_contract,
            "mvp_phase": spec.mvp_phase,
            "first_workflows": spec.first_workflows,
        }
        # Check if execute() actually calls LLM
        has_real_llm = spec.role_id in {
            "article_modeler", "article_semantic_profiler",
            "disciplinary_pathway_mapper", "venue_profiler", "fit_assessor",
        }
        d["has_real_llm"] = has_real_llm
        d["has_orphaned_prompt"] = (
            bool(spec.prompt_family_ids)
            and not has_real_llm
            and spec.implementation_status != "contract_only"
        )
        agents.append(d)

    workflows = []
    for wf in WORKFLOW_REGISTRY.values():
        steps = []
        for s in wf.steps:
            sd = s if isinstance(s, dict) else s.to_dict() if hasattr(s, "to_dict") else {}
            steps.append(sd)
        workflows.append({
            "workflow_id": wf.workflow_id,
            "display_name": wf.display_name,
            "description": wf.description,
            "implementation_status": wf.implementation_status,
            "steps": steps,
        })

    prompts = {}
    for fam_id, fam in PROMPT_FAMILY_CATALOG.items():
        sp = fam.get("system_prompt", "")
        up = fam.get("user_prompt_template", "")
        schema = fam.get("output_schema", {})
        schema_fields = list(schema.get("properties", {}).keys()) if schema else []
        prompts[fam_id] = {
            "family_id": fam_id,
            "agent_role_id": fam.get("agent_role_id", ""),
            "version": fam.get("version", ""),
            "system_prompt": sp,
            "user_prompt_template": up,
            "system_prompt_lines": sp.count("\n") + 1 if sp else 0,
            "user_prompt_lines": up.count("\n") + 1 if up else 0,
            "output_schema_fields": schema_fields,
            "purpose": fam.get("purpose", ""),
            "forbidden_behaviors": fam.get("forbidden_behaviors", []),
            "evidence_requirements": fam.get("evidence_requirements", []),
        }

    # Also include Gen-1 prompts from src/kairoskopion/prompts/
    try:
        from ..prompts.article_modeling import ARTICLE_MODELING_FAMILY
        from ..prompts.venue_fact_extraction import VENUE_FACT_EXTRACTION_FAMILY
        from ..prompts.fit_assessment import FIT_ASSESSMENT_FAMILY
        from ..prompts.semantic_profiling import SEMANTIC_PROFILING_FAMILY
        from ..prompts.disciplinary_mapping import DISCIPLINARY_MAPPING_FAMILY
        for fam in [ARTICLE_MODELING_FAMILY, VENUE_FACT_EXTRACTION_FAMILY,
                     FIT_ASSESSMENT_FAMILY, SEMANTIC_PROFILING_FAMILY,
                     DISCIPLINARY_MAPPING_FAMILY]:
            fid = fam.get("family_id", "")
            if fid and fid not in prompts:
                sp = fam.get("system_prompt", "")
                up = fam.get("user_prompt_template", "")
                schema = fam.get("output_schema", {})
                schema_fields = list(schema.get("properties", {}).keys()) if schema else []
                prompts[fid] = {
                    "family_id": fid,
                    "agent_role_id": fam.get("agent_role_id", ""),
                    "version": fam.get("version", ""),
                    "system_prompt": sp,
                    "user_prompt_template": up,
                    "system_prompt_lines": sp.count("\n") + 1 if sp else 0,
                    "user_prompt_lines": up.count("\n") + 1 if up else 0,
                    "output_schema_fields": schema_fields,
                    "purpose": fam.get("purpose", ""),
                }
    except Exception:
        pass

    return {
        "agents": agents,
        "workflows": workflows,
        "prompts": prompts,
        "llm": provider_status(),
    }


# ---------------------------------------------------------------------------
# Static frontend (SPA) — serves built UI if dist/ exists
# ---------------------------------------------------------------------------

_frontend_dir = Path(__file__).resolve().parent.parent.parent.parent / "ui" / "dist"

if _frontend_dir.is_dir():
    from starlette.responses import FileResponse
    from starlette.staticfiles import StaticFiles

    app.mount("/assets", StaticFiles(directory=_frontend_dir / "assets"), name="static-assets")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = _frontend_dir / path
        if file_path.is_file() and ".." not in path:
            return FileResponse(file_path)
        return FileResponse(_frontend_dir / "index.html")
