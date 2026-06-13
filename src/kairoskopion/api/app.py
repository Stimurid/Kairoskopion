"""Kairoskopion API — thin FastAPI wrapper over domain services.

Exposes case-oriented endpoints for the publication positioning cockpit.
All heavy logic lives in services/agents/pipelines; this module only
serializes inputs/outputs and manages case state.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .cases import CaseStore, Case, CaseStage

app = FastAPI(
    title="Kairoskopion",
    version="0.1.0",
    description="Publication positioning cockpit API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
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
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# Cases CRUD
# ---------------------------------------------------------------------------

class CreateCaseRequest(BaseModel):
    title: str = ""


@app.get("/cases")
def list_cases():
    return [c.summary() for c in store.all()]


@app.post("/cases")
def create_case(req: CreateCaseRequest):
    case = store.create(title=req.title)
    return case.summary()


@app.get("/cases/{case_id}")
def get_case(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.to_dict()


@app.delete("/cases/{case_id}")
def delete_case(case_id: str):
    if not store.delete(case_id):
        raise HTTPException(404, f"Case {case_id} not found")
    return {"deleted": case_id}


# ---------------------------------------------------------------------------
# Intake — accept text, abstract, or file
# ---------------------------------------------------------------------------

class IntakeTextRequest(BaseModel):
    text: str
    input_type: str = "auto"  # auto | article | venue | review_letter


@app.post("/cases/{case_id}/intake/text")
def intake_text(case_id: str, req: IntakeTextRequest):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    result = case.intake_text(req.text, req.input_type)
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Venue Investigation
# ---------------------------------------------------------------------------

class InvestigateVenueRequest(BaseModel):
    text: str


@app.post("/cases/{case_id}/investigate-venue")
def investigate_venue(case_id: str, req: InvestigateVenueRequest):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.investigate_venue(req.text)


@app.get("/cases/{case_id}/investigated-venue")
def get_investigated_venue(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
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
def get_article_model(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    if not case.article_model:
        raise HTTPException(404, "Article model not built yet")
    return case.article_model.to_dict()


class ConfirmArticleRequest(BaseModel):
    protected_core: list[str] | None = None
    corrections: dict[str, Any] | None = None


@app.post("/cases/{case_id}/article-model/confirm")
def confirm_article_model(case_id: str, req: ConfirmArticleRequest):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
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
def set_scenario(case_id: str, req: SetScenarioRequest):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    result = case.set_scenario(req.model_dump())
    store.save(case)
    return result


@app.get("/cases/{case_id}/scenario")
def get_scenario(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    if not case.scenario:
        raise HTTPException(404, "Scenario not set")
    return case.scenario.to_dict()


# ---------------------------------------------------------------------------
# Pathways
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/pathways")
def get_pathways(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_pathways()


# ---------------------------------------------------------------------------
# Venue Pool
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/venue-pool")
def get_venue_pool(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_venue_pool()


# ---------------------------------------------------------------------------
# Selected Venue & Fit
# ---------------------------------------------------------------------------

@app.post("/cases/{case_id}/select-venue/{venue_id}")
def select_venue(case_id: str, venue_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    result = case.select_venue(venue_id)
    store.save(case)
    return result


@app.get("/cases/{case_id}/fit")
def get_fit(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_fit()


@app.get("/cases/{case_id}/mismatch-map")
def get_mismatch_map(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_mismatch_map()


# ---------------------------------------------------------------------------
# Adaptation Plan & Decisions
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/adaptation-plan")
def get_adaptation_plan(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_adaptation_plan()


class UserDecisionRequest(BaseModel):
    change_id: str
    action: str  # accept | reject | defer
    reason: str = ""


@app.post("/cases/{case_id}/decisions")
def apply_decisions(case_id: str, decisions: list[UserDecisionRequest]):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    result = case.apply_decisions([d.model_dump() for d in decisions])
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Evidence drill-down
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/evidence/{entity_type}/{field_path}")
def get_evidence(case_id: str, entity_type: str, field_path: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_evidence(entity_type, field_path)


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/quality-gates")
def get_quality_gates(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.get_quality_gates()


# ---------------------------------------------------------------------------
# Dossier
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/dossier")
def get_dossier(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.build_dossier()


# ---------------------------------------------------------------------------
# Decision log
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/decision-log")
def get_decision_log(case_id: str):
    case = store.get(case_id)
    if not case:
        raise HTTPException(404, f"Case {case_id} not found")
    return case.decision_log
