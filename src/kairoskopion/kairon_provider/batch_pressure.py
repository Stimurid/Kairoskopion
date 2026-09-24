"""Evidence-bounded pressure derivation for batch qualification cells.

This module uses only an Artikl-governed ArticleModel projection, the batch
academic-world path, and a frozen TargetWorld snapshot. It intentionally avoids
model-memory venue facts.
"""

from __future__ import annotations

from datetime import datetime, timezone
import statistics
from typing import Any

from ..schema import ArticleModel
from .batch import BatchArticleInput, BatchTargetInput
from .models import TargetPressureItem, TargetPressurePack


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(x for x in values if x))


def corpus_years(snapshot: dict[str, Any]) -> list[int]:
    artifacts = (snapshot.get("corpus_manifest") or {}).get("artifacts") or []
    out: list[int] = []
    for artifact in artifacts:
        year = artifact.get("year") if isinstance(artifact, dict) else None
        if isinstance(year, int):
            out.append(year)
    return out


def assess_corpus_temporal_adequacy(
    snapshot: dict[str, Any],
    *,
    current_year: int | None = None,
    max_median_age_years: int = 3,
) -> dict[str, Any]:
    """Separate snapshot recency from the temporal adequacy of its corpus."""
    current_year = current_year or datetime.now(timezone.utc).year
    years = corpus_years(snapshot)
    if not years:
        return {
            "status": "unknown",
            "years": [],
            "median_year": None,
            "max_year": None,
            "median_age_years": None,
            "reason": "corpus records do not expose publication years",
        }
    median_year = float(statistics.median(years))
    age = current_year - median_year
    status = "adequate" if age <= max_median_age_years else "stale"
    return {
        "status": status,
        "years": years,
        "median_year": median_year,
        "max_year": max(years),
        "min_year": min(years),
        "median_age_years": age,
        "reason": (
            f"corpus median year {median_year:g}; current year {current_year}; "
            f"median age {age:g} years"
        ),
    }


def _evidence_refs(snapshot: dict[str, Any]) -> list[str]:
    refs = list(snapshot.get("evidence_refs") or [])
    refs.extend((snapshot.get("target_models") or {}).get("evidence_refs") or [])
    refs.append(str(snapshot.get("snapshot_id") or ""))
    return _unique(refs)


def _target_disciplines(target: BatchTargetInput) -> set[str]:
    return {x for x in target.academic_world_path if x.startswith("discipline:")}


def _article_hint_nodes(article_input: BatchArticleInput) -> set[str]:
    return {node for path in article_input.academic_world_path_hints for node in path}


def _pattern_share(target_models: dict[str, Any], key: str, label: str) -> float | None:
    rows = target_models.get(key) or []
    if not rows:
        return None
    for row in rows:
        if isinstance(row, dict) and row.get("label") == label:
            try:
                return float(row.get("share") or 0)
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def _corpus_is_english_dominant(snapshot: dict[str, Any]) -> bool | None:
    artifacts = (snapshot.get("corpus_manifest") or {}).get("artifacts") or []
    titles = [str(x.get("title") or "") for x in artifacts if isinstance(x, dict)]
    titles = [x for x in titles if x.strip()]
    if not titles:
        return None
    asciiish = 0
    for title in titles:
        letters = [c for c in title if c.isalpha()]
        if not letters:
            continue
        latin = sum(1 for c in letters if "LATIN" in __import__("unicodedata").name(c, ""))
        if latin / len(letters) >= 0.9:
            asciiish += 1
    return asciiish / len(titles) >= 0.8


def _normalize_language(value: str | None) -> str | None:
    raw = (value or "").strip().lower()
    if not raw:
        return None
    aliases = {
        "russian": "ru", "русский": "ru", "ru-ru": "ru",
        "english": "en", "английский": "en", "en-us": "en", "en-uk": "en",
        "french": "fr", "французский": "fr",
        "german": "de", "немецкий": "de",
    }
    if raw in aliases:
        return aliases[raw]
    if len(raw) == 2:
        return raw
    if "-" in raw and len(raw.split("-", 1)[0]) == 2:
        return raw.split("-", 1)[0]
    return raw


def _accepted_languages(snapshot: dict[str, Any]) -> tuple[set[str], list[str]]:
    """Return formal accepted-language rules when the frozen snapshot has them.

    Formal venue policy outranks corpus-title script inference. Crossref/OpenAlex
    often expose translated/romanized titles, so title language alone cannot
    override an explicit bilingual/multilingual submission rule.
    """
    rules = dict(snapshot.get("canonical_target_rules") or {})
    raw = (
        rules.get("accepted_languages")
        or rules.get("languages_accepted")
        or rules.get("submission_languages")
        or []
    )
    if isinstance(raw, str):
        raw = [raw]
    langs = {_normalize_language(str(x)) for x in raw if str(x).strip()}
    langs.discard(None)
    refs = [str(x) for x in (rules.get("language_evidence_refs") or []) if x]
    return {str(x) for x in langs}, refs


def derive_batch_target_pressure(
    *,
    article_input: BatchArticleInput,
    article: ArticleModel,
    target: BatchTargetInput,
    snapshot: dict[str, Any],
    current_year: int | None = None,
) -> TargetPressurePack:
    """Derive a conservative pressure pack from frozen target evidence."""
    if snapshot.get("snapshot_id") != target.snapshot_id:
        raise ValueError("target snapshot_id does not match supplied snapshot")
    refs = _evidence_refs(snapshot)
    target_models = dict(snapshot.get("target_models") or {})
    items: list[TargetPressureItem] = []
    unknowns: list[str] = []

    temporal = assess_corpus_temporal_adequacy(snapshot, current_year=current_year)
    if temporal["status"] == "stale":
        items.append(TargetPressureItem(
            pressure_id="target:corpus:temporal_adequacy",
            dimension="target_evidence_freshness",
            observation=(
                f"Frozen snapshot is recent, but its sampled publication corpus is stale: "
                f"{temporal['reason']}. Refresh target evidence before fit decisions."
            ),
            evidence_refs=refs,
            evidence_status="corpus_observation",
            severity="major",
            transformation_depth_hint="evidence_needed",
            source_kind="target_world_temporal_audit",
        ))
    elif temporal["status"] == "unknown":
        unknowns.append("target:corpus:publication_years")

    target_disciplines = _target_disciplines(target)
    hint_nodes = _article_hint_nodes(article_input)
    if target_disciplines:
        if not (target_disciplines & hint_nodes):
            items.append(TargetPressureItem(
                pressure_id="target:disciplinary_path:translation",
                dimension="disciplinary_path",
                observation=(
                    "No current Artikl academic-world path hint reaches the target "
                    f"discipline node(s) {sorted(target_disciplines)}; target-specific "
                    "disciplinary translation/reframing must be tested."
                ),
                evidence_refs=refs,
                evidence_status="artikl_path_vs_target_graph",
                severity="weak",
                transformation_depth_hint="local_or_structural",
                source_kind="academic_world_graph",
            ))
    elif target.academic_world_path:
        unknowns.append("target:disciplinary_path:no_discipline_node")

    genre = (article.genre_current or "").lower()
    conceptual_article = genre in {
        "conceptual_article", "theoretical_essay", "theoretical_article"
    }
    conceptual_share = _pattern_share(target_models, "genre_patterns", "conceptual_article")
    if conceptual_article:
        if conceptual_share is None:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:genre:unknown",
                dimension="genre",
                observation="Frozen target corpus is insufficient to establish conceptual-article genre prevalence.",
                evidence_refs=refs,
                evidence_status="evidence_need",
                severity="unknown",
                transformation_depth_hint="evidence_needed",
                source_kind="target_corpus_profile",
            ))
            unknowns.append("target:corpus:genre")
        elif conceptual_share < 0.15:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:genre:weak",
                dimension="genre",
                observation=(
                    f"Article is conceptual/theoretical; conceptual_article share in "
                    f"the frozen corpus is {conceptual_share:.3f}."
                ),
                evidence_refs=refs,
                evidence_status="corpus_observation",
                severity="weak",
                transformation_depth_hint="local_or_structural",
                source_kind="target_corpus_profile",
            ))

    method_text = " ".join([
        article.method_status or "",
        article.method_description or "",
    ]).lower()
    conceptual_method = any(
        marker in method_text
        for marker in ("concept", "theoret", "genealog", "philosoph", "reconstruct")
    )
    conceptual_method_share = _pattern_share(target_models, "method_patterns", "conceptual")
    if conceptual_method:
        if conceptual_method_share is None:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:method:unknown",
                dimension="method_regime",
                observation="Frozen target corpus is insufficient to establish conceptual-method prevalence.",
                evidence_refs=refs,
                evidence_status="evidence_need",
                severity="unknown",
                transformation_depth_hint="evidence_needed",
                source_kind="target_corpus_profile",
            ))
            unknowns.append("target:corpus:method")
        elif conceptual_method_share < 0.15:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:method:weak",
                dimension="method_regime",
                observation=(
                    f"Article uses a conceptual/theoretical method; conceptual method "
                    f"share in the frozen target corpus is {conceptual_method_share:.3f}."
                ),
                evidence_refs=refs,
                evidence_status="corpus_observation",
                severity="weak",
                transformation_depth_hint="local_or_structural",
                source_kind="target_corpus_profile",
            ))

    citation = target_models.get("citation_patterns") or {}
    try:
        median_refs = float(citation.get("median_reference_count"))
    except (TypeError, ValueError):
        median_refs = 0.0
    if median_refs > 0:
        if article.reference_count is None:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:citation:article_unknown",
                dimension="citation_ecology",
                observation=(
                    f"Frozen target corpus median reference count is {median_refs:g}; "
                    "the current article projection has no verified reference count."
                ),
                evidence_refs=refs,
                evidence_status="evidence_need",
                severity="unknown",
                transformation_depth_hint="evidence_needed",
                source_kind="target_corpus_profile",
            ))
            unknowns.append("article:reference_count")
        elif article.reference_count < median_refs * 0.5:
            items.append(TargetPressureItem(
                pressure_id="target:corpus:citation:thin",
                dimension="citation_ecology",
                observation=(
                    f"Current article has {article.reference_count} verified references; "
                    f"frozen target corpus median is {median_refs:g}. Citation dialogue "
                    "likely needs target-specific expansion."
                ),
                evidence_refs=refs,
                evidence_status="corpus_observation",
                severity="weak",
                transformation_depth_hint="local_or_structural",
                source_kind="target_corpus_profile",
            ))
    else:
        items.append(TargetPressureItem(
            pressure_id="target:corpus:citation:unknown",
            dimension="citation_ecology",
            observation="Frozen target corpus does not provide a usable reference-count baseline.",
            evidence_refs=refs,
            evidence_status="evidence_need",
            severity="unknown",
            transformation_depth_hint="evidence_needed",
            source_kind="target_corpus_profile",
        ))
        unknowns.append("target:corpus:citation")

    accepted_languages, language_rule_refs = _accepted_languages(snapshot)
    article_language = _normalize_language(article.language)
    if accepted_languages and article_language:
        if article_language not in accepted_languages:
            items.append(TargetPressureItem(
                pressure_id="target:formal:language:target_variant_required",
                dimension="language_register",
                observation=(
                    f"The authoritative current article language is {article_language!r}, "
                    f"while the frozen formal target rule accepts {sorted(accepted_languages)}. "
                    "A target-language sibling TARGET_VARIANT is required."
                ),
                evidence_refs=_unique([*refs, *language_rule_refs]),
                evidence_status="formal_target_rule",
                severity="major",
                transformation_depth_hint="target_variant_branch",
                source_kind="canonical_target_rules",
            ))
    else:
        english = _corpus_is_english_dominant(snapshot)
        if english and article_language == "ru":
            items.append(TargetPressureItem(
                pressure_id="target:corpus:language:english_realization",
                dimension="language_register",
                observation=(
                    "The frozen target corpus is English-dominant while the authoritative "
                    "current article state is Russian. An English sibling TARGET_VARIANT is "
                    "provisionally required for this batch trajectory; formal language policy "
                    "remains unverified and can override corpus-title inference."
                ),
                evidence_refs=refs,
                evidence_status="corpus_observation",
                severity="major",
                transformation_depth_hint="target_variant_branch",
                uncertainty=["formal submission language policy not yet verified in B8"],
                source_kind="target_corpus_profile",
            ))

    for limitation in target_models.get("limitations") or []:
        items.append(TargetPressureItem(
            pressure_id=f"target:corpus:limitation:{len(items)}",
            dimension="target_evidence",
            observation=str(limitation),
            evidence_refs=refs,
            evidence_status="evidence_need",
            severity="unknown",
            transformation_depth_hint="evidence_needed",
            source_kind="target_corpus_profile",
        ))
        unknowns.append(f"target:corpus:limitation:{limitation}")

    return TargetPressurePack(
        target_id=target.target_id,
        snapshot_id=target.snapshot_id,
        items=items,
        unknowns=_unique(unknowns),
    )