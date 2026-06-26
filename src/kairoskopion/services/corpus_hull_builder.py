"""Deterministic corpus hull builder — venue-side baseline.

Converts a venue's published article corpus into an empirical envelope
expressed as a `FieldPositionModel(entity_type="venue")`.

This is the deterministic primary-computation layer for several venue
envelope axes per the source-layer rubric (D corpus):

- discipline_envelope         — from method/school/topic distribution
- argument_move_envelope      — from genre + abstract patterns
- evidence_type_envelope      — from method patterns
- method_envelope             — from method patterns + reference counts
- genre_envelope              — from genre summary

No LLM. No network. Pure aggregation over data already available from
`services.corpus_sampler` and `services.corpus_analyzer`.

When an axis cannot be computed from the available data, it is left
empty / null with an explicit unknowns entry. UNKNOWN is never coerced
to absent.

Authority: D corpus per `benchmarks/golden/venue_source_layer_map.md`.
Output evidence_status: `corpus_observation`.
"""

from __future__ import annotations

import dataclasses as dc
from collections import defaultdict
from typing import Any

from ..schema import FieldPositionModel
from .corpus_analyzer import CorpusAnalysisResult, CorpusPattern


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dc.dataclass(frozen=True)
class HullBuilderConfig:
    """Knobs for envelope width and noise floor.

    The envelope for each dimension is `[max(0, share - margin),
    min(1, share + margin)]` by default. Margin widens with smaller
    corpora — small corpus = wider envelope = lower confidence.
    """
    margin_quick: float = 0.20    # corpus 1-9
    margin_standard: float = 0.15  # corpus 10-34
    margin_deep: float = 0.10      # corpus 35+
    # Minimum frequency to enter the envelope at all (noise floor).
    floor_quick: float = 0.10
    floor_standard: float = 0.05
    floor_deep: float = 0.02


_DEFAULT = HullBuilderConfig()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_venue_corpus_hull(
    analysis: CorpusAnalysisResult,
    venue_model_id: str | None = None,
    config: HullBuilderConfig = _DEFAULT,
) -> FieldPositionModel:
    """Build a venue FieldPositionModel from a corpus analysis.

    The result is a FieldPositionModel with `entity_type="venue"` and
    envelopes populated for whichever axes the analysis can support.

    Parameters
    ----------
    analysis
        Output of `analyze_venue_corpus`. Must have `corpus_size > 0`
        for any envelope to be built; otherwise everything is unknown.
    venue_model_id
        Override for `entity_id`. Defaults to `analysis.venue_model_id`.
    config
        Margin/floor knobs.

    Returns
    -------
    FieldPositionModel
        Venue-side FPM. Axes that cannot be computed are left empty
        with the reason in `unknowns`. Envelopes are dict[name, [lo, hi]].
    """
    unknowns: list[str] = []
    fpm = FieldPositionModel(
        entity_type="venue",
        entity_id=venue_model_id or analysis.venue_model_id,
    )

    n = analysis.corpus_size
    if n is None or n == 0:
        fpm.unknowns = [
            "Empty corpus — no envelope can be built; all axes marked unknown",
        ]
        fpm.confidence = "none"
        return fpm

    margin, floor, depth_label = _depth_params(n, config)

    # ---- Discipline / school envelopes ----
    # We deliberately distinguish:
    #  - school_patterns -> tradition_envelope
    #  - method_patterns -> evidence_type_envelope + method_envelope hint
    #
    # We do NOT derive discipline_envelope from a single keyword set;
    # the corpus analyzer does not classify into the 8-10 disciplinary
    # buckets the FPM expects. discipline_envelope therefore is left
    # empty here with an explicit unknown — D primary layer is corpus
    # topic distribution which requires either OpenAlex concepts (G
    # corroborator) or operator-supplied topic seeds. Either feeds in
    # at the harness level, not here.

    if analysis.school_patterns:
        fpm.tradition_envelope = _envelope_from_patterns(
            analysis.school_patterns, n, margin, floor
        )
        # Also expose a center as the tradition_affiliation_vector (single point
        # = arithmetic mean of envelope; useful for venue→article distance).
        fpm.tradition_affiliation_vector = _vector_center(fpm.tradition_envelope)
    else:
        unknowns.append(
            "No school_patterns in corpus analysis — tradition_envelope empty"
        )

    if analysis.method_patterns:
        evidence_envelope = _envelope_from_patterns(
            analysis.method_patterns, n, margin, floor
        )
        fpm.evidence_type_profile = _vector_center(evidence_envelope)
        # method_envelope is a structured object — we mark the dominant
        # families as accepted, the absent-from-corpus ones as rejected.
        fpm.method_stance = _method_stance_from_patterns(
            analysis.method_patterns, n
        )
    else:
        unknowns.append(
            "No method_patterns in corpus analysis — evidence_type and "
            "method_envelope empty"
        )

    # ---- Argument move envelope ----
    # The analyzer's `genre_summary` is a {genre: share} dict already.
    if analysis.genre_summary:
        # genre_summary shares are already normalised by `_genre_shares`
        # in the analyzer. We treat each genre as a single argument move
        # axis. This is a coarse approximation; refinement (separate
        # genre vs argument_move) is a future sprint.
        fpm.argument_move_vector = dict(analysis.genre_summary)
        fpm.argument_move_envelope = _envelope_from_shares(
            analysis.genre_summary, margin, floor
        )
        fpm.genre_position = {
            "dominant_genre": _dominant_key(analysis.genre_summary),
            "share_distribution": dict(analysis.genre_summary),
        }
    else:
        unknowns.append(
            "No genre_summary in corpus analysis — argument_move_envelope "
            "and genre_position empty"
        )

    # ---- Citation expectation hints ----
    # The analyzer's citation_stats are counts/distributions, not authors.
    # We surface the stats verbatim, leave the canonical_must_cite list
    # to the citation graph step (G primary layer), not here.
    if analysis.citation_stats:
        fpm.citation_network_signature = {
            "corpus_citation_stats": analysis.citation_stats,
            "canonical_must_cite": [],  # G primary layer fills this
            "absent_traditions_risk": [],
            "_note": "From corpus stats only; canonical names require OpenCitations",
        }
    else:
        unknowns.append(
            "No citation_stats in corpus analysis — "
            "citation_network_signature placeholder only"
        )

    # ---- Meta ----
    fpm.confidence = _confidence_for(n, analysis.confidence)
    fpm.unknowns = unknowns + list(analysis.unknowns or [])

    # We do NOT touch discipline_vector / discipline_envelope from here.
    # That requires OpenAlex topic distribution (G corroborator) at the
    # harness level. We make the empty state explicit:
    if not fpm.discipline_vector and not fpm.discipline_envelope:
        fpm.unknowns.append(
            "discipline_envelope not computed by corpus_hull_builder — "
            "requires OpenAlex concepts (G corroborator) at harness level"
        )

    return fpm


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _depth_params(
    n: int, config: HullBuilderConfig
) -> tuple[float, float, str]:
    if n < 10:
        return config.margin_quick, config.floor_quick, "quick"
    if n < 35:
        return config.margin_standard, config.floor_standard, "standard"
    return config.margin_deep, config.floor_deep, "deep"


def _envelope_from_patterns(
    patterns: list[CorpusPattern],
    corpus_size: int,
    margin: float,
    floor: float,
) -> dict[str, list[float]]:
    """Convert per-pattern counts into a {key: [lo, hi]} envelope.

    `CorpusPattern.frequency` is already a share in [0, 1] from the
    analyzer. We widen by `margin` and floor by `floor`.
    """
    envelope: dict[str, list[float]] = {}
    for p in patterns:
        share = float(p.frequency)
        if share < floor:
            continue
        lo = max(0.0, share - margin)
        hi = min(1.0, share + margin)
        if hi < lo:  # defensive; shouldn't happen with positive margin
            lo, hi = hi, lo
        envelope[p.pattern_key] = [round(lo, 3), round(hi, 3)]
    return envelope


def _envelope_from_shares(
    shares: dict[str, float],
    margin: float,
    floor: float,
) -> dict[str, list[float]]:
    """Same as `_envelope_from_patterns` but for plain {key: share} dicts."""
    envelope: dict[str, list[float]] = {}
    for key, share_raw in shares.items():
        share = float(share_raw)
        if share < floor:
            continue
        lo = max(0.0, share - margin)
        hi = min(1.0, share + margin)
        envelope[key] = [round(lo, 3), round(hi, 3)]
    return envelope


def _vector_center(envelope: dict[str, list[float]]) -> dict[str, float]:
    """Arithmetic-mean center of an envelope, for downstream distance calc."""
    return {
        key: round((rng[0] + rng[1]) / 2, 3)
        for key, rng in envelope.items()
        if isinstance(rng, list) and len(rng) >= 2
    }


def _method_stance_from_patterns(
    patterns: list[CorpusPattern],
    corpus_size: int,
) -> dict[str, Any]:
    """Build a venue method_stance from observed method patterns.

    A method appearing in ≥ 20 % of the corpus is `accepted`. A method
    with frequency < 5 % is `rejected_or_absent` (we surface as
    rejected only if at least one other method dominates — otherwise
    it stays as unknown).
    """
    accepted: list[str] = []
    rejected_or_absent: list[str] = []
    for p in patterns:
        share = float(p.frequency)
        if share >= 0.20:
            accepted.append(p.pattern_key)
        elif share < 0.05:
            rejected_or_absent.append(p.pattern_key)

    # If we have at least one accepted method, surface absent ones as
    # rejected. Otherwise the rejected_or_absent are just "not seen".
    if accepted:
        rejected = rejected_or_absent
    else:
        rejected = []

    explicit_required = any(
        share_ok(p) for p in patterns
        if "explicit" in p.pattern_key.lower()
    )

    return {
        "requires_explicit_method": explicit_required,
        "accepted_method_families": accepted,
        "rejected_method_families": rejected,
        "_corpus_size": corpus_size,
        "_evidence_status": "corpus_observation",
    }


def share_ok(pattern: CorpusPattern, threshold: float = 0.10) -> bool:
    return float(pattern.frequency) >= threshold


def _dominant_key(shares: dict[str, float]) -> str | None:
    if not shares:
        return None
    return max(shares.items(), key=lambda kv: kv[1])[0]


def _confidence_for(n: int, analyzer_confidence: str | None) -> str:
    """Hull confidence is bounded above by analyzer confidence."""
    analyzer_conf = (analyzer_confidence or "low").lower()
    if n >= 35 and analyzer_conf == "high":
        return "high"
    if n >= 15 and analyzer_conf in ("high", "medium"):
        return "medium"
    return "low"
