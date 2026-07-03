"""Prompt Override and Correction models (Track 6).

Allows the operator to create per-case prompt overrides that replace
or augment the default system/user prompts for any prompt family.
Also supports correction candidates (post-hoc feedback on pipeline output).
"""
from __future__ import annotations

import dataclasses as dc
import json
from pathlib import Path
from typing import Any

from ..ids import generate_id


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


@dc.dataclass
class PromptOverride:
    override_id: str = dc.field(default_factory=lambda: generate_id("povr"))
    case_id: str = ""
    base_prompt_family_id: str = ""
    base_prompt_version_hash: str = ""
    scope: str = "case"
    status: str = "draft"
    edited_system_prompt: str | None = None
    edited_user_template: str | None = None
    notes: str = ""
    created_at: str = dc.field(default_factory=_now)
    created_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dc.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptOverride:
        valid = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


@dc.dataclass
class PromptPatchCandidate:
    candidate_id: str = dc.field(default_factory=lambda: generate_id("ppatch"))
    case_id: str = ""
    node_id: str = ""
    correction_type: str = ""
    user_note: str = ""
    affected_prompt_family_id: str = ""
    proposed_change: str | None = None
    status: str = "pending_review"
    created_at: str = dc.field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in dc.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptPatchCandidate:
        valid = {f.name for f in dc.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in valid})


class PromptOverrideStore:
    """In-memory + JSONL store for prompt overrides and corrections."""

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir
        self._overrides: dict[str, PromptOverride] = {}
        self._corrections: dict[str, PromptPatchCandidate] = {}
        if data_dir:
            data_dir.mkdir(parents=True, exist_ok=True)
            self._load()

    def _load(self) -> None:
        if not self._data_dir:
            return
        ovr_path = self._data_dir / "prompt_overrides.jsonl"
        if ovr_path.exists():
            for line in ovr_path.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                obj = PromptOverride.from_dict(json.loads(line))
                self._overrides[obj.override_id] = obj
        cor_path = self._data_dir / "prompt_corrections.jsonl"
        if cor_path.exists():
            for line in cor_path.read_text(encoding="utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                obj = PromptPatchCandidate.from_dict(json.loads(line))
                self._corrections[obj.candidate_id] = obj

    def _persist(self, record: Any, filename: str) -> None:
        if not self._data_dir:
            return
        path = self._data_dir / filename
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    # -- overrides ----------------------------------------------------------

    def save_override(self, ovr: PromptOverride) -> PromptOverride:
        self._overrides[ovr.override_id] = ovr
        self._persist(ovr, "prompt_overrides.jsonl")
        return ovr

    def get_override(self, override_id: str) -> PromptOverride | None:
        return self._overrides.get(override_id)

    def list_overrides(self, case_id: str) -> list[PromptOverride]:
        return [o for o in self._overrides.values() if o.case_id == case_id]

    def get_active_override(self, case_id: str, prompt_family_id: str) -> PromptOverride | None:
        for o in self._overrides.values():
            if o.case_id == case_id and o.base_prompt_family_id == prompt_family_id and o.status == "active":
                return o
        return None

    def update_status(self, override_id: str, status: str) -> PromptOverride | None:
        ovr = self._overrides.get(override_id)
        if ovr:
            ovr.status = status
        return ovr

    # -- corrections --------------------------------------------------------

    def save_correction(self, corr: PromptPatchCandidate) -> PromptPatchCandidate:
        self._corrections[corr.candidate_id] = corr
        self._persist(corr, "prompt_corrections.jsonl")
        return corr

    def list_corrections(self, case_id: str) -> list[PromptPatchCandidate]:
        return [c for c in self._corrections.values() if c.case_id == case_id]
