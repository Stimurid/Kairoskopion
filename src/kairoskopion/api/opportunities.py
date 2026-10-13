"""Authenticated read-only API for the independent publication opportunity front.

Per-user filesystem root. Does not expose external submission or accept an
unverified W12 XLSX upload. Internal writer/import adapter is a later gate.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from .auth import User, get_current_user, get_data_dir
from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..kairon_provider.opportunity_portfolio import build_portfolio
from ..kairon_provider.w12_private_runtime import W12AdmissionError, research_stage_projection


router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])

def _private_research_read_enabled() -> bool:
    """Default OFF while Kairoskopion uses staging soft-auth.

    Operator may enable only in an isolated staging environment after
    separately verifying identity and filesystem ACLs; never automatically
    expose owner-private source rows on a public soft-auth service.
    """
    return os.environ.get("KAIROSKOPION_W12_PRIVATE_STAGE_READ_ENABLED") == "1"



def _user_opportunity_root(user: User) -> Path:
    # Soft-auth users are generated with user_<12 hex>, never user-controlled
    # path elements or submitted email strings.
    if re.fullmatch(r"user_[a-f0-9]{12}", user.user_id) is None:
        raise HTTPException(status_code=403, detail="invalid user workspace id")
    return get_data_dir() / "users" / user.user_id


@router.get("/portfolio")
def get_opportunity_portfolio(current_user: User = Depends(get_current_user)):
    """Return evidence-grounded objects, not Indago's unimported W12 totals."""
    user_root = _user_opportunity_root(current_user)
    store = OpportunityGraphStore(user_root)
    result = build_portfolio(store)
    # A private staged research corpus is NOT an imported ArticleOpportunity.
    # Never self-certify source policies, full-text reads or author decisions.
    if _private_research_read_enabled():
        try:
            stage = research_stage_projection(user_root, limit=1)
        except W12AdmissionError as exc:
            raise HTTPException(status_code=503, detail="private W12 stage requires operator repair") from exc
    else:
        stage = {"status": "RUNTIME_IMPORT_PENDING", "rows": []}
    result["importStatus"] = stage["status"]
    result["importReceipt"] = stage.get("sourceSha256")
    result["researchStage"] = {
        key: value for key, value in stage.items() if key not in {"rows"}
    }
    return result


@router.get("/trace")
def get_opportunity_trace(current_user: User = Depends(get_current_user)):
    """Read negative hunt observations and decisions without mutating canon."""
    store = OpportunityGraphStore(_user_opportunity_root(current_user))
    return {"events": store.replay_events(), "external_submission": "FORBIDDEN"}


@router.get("/research-stage")
def get_private_w12_research_stage(
    offset: int = Query(default=0, ge=0, le=100_000),
    limit: int = Query(default=53, ge=1, le=100),
    current_user: User = Depends(get_current_user),
):
    """Owner-scoped, read-only research routes, never sendable submissions.

    No private source/author profile download endpoint; only bounded route
    summaries with pinned sheet/row hashes and explicit authority blockers.
    """
    if not _private_research_read_enabled():
        raise HTTPException(status_code=403, detail="private W12 research readback is disabled")
    try:
        return research_stage_projection(
            _user_opportunity_root(current_user), offset=offset, limit=limit
        )
    except W12AdmissionError as exc:
        raise HTTPException(
            status_code=503, detail="private W12 stage integrity requires operator repair"
        ) from exc
