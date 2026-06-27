"""Prompt Registry — discovers and indexes all prompt families (Track 5).

Scans `src/kairoskopion/prompts/` at runtime, extracts system prompts,
user templates, schemas, and computes version hashes. Provides lookup
by prompt_family_id and version tracking.
"""
from __future__ import annotations

import hashlib
import importlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


@dataclass
class PromptFamilyInfo:
    prompt_family_id: str
    path: str
    source_module: str
    version_hash: str
    has_schema: bool = False
    schema_ref: str | None = None
    agent_ref: str | None = None
    description: str = ""
    system_prompt: str = ""
    user_template: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None and v != "" and v != []}

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> PromptFamilyInfo:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in valid})


# Well-known variable name patterns in prompt modules
_SYSTEM_PATTERNS = [
    re.compile(r"^([A-Z_]+_SYSTEM)\s*=", re.MULTILINE),
    re.compile(r"^(SYSTEM_PROMPT)\s*=", re.MULTILINE),
]

_USER_PATTERNS = [
    re.compile(r"^([A-Z_]+_USER)\s*=", re.MULTILINE),
    re.compile(r"^([A-Z_]+_USER_TEMPLATE)\s*=", re.MULTILINE),
    re.compile(r"^(USER_PROMPT)\s*=", re.MULTILINE),
]

_SCHEMA_PATTERNS = [
    re.compile(r"^([A-Z_]+_SCHEMA)\s*=", re.MULTILINE),
    re.compile(r"^([A-Z_]+_JSON_SCHEMA)\s*=", re.MULTILINE),
]

# Map prompt_family_id → agent class name
_AGENT_MAP: dict[str, str] = {
    "article_modeling": "ArticleModelerAgent",
    "venue_fact_extraction": "VenueProfilerAgent",
    "fit_assessment": "FitAssessorAgent",
    "semantic_profiling": "SemanticProfilerAgent",
    "input_classification": "InputClassifierAgent",
    "citation_ecology_analysis": "CitationEcologyAgent",
    "compliance_assessment": "ComplianceAssessorAgent",
    "disciplinary_mapping": "DisciplinaryMapperAgent",
    "discipline_intent_parsing": "DisciplineIntentParserAgent",
    "discipline_matching": "DisciplineMatcherAgent",
    "discipline_seeding": "DisciplineSeederAgent",
    "discipline_source_acquisition": "DisciplineSourceAcquisitionAgent",
    "depth_recommendation": "DepthRecommendationAgent",
    "field_positioning": "ArticleFieldPositionerAgent",
    "mismatch_narrative": "MismatchNarratorAgent",
    "rewrite_planning": "RewritePlanningService",
    "venue_family_context": "VenueFamilyContextBuilderAgent",
    "venue_funnel_planning": "VenueFunnelPlannerAgent",
    "venue_matrix_assessment": "VenueMatrixAssessorAgent",
}


class PromptRegistry:
    """Discovers and indexes prompt families from the prompts package."""

    def __init__(self, prompts_dir: Path | None = None):
        self._prompts_dir = prompts_dir or self._default_prompts_dir()
        self._families: dict[str, PromptFamilyInfo] = {}
        self._scan()

    @staticmethod
    def _default_prompts_dir() -> Path:
        return Path(__file__).parent.parent / "prompts"

    def _scan(self) -> None:
        if not self._prompts_dir.is_dir():
            return
        for py_file in sorted(self._prompts_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            family_id = py_file.stem
            source_text = py_file.read_text(encoding="utf-8")
            info = self._parse_prompt_module(family_id, py_file, source_text)
            self._families[family_id] = info

    def _parse_prompt_module(
        self, family_id: str, path: Path, source: str,
    ) -> PromptFamilyInfo:
        system_prompt = ""
        user_template = ""
        has_schema = False
        schema_ref = None

        for pat in _SYSTEM_PATTERNS:
            m = pat.search(source)
            if m:
                var_name = m.group(1)
                system_prompt = self._extract_string_var(source, var_name)
                break

        for pat in _USER_PATTERNS:
            m = pat.search(source)
            if m:
                var_name = m.group(1)
                user_template = self._extract_string_var(source, var_name)
                break

        for pat in _SCHEMA_PATTERNS:
            m = pat.search(source)
            if m:
                has_schema = True
                schema_ref = m.group(1)
                break

        version_text = system_prompt + user_template
        version_hash = _hash_text(version_text) if version_text else _hash_text(source)

        description = ""
        doc_match = re.match(r'^"""(.*?)"""', source, re.DOTALL)
        if doc_match:
            first_line = doc_match.group(1).strip().split("\n")[0]
            description = first_line

        return PromptFamilyInfo(
            prompt_family_id=family_id,
            path=str(path),
            source_module=f"kairoskopion.prompts.{family_id}",
            version_hash=version_hash,
            has_schema=has_schema,
            schema_ref=schema_ref,
            agent_ref=_AGENT_MAP.get(family_id),
            description=description,
            system_prompt=system_prompt,
            user_template=user_template,
        )

    @staticmethod
    def _extract_string_var(source: str, var_name: str) -> str:
        """Best-effort extraction of a top-level string assignment."""
        pattern = re.compile(
            rf'^{re.escape(var_name)}\s*=\s*(?:"""(.*?)"""|"(.*?)")',
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(source)
        if m:
            return (m.group(1) or m.group(2) or "").strip()

        pattern2 = re.compile(
            rf"^{re.escape(var_name)}\s*=\s*(?:'''(.*?)'''|'(.*?)')",
            re.MULTILINE | re.DOTALL,
        )
        m2 = pattern2.search(source)
        if m2:
            return (m2.group(1) or m2.group(2) or "").strip()

        # Backslash-continuation or concatenation — just return marker
        return f"<see {var_name} in source>"

    def get(self, family_id: str) -> PromptFamilyInfo | None:
        return self._families.get(family_id)

    def list_all(self) -> list[PromptFamilyInfo]:
        return list(self._families.values())

    def list_ids(self) -> list[str]:
        return list(self._families.keys())

    def get_version_hash(self, family_id: str) -> str | None:
        info = self._families.get(family_id)
        return info.version_hash if info else None
