"""TRM-071 deep target-model parity restoration.

Restores the Journal-Yuga chain:
complete published fulltext -> PublishedArticlePattern ->
GenreMoveProfile/archetypes -> CitationExpectationProfile ->
deep-model gate -> article x model simulation.

Fail-closed: partial extraction, oversized input, LLM parse failure, or a
shallow corpus never count as a completed semantic fulltext model.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from ..adapters.source_intake import SourceRole, register_local_source
from ..agents.base_shell import try_llm_call_with_outcome
from ..agents.prompt_families.article_target_model_simulation import (
    ARTICLE_TARGET_MODEL_SIMULATION_FAMILY,
)
from ..agents.prompt_families.genre_move_aggregation import (
    GENRE_MOVE_AGGREGATION_FAMILY,
)
from ..agents.prompt_families.published_article_pattern import (
    PUBLISHED_ARTICLE_PATTERN_FAMILY,
)
from ..agents.prompt_families.target_citation_ecology import (
    TARGET_CITATION_ECOLOGY_FAMILY,
)
from ..llm.config import LLMConfig
from ..llm.openai_compat import OpenAICompatProvider
from ..schema import (
    CitationExpectationProfile,
    GenreMoveProfile,
    PublishedArticleCorpus,
    PublishedArticlePattern,
)
from .fulltext_models import model_article_text
from .models import CorpusArtifactManifest

DEFAULT_MAX_ARTICLE_CHARS = 80_000
DEFAULT_MIN_ARTICLE_CHARS = 5_000
DEFAULT_MIN_DEEP_FULLTEXTS = 10


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        default=str,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def configured_provider(role_id: str) -> OpenAICompatProvider | None:
    cfg = LLMConfig.for_role(role_id)
    if cfg is None or not cfg.api_key:
        return None
    return OpenAICompatProvider(cfg)


def max_article_chars() -> int:
    raw = os.environ.get("KAIROSKOPION_DEEP_MODEL_MAX_ARTICLE_CHARS", "")
    try:
        value = int(raw) if raw else DEFAULT_MAX_ARTICLE_CHARS
    except ValueError:
        value = DEFAULT_MAX_ARTICLE_CHARS
    return max(10_000, value)


def min_article_chars() -> int:
    raw = os.environ.get("KAIROSKOPION_DEEP_MODEL_MIN_ARTICLE_CHARS", "")
    try:
        value = int(raw) if raw else DEFAULT_MIN_ARTICLE_CHARS
    except ValueError:
        value = DEFAULT_MIN_ARTICLE_CHARS
    return max(1_000, value)


def _parsed_dict(outcome: Any) -> dict[str, Any] | None:
    if outcome is None:
        return None
    value = getattr(outcome, "parsed", None) or getattr(
        outcome, "loose_parsed", None
    )
    return value if isinstance(value, dict) else None


def _attempt_diag(outcome: Any) -> dict[str, Any]:
    if outcome is None:
        return {"provider_status": "not_called", "parse_status": "not_attempted"}
    try:
        data = outcome.to_dict()
    except Exception:
        data = {}
    meta = getattr(outcome, "meta", None)
    if isinstance(meta, dict):
        data["model"] = meta.get("model")
        data["input_tokens"] = meta.get("input_tokens")
        data["output_tokens"] = meta.get("output_tokens")
    return data


_VOLATILE_SEMANTIC_KEYS = {
    "created_at", "updated_at", "last_checked_at", "observed_at",
    "latency_ms", "input_tokens", "output_tokens", "attempt_count",
}


def _stable_attempt_diag(outcome: Any) -> dict[str, Any]:
    """Persist provenance without run-timing/token-count noise."""
    diag = _attempt_diag(outcome)
    keep = (
        "provider_status", "parse_status", "parse_failure_category",
        "schema_error_category", "content_hash_prefix", "model",
        "fallback_reason",
    )
    return {k: diag.get(k) for k in keep if diag.get(k) not in (None, "")}


def _stable_semantic(value: Any) -> Any:
    """Remove runtime-only fields before content addressing."""
    if isinstance(value, dict):
        return {
            key: _stable_semantic(item)
            for key, item in value.items()
            if key not in _VOLATILE_SEMANTIC_KEYS
            and key not in {"attempt_diagnostics", "llm_attempt"}
        }
    if isinstance(value, list):
        return [_stable_semantic(item) for item in value]
    return value


def _pattern_id(
    content_hash: str, source_ref: str, semantic_output: dict[str, Any]
) -> str:
    key = {
        "content_hash": content_hash,
        "source_ref": source_ref,
        "prompt_family": PUBLISHED_ARTICLE_PATTERN_FAMILY["family_id"],
        "prompt_version": PUBLISHED_ARTICLE_PATTERN_FAMILY["version"],
        "semantic_output": semantic_output,
    }
    return f"papat_{_digest(key)[:16]}"


def _corpus_id(target_id: str, patterns: list[dict[str, Any]]) -> str:
    key = {
        "target_id": target_id,
        "pattern_ids": sorted(
            str(p.get("published_article_pattern_id") or "")
            for p in patterns
        ),
    }
    return f"deepcorpus:{target_id}:{_digest(key)[:16]}"


def _validate_pattern(parsed: dict[str, Any]) -> list[str]:
    required = (
        "section_structure", "intro_moves", "method_moves", "argument_moves",
        "conclusion_moves", "theory_presence", "citation_features",
        "novelty_moves", "evidence_anchors", "unknowns", "warnings",
        "confidence",
    )
    errors = [f"missing:{key}" for key in required if key not in parsed]
    if not isinstance(parsed.get("evidence_anchors"), list):
        errors.append("invalid:evidence_anchors")
    return errors


def build_published_article_patterns(
    *,
    target_id: str,
    manifest: CorpusArtifactManifest,
    provider: Any | None = None,
    max_articles: int = 20,
    max_chars: int | None = None,
    min_chars: int | None = None,
) -> dict[str, Any]:
    """Read complete acquired bodies and create semantic article cards.

    Only a complete extracted body counts toward HS-016. Partial extraction or
    a body too large for the configured complete-pass budget stays a blocker.
    """
    provider = provider or configured_provider("published_article_pattern_miner")
    limit = max_chars if max_chars is not None else max_article_chars()
    floor = min_chars if min_chars is not None else min_article_chars()
    patterns: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    attempted = 0
    complete_seen = 0
    seen_content_hashes: set[str] = set()

    if provider is None:
        return {
            "patterns": [],
            "failures": [{
                "status": "provider_unavailable",
                "detail": "LLM provider unavailable for semantic fulltext modeling",
            }],
            "attempted": 0,
            "modeled": 0,
            "complete_fulltexts_seen": 0,
        }

    for artifact in manifest.artifacts:
        if len(patterns) >= max(1, max_articles):
            break
        if not artifact.local_ref:
            continue
        attempted += 1
        if artifact.acquisition_state != "validated_artifact":
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "unvalidated_artifact",
                "acquisition_state": artifact.acquisition_state,
                "detail": (
                    "Local bytes exist but are not a validated full-text "
                    "artifact and cannot enter HS-016 semantic modeling."
                ),
            })
            continue
        snapshot, text = register_local_source(
            Path(artifact.local_ref),
            role=SourceRole.PUBLISHED_ARTICLE,
            source_id=artifact.source_ref,
        )
        if snapshot.extraction_status != "extracted" or not text:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "incomplete_extraction",
                "extraction_status": snapshot.extraction_status,
                "detail": "; ".join(snapshot.extraction_errors or []),
            })
            continue

        text_chars = len(text)
        if text_chars < floor:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "body_too_short_for_fulltext",
                "chars": text_chars,
                "min_chars": floor,
                "detail": (
                    "Extracted text is too short to count as a genuinely "
                    "read full-text article."
                ),
            })
            continue

        content_hash = (
            snapshot.content_hash or artifact.content_hash or _digest(text)
        )
        if content_hash in seen_content_hashes:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "duplicate_fulltext_content",
                "content_hash": content_hash,
                "detail": (
                    "The same extracted body is already represented in this "
                    "corpus and cannot count twice toward HS-016."
                ),
            })
            continue
        seen_content_hashes.add(content_hash)
        complete_seen += 1

        if text_chars > limit:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "input_too_large_requires_chunking",
                "chars": text_chars,
                "max_chars": limit,
                "detail": "Complete text was not sent; article does not count.",
            })
            continue

        structural = model_article_text(text, source_ref=artifact.source_ref)
        outcome = try_llm_call_with_outcome(
            provider,
            PUBLISHED_ARTICLE_PATTERN_FAMILY,
            {
                "target_id": target_id,
                "source_ref": artifact.source_ref,
                "title": artifact.title or "",
                "structural_json": _safe_json(structural),
                "article_text": text,
            },
            strict_schema=False,
            temperature=0.0,
            max_tokens=2600,
            agent_role="published_article_pattern_miner",
            model_role="published_article_pattern_miner",
        )
        parsed = _parsed_dict(outcome)
        if parsed is None:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "semantic_parse_failed",
                "attempt": _stable_attempt_diag(outcome),
            })
            continue
        validation = _validate_pattern(parsed)
        if validation:
            failures.append({
                "source_ref": artifact.source_ref,
                "status": "semantic_schema_failed",
                "errors": validation,
                "attempt": _stable_attempt_diag(outcome),
            })
            continue

        pattern = PublishedArticlePattern(
            published_article_pattern_id=_pattern_id(
                content_hash, artifact.source_ref, parsed
            ),
            article_source_id=artifact.source_ref,
            title=artifact.title,
            abstract_pattern=parsed.get("abstract_pattern"),
            section_structure=list(parsed.get("section_structure") or []),
            intro_moves=list(parsed.get("intro_moves") or []),
            method_moves=list(parsed.get("method_moves") or []),
            argument_moves=list(parsed.get("argument_moves") or []),
            conclusion_moves=list(parsed.get("conclusion_moves") or []),
            method_presence=parsed.get("method_presence"),
            theory_presence=list(parsed.get("theory_presence") or []),
            empirical_presence=parsed.get("empirical_presence"),
            citation_features=dict(parsed.get("citation_features") or {}),
            novelty_moves=list(parsed.get("novelty_moves") or []),
            evidence_anchors=list(parsed.get("evidence_anchors") or []),
            source_snapshot_id=snapshot.snapshot_id,
            content_hash=content_hash,
            evidence_status="corpus_observation",
            semantic_status="llm_grounded_fulltext",
            prompt_family_version=(
                f"{PUBLISHED_ARTICLE_PATTERN_FAMILY['family_id']}:"
                f"{PUBLISHED_ARTICLE_PATTERN_FAMILY['version']}"
            ),
            unknowns=list(parsed.get("unknowns") or []),
            warnings=list(parsed.get("warnings") or []),
            confidence=parsed.get("confidence") or "low",
        ).to_dict()
        # Keep the semantic card durable and content-addressable. Runtime
        # timing/token diagnostics belong to execution receipts, not the card.
        pattern.pop("created_at", None)
        pattern["structural_observation"] = structural
        pattern["source_text_chars"] = text_chars
        pattern["llm_attempt"] = _stable_attempt_diag(outcome)
        patterns.append(pattern)

    corpus_id = _corpus_id(target_id, patterns)
    for pattern in patterns:
        pattern["published_corpus_id"] = corpus_id

    return {
        "published_corpus_id": corpus_id,
        "patterns": patterns,
        "failures": failures,
        "attempted": attempted,
        "modeled": len(patterns),
        "complete_fulltexts_seen": complete_seen,
        "min_article_chars": floor,
        "max_article_chars": limit,
        "unique_content_hashes_seen": len(seen_content_hashes),
    }


def _validate_archetypes(
    archetypes: list[dict[str, Any]], pattern_ids: set[str]
) -> list[str]:
    errors: list[str] = []
    for i, item in enumerate(archetypes):
        members = set(item.get("member_pattern_ids") or [])
        if not members:
            errors.append(f"archetype[{i}]:no_members")
        unknown = members - pattern_ids
        if unknown:
            errors.append(
                f"archetype[{i}]:unknown_members:{','.join(sorted(unknown))}"
            )
    return errors


def aggregate_deep_target_model(
    *,
    target_id: str,
    pattern_result: dict[str, Any],
    selection_strategy: str,
    bias_notes: list[str],
    editor_profiles: list[dict[str, Any]],
    provider: Any | None = None,
    min_fulltexts: int = DEFAULT_MIN_DEEP_FULLTEXTS,
) -> dict[str, Any]:
    """Aggregate fulltext-grounded cards into restored Journal-Yuga profiles."""
    patterns = list(pattern_result.get("patterns") or [])
    corpus_id = str(pattern_result.get("published_corpus_id") or "")
    pattern_hashes = [
        str(p.get("content_hash") or "").strip() for p in patterns
    ]
    nonempty_pattern_hashes = [h for h in pattern_hashes if h]
    unique_pattern_hashes = set(nonempty_pattern_hashes)
    missing_pattern_hashes = len(pattern_hashes) - len(nonempty_pattern_hashes)
    duplicate_pattern_hashes = (
        len(nonempty_pattern_hashes) - len(unique_pattern_hashes)
    )
    pattern_ids = {
        str(p.get("published_article_pattern_id") or "") for p in patterns
    } - {""}
    provider = provider or configured_provider("genre_move_aggregator")

    word_counts = [
        int((p.get("structural_observation") or {}).get("word_count") or 0)
        for p in patterns
    ]
    corpus = PublishedArticleCorpus(
        published_article_corpus_id=corpus_id,
        corpus_size=len(patterns),
        average_word_count=(
            round(sum(word_counts) / len(word_counts)) if word_counts else None
        ),
        unknowns=[],
        confidence=(
            "medium" if len(patterns) >= min_fulltexts
            else "low" if patterns else "unknown"
        ),
        evidence_refs=sorted(pattern_ids),
    ).to_dict()
    corpus.pop("created_at", None)
    corpus["selection_strategy"] = selection_strategy
    corpus["bias_notes"] = list(bias_notes or [])
    corpus["fulltext_semantic_pattern_count"] = len(patterns)

    genre_parsed = None
    genre_diag: dict[str, Any] = {}
    citation_parsed = None
    citation_diag: dict[str, Any] = {}

    if provider is not None and patterns:
        outcome = try_llm_call_with_outcome(
            provider,
            GENRE_MOVE_AGGREGATION_FAMILY,
            {
                "target_id": target_id,
                "published_corpus_id": corpus_id,
                "corpus_context_json": _safe_json({
                    "selection_strategy": selection_strategy,
                    "bias_notes": bias_notes,
                    "sample_size": len(patterns),
                }),
                "sample_size": str(len(patterns)),
                "patterns_json": _safe_json(patterns),
            },
            strict_schema=False,
            temperature=0.0,
            max_tokens=3200,
            agent_role="genre_move_aggregator",
            model_role="genre_move_aggregator",
        )
        genre_parsed = _parsed_dict(outcome)
        genre_diag = _stable_attempt_diag(outcome)

        citation_provider = configured_provider(
            "target_citation_ecologist"
        ) or provider
        c_outcome = try_llm_call_with_outcome(
            citation_provider,
            TARGET_CITATION_ECOLOGY_FAMILY,
            {
                "target_id": target_id,
                "published_corpus_id": corpus_id,
                "patterns_json": _safe_json(patterns),
            },
            strict_schema=False,
            temperature=0.0,
            max_tokens=2600,
            agent_role="target_citation_ecologist",
            model_role="target_citation_ecologist",
        )
        citation_parsed = _parsed_dict(c_outcome)
        citation_diag = _stable_attempt_diag(c_outcome)

    archetypes = list((genre_parsed or {}).get("archetypes") or [])
    archetype_errors = _validate_archetypes(archetypes, pattern_ids)

    genre_id_key = {
        "corpus_id": corpus_id,
        "prompt": GENRE_MOVE_AGGREGATION_FAMILY["version"],
        "output": genre_parsed or {},
    }
    genre_profile = GenreMoveProfile(
        genre_move_profile_id=f"gmove_{_digest(genre_id_key)[:16]}",
        observed_moves=dict((genre_parsed or {}).get("observed_moves") or {}),
        dominant_moves=list((genre_parsed or {}).get("dominant_moves") or []),
        conspicuously_absent_moves=list(
            (genre_parsed or {}).get("absent_in_sample_moves") or []
        ),
        evidence_refs=sorted(pattern_ids),
        source_category="corpus_observation",
        confidence=(genre_parsed or {}).get("confidence") or "unknown",
        evidence_status="corpus_observation" if genre_parsed else "unknown",
        unknowns=list((genre_parsed or {}).get("unknowns") or []),
        warnings=list((genre_parsed or {}).get("warnings") or []),
    ).to_dict()
    genre_profile.pop("created_at", None)
    genre_profile["rare_moves"] = list(
        (genre_parsed or {}).get("rare_moves") or []
    )
    genre_profile["article_comparison_dimensions"] = list(
        (genre_parsed or {}).get("article_comparison_dimensions") or []
    )

    citation_id_key = {
        "corpus_id": corpus_id,
        "prompt": TARGET_CITATION_ECOLOGY_FAMILY["version"],
        "output": citation_parsed or {},
    }
    citation_profile = CitationExpectationProfile(
        citation_expectation_profile_id=(
            f"cexp_{_digest(citation_id_key)[:16]}"
        ),
        typical_reference_count=(
            (citation_parsed or {}).get("reference_count_observation")
        ),
        dominant_traditions=list(
            (citation_parsed or {}).get(
                "dominant_theoretical_traditions"
            ) or []
        ),
        expected_bridge_references=[],
        recency_bias=(citation_parsed or {}).get("recentness_observation"),
        canonical_works_expected=[],
        absent_traditions_risk=list(
            (citation_parsed or {}).get("not_observed_traditions") or []
        ),
        unknowns=list((citation_parsed or {}).get("unknowns") or []),
        confidence=(citation_parsed or {}).get("confidence") or "unknown",
        evidence_refs=list(
            (citation_parsed or {}).get("evidence_pattern_ids")
            or sorted(pattern_ids)
        ),
    ).to_dict()
    citation_profile.pop("created_at", None)
    citation_profile.update({
        "observed_cited_authors": list(
            (citation_parsed or {}).get("dominant_cited_authors") or []
        ),
        "observed_cited_journals": list(
            (citation_parsed or {}).get("dominant_cited_journals") or []
        ),
        "observed_citation_roles": list(
            (citation_parsed or {}).get("citation_roles") or []
        ),
        "bridge_opportunity_categories": list(
            (citation_parsed or {}).get("bridge_opportunities") or []
        ),
        "classic_reference_observation": (
            (citation_parsed or {}).get("classic_reference_observation")
        ),
        "warnings": list((citation_parsed or {}).get("warnings") or []),
        "evidence_status": (
            "corpus_observation" if citation_parsed else "unknown"
        ),
    })

    meaningful_editors = [
        profile for profile in (editor_profiles or [])
        if str(profile.get("name") or "").strip()
        and list(profile.get("source_refs") or [])
        and str(profile.get("evidence_status") or "unknown") != "unknown"
        and any((
            profile.get("disciplines"),
            profile.get("research_topics"),
            profile.get("theoretical_traditions"),
            profile.get("key_works"),
        ))
    ]

    requirements = {
        "min_fulltext_semantic_patterns": {
            "required": int(min_fulltexts),
            "actual": len(patterns),
            "pass": len(patterns) >= int(min_fulltexts),
        },
        "all_patterns_fulltext_grounded": {
            "pass": bool(patterns) and all(
                p.get("semantic_status") == "llm_grounded_fulltext"
                for p in patterns
            ),
        },
        "unique_fulltext_content_hashes": {
            "required": int(min_fulltexts),
            "actual": len(unique_pattern_hashes),
            "missing_hashes": missing_pattern_hashes,
            "duplicate_hashes": duplicate_pattern_hashes,
            "pass": (
                len(unique_pattern_hashes) >= int(min_fulltexts)
                and missing_pattern_hashes == 0
                and duplicate_pattern_hashes == 0
            ),
        },
        "archetypes_2_to_6": {
            "actual": len(archetypes),
            "pass": 2 <= len(archetypes) <= 6 and not archetype_errors,
        },
        "citation_ecology_profile": {"pass": citation_parsed is not None},
        "editor_scholarly_ecology": {
            "actual": len(meaningful_editors),
            "total_editor_profiles": len(editor_profiles or []),
            "pass": len(meaningful_editors) > 0,
            "minimum_contract": (
                "name + source_refs + non-unknown evidence_status + "
                "discipline/topic/tradition/key_work signal"
            ),
        },
    }
    blockers = [
        name for name, item in requirements.items() if not item.get("pass")
    ]
    if genre_parsed is None:
        blockers.append("genre_move_aggregation")
    blockers.extend(archetype_errors)
    blockers = sorted(set(blockers))

    payload = {
        "schema_version": "deep-target-model-v1",
        "target_id": target_id,
        "published_article_corpus": corpus,
        "published_article_patterns": patterns,
        "genre_move_profile": genre_profile,
        "citation_expectation_profile": citation_profile,
        "archetypes": archetypes,
        "countermodels": list(
            (genre_parsed or {}).get("countermodels") or []
        ),
        "editor_scholarly_ecology": list(meaningful_editors),
        "pattern_failures": list(pattern_result.get("failures") or []),
        "prompt_versions": {
            "published_article_pattern": (
                f"{PUBLISHED_ARTICLE_PATTERN_FAMILY['family_id']}:"
                f"{PUBLISHED_ARTICLE_PATTERN_FAMILY['version']}"
            ),
            "genre_move_aggregation": (
                f"{GENRE_MOVE_AGGREGATION_FAMILY['family_id']}:"
                f"{GENRE_MOVE_AGGREGATION_FAMILY['version']}"
            ),
            "target_citation_ecology": (
                f"{TARGET_CITATION_ECOLOGY_FAMILY['family_id']}:"
                f"{TARGET_CITATION_ECOLOGY_FAMILY['version']}"
            ),
        },
        "attempt_diagnostics": {
            "genre_move_aggregation": genre_diag,
            "target_citation_ecology": citation_diag,
        },
    }
    digest = _digest(_stable_semantic(payload))
    payload["deep_target_model_id"] = f"deep-target:{target_id}:{digest[:16]}"
    payload["content_digest"] = digest
    payload["deep_model_gate"] = {
        "status": "READY" if not blockers else "BLOCKED",
        "requirements": requirements,
        "blockers": blockers,
        "hs016_note": (
            "Target-level deep model readiness only. Each article still "
            "requires article x model simulation for its HS-016 cell gate."
        ),
    }
    return payload


def build_deep_target_model(
    *,
    target_id: str,
    manifest: CorpusArtifactManifest,
    editor_profiles: list[dict[str, Any]],
    selection_strategy: str,
    bias_notes: list[str],
    provider: Any | None = None,
    max_articles: int = 20,
    min_fulltexts: int = DEFAULT_MIN_DEEP_FULLTEXTS,
) -> dict[str, Any]:
    pattern_result = build_published_article_patterns(
        target_id=target_id,
        manifest=manifest,
        provider=provider,
        max_articles=max_articles,
    )
    return aggregate_deep_target_model(
        target_id=target_id,
        pattern_result=pattern_result,
        selection_strategy=selection_strategy,
        bias_notes=bias_notes,
        editor_profiles=editor_profiles,
        provider=provider,
        min_fulltexts=min_fulltexts,
    )


def simulate_article_against_deep_model(
    *,
    article: dict[str, Any],
    deep_target_model: dict[str, Any],
    provider: Any | None = None,
) -> dict[str, Any]:
    gate = deep_target_model.get("deep_model_gate") or {}
    if gate.get("status") != "READY":
        return {
            "status": "BLOCKED",
            "blockers": ["deep_target_model_not_ready"],
            "deep_target_model_id": deep_target_model.get(
                "deep_target_model_id"
            ),
        }

    provider = provider or configured_provider(
        "article_target_model_simulator"
    )
    if provider is None:
        return {
            "status": "BLOCKED",
            "blockers": ["llm_provider_unavailable"],
            "deep_target_model_id": deep_target_model.get(
                "deep_target_model_id"
            ),
        }

    comparison_model = {
        "deep_target_model_id": deep_target_model.get("deep_target_model_id"),
        "archetypes": deep_target_model.get("archetypes") or [],
        "countermodels": deep_target_model.get("countermodels") or [],
        "genre_move_profile": deep_target_model.get("genre_move_profile") or {},
        "citation_expectation_profile": (
            deep_target_model.get("citation_expectation_profile") or {}
        ),
        "article_comparison_dimensions": (
            (deep_target_model.get("genre_move_profile") or {}).get(
                "article_comparison_dimensions"
            ) or []
        ),
    }
    outcome = try_llm_call_with_outcome(
        provider,
        ARTICLE_TARGET_MODEL_SIMULATION_FAMILY,
        {
            "article_json": _safe_json(article),
            "deep_target_model_json": _safe_json(comparison_model),
        },
        strict_schema=False,
        temperature=0.0,
        max_tokens=2600,
        agent_role="article_target_model_simulator",
        model_role="article_target_model_simulator",
    )
    parsed = _parsed_dict(outcome)
    if parsed is None:
        return {
            "status": "BLOCKED",
            "blockers": ["article_model_simulation_parse_failed"],
            "deep_target_model_id": deep_target_model.get(
                "deep_target_model_id"
            ),
            "attempt": _attempt_diag(outcome),
        }

    valid_archetypes = {
        str(item.get("archetype_id") or "")
        for item in (deep_target_model.get("archetypes") or [])
    } - {""}
    valid_patterns = {
        str(item.get("published_article_pattern_id") or "")
        for item in (
            deep_target_model.get("published_article_patterns") or []
        )
    } - {""}
    used_archetypes = {
        str(item.get("archetype_id") or "")
        for item in (parsed.get("closest_archetypes") or [])
    } - {""}
    used_patterns = {
        str(item) for item in (parsed.get("evidence_pattern_ids") or [])
    } - {""}
    evidence_errors = []
    if used_archetypes - valid_archetypes:
        evidence_errors.append("simulation_unknown_archetype_id")
    if not used_patterns:
        evidence_errors.append("simulation_missing_evidence_pattern_ids")
    if used_patterns - valid_patterns:
        evidence_errors.append("simulation_unknown_evidence_pattern_id")
    if evidence_errors:
        return {
            "status": "BLOCKED",
            "blockers": sorted(set(evidence_errors)),
            "deep_target_model_id": deep_target_model.get(
                "deep_target_model_id"
            ),
            "attempt": _attempt_diag(outcome),
        }

    payload = {
        "schema_version": "article-target-model-simulation-v1",
        "article_id": (
            article.get("article_id")
            or article.get("article_model_id")
            or article.get("state_id")
        ),
        "deep_target_model_id": deep_target_model.get("deep_target_model_id"),
        "result": parsed,
        "attempt": _attempt_diag(outcome),
        "prompt_version": (
            f"{ARTICLE_TARGET_MODEL_SIMULATION_FAMILY['family_id']}:"
            f"{ARTICLE_TARGET_MODEL_SIMULATION_FAMILY['version']}"
        ),
    }
    digest = _digest(_stable_semantic({
        "schema_version": payload["schema_version"],
        "article_id": payload["article_id"],
        "deep_target_model_id": payload["deep_target_model_id"],
        "result": payload["result"],
        "prompt_version": payload["prompt_version"],
    }))
    payload["simulation_id"] = f"targetsim:{digest[:16]}"
    payload["content_digest"] = digest
    payload["status"] = "READY"
    payload["hs016_cell_gate"] = {
        "status": "READY",
        "blockers": [],
        "note": "Comparison only; this is not an acceptance prediction.",
    }
    return payload
