"""WhiteCrow integration stubs (spec Wave 3 §14).

These are interface/stub dataclasses representing WhiteCrow objects that
Kairoskopion receives from or sends to the field/manuscript layer.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..enums import FieldCoreImpact
from ..schema import _DictMixin, _field, _list, _now


@dc.dataclass
class FieldModelReference(_DictMixin):
    """Projection of WhiteCrow field data relevant for publication positioning."""
    field_ref_id: str = ""
    whitecrow_field_id: str | None = _field()
    field_text_refs: list[str] = _list()
    context_pack_refs: list[str] = _list()
    field_summary: str | None = _field()
    central_tensions: list[str] = _list()
    protected_core: list[str] = _list()
    possible_article_trajectories: list[str] = _list()
    source_refs: list[str] = _list()
    confidence: str | None = _field()
    unknowns: list[str] = _list()


@dc.dataclass
class ProtectedCore(_DictMixin):
    """Semantic elements that cannot be changed without user acceptance."""
    central_thesis: str | None = _field()
    object_of_inquiry: str | None = _field()
    key_distinctions: list[str] = _list()
    methodological_stance: str | None = _field()
    philosophical_commitments: list[str] = _list()
    authorial_voice: str | None = _field()
    conceptual_vocabulary: list[str] = _list()
    non_negotiable_claims: list[str] = _list()
    do_not_flatten_constraints: list[str] = _list()


@dc.dataclass
class PatchCandidate(_DictMixin):
    """Proposed change from Kairoskopion to WhiteCrow manuscript."""
    patch_id: str = ""
    source_plan_id: str | None = _field()
    target_document_ref: str | None = _field()
    target_block_or_section: str | None = _field()
    change_summary: str | None = _field()
    change_type: str | None = _field()
    reason: str | None = _field()
    evidence_refs: list[str] = _list()
    related_mismatch_id: str | None = _field()
    field_core_impact: str = FieldCoreImpact.UNKNOWN_CORE_IMPACT.value
    estimated_effort: str | None = _field()
    status: str = "proposed"
    user_decision: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class ExternalDocAction(_DictMixin):
    """Structured action to send to an external document (Google Docs, DOCX)."""
    action_id: str = ""
    action_type: str | None = _field()
    target_document_ref: str | None = _field()
    target_location: str | None = _field()
    content: str | None = _field()
    reason: str | None = _field()
    source_plan_id: str | None = _field()
    status: str = "pending"
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class WhiteCrowManuscriptRef(_DictMixin):
    """Pointer to a WhiteCrow manuscript."""
    manuscript_ref_id: str = ""
    whitecrow_manuscript_id: str | None = _field()
    title: str | None = _field()
    version: int | None = _field()
    notes: str | None = _field()


@dc.dataclass
class WhiteCrowArticleTrajectoryRef(_DictMixin):
    """Pointer to a WhiteCrow article trajectory."""
    trajectory_ref_id: str = ""
    whitecrow_trajectory_id: str | None = _field()
    description: str | None = _field()
    target_disciplines: list[str] = _list()
    notes: str | None = _field()
