"""Tests for the deterministic corpus hull builder.

These tests enforce the six fundamental caveats from
`benchmarks/golden/venue_source_layer_map.md` §3:

- Official scope = vendor claim, not corpus fact.
- Indexing = strategic signal, not fit.
- Full text = corpus material, not metadata authority.
- Editorial board = inference, not psychology.
- Unknown != absent.
- Incomplete graph != absence of tradition.

Plus shape compatibility with the article-side `FieldPositionModel` so
`compute_field_position_fit` can consume the venue hull directly.
"""

from __future__ import annotations

import unittest

from kairoskopion.logic.field_position_fit import compute_field_position_fit
from kairoskopion.schema import FieldPositionModel, PublishedArticleCorpus
from kairoskopion.services.corpus_analyzer import (
    CorpusAnalysisResult,
    CorpusPattern,
    analyze_venue_corpus,
)
from kairoskopion.services.corpus_hull_builder import (
    HullBuilderConfig,
    build_venue_corpus_hull,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _empty_analysis(venue_id: str = "ven_test") -> CorpusAnalysisResult:
    return CorpusAnalysisResult(
        venue_model_id=venue_id,
        corpus_size=0,
        method_patterns=[],
        school_patterns=[],
        genre_summary={},
        citation_stats={},
        abstract_patterns=[],
        warnings=[],
        confidence="none",
        unknowns=[],
    )


def _synthetic_continental_analysis(
    n: int = 30, venue_id: str = "ven_continental"
) -> CorpusAnalysisResult:
    """A synthetic analysis result mimicking a continental philosophy
    journal corpus (theory-dominant, no empirical, Deleuze/Foucault
    heavy)."""
    return CorpusAnalysisResult(
        venue_model_id=venue_id,
        corpus_size=n,
        method_patterns=[
            CorpusPattern("method", "theoretical", frequency=0.70,
                          confidence="high", evidence=[f"art_{i}" for i in range(5)]),
            CorpusPattern("method", "textual", frequency=0.20,
                          confidence="medium", evidence=[]),
            CorpusPattern("method", "case_study", frequency=0.05,
                          confidence="low", evidence=[]),
            CorpusPattern("method", "experimental", frequency=0.0,
                          confidence="low", evidence=[]),
        ],
        school_patterns=[
            CorpusPattern("school", "Deleuze_Guattari", frequency=0.45,
                          confidence="high", evidence=[]),
            CorpusPattern("school", "Foucault", frequency=0.40,
                          confidence="high", evidence=[]),
            CorpusPattern("school", "Agamben", frequency=0.20,
                          confidence="medium", evidence=[]),
            CorpusPattern("school", "Latour_ANT", frequency=0.03,
                          confidence="low", evidence=[]),
        ],
        genre_summary={
            "theoretical_essay": 0.60,
            "conceptual_article": 0.30,
            "commentary": 0.10,
        },
        citation_stats={
            "avg_references": 42.5,
            "median_year": 1995,
        },
        abstract_patterns=["genealogical framing", "dispositif language"],
        warnings=[],
        confidence="high",
        unknowns=[],
    )


# ---------------------------------------------------------------------------
# 1. Aggregation from a synthetic corpus
# ---------------------------------------------------------------------------

class TestCorpusHullAggregation(unittest.TestCase):
    def test_builds_envelope_from_synthetic_continental_corpus(self):
        analysis = _synthetic_continental_analysis(n=30)
        fpm = build_venue_corpus_hull(analysis)

        # Shape: it's a venue FPM
        self.assertIsInstance(fpm, FieldPositionModel)
        self.assertEqual(fpm.entity_type, "venue")
        self.assertEqual(fpm.entity_id, "ven_continental")

        # School envelope contains the constructive triad
        self.assertIn("Deleuze_Guattari", fpm.framework_envelope or {})
        self.assertIn("Foucault", fpm.framework_envelope or {})
        self.assertIn("Agamben", fpm.framework_envelope or {})

        # Latour is below the noise floor → must NOT appear
        # (this is "incomplete graph != absence of tradition" — the
        # absence here is *not* a claim Latour is taboo; it's a noise-
        # floor exclusion the rubric tolerates)
        # We just check it's filtered, the absence-of-claim is handled
        # by §3.6 caveat, not by this test.
        self.assertNotIn("Latour_ANT", fpm.framework_envelope or {})

        # Argument move envelope populated from genre_summary
        self.assertIn("theoretical_essay", fpm.argument_move_envelope or {})

        # Method stance: theoretical accepted, experimental rejected
        ms = fpm.method_stance
        self.assertIn("theoretical", ms.get("accepted_method_families", []))
        self.assertIn("experimental", ms.get("rejected_method_families", []))

        # Confidence reflects size (n=30, analyzer high → medium for hull)
        self.assertEqual(fpm.confidence, "medium")

    def test_deep_corpus_yields_high_confidence(self):
        analysis = _synthetic_continental_analysis(n=60)
        fpm = build_venue_corpus_hull(analysis)
        self.assertEqual(fpm.confidence, "high")

    def test_quick_corpus_yields_wide_envelopes(self):
        analysis = _synthetic_continental_analysis(n=8)
        fpm = build_venue_corpus_hull(analysis)
        # Quick mode uses margin 0.20, so each envelope width should
        # be roughly 0.40 unless clipped to [0,1].
        dg_range = (fpm.framework_envelope or {}).get("Deleuze_Guattari")
        self.assertIsNotNone(dg_range)
        width = dg_range[1] - dg_range[0]
        self.assertGreaterEqual(width, 0.30)
        # Quick mode → confidence cannot exceed 'low' regardless of
        # analyzer confidence (the hull is honest about small samples).
        self.assertEqual(fpm.confidence, "low")


# ---------------------------------------------------------------------------
# 2. Unknown != absent
# ---------------------------------------------------------------------------

class TestUnknownNotAbsent(unittest.TestCase):
    def test_empty_corpus_marks_all_axes_unknown(self):
        analysis = _empty_analysis()
        fpm = build_venue_corpus_hull(analysis)
        # No envelopes populated
        self.assertFalse(fpm.framework_envelope)
        self.assertFalse(fpm.argument_move_envelope)
        # But the FPM exists with a clear unknowns marker, not silent absence
        self.assertEqual(fpm.confidence, "none")
        self.assertTrue(any("Empty corpus" in u for u in fpm.unknowns))

    def test_missing_school_patterns_logs_unknown_not_silent(self):
        analysis = _synthetic_continental_analysis(n=30)
        analysis.school_patterns = []
        fpm = build_venue_corpus_hull(analysis)
        # framework_envelope must be empty AND there must be an explicit
        # unknown explaining why (not just missing the field silently)
        self.assertFalse(fpm.framework_envelope)
        self.assertTrue(any("school" in u.lower() for u in fpm.unknowns))

    def test_missing_genre_logs_unknown(self):
        analysis = _synthetic_continental_analysis(n=30)
        analysis.genre_summary = {}
        fpm = build_venue_corpus_hull(analysis)
        self.assertFalse(fpm.argument_move_envelope)
        self.assertTrue(any("genre" in u.lower() for u in fpm.unknowns))


# ---------------------------------------------------------------------------
# 3. Official scope != corpus fact
# ---------------------------------------------------------------------------

class TestOfficialScopeNotCorpusFact(unittest.TestCase):
    """The builder operates on D corpus only. If the operator supplies
    scope text via a different path (A) and it disagrees with the
    corpus, the corpus wins for envelope construction. We test that
    the builder does NOT accept a `scope_summary` kwarg or read it
    out of the analysis result."""

    def test_builder_signature_does_not_accept_scope(self):
        # Public API has no scope/aims parameter.
        import inspect
        sig = inspect.signature(build_venue_corpus_hull)
        params = set(sig.parameters.keys())
        self.assertNotIn("scope", params)
        self.assertNotIn("aims_scope", params)
        self.assertNotIn("scope_summary", params)
        # The only accepted inputs are analysis, venue_model_id, config
        self.assertEqual(params, {"analysis", "venue_model_id", "config"})

    def test_envelope_axes_match_corpus_not_scope(self):
        # An analysis with NO continental schools — corpus is actually
        # all STS — must yield STS envelope, regardless of any (absent)
        # scope claim the analyzer's input might have carried.
        sts_analysis = CorpusAnalysisResult(
            venue_model_id="ven_sts_test",
            corpus_size=25,
            method_patterns=[
                CorpusPattern("method", "case_study", frequency=0.70,
                              confidence="high", evidence=[]),
                CorpusPattern("method", "interview_ethnographic", frequency=0.30,
                              confidence="high", evidence=[]),
            ],
            school_patterns=[
                CorpusPattern("school", "Latour_ANT", frequency=0.50,
                              confidence="high", evidence=[]),
            ],
            genre_summary={"empirical_conceptual_hybrid": 0.80},
            citation_stats={},
            abstract_patterns=[],
            warnings=[],
            confidence="high",
            unknowns=[],
        )
        fpm = build_venue_corpus_hull(sts_analysis)
        # Corpus says STS; envelope says STS. No Deleuze/Foucault
        # leakage from any "scope" hint.
        self.assertIn("Latour_ANT", fpm.framework_envelope or {})
        self.assertNotIn("Deleuze_Guattari", fpm.framework_envelope or {})
        self.assertIn("case_study",
                      fpm.method_stance.get("accepted_method_families", []))


# ---------------------------------------------------------------------------
# 4. Full text != metadata authority
# ---------------------------------------------------------------------------

class TestFullTextNotMetadataAuthority(unittest.TestCase):
    """The builder accepts a `CorpusAnalysisResult`. Whether the
    analyzer derived its patterns from abstracts, metadata, or
    full-text PDFs is opaque to the builder. The builder must NOT
    inject any metadata field (publisher, ISSN, indexing, board) into
    the FPM."""

    def test_no_metadata_fields_populated(self):
        analysis = _synthetic_continental_analysis(n=30)
        fpm = build_venue_corpus_hull(analysis)
        # institutional_signals belongs to C registry, never D corpus.
        # The builder must not populate it.
        self.assertFalse(fpm.institutional_signals)

    def test_no_publisher_or_indexing_inferred(self):
        analysis = _synthetic_continental_analysis(n=30)
        fpm = build_venue_corpus_hull(analysis)
        # No publisher claim should leak in.
        self.assertNotIn("publisher", str(fpm.institutional_signals).lower())
        self.assertNotIn("scopus", str(fpm.institutional_signals).lower())
        self.assertNotIn("wos", str(fpm.institutional_signals).lower())


# ---------------------------------------------------------------------------
# 5. Indexing != fit
# ---------------------------------------------------------------------------

class TestIndexingNotFit(unittest.TestCase):
    def test_hull_does_not_consume_indexing_signal(self):
        # Even if we craftily inject indexing into citation_stats
        # (the most-likely accidental channel), it must not move
        # discipline_envelope or framework_envelope.
        analysis = _synthetic_continental_analysis(n=30)
        analysis.citation_stats = {
            "avg_references": 42.5,
            "median_year": 1995,
            # Adversarial: try to leak indexing into citation_stats.
            "indexed_in_scopus": True,
            "scopus_quartile": "Q1",
        }
        fpm = build_venue_corpus_hull(analysis)
        # discipline and school envelopes still derive from
        # school_patterns / method_patterns only.
        self.assertIn("Deleuze_Guattari", fpm.framework_envelope or {})
        # The indexing claim survives in citation_network_signature.corpus_citation_stats
        # because the builder is faithful to inputs, BUT it must NOT
        # be promoted into institutional_signals or into the school
        # envelope.
        self.assertFalse(fpm.institutional_signals)
        sig = fpm.citation_network_signature or {}
        self.assertEqual(sig.get("canonical_must_cite"), [])  # G layer fills this


# ---------------------------------------------------------------------------
# 6. Editorial board = inference, not psychology
# ---------------------------------------------------------------------------

class TestEditorialBoardPlaceholderIsInference(unittest.TestCase):
    """The builder does not produce an EditorialBoardCloud — that's E.
    But the rubric requires that any board-derived signal carry an
    inference marker. We test the builder does not accidentally write
    a board-derived signal as a corpus fact."""

    def test_no_geographic_affinity_from_corpus(self):
        # geographic_affinity envelope requires E (board) + F (authors-
        # of-corpus). The builder has access to neither at this layer.
        # It must NOT populate geographic_affinity.
        analysis = _synthetic_continental_analysis(n=30)
        fpm = build_venue_corpus_hull(analysis)
        self.assertFalse(fpm.geographic_affinity)


# ---------------------------------------------------------------------------
# 7. Output shape compatible with article FPM for fit computation
# ---------------------------------------------------------------------------

class TestEnvelopeOutputShapeFPMCompatible(unittest.TestCase):
    def test_hull_can_be_compared_to_article_point(self):
        venue_fpm = build_venue_corpus_hull(
            _synthetic_continental_analysis(n=30)
        )
        # Article point in continental space
        article_fpm = FieldPositionModel(
            entity_type="article",
            entity_id="art_mavrinsky",
            framework_affiliation_vector={
                "Deleuze_Guattari": 0.6,
                "Foucault": 0.5,
                "Agamben": 0.4,
            },
            argument_move_vector={
                "theoretical_essay": 0.5,
                "conceptual_article": 0.3,
            },
            language_register={"language": "en"},
        )
        # compute_field_position_fit consumes both as dicts via to_dict
        fit = compute_field_position_fit(
            article_fpm.to_dict(),
            venue_fpm.to_dict(),
        )
        # It must produce a non-trivial result and a label, not crash.
        self.assertIn("axes", fit)
        self.assertGreater(len(fit["axes"]), 0)
        self.assertIn(
            fit["overall_label"],
            {"strong_candidate", "possible", "possible_but_costly",
             "poor_fit", "not_enough_data"},
        )

    def test_hull_envelope_format_is_lo_hi_list(self):
        venue_fpm = build_venue_corpus_hull(
            _synthetic_continental_analysis(n=30)
        )
        for key, rng in (venue_fpm.framework_envelope or {}).items():
            self.assertIsInstance(rng, list, f"envelope {key} not a list")
            self.assertEqual(len(rng), 2, f"envelope {key} not [lo,hi]")
            self.assertLessEqual(rng[0], rng[1], f"envelope {key} lo > hi")
            self.assertGreaterEqual(rng[0], 0.0)
            self.assertLessEqual(rng[1], 1.0)


# ---------------------------------------------------------------------------
# 8. End-to-end via analyze_venue_corpus
# ---------------------------------------------------------------------------

class TestEndToEndViaAnalyzer(unittest.TestCase):
    def test_corpus_to_hull_full_pipeline(self):
        # Build a tiny synthetic corpus + texts, run real analyzer, then
        # hand to hull builder. This confirms the pipeline is wired.
        corpus = PublishedArticleCorpus(
            venue_model_id="ven_e2e",
            corpus_size=6,
            collection_period="2020-2024",
        )
        article_texts = [
            {"title": "Dispositif and the digital",
             "abstract": "theoretical analysis of Foucault's apparatus in software systems",
             "keywords": ["Foucault", "dispositif", "theory"],
             "reference_count": 35},
            {"title": "Deleuze on capture apparatuses",
             "abstract": "conceptual reading of Deleuze and Guattari on machinic enslavement",
             "keywords": ["Deleuze", "Guattari", "theory"],
             "reference_count": 28},
            {"title": "Agamben's profanation",
             "abstract": "philosophical essay on profanation and dispositif",
             "keywords": ["Agamben", "theory"],
             "reference_count": 22},
            {"title": "Genealogy of subjectivation",
             "abstract": "Foucauldian genealogy applied to contemporary subjectivity",
             "keywords": ["Foucault", "theory"],
             "reference_count": 41},
            {"title": "Reading Anti-Oedipus today",
             "abstract": "conceptual analysis of Deleuze and Guattari",
             "keywords": ["Deleuze", "Guattari"],
             "reference_count": 30},
            {"title": "Beyond the apparatus",
             "abstract": "theoretical Foucault Deleuze synthesis",
             "keywords": ["Foucault", "Deleuze"],
             "reference_count": 25},
        ]
        analysis = analyze_venue_corpus(corpus, article_texts)
        fpm = build_venue_corpus_hull(analysis)
        # Quick mode (n=6) → wide envelopes, low confidence
        self.assertEqual(fpm.confidence, "low")
        # And some schools detected from the synthetic texts
        self.assertTrue(fpm.framework_envelope or fpm.unknowns,
                        "either schools detected or explicit unknown logged")


if __name__ == "__main__":
    unittest.main()
