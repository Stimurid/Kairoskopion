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


# ---------------------------------------------------------------------------
# Load .env BEFORE anything imports LLMConfig / reads os.environ.
# Per docs/LLM_PROVIDER_REALITY_302AI.md §1 — every entry point should
# read via python-dotenv. Without this, `uvicorn ...:app` starts with an
# empty env and LLMConfig.from_env() returns None even when .env is
# populated, silently dropping all agents to deterministic fallback.
# Pure-stdlib loader so this is a no-op when no .env exists and adds
# zero runtime deps.
# ---------------------------------------------------------------------------

def _load_dotenv_if_present() -> None:
    # Skip when running under pytest: tests already control env via
    # monkeypatch; auto-loading a real .env (with real LLM keys) would
    # turn cases-intake unit tests into live LLM HTTP calls that hang.
    import sys
    if "pytest" in sys.modules or os.environ.get("PYTEST_CURRENT_TEST"):
        return
    if os.environ.get("KAIROSKOPION_NO_DOTENV") == "1":
        return
    env_path_str = os.environ.get("KAIROSKOPION_ENV_FILE", ".env")
    env_path = Path(env_path_str)
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip()
        # Strip optional surrounding quotes
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        # Do NOT overwrite already-set env (operator overrides win).
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv_if_present()

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

_default_origins = [
    "http://localhost:5173", "http://localhost:3000",
    "http://127.0.0.1:5173", "http://127.0.0.1:3000",
]
_env_origins = os.environ.get("KAIROSKOPION_ALLOWED_ORIGINS", "")
_origins = [o.strip() for o in _env_origins.split(",") if o.strip()] if _env_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    # Must cover every method the UI client uses: GET/POST/DELETE plus
    # PATCH (workbench prompt-override update, ui/src/api/client.ts).
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

store = CaseStore()

from kairoskopion.services.venue_memory import VenueMemoryRegistry
from pathlib import Path as _Path
_vm_data_dir = _Path(
    os.environ.get("KAIROSKOPION_DATA_DIR") or ".kairoskopion"
)
venue_memory_registry = VenueMemoryRegistry(_vm_data_dir)

# P11 Prompt Pipeline Workbench routes
from .workbench import router as _workbench_router
app.include_router(_workbench_router, prefix="/api")


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
    region: str = "auto"  # auto | ru | international | eu-fr | ...


@app.post("/cases/{case_id}/intake/text")
def intake_text(req: IntakeTextRequest, case: Case = Depends(_user_case)):
    from ..llm.input_limits import INTAKE_HARD_CHAR_CAP
    if len(req.text) > INTAKE_HARD_CHAR_CAP:
        raise HTTPException(
            status_code=413,
            detail={
                "error": "input_too_large",
                "received_chars": len(req.text),
                "max_chars": INTAKE_HARD_CHAR_CAP,
                "message": (
                    f"Текст слишком длинный ({len(req.text)} символов). "
                    f"Максимум: {INTAKE_HARD_CHAR_CAP}. Сократите вход "
                    f"или разделите его на части."
                ),
            },
        )
    result = case.intake_text(
        req.text, req.input_type, req.search_depth, region=req.region,
    )
    store.save(case)
    return result


class IntakeOverrideRequest(BaseModel):
    chosen_type: str  # manuscript | article | abstract | bibliography
                      # | journal_or_venue | review_letter | field_notes
                      # | mixed | unknown


@app.post("/cases/{case_id}/intake/override")
def intake_override(req: IntakeOverrideRequest, case: Case = Depends(_user_case)):
    """Operator picks a different input_type than the classifier did
    (or confirms an ambiguous one) and reruns the pipeline. The original
    classifier verdict is preserved on the case for audit; the pipeline
    runs on the user's chosen type."""
    if not case.input_text:
        raise HTTPException(
            400, "No text on this case yet — call /intake/text first.",
        )
    try:
        result = case.apply_input_override(req.chosen_type)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    store.save(case)
    return result


_SUPPORTED_UPLOAD_EXTENSIONS = {
    ".pdf", ".docx", ".doc", ".txt", ".md",
    ".html", ".htm", ".rtf", ".json",
}


@app.post("/cases/{case_id}/intake/file")
async def intake_file(
    file: UploadFile = File(...),
    input_type: str = Form("auto"),
    search_depth: str = Form("none"),
    region: str = Form("auto"),
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

    import tempfile, hashlib
    from datetime import datetime, timezone
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)
    original_size = len(content)
    content_hash_prefix = hashlib.sha256(content).hexdigest()[:16]
    uploaded_at = datetime.now(timezone.utc).isoformat()

    try:
        from .source_intake_util import extract_text_from_file

        text, extraction_status, errors = extract_text_from_file(tmp_path)
        if not text:
            raise HTTPException(
                400,
                f"Could not extract text from {filename}: "
                + "; ".join(errors or ["unknown error"]),
            )

        from ..llm.input_limits import INTAKE_HARD_CHAR_CAP
        if len(text) > INTAKE_HARD_CHAR_CAP:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "extracted_text_too_large",
                    "filename": filename,
                    "received_chars": len(text),
                    "max_chars": INTAKE_HARD_CHAR_CAP,
                    "message": (
                        f"Извлечённый текст слишком длинный "
                        f"({len(text)} символов). Максимум: "
                        f"{INTAKE_HARD_CHAR_CAP}. Загрузите фрагмент "
                        f"или сократите файл."
                    ),
                },
            )

        result = case.intake_text(text, input_type, search_depth, region=region)
        result["filename"] = filename
        result["extraction_status"] = extraction_status
        # Round III-H: persist upload metadata for human-dossier source
        # header and technical footer. No raw text is duplicated here —
        # only file-level structural facts and short hashes.
        text_hash_prefix = hashlib.sha256(
            text.encode("utf-8", errors="ignore"),
        ).hexdigest()[:16]
        case.upload_metadata = {
            "original_filename": filename,
            "original_extension": suffix.lstrip(".") or None,
            "upload_source_type": (suffix.lstrip(".") or "unknown"),
            "original_file_size_bytes": original_size,
            "content_hash_prefix": content_hash_prefix,
            "text_hash_prefix": text_hash_prefix,
            "uploaded_at": uploaded_at,
            "extraction_status": extraction_status,
            "text_char_count": len(text),
            "text_word_count": len(text.split()),
        }
        store.save(case)
        return result
    finally:
        tmp_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Venue Investigation
# ---------------------------------------------------------------------------

class InvestigateVenueRequest(BaseModel):
    text: str


class InvestigateVenueByReferenceRequest(BaseModel):
    issn: str | None = None
    name: str | None = None


@app.post("/cases/{case_id}/investigate-venue")
def investigate_venue(
    req: InvestigateVenueRequest, case: Case = Depends(_user_case),
):
    result = case.investigate_venue(req.text)
    store.save(case)
    return result


@app.post("/cases/{case_id}/investigate-venue-by-reference")
def investigate_venue_by_reference(
    req: InvestigateVenueByReferenceRequest,
    case: Case = Depends(_user_case),
):
    if not req.issn and not req.name:
        raise HTTPException(400, "Provide issn or name")
    result = case.investigate_venue_by_reference(
        issn=req.issn, name=req.name,
    )
    store.save(case)
    return result


class InvestigateVenueByUrlRequest(BaseModel):
    url: str


class SetAdapterModeRequest(BaseModel):
    mode: str


@app.post("/cases/{case_id}/investigate-venue-by-url")
def investigate_venue_by_url(
    req: InvestigateVenueByUrlRequest, case: Case = Depends(_user_case),
):
    result = case.investigate_venue_by_url(req.url)
    store.save(case)
    return result


@app.post("/cases/{case_id}/set-adapter-mode")
def set_adapter_mode(
    req: SetAdapterModeRequest, case: Case = Depends(_user_case),
):
    result = case.set_adapter_mode(req.mode)
    store.save(case)
    return result


@app.get("/cases/{case_id}/investigated-venue")
def get_investigated_venue(case: Case = Depends(_user_case)):
    if not case.investigated_venue:
        raise HTTPException(404, "No venue investigated yet")
    result: dict = {"venue": case.investigated_venue.to_dict()}
    if case.publication_regime:
        result["publication_regime"] = case.publication_regime.to_dict()
    return result


# ---------------------------------------------------------------------------
# Phase 2: Venue Enrichment & Profile Package
# ---------------------------------------------------------------------------

@app.post("/cases/{case_id}/enrich-venue")
def enrich_venue(case: Case = Depends(_user_case)):
    result = case.enrich_venue()
    store.save(case)
    return result


@app.get("/cases/{case_id}/venue-profile-package")
def get_venue_profile_package(case: Case = Depends(_user_case)):
    return case.get_venue_profile_package()


@app.get("/cases/{case_id}/compliance")
def get_compliance(case: Case = Depends(_user_case)):
    result = case.get_compliance()
    store.save(case)
    return result


@app.post("/cases/{case_id}/build-submission-pack")
def build_submission_pack_api(case: Case = Depends(_user_case)):
    result = case.build_submission_pack_api()
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Phase 3: Track A — Discipline to Venue Funnel
# ---------------------------------------------------------------------------

class SetDisciplineIntentRequest(BaseModel):
    text: str
    region: str = "auto"
    constraints: list[str] | None = None


@app.post("/cases/{case_id}/set-discipline-intent")
def set_discipline_intent(
    req: SetDisciplineIntentRequest, case: Case = Depends(_user_case),
):
    result = case.set_discipline_intent(
        text=req.text, region=req.region, constraints=req.constraints,
    )
    store.save(case)
    return result


@app.get("/cases/{case_id}/venue-matrix")
def get_venue_matrix(case: Case = Depends(_user_case)):
    return case.get_venue_matrix()


@app.get("/cases/{case_id}/venue-family-context")
def get_venue_family_context(case: Case = Depends(_user_case)):
    if not case.venue_family_context:
        raise HTTPException(404, "No venue family context available")
    return case.venue_family_context


# ---------------------------------------------------------------------------
# Article Model
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/article-model")
def get_article_model(case: Case = Depends(_user_case)):
    if not case.article_model:
        raise HTTPException(404, "Article model not built yet")
    return case.article_model.to_dict()


@app.get("/cases/{case_id}/discipline-matches")
def get_discipline_matches(case: Case = Depends(_user_case)):
    """Phase B2: discipline matcher verdict produced during intake.
    Returns 404 (not 200 with empty) when matcher hasn't run yet, so
    the UI can show a "matcher pending" state distinctly from an
    intentional "no matches found" state.
    """
    if not case.discipline_matches:
        raise HTTPException(404, "Discipline matcher has not run yet")
    return {
        "region_hint": case.region_hint,
        **case.discipline_matches,
    }


class RerunDisciplineRequest(BaseModel):
    comment: str | None = None


@app.post("/cases/{case_id}/discipline-matches/rerun")
def rerun_discipline_analysis(
    req: RerunDisciplineRequest, case: Case = Depends(_user_case),
):
    result = case.rerun_discipline_analysis(comment=req.comment)
    store.save(case)
    return {
        "region_hint": case.region_hint,
        **result,
    }


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


class RerunArticleModelRequest(BaseModel):
    comment: str | None = None


@app.post("/cases/{case_id}/article-model/rerun")
def rerun_article_model(
    req: RerunArticleModelRequest, case: Case = Depends(_user_case),
):
    if not case.article_model:
        raise HTTPException(400, "Article model not built yet")
    result = case.rerun_article_model(comment=req.comment)
    store.save(case)
    return result


# ---------------------------------------------------------------------------
# Source text (for text-evidence binding in the UI)
# ---------------------------------------------------------------------------


@app.get("/cases/{case_id}/source-text")
def get_source_text(case: Case = Depends(_user_case)):
    """Return the preserved article input text for text-evidence binding."""
    text = case.article_input_text or case.input_text or ""
    if not text:
        raise HTTPException(404, "No source text available on this case")
    return {"text": text, "char_count": len(text)}


# ---------------------------------------------------------------------------
# M-8: LLM refinement dialog
# ---------------------------------------------------------------------------


class RefineRequest(BaseModel):
    message: str


@app.post("/cases/{case_id}/article-model/refine")
def refine_article_model(
    req: RefineRequest, case: Case = Depends(_user_case),
):
    if not case.article_model:
        raise HTTPException(400, "Article model not built yet")
    result = case.refine_article_model(req.message)
    store.save(case)
    return result


@app.get("/cases/{case_id}/article-model/refinement-chat")
def get_refinement_chat(case: Case = Depends(_user_case)):
    return case.get_refinement_chat()


# ---------------------------------------------------------------------------
# M-9: PromptCorrectionSignal — pattern detection from corrections
# ---------------------------------------------------------------------------


@app.get("/correction-signals")
def get_correction_signals(min_occurrences: int = 3):
    """Analyze CorrectionRegistry for recurring patterns."""
    from .cases import CorrectionRegistry
    signals = CorrectionRegistry.analyze_signals(min_occurrences=min_occurrences)
    return {"signals": signals, "total": len(signals)}


# ---------------------------------------------------------------------------
# Human-readable model views (author-facing markdown)
# ---------------------------------------------------------------------------


@app.get(
    "/cases/{case_id}/article-model/human-view",
    response_class=JSONResponse,
)
def get_article_model_human_view(case: Case = Depends(_user_case)):
    """Return the author-facing prose review of the ArticleModel."""
    if not case.article_model:
        raise HTTPException(404, "Article model not built yet")
    from ..services.human_readable_card import article_model_human_view
    article = case.article_model.to_dict()
    pathways = [
        p.to_dict() if hasattr(p, "to_dict") else p
        for p in (case.pathways or [])
    ]
    # Surface semantic profile + fit assessment fallback warnings if
    # those layers carry extraction_attempt metadata. Optional fields.
    sem = case.semantic_profile.to_dict() if case.semantic_profile else None
    fit = case.fit_assessment.to_dict() if case.fit_assessment else None
    return {
        "format": "markdown",
        "case_id": case.case_id,
        "lifecycle_status": article.get("lifecycle_status", "preliminary"),
        "not_a_submission_recommendation": True,
        "markdown": article_model_human_view(
            article, pathways=pathways,
            semantic_profile=sem, fit_assessment=fit,
            discipline_matches=case.discipline_matches,
        ),
    }


@app.get("/cases/{case_id}/venues/{venue_key}/human-view")
def get_venue_human_view(
    venue_key: str, case: Case = Depends(_user_case),
):
    """Return the author-facing prose review of a venue / VPKG.

    `venue_key` matches either:
      - the case's currently `investigated_venue` (use literal
        "investigated");
      - or a `canonical_name` of a candidate in `case.venue_pool`;
      - or a venue_model_id / venue_candidate_id present on the case.
    """
    from ..services.human_readable_card import venue_human_view

    venue_dict: dict | None = None
    if venue_key == "investigated":
        if case.investigated_venue is None:
            raise HTTPException(404, "No investigated venue on this case yet")
        venue_dict = case.investigated_venue.to_dict()
    else:
        pool = case.venue_pool
        if pool is not None and hasattr(pool, "candidates"):
            for cand in pool.candidates or []:
                cand_dict = cand.to_dict() if hasattr(cand, "to_dict") else cand
                if (
                    cand_dict.get("canonical_name") == venue_key
                    or cand_dict.get("venue_candidate_id") == venue_key
                    or cand_dict.get("venue_model_id") == venue_key
                    or cand_dict.get("venue_profile_package_id") == venue_key
                ):
                    venue_dict = cand_dict
                    break
        if venue_dict is None and case.investigated_venue is not None:
            iv = case.investigated_venue.to_dict()
            if iv.get("canonical_name") == venue_key:
                venue_dict = iv
        if venue_dict is None and case.selected_venue is not None:
            sv = case.selected_venue.to_dict()
            if sv.get("canonical_name") == venue_key:
                venue_dict = sv

    if venue_dict is None:
        raise HTTPException(404, f"Venue {venue_key!r} not found on this case")

    return {
        "format": "markdown",
        "case_id": case.case_id,
        "venue_key": venue_key,
        "not_a_submission_recommendation": True,
        "markdown": venue_human_view(venue_dict),
    }


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
# Semantic hypotheses
# ---------------------------------------------------------------------------

@app.get("/cases/{case_id}/semantic-hypotheses")
def get_semantic_hypotheses(case: Case = Depends(_user_case)):
    return case.get_semantic_hypotheses()


@app.get("/cases/{case_id}/semantic-hypotheses/{axis}")
def get_semantic_hypothesis(axis: str, case: Case = Depends(_user_case)):
    hyp = case.get_semantic_hypothesis(axis)
    if hyp is None:
        raise HTTPException(404, f"No hypothesis for axis {axis}")
    return hyp


class AcceptHypothesisRequest(BaseModel):
    comment: str | None = None


@app.post("/cases/{case_id}/semantic-hypotheses/{axis}/accept")
def accept_semantic_hypothesis(
    axis: str, req: AcceptHypothesisRequest,
    case: Case = Depends(_user_case),
):
    result = case.accept_semantic_hypothesis(axis, comment=req.comment)
    store.save(case)
    return result


class DisputeHypothesisRequest(BaseModel):
    comment: str


@app.post("/cases/{case_id}/semantic-hypotheses/{axis}/dispute")
def dispute_semantic_hypothesis(
    axis: str, req: DisputeHypothesisRequest,
    case: Case = Depends(_user_case),
):
    result = case.dispute_semantic_hypothesis(axis, comment=req.comment)
    store.save(case)
    return result


class RerunHypothesisRequest(BaseModel):
    comment: str | None = None


@app.post("/cases/{case_id}/semantic-hypotheses/{axis}/rerun")
def rerun_semantic_hypothesis(
    axis: str, req: RerunHypothesisRequest,
    case: Case = Depends(_user_case),
):
    result = case.rerun_semantic_hypothesis(axis, comment=req.comment)
    store.save(case)
    return result


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
    result = case.build_dossier()
    store.save(case)
    return result


@app.get("/cases/{case_id}/human-dossier")
def get_human_dossier(case: Case = Depends(_user_case)):
    """Russian author-facing dossier built on top of build_dossier().

    Pure presentation layer: no LLM, no network, no new claims.
    """
    from kairoskopion.services.human_dossier import build_human_dossier
    result = build_human_dossier(case.build_dossier()).to_dict()
    store.save(case)
    return result


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
        has_real_llm = spec.execution_mode in ("llm_optional", "llm_required")
        d["has_real_llm"] = has_real_llm
        d["has_orphaned_prompt"] = False
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
# Phase 4: VenueMemory
# ---------------------------------------------------------------------------

@app.get("/venue-memory")
def list_venue_memory():
    return [r.to_dict() for r in venue_memory_registry.list_all()]


@app.get("/venue-memory/{venue_memory_id}")
def get_venue_memory(venue_memory_id: str):
    rec = venue_memory_registry.get(venue_memory_id)
    if not rec:
        raise HTTPException(404, "Venue memory not found")
    return rec.to_dict()


class VenueMemoryNoteRequest(BaseModel):
    text: str


@app.post("/venue-memory/{venue_memory_id}/note")
def add_venue_memory_note(
    venue_memory_id: str, req: VenueMemoryNoteRequest,
):
    rec = venue_memory_registry.add_note(venue_memory_id, req.text)
    if not rec:
        raise HTTPException(404, "Venue memory not found")
    return rec.to_dict()


class VenueMemoryOutcomeRequest(BaseModel):
    result: str
    notes: str = ""


@app.post("/venue-memory/{venue_memory_id}/outcome")
def add_venue_memory_outcome(
    venue_memory_id: str, req: VenueMemoryOutcomeRequest,
):
    rec = venue_memory_registry.add_outcome(
        venue_memory_id,
        {"result": req.result, "notes": req.notes},
    )
    if not rec:
        raise HTTPException(404, "Venue memory not found")
    return rec.to_dict()


class VenueMemoryReviewRequest(BaseModel):
    status: str


@app.post("/venue-memory/{venue_memory_id}/review")
def review_venue_memory(
    venue_memory_id: str, req: VenueMemoryReviewRequest,
):
    rec = venue_memory_registry.set_review_status(venue_memory_id, req.status)
    if not rec:
        raise HTTPException(
            400 if venue_memory_id in {r.venue_memory_id for r in venue_memory_registry.list_all()} else 404,
            "Invalid status or venue memory not found",
        )
    return rec.to_dict()


# ---------------------------------------------------------------------------
# Phase 5: Depth / budget controls
# ---------------------------------------------------------------------------

class SetDepthModeRequest(BaseModel):
    mode: str


@app.post("/cases/{case_id}/set-depth-mode")
def set_depth_mode(req: SetDepthModeRequest, case: Case = Depends(_user_case)):
    result = case.set_depth_mode(req.mode)
    store.save(case)
    return result


class SetBudgetRequest(BaseModel):
    max_api_calls: int | None = None
    max_tokens: int | None = None


@app.post("/cases/{case_id}/set-budget")
def set_budget(req: SetBudgetRequest, case: Case = Depends(_user_case)):
    result = case.set_budget_constraints(
        max_api_calls=req.max_api_calls, max_tokens=req.max_tokens,
    )
    store.save(case)
    return result


@app.get("/cases/{case_id}/cost-estimate")
def get_cost_estimate(case: Case = Depends(_user_case)):
    return case.get_cost_estimate()


# ---------------------------------------------------------------------------
# Static frontend (SPA) — serves built UI if dist/ exists
# ---------------------------------------------------------------------------

# -- P6 registry router ------------------------------------------------
from .registry_router import router as _registry_router
app.include_router(_registry_router)

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
