"""Round III-B: source-backed Russian-philosophy academic writing rubric.

Loads the rubric JSON from ``data/rubrics/`` and exposes it as a
prompt-side context that LLM semantic organs (RiskOfficer /
RewritePlanner / CitationPlanner) can include in their prompts.

Hard rules enforced by this module:
  - Rubric MUST NOT be used by deterministic code to author semantic
    claims. This module only loads and formats; it never decides that
    an article lacks a thesis / a problem / a method.
  - Rubric MUST NOT be treated as venue evidence. The loaded object's
    ``not_a_venue_profile`` and ``not_journal_policy`` flags are
    asserted at load time.
  - When the rubric is applied to an LLM organ, the output's
    ``created_from`` list gets ``rubric_source=<rubric_id>`` appended
    so the operator can trace which fields are rubric-informed.
"""

from __future__ import annotations

import functools
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Default rubric file relative to repo root
_DEFAULT_RUBRIC_PATH = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "data" / "rubrics"
    / "russian_philosophy_academic_writing_rubric_v0_1.json"
)

# Allowed applicability tokens for selecting the rubric per article
APPLICABILITY_RU_PHIL = "russian_language_philosophical_papers"


@functools.lru_cache(maxsize=4)
def load_rubric(path: str | None = None) -> dict[str, Any] | None:
    """Load the rubric JSON. Returns None if the file is missing.

    Asserts the rubric is marked as NOT venue evidence at load time.
    Cached because the file is small and immutable per build.
    """
    p = Path(path) if path else _DEFAULT_RUBRIC_PATH
    if not p.exists():
        logger.info("Rubric not found at %s", p)
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("Rubric load failed: %s", exc)
        return None

    if not data.get("not_a_venue_profile") or not data.get("not_journal_policy"):
        # Refuse to load anything that claims to be venue evidence.
        logger.error(
            "Rubric refused to load: not_a_venue_profile / "
            "not_journal_policy flag missing or false; doctrine "
            "forbids rubric being treated as venue policy.",
        )
        return None
    return data


def rubric_id() -> str | None:
    r = load_rubric()
    return r.get("rubric_id") if r else None


def _cyrillic_ratio(text: str | None) -> float:
    """Structural language hint — share of Cyrillic letters in the
    supplied raw text. Pure mechanical extraction, not semantic.
    """
    if not text:
        return 0.0
    cyr = 0
    letters = 0
    for ch in text:
        if ch.isalpha():
            letters += 1
            if "Ѐ" <= ch <= "ӿ":
                cyr += 1
    return (cyr / letters) if letters else 0.0


def _article_concat_for_cyrillic_probe(article: Any) -> str:
    """Concatenate text fields from ArticleModel for structural
    Cyrillic-ratio detection. No semantic interpretation.
    """
    parts: list[str] = []
    for f in (
        "title_current", "abstract_current",
        "problem_statement", "research_question", "object_of_inquiry",
        "method_description", "citation_ecology_current",
    ):
        v = getattr(article, f, None)
        if isinstance(v, str):
            parts.append(v)
    for f in ("core_claims", "theoretical_shoulders",
              "protected_core", "mutable_zones"):
        v = getattr(article, f, None)
        if isinstance(v, list):
            for x in v:
                if isinstance(x, str):
                    parts.append(x)
    return " ".join(parts)


def rubric_applies_to_article(
    article: Any, raw_article_text: str | None = None,
) -> bool:
    """Round III-E: structural gate.

    Rubric applies when (a) article language is explicitly Russian, OR
    (b) the supplied raw text is predominantly Cyrillic (≥30% of
    alphabetic chars), OR (c) the concatenated ArticleModel text
    fields are predominantly Cyrillic. AND (d) the genre/register has
    any philosophical/humanities marker OR is unknown (rubric still
    safe as academic-writing context for philosophical humanities).

    Deterministic structural gate — selection, not semantic claim.
    """
    if article is None:
        return False
    lang = (getattr(article, "language", "") or "").lower()
    fallback_text = (
        raw_article_text if raw_article_text
        else _article_concat_for_cyrillic_probe(article)
    )
    is_ru = (
        lang.startswith("ru")
        or "russ" in lang
        or _cyrillic_ratio(fallback_text) >= 0.30
    )
    if not is_ru:
        return False
    genre = (getattr(article, "genre_current", "") or "").lower()
    register = getattr(article, "disciplinary_register_current", "") or ""
    if isinstance(register, list):
        register = " ".join(register)
    register = (register or "").lower()
    phil_markers = (
        "philosophy", "философ", "philosoph", "phenomenolog", "феномено",
        "postphenomen", "постфеномено", "ethics", "этик",
        "humanit", "гуманитар",
    )
    is_phil = any(m in genre or m in register for m in phil_markers)
    # If Russian + unknown OR humanities-leaning genre, still apply
    # the rubric — it is a general academic-writing-quality rubric for
    # the philosophical humanities. Doctrine intact: not venue policy.
    _phil_friendly_genres = (
        "", "unknown",
        "theoretical_essay", "theoretical",
        "conceptual_article", "conceptual",
        "essay", "humanities", "humanity",
        "review_article", "systematic_review",
    )
    return bool(is_phil) or (is_ru and (genre in _phil_friendly_genres))


def render_prompt_block(rubric: dict[str, Any] | None = None) -> str:
    """Format the rubric as a compact prompt-side context block.

    The block is preceded by an explicit marker so the LLM and any
    downstream reader can see this is a RUBRIC, not venue policy.
    Returns "" when the rubric is unavailable.
    """
    r = rubric if rubric is not None else load_rubric()
    if r is None:
        return ""
    lines: list[str] = [
        "## Russian-philosophy academic-writing rubric (CONTEXT ONLY — NOT venue policy)",
        f"rubric_id: {r.get('rubric_id')}",
        f"source: {r.get('source_file')} (status={r.get('source_status')})",
        "Doctrine: this rubric is a source-backed manuscript-writing rubric. "
        "It is NOT the target venue's submission policy. It is NOT "
        "`Вопросы философии` policy. Apply it ONLY as background "
        "academic-writing quality context, NOT as venue evidence. "
        "Tag any rubric-informed claim with origin=llm, "
        "rubric_source=" + str(r.get("rubric_id")) + ".",
        "",
    ]
    for cat in r.get("categories") or []:
        lines.append(f"### {cat.get('name')} ({cat.get('category_id')})")
        for it in cat.get("items") or []:
            lines.append(f"- {it.get('key')}: {it.get('summary')}")
        lines.append("")
    return "\n".join(lines)


def appended_created_from(existing: list[str] | None) -> list[str]:
    """Return a new created_from list with rubric_source appended."""
    rid = rubric_id()
    base = list(existing or [])
    if rid is None:
        return base
    tag = f"rubric_source={rid}"
    if tag not in base:
        base.append(tag)
    return base
