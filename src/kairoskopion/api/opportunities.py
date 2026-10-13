"""Authenticated read-only API for the independent publication opportunity front.

Per-user filesystem root. Does not expose external submission or accept an
unverified W12 XLSX upload. Internal writer/import adapter is a later gate.
"""
from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from .auth import User, get_current_user, get_data_dir
from ..kairon_provider.opportunity_graph import OpportunityGraphStore
from ..kairon_provider.opportunity_portfolio import build_portfolio


router = APIRouter(prefix="/api/opportunities", tags=["opportunities"])


def _user_opportunity_root(user: User) -> Path:
    # Soft-auth users are generated with user_<12 hex>, never user-controlled
    # path elements or submitted email strings.
    if re.fullmatch(r"user_[a-f0-9]{12}", user.user_id) is None:
        raise HTTPException(status_code=403, detail="invalid user workspace id")
    return get_data_dir() / "users" / user.user_id


@router.get("/portfolio")
def get_opportunity_portfolio(current_user: User = Depends(get_current_user)):
    """Return evidence-grounded objects, not Indago's unimported W12 totals."""
    store = OpportunityGraphStore(_user_opportunity_root(current_user))
    return build_portfolio(store)


@router.get("/trace")
def get_opportunity_trace(current_user: User = Depends(get_current_user)):
    """Read negative hunt observations and decisions without mutating canon."""
    store = OpportunityGraphStore(_user_opportunity_root(current_user))
    return {"events": store.replay_events(), "external_submission": "FORBIDDEN"}
