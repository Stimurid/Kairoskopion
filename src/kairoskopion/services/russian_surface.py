"""Round III-J3: Russian surface narrator.

Translate / paraphrase upstream English semantic fields into Russian so
the author-facing human dossier reads as real Russian — not as honest
stubs and not as `(англ.) «…»` wrappers.

Hard constraints (Track A/B/C):

  - The narrator is a TRANSLATION layer only. Input = field name +
    field value + section context. Output = Russian text that has the
    same factual content as the input.
  - No new facts. No new sources. No new author-year refs. No new
    DOIs. No venue claims that weren't already in the input.
  - The narrator is NEVER asked to analyse the article, plan citations,
    propose a fit, draft a rewrite, or diagnose risks. Those are the
    upstream organs' jobs and they ran already.
  - Raw LLM output is not stored on the author surface. Diagnostics
    (provider_status, parse_status, content_length, hash_prefix) live
    in the technical footer.
  - Uses the existing LLM routing seam via ``try_llm_call_with_outcome``
    + ``_get_llm_provider``. No local model / env / temperature tuning.

Cache discipline (Track D):

  - Result cache key = sha256(field_path + value + prompt_version) [:16].
  - Cache lives on the Case as ``case.russian_surface_cache``.
  - Renderer reads from cache; only the population pass calls the LLM.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


PROMPT_VERSION = "v1"


# --------------------------------------------------------------------------
# Result envelope
# --------------------------------------------------------------------------

@dataclass
class RussianSurfaceResult:
    text_ru: str
    source_language_detected: str  # "ru" | "en" | "mixed" | "unknown"
    method: str  # already_russian | deterministic_label_map |
                 # llm_surface_translation | safe_fallback
    added_facts_claim: bool = False
    raw_output_exposed: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text_ru": self.text_ru,
            "source_language_detected": self.source_language_detected,
            "method": self.method,
            "added_facts_claim": self.added_facts_claim,
            "raw_output_exposed": self.raw_output_exposed,
            "diagnostics": dict(self.diagnostics),
        }


# --------------------------------------------------------------------------
# Language detection + safe stub
# --------------------------------------------------------------------------

def _cyrillic_ratio(text: str) -> float:
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


def needs_russian_surface(value: Any) -> bool:
    """True iff a value carries English semantic content that needs to
    be surfaced as Russian. Numbers / dicts / lists fall through to
    other helpers; this is for plain strings.
    """
    if not isinstance(value, str):
        return False
    s = value.strip()
    if not s or len(s) < 8:
        return False
    return _cyrillic_ratio(s) < 0.30


def _safe_fallback_stub(field_label_ru: str) -> str:
    return (
        f"{field_label_ru}: формулировка модели — англоязычная; "
        "русский авторский перенос не построен."
    )


# --------------------------------------------------------------------------
# Cache layer (on the Case)
# --------------------------------------------------------------------------

def cache_key(field_path: str, value: str) -> str:
    h = hashlib.sha256(
        f"{PROMPT_VERSION}::{field_path}::{value}".encode("utf-8")
    ).hexdigest()
    return h[:24]


def cache_get(cache: dict[str, Any] | None, field_path: str, value: str) -> str | None:
    if not isinstance(cache, dict):
        return None
    entry = cache.get(cache_key(field_path, value))
    if isinstance(entry, dict):
        return entry.get("text_ru")
    if isinstance(entry, str):
        return entry
    return None


# --------------------------------------------------------------------------
# Anti-fake filters (Track C validation)
# --------------------------------------------------------------------------

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"']+")
_AUTHOR_YEAR_RE = re.compile(
    r"\b[A-ZА-ЯЁ][A-Za-zА-Яа-яёЁ\-]{2,}\s*(?:\(|, )(?:19|20)\d{2}\b"
)
_FENCED_JSON_RE = re.compile(r"```")


def _strip_dois(text: str) -> tuple[str, int]:
    n = 0

    def _sub(_m: re.Match) -> str:
        nonlocal n
        n += 1
        return ""

    return _DOI_RE.sub(_sub, text).strip(), n


def _detect_invented_author_years(original: str, translated: str) -> int:
    """Count author-year patterns in translated that were not in the original."""
    orig_years = set(_AUTHOR_YEAR_RE.findall(original))
    new = [m for m in _AUTHOR_YEAR_RE.findall(translated) if m not in orig_years]
    return len(new)


def _validate_translation(
    original: str, translated: str,
) -> tuple[bool, dict[str, Any]]:
    """Validate a single field translation.

    Pass criteria:
      - text_ru non-empty
      - Cyrillic-dominant (≥0.45)
      - No bare DOI not in original
      - No invented author-year patterns
      - No JSON fences leaking through
      - Length within 4× original (loose to allow honest expansion)
    """
    diag: dict[str, Any] = {}
    if not translated or not translated.strip():
        return False, {"reason": "empty_translation"}
    cyr = _cyrillic_ratio(translated)
    diag["cyrillic_ratio"] = round(cyr, 3)
    if cyr < 0.45:
        return False, {**diag, "reason": "not_russian_dominant"}
    orig_dois = set(_DOI_RE.findall(original))
    new_dois = [d for d in _DOI_RE.findall(translated) if d not in orig_dois]
    if new_dois:
        return False, {**diag, "reason": "invented_doi", "count": len(new_dois)}
    invented_ay = _detect_invented_author_years(original, translated)
    diag["invented_author_year_count"] = invented_ay
    if invented_ay > 1:
        return False, {**diag, "reason": "invented_author_year"}
    if _FENCED_JSON_RE.search(translated):
        return False, {**diag, "reason": "json_fence_leak"}
    if len(translated) > max(120, 4 * len(original)):
        return False, {**diag, "reason": "length_runaway"}
    return True, diag


# --------------------------------------------------------------------------
# Prompt family (per Round III-G outcome-envelope contract)
# --------------------------------------------------------------------------

_SYSTEM_PROMPT = (
    "You are a Russian-language editorial assistant. Your ONLY job is "
    "to translate or lightly rephrase upstream model fields from "
    "English into clear, natural Russian academic prose. You MUST NOT "
    "add new facts, new sources, new author-year citations, new DOIs, "
    "new venue claims, new analytical conclusions, or any content not "
    "already present in the input value. Preserve author names, work "
    "titles, and acronyms (AI, STS, DOI, LLM, API) verbatim. Keep "
    "uncertainty markers when they exist in the input. Output strict "
    "JSON only — no prose around it."
)

_USER_TEMPLATE = (
    "Translate each field below into Russian for an author-facing "
    "dossier. Return STRICT JSON with this shape:\n"
    "{{\"items\": [{{\"id\": \"<id>\", \"text_ru\": \"<russian>\", "
    "\"confidence\": \"high|medium|low\"}}, ...]}}\n"
    "Rules:\n"
    "- text_ru must be Russian; preserve names/acronyms verbatim.\n"
    "- Do NOT add facts, sources, DOIs, author-year refs, venue "
    "claims, or any content not in the value.\n"
    "- Keep the meaning faithful — this is a translation pass, not "
    "rewriting.\n\n"
    "Fields:\n{items_json}\n"
)

_FAMILY = {
    "agent_role_id": "russian_surface_narrator",
    "system_prompt": _SYSTEM_PROMPT,
    "user_prompt_template": _USER_TEMPLATE,
    "output_schema": {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "text_ru": {"type": "string"},
                        "confidence": {"type": "string"},
                    },
                    "required": ["id", "text_ru"],
                    "additionalProperties": True,
                },
            },
        },
        "required": ["items"],
        "additionalProperties": True,
    },
}


# --------------------------------------------------------------------------
# Single-field API (used by population pass)
# --------------------------------------------------------------------------

def _strip_meta(text: str) -> str:
    text, _ = _strip_dois(text)
    return text.strip()


def russianize_fields_batch(
    provider: Any,
    items: list[dict[str, str]],
    *,
    cache: dict[str, Any] | None = None,
) -> dict[str, RussianSurfaceResult]:
    """Translate a batch of fields. ``items`` is a list of dicts with
    keys ``id``, ``field``, ``value``. Returns a dict {id: result}.

    Cache lookup happens BEFORE batching. The provider call only sends
    cache misses. The returned dict contains entries for every input id
    — both cache hits and fresh translations.
    """
    out: dict[str, RussianSurfaceResult] = {}
    miss_items: list[dict[str, str]] = []
    for it in items:
        v = it.get("value") or ""
        field_path = it.get("field") or ""
        if not v.strip():
            continue
        if not needs_russian_surface(v):
            out[it["id"]] = RussianSurfaceResult(
                text_ru=v.strip(),
                source_language_detected=(
                    "ru" if _cyrillic_ratio(v) >= 0.30 else "mixed"
                ),
                method="already_russian",
            )
            continue
        cached = cache_get(cache, field_path, v)
        if cached:
            out[it["id"]] = RussianSurfaceResult(
                text_ru=cached,
                source_language_detected="en",
                method="llm_surface_translation",
                diagnostics={"cache": "hit"},
            )
            continue
        miss_items.append(it)

    if not miss_items:
        return out

    if provider is None:
        for it in miss_items:
            out[it["id"]] = RussianSurfaceResult(
                text_ru=_safe_fallback_stub(it.get("field") or "Поле"),
                source_language_detected="en",
                method="safe_fallback",
                diagnostics={"reason": "provider_unavailable"},
            )
        return out

    from ..agents.base_shell import try_llm_call_with_outcome

    items_payload = json.dumps(
        [
            {
                "id": it["id"],
                "field": it.get("field", ""),
                "value": _strip_meta(it["value"]),
            }
            for it in miss_items
        ],
        ensure_ascii=False, indent=2,
    )
    outcome = try_llm_call_with_outcome(
        provider, _FAMILY, {"items_json": items_payload},
        temperature=0.2, max_tokens=4096,
        agent_role="russian_surface_narrator",
        model_role="russian_surface_narrator",
    )

    parsed = outcome.parsed or outcome.loose_parsed
    if not isinstance(parsed, dict):
        for it in miss_items:
            out[it["id"]] = RussianSurfaceResult(
                text_ru=_safe_fallback_stub(it.get("field") or "Поле"),
                source_language_detected="en",
                method="safe_fallback",
                diagnostics={
                    "reason": "llm_parse_failed",
                    "provider_status": outcome.provider_status,
                    "parse_status": outcome.parse_status,
                    "content_length": outcome.content_length,
                    "content_hash_prefix": outcome.content_hash_prefix,
                },
            )
        return out

    items_out = parsed.get("items") if isinstance(parsed.get("items"), list) else []
    by_id: dict[str, dict] = {
        i.get("id"): i for i in items_out if isinstance(i, dict)
    }

    for it in miss_items:
        item_id = it["id"]
        translated_entry = by_id.get(item_id) or {}
        text_ru = (translated_entry.get("text_ru") or "").strip()
        text_ru = _strip_meta(text_ru)
        ok, diag = _validate_translation(it["value"], text_ru)
        if ok:
            result = RussianSurfaceResult(
                text_ru=text_ru,
                source_language_detected="en",
                method="llm_surface_translation",
                diagnostics={
                    **diag,
                    "confidence": translated_entry.get("confidence"),
                    "content_length": outcome.content_length,
                    "content_hash_prefix": outcome.content_hash_prefix,
                    "cache": "miss_written",
                },
            )
            if isinstance(cache, dict):
                cache[cache_key(it.get("field") or "", it["value"])] = {
                    "text_ru": text_ru,
                    "prompt_version": PROMPT_VERSION,
                }
        else:
            result = RussianSurfaceResult(
                text_ru=_safe_fallback_stub(it.get("field") or "Поле"),
                source_language_detected="en",
                method="safe_fallback",
                diagnostics={
                    "reason": diag.get("reason"),
                    "validation_diag": diag,
                    "content_hash_prefix": outcome.content_hash_prefix,
                    "content_length": outcome.content_length,
                },
            )
        out[item_id] = result
    return out


# --------------------------------------------------------------------------
# Field collection — what we translate per case
# --------------------------------------------------------------------------

def collect_translation_items(dossier: dict[str, Any]) -> list[dict[str, str]]:
    """Walk a dossier dict and return the list of {id, field, value}
    triples whose values are predominantly English. Stable ids let the
    cache survive re-runs.
    """
    items: list[dict[str, str]] = []

    def add(field_path: str, value: Any) -> None:
        if not isinstance(value, str):
            return
        if not value.strip():
            return
        if not needs_russian_surface(value):
            return
        items.append({
            "id": cache_key(field_path, value),
            "field": field_path,
            "value": value.strip(),
        })

    def add_list(field_path: str, values: Any) -> None:
        if not isinstance(values, list):
            return
        for idx, v in enumerate(values):
            if isinstance(v, str):
                add(f"{field_path}[{idx}]", v)
            elif isinstance(v, dict):
                # Pull text-y inner values
                for k in (
                    "tradition", "school", "scholar", "author", "name",
                    "title", "label",
                    "debt", "contribution", "evidence",
                    "summary", "requirement",
                ):
                    inner = v.get(k)
                    if isinstance(inner, str) and inner.strip():
                        add(f"{field_path}[{idx}].{k}", inner)

    am = dossier.get("article_model") or {}
    for k in ("problem_statement", "research_question", "object_of_inquiry",
              "method_description"):
        add(f"article_model.{k}", am.get(k))
    add_list("article_model.core_claims", am.get("core_claims"))
    add_list("article_model.protected_core", am.get("protected_core"))
    add_list("article_model.mutable_zones", am.get("mutable_zones"))
    add_list("article_model.unknowns", am.get("unknowns"))

    sp = dossier.get("semantic_profile") or {}
    add_list("semantic_profile.schools_and_traditions",
             sp.get("schools_and_traditions"))
    add_list("semantic_profile.theoretical_shoulders",
             sp.get("theoretical_shoulders"))
    add_list("semantic_profile.opponents_or_foils",
             sp.get("opponents_or_foils"))
    add_list("semantic_profile.citation_bridges_needed",
             sp.get("citation_bridges_needed"))
    add(f"semantic_profile.argument_move_description",
        sp.get("argument_move_description"))

    mm = (dossier.get("mismatch_map") or {}).get("mismatches") or []
    for i, m in enumerate(mm):
        if not isinstance(m, dict):
            continue
        for k in ("article_side", "venue_side", "description"):
            add(f"mismatch_map.mismatches[{i}].{k}", m.get(k))
        add_list(f"mismatch_map.mismatches[{i}].possible_actions",
                 m.get("possible_actions"))

    cp = dossier.get("citation_plan") or {}
    add_list("citation_plan.citation_gap_categories",
             cp.get("citation_gap_categories"))
    add_list("citation_plan.missing_bridge_categories",
             cp.get("missing_bridge_categories"))
    add_list("citation_plan.recommended_reference_search_tasks",
             cp.get("recommended_reference_search_tasks"))
    add_list("citation_plan.verification_tasks", cp.get("verification_tasks"))
    add_list("citation_plan.dangerous_padding_warnings",
             cp.get("dangerous_padding_warnings"))
    add_list("citation_plan.unknowns", cp.get("unknowns"))

    fa = dossier.get("fit_assessment") or {}
    add("fit_assessment.recommendation", fa.get("recommendation"))
    axes = fa.get("axes") or []
    for i, ax in enumerate(axes):
        if isinstance(ax, dict):
            add(f"fit_assessment.axes[{i}].notes", ax.get("notes"))

    cc = dossier.get("compliance_checklist") or {}
    cc_items = cc.get("checklist_items") or cc.get("items") or []
    for i, it in enumerate(cc_items):
        if isinstance(it, dict):
            add(f"compliance_checklist.items[{i}].requirement",
                it.get("requirement"))

    sub = dossier.get("submission_pack") or {}
    add_list("submission_pack.next_actions", sub.get("next_actions"))

    return items


__all__ = (
    "RussianSurfaceResult",
    "PROMPT_VERSION",
    "needs_russian_surface",
    "cache_key", "cache_get",
    "russianize_fields_batch",
    "collect_translation_items",
)
