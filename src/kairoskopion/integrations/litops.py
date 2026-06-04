"""Litops integration stubs (spec Wave 3 §13).

These are interface/stub dataclasses representing Litops objects that
Kairoskopion receives from or sends to the Litops source layer.
In standalone mode, Kairoskopion creates internal equivalents.
"""

from __future__ import annotations

import dataclasses as dc
from typing import Any

from ..schema import _DictMixin, _field, _list, _now


@dc.dataclass
class LitopsSourceRef(_DictMixin):
    """Pointer to a Litops Source."""
    source_id: str = ""
    source_type: str | None = _field()
    title: str | None = _field()
    url_or_path: str | None = _field()
    registered_at: str | None = _field()
    notes: str | None = _field()


@dc.dataclass
class LitopsContextPackRef(_DictMixin):
    """Pointer to a Litops ContextPack."""
    context_pack_id: str = ""
    context_pack_type: str | None = _field()
    scope: str | None = _field()
    source_ids: list[str] = _list()
    evidence_ids: list[str] = _list()
    created_at: str | None = _field()
    coverage_notes: str | None = _field()
    known_gaps: list[str] = _list()


@dc.dataclass
class LitopsArtifactRef(_DictMixin):
    """Pointer to a Litops Artifact produced by Kairoskopion."""
    artifact_id: str = ""
    artifact_type: str | None = _field()
    title: str | None = _field()
    source_entity_id: str | None = _field()
    file_ref: str | None = _field()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class LitopsVaultProjection(_DictMixin):
    """Vault card metadata for Litops integration."""
    vault_card_id: str = ""
    entity_type: str | None = _field()
    entity_id: str | None = _field()
    markdown_content: str | None = _field()
    source_refs: list[str] = _list()
    created_at: str = dc.field(default_factory=_now)


@dc.dataclass
class LitopsWorksetRef(_DictMixin):
    """Pointer to a Litops Workset."""
    workset_id: str = ""
    title: str | None = _field()
    source_ids: list[str] = _list()
    notes: str | None = _field()
