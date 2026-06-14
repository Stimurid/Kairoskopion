"""Mavrinsky venue selection v1 — first evidence-backed fit pass.

Not a journal recommender. NOT keyword ranking. This is the first
real ArticleModel × VenueProfilePackage × corpus-evidence fit run.

What lives here:

  - `mavrinsky_article_model()` — structured ArticleModel built from the
    article-side gold rubric (not from memory; the rubric is committed
    in benchmarks/golden/).
  - `assess_fit_for_vpkg()` — 16-axis preliminary FitAssessment per
    rubric v1 §8. Allowed values: strong / medium / weak / bad /
    unknown. Every axis points to one of: article_evidence /
    vpkg_evidence / corpus_observation / cyberleninka_observation /
    inference / unknown.
  - `select_shortlist()` — buckets all VPKGs:
    good_fit / possible_but_costly / sibling_manuscript /
    poor_fit / insufficient_data.
  - `build_mismatch_map()` — preliminary MismatchMap for top venues.
  - `stub_rewrite_plan()`, `stub_citation_plan()`, `stub_risk_report()`.

NO LLM. NO numeric black-box score. NO invented references.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# D. Mavrinsky structured ArticleModel
# ---------------------------------------------------------------------------

def mavrinsky_article_model() -> dict[str, Any]:
    """Structured ArticleModel from benchmarks/golden/mavrinsky_article_side_gold.md.

    Marked PRELIMINARY_ARTICLE_MODEL: built from the rubric, not from
    a live LLM extraction. Fields without rubric support are explicit
    unknowns.
    """
    return {
        "_lifecycle_status": "PRELIMINARY_ARTICLE_MODEL",
        "_source": "benchmarks/golden/mavrinsky_article_side_gold.md",
        "title_working": (
            "Желание, виртуальность и интерфейс: к онтологии технических форм"
        ),
        "object_of_inquiry": (
            "Interface as ontological technical form, in continental "
            "register, treated through desire-as-excess (vs Lacanian "
            "desire-as-lack) and the dispositif/capture apparatus."
        ),
        "central_problem": (
            "How does interface mediate technicity-of-subject under "
            "post-structuralist accounts of desire and capture? What is "
            "the difference between greedy and generous interface as "
            "ontological regimes?"
        ),
        "core_claims": [
            "Desire-as-excess displaces Lacanian desire-as-lack and "
            "reframes the interface as productive ontology, not deficit.",
            "Greedy interface = dispositif of capture; generous interface "
            "= opening of possibility space.",
            "The greedy/generous distinction is ontological, not "
            "ergonomic.",
        ],
        "genre": "theoretical_essay",
        "disciplinary_registers": [
            "continental_philosophy",
            "philosophy_of_technology",
            "media_philosophy",
        ],
        "novelty_mode": "concept_introduction_with_reconstruction",
        "method_status": "no_method_continental_argument",
        "argument_form": "concept_reconstruction_plus_concept_introduction",
        "evidence_type_profile": {
            "theoretical_argument": 0.85,
            "textual_analysis_implicit": 0.10,
            "case_study": 0.0,
            "quantitative_data": 0.0,
            "experimental": 0.0,
        },
        "tribes_present": {
            "Deleuze_Guattari": "constructive",
            "Foucault": "constructive",
            "Agamben": "constructive",
            "Lacan": "foil",
            "Simondon": "absent",
            "Stiegler": "absent",
            "Latour_ANT": "absent",
            "HCI_dark_patterns": "absent",
        },
        "citation_ecology_current": "continental_philosophy_canon_only",
        "protected_core": [
            "desire-as-excess shift",
            "interface as dispositif/capture",
            "greedy/generous distinction as ontology, not UX",
        ],
        "language_register": {
            "primary_language": "ru",
            "abstract_languages": ["ru", "en"],
            "register": "academic_dense",
            "jargon_density": 0.78,
        },
        "geographic_affinity": {
            "author_region": "Russia",
            "intellectual_tradition": "France_Germany",
        },
        "audience": "deep_specialist",
        "unknowns": [
            "exact reference list not extracted here (rubric does not pin it)",
            "exact word count not pinned by rubric",
        ],
    }


# ---------------------------------------------------------------------------
# E. FitAssessment v1
# ---------------------------------------------------------------------------

FIT_AXES = [
    "topic_fit",
    "disciplinary_fit",
    "genre_fit",
    "argument_form_fit",
    "method_fit",
    "novelty_mode_fit",
    "citation_ecology_fit",
    "language_register_fit",
    "formal_compliance_fit",
    "publication_regime_fit",
    "rewrite_effort",
    "citation_effort",
    "field_core_risk",
    "strategic_value",
    "evidence_confidence",
    "unknowns",
]

ALLOWED_VALUES = {"strong", "medium", "weak", "bad", "unknown"}


def _axis(value: str, evidence: str, note: str = "") -> dict[str, Any]:
    if value not in ALLOWED_VALUES:
        value = "unknown"
    return {"value": value, "evidence": evidence, "note": note}


# Continental / Deleuze-Foucault-Agamben token bags used to detect
# topic alignment via VPKG corpus or scope material.
_CONTINENTAL_TOKENS = {
    "deleuze", "guattari", "foucault", "agamben", "heidegger",
    "phenomenolog", "continental", "post-structural", "poststructural",
    "philosophy", "philosophical", "media philosophy", "media-philosophy",
    "dispositif", "biopolit", "ontology", "subjectivity",
}
_PHILTECH_TOKENS = {
    "philosophy of technology", "techn", "simondon", "stiegler",
    "yuk hui", "verbeek", "postphenomenolog", "ihde",
    "philosophy_of_technology", "technological mediation",
}
_STS_TOKENS = {
    "sts", "science and technology studies", "actor-network",
    "actor network", "latour", "callon", "platform studies",
    "sociotechnical", "infrastructure",
}
_HCI_TOKENS = {
    "human-computer interaction", "human computer interaction",
    "hci", "dark pattern", "design", "user study", "user experience",
    "ux", "ui", "usability",
}
_THEORY_TOKENS = {
    "theory", "theoretical", "conceptual", "philosophical", "essay",
    "ontolog", "metaphysic",
}
_EMPIRICAL_TOKENS = {
    "empirical", "data", "interview", "ethnograph", "survey",
    "experiment", "regression", "questionnaire", "n=",
}


def _vpkg_text_blob(vpkg: dict[str, Any], corpus_titles: list[str] | None = None) -> str:
    """Concatenate the venue's text-bearing fields for token detection."""
    parts: list[str] = []
    for k in ("canonical_name", "publisher"):
        v = vpkg.get(k)
        if v:
            parts.append(str(v))
    for c in vpkg.get("discovery_clusters", []) or []:
        parts.append(str(c))
    if corpus_titles:
        parts.extend(corpus_titles)
    return " ".join(parts).lower()


def _count_hits(blob: str, tokens: set[str]) -> int:
    return sum(1 for t in tokens if t in blob)


def assess_fit_for_vpkg(
    article_model: dict[str, Any],
    vpkg: dict[str, Any],
    corpus_titles: list[str] | None = None,
    corpus_works_n: int = 0,
    has_formal_profile: bool = False,
    is_russian_venue: bool = False,
) -> dict[str, Any]:
    """Build a 16-axis FitAssessment for one venue."""
    blob = _vpkg_text_blob(vpkg, corpus_titles)
    cont = _count_hits(blob, _CONTINENTAL_TOKENS)
    pht = _count_hits(blob, _PHILTECH_TOKENS)
    sts = _count_hits(blob, _STS_TOKENS)
    hci = _count_hits(blob, _HCI_TOKENS)
    theory = _count_hits(blob, _THEORY_TOKENS)
    empirical = _count_hits(blob, _EMPIRICAL_TOKENS)
    completeness = vpkg.get("completeness", {}) or {}
    has_corpus = completeness.get("PublishedCorpusHull") in ("present", "partial")
    has_board = completeness.get("EditorialBoardCloud") in ("present", "partial")
    has_id = bool(vpkg.get("openalex_source_id") or vpkg.get("issns"))

    # ---- topic_fit ----
    if has_corpus:
        topic_hits = cont + pht
        if topic_hits >= 3:
            topic_fit = _axis("medium", "corpus_observation",
                              f"continental/philtech token hits={topic_hits} in corpus titles")
        elif topic_hits >= 1:
            topic_fit = _axis("weak", "corpus_observation",
                              f"only {topic_hits} continental/philtech hit(s)")
        else:
            topic_fit = _axis("bad", "corpus_observation",
                              "no continental/philtech hits in corpus titles")
    else:
        topic_fit = _axis("unknown", "vpkg_evidence",
                           "no corpus hull — topic from venue name/cluster only; insufficient")

    # ---- disciplinary_fit ----
    if has_corpus or vpkg.get("discovery_clusters"):
        cl = " ".join(vpkg.get("discovery_clusters") or []).lower()
        if any(c in cl for c in ("continental_philosophy", "media_philosophy", "philosophy_of_technology",
                                   "ru_philosophy")):
            disc_fit = _axis("medium" if cont + pht >= 2 else "weak",
                              "vpkg_evidence",
                              f"cluster signal: {cl[:60]}")
        elif "sts" in cl or "hci" in cl:
            disc_fit = _axis("weak", "vpkg_evidence", "STS/HCI cluster — adjacent")
        else:
            disc_fit = _axis("weak", "vpkg_evidence", f"cluster: {cl[:60]}")
    else:
        disc_fit = _axis("unknown", "vpkg_evidence", "no cluster, no corpus")

    # ---- genre_fit ----
    if has_corpus and theory > 0 and empirical == 0:
        genre_fit = _axis("medium", "corpus_observation",
                           f"theoretical signal {theory}, no empirical")
    elif has_corpus and empirical > theory and empirical >= 2:
        genre_fit = _axis("weak", "corpus_observation",
                           "empirical-leaning corpus vs theoretical_essay article")
    elif has_corpus:
        genre_fit = _axis("medium", "corpus_observation",
                           f"theory={theory} empirical={empirical}")
    else:
        genre_fit = _axis("unknown", "vpkg_evidence",
                           "no corpus to verify genre")

    # ---- argument_form_fit ----
    # Article does concept_reconstruction+introduction. Venues that empirical-skew reject it.
    if has_corpus and empirical >= 3 and theory <= 1:
        arg_fit = _axis("bad", "corpus_observation",
                         "venue corpus skews empirical-conceptual; concept reconstruction not the norm")
    elif has_corpus and theory >= 2:
        arg_fit = _axis("medium", "corpus_observation",
                         "venue corpus admits theoretical/conceptual argument form")
    else:
        arg_fit = _axis("unknown", "vpkg_evidence",
                         "no corpus — argument form fit undetermined")

    # ---- method_fit ----
    # Article has no_method. Venues requiring explicit method = bad.
    if has_formal_profile:
        method_fit = _axis("medium", "vpkg_evidence",
                            "formal profile present; method requirement verifiable")
    elif has_corpus and empirical >= 3:
        method_fit = _axis("weak", "corpus_observation",
                            "corpus suggests empirical methods expected; article has none")
    else:
        method_fit = _axis("unknown", "vpkg_evidence", "method requirement unknown")

    # ---- novelty_mode_fit ----
    if has_corpus and (theory + cont + pht) >= 3:
        nov_fit = _axis("medium", "corpus_observation",
                         "venue accepts conceptual-novelty contributions")
    else:
        nov_fit = _axis("unknown", "vpkg_evidence",
                         "novelty mode tolerance unknown")

    # ---- citation_ecology_fit ----
    if cont >= 2:
        cite_fit = _axis("medium", "corpus_observation",
                          "continental token presence — citation ecology adjacent")
    elif pht >= 2 and cont == 0:
        cite_fit = _axis("weak", "corpus_observation",
                          "philtech-mainstream corpus needs bridge to Deleuze/Agamben line")
    else:
        cite_fit = _axis("unknown", "vpkg_evidence",
                          "citation ecology cannot be assessed without corpus refs")

    # ---- language_register_fit ----
    art_lang = article_model.get("language_register", {}).get("primary_language", "ru")
    venue_langs = vpkg.get("languages") or []
    if art_lang == "ru" and is_russian_venue:
        lang_fit = _axis("strong", "vpkg_evidence",
                          "RU article × RU venue")
    elif art_lang == "ru" and any(l == "en" for l in venue_langs):
        lang_fit = _axis("medium", "vpkg_evidence",
                          "article in RU; venue requires EN — translation needed")
    elif art_lang == "ru" and not venue_langs:
        lang_fit = _axis("unknown", "vpkg_evidence", "venue language unknown")
    else:
        lang_fit = _axis("medium", "vpkg_evidence",
                          f"art={art_lang} venue={venue_langs}")

    # ---- formal_compliance_fit ----
    fc_fit = _axis("unknown", "vpkg_evidence",
                    "no FormalSubmissionProfile yet") if not has_formal_profile \
        else _axis("medium", "vpkg_evidence", "formal profile available")

    # ---- publication_regime_fit ----
    pr_fit = _axis("unknown", "vpkg_evidence",
                    "publication_regime_model not built") if not vpkg.get(
        "publication_regime_id"
    ) else _axis("medium", "vpkg_evidence", "regime model attached")

    # ---- rewrite_effort ----
    if empirical >= 3 or hci >= 2:
        rewrite = _axis("weak", "corpus_observation",
                         "heavy rewrite needed (empirical or HCI venue)")
    elif pht >= 2 and cont == 0:
        rewrite = _axis("medium", "corpus_observation",
                         "moderate rewrite + citation bridge to philtech canon")
    elif cont >= 2:
        rewrite = _axis("strong", "corpus_observation",
                         "minimal rewrite — continental-friendly venue")
    else:
        rewrite = _axis("unknown", "vpkg_evidence", "rewrite effort undetermined")

    # ---- citation_effort ----
    if pht >= 2 and cont == 0:
        cite_eff = _axis("weak", "corpus_observation",
                          "must add Simondon/Stiegler/Hui bridge")
    elif cont >= 2:
        cite_eff = _axis("strong", "corpus_observation",
                          "existing canon already aligned")
    elif sts >= 2 or hci >= 2:
        cite_eff = _axis("weak", "corpus_observation",
                          "must rewire to Latour/ANT or HCI canon")
    else:
        cite_eff = _axis("unknown", "vpkg_evidence", "citation effort unclear")

    # ---- field_core_risk ----
    # destructive_high = HCI; high = STS; medium = philtech; low = continental
    if hci >= 2:
        fcr = _axis("bad", "corpus_observation",
                     "HCI venue would dissolve desire-as-excess into UX")
    elif sts >= 2 and empirical >= 2:
        fcr = _axis("weak", "corpus_observation",
                     "STS empirical pressure threatens conceptual core")
    elif pht >= 2 and cont == 0:
        fcr = _axis("medium", "corpus_observation",
                     "philtech bridge preserves core if Deleuze/Agamben line stays")
    elif cont >= 2:
        fcr = _axis("strong", "corpus_observation",
                     "continental venue preserves core natively")
    else:
        fcr = _axis("unknown", "vpkg_evidence", "field_core_risk undetermined")

    # ---- strategic_value ----
    # If venue has corpus and identity and language match, strategic value is decent.
    if has_id and has_corpus:
        if has_board:
            sv = _axis("strong", "vpkg_evidence",
                        "venue is real and partially profiled (identity + corpus + board)")
        else:
            sv = _axis("medium", "vpkg_evidence",
                        "venue is real and partially profiled (identity + corpus)")
    elif has_id:
        sv = _axis("medium", "vpkg_evidence", "venue identity attached only")
    else:
        sv = _axis("weak", "vpkg_evidence", "venue identity thin")

    # ---- evidence_confidence ----
    completeness_score = sum(
        1 for v in completeness.values() if v == "present"
    ) + 0.5 * sum(1 for v in completeness.values() if v == "partial")
    if completeness_score >= 4:
        ec = _axis("strong", "vpkg_evidence",
                    f"completeness={completeness_score}")
    elif completeness_score >= 2:
        ec = _axis("medium", "vpkg_evidence",
                    f"completeness={completeness_score}")
    else:
        ec = _axis("weak", "vpkg_evidence",
                    f"completeness={completeness_score}")

    # ---- unknowns (axis) ----
    unknowns_count = sum(
        1 for ax in (topic_fit, disc_fit, genre_fit, arg_fit, method_fit,
                      nov_fit, cite_fit, lang_fit, fc_fit, pr_fit, rewrite,
                      cite_eff, fcr, sv) if ax["value"] == "unknown"
    )
    if unknowns_count >= 8:
        unk = _axis("bad", "inference", f"{unknowns_count}/14 axes unknown")
    elif unknowns_count >= 5:
        unk = _axis("weak", "inference", f"{unknowns_count}/14 axes unknown")
    elif unknowns_count >= 3:
        unk = _axis("medium", "inference", f"{unknowns_count}/14 axes unknown")
    else:
        unk = _axis("strong", "inference", f"{unknowns_count}/14 axes unknown")

    return {
        "venue_profile_package_id": vpkg.get("venue_profile_package_id"),
        "canonical_name": vpkg.get("canonical_name"),
        "_lifecycle_status": "PRELIMINARY",
        "axes": {
            "topic_fit": topic_fit,
            "disciplinary_fit": disc_fit,
            "genre_fit": genre_fit,
            "argument_form_fit": arg_fit,
            "method_fit": method_fit,
            "novelty_mode_fit": nov_fit,
            "citation_ecology_fit": cite_fit,
            "language_register_fit": lang_fit,
            "formal_compliance_fit": fc_fit,
            "publication_regime_fit": pr_fit,
            "rewrite_effort": rewrite,
            "citation_effort": cite_eff,
            "field_core_risk": fcr,
            "strategic_value": sv,
            "evidence_confidence": ec,
            "unknowns_axis": unk,
        },
        "_signals_used": {
            "continental_hits": cont,
            "philtech_hits": pht,
            "sts_hits": sts,
            "hci_hits": hci,
            "theory_hits": theory,
            "empirical_hits": empirical,
            "corpus_works_n": corpus_works_n,
            "has_corpus": has_corpus,
            "has_board": has_board,
            "has_formal_profile": has_formal_profile,
            "is_russian_venue": is_russian_venue,
        },
    }


# ---------------------------------------------------------------------------
# F. Shortlist + MismatchMap
# ---------------------------------------------------------------------------

def _bucket(fit: dict[str, Any]) -> str:
    """Legacy v1 bucketer. Kept for backwards-compat. Use `_bucket_v2`."""
    axes = fit["axes"]
    fcr = axes["field_core_risk"]["value"]
    rewrite = axes["rewrite_effort"]["value"]
    topic = axes["topic_fit"]["value"]
    confidence = axes["evidence_confidence"]["value"]
    unknowns = axes["unknowns_axis"]["value"]

    if confidence == "weak" and unknowns in ("weak", "bad"):
        return "insufficient_data"
    if fcr == "bad":
        return "poor_fit"
    if topic in ("strong", "medium") and rewrite == "strong" and fcr == "strong":
        return "good_fit"
    if topic in ("medium", "weak") and rewrite in ("strong", "medium") and fcr in ("strong", "medium"):
        return "possible_but_costly"
    if fcr == "weak":
        return "sibling_manuscript"
    return "possible_but_costly"


def _bucket_v2(fit: dict[str, Any]) -> tuple[str, list[str]]:
    """Calibrated bucketer per v2 rubric. Returns (bucket, reasons).

    Order matters — first matching rule wins. Reasons are short
    human-readable strings stating which axis values triggered the
    rule (and so why the label is what it is).

    Rules:
      1. INSUFFICIENT_DATA — too many `unknown` axes, or the corpus/
         identity stack is too thin to judge. Catchall for "we don't
         know enough to call it". No catchall to possible_but_costly.
      2. POOR_FIT — structural mismatch on topic / discipline /
         argument form / field core. Cannot be rewritten without
         destroying the article.
      3. SIBLING_MANUSCRIPT — venue would require a genre / method /
         empirical conversion that produces a different article, not
         a rewrite of this one.
      4. GOOD_FIT — strict: topic medium+, rewrite strong, field core
         strong, citation ecology medium+, confidence medium+.
      5. POSSIBLE_BUT_COSTLY — plausible bounded path with rewrite or
         citation effort but core preserved. Topic medium+ or
         disciplinary medium+, rewrite strong/medium, fcr strong/medium,
         arg_form not bad, confidence medium+.
      6. Else INSUFFICIENT_DATA (no permissive catchall).
    """
    axes = fit["axes"]
    topic = axes["topic_fit"]["value"]
    disc = axes["disciplinary_fit"]["value"]
    genre = axes["genre_fit"]["value"]
    arg_form = axes["argument_form_fit"]["value"]
    method = axes["method_fit"]["value"]
    fcr = axes["field_core_risk"]["value"]
    rewrite = axes["rewrite_effort"]["value"]
    cite = axes["citation_ecology_fit"]["value"]
    cite_eff = axes["citation_effort"]["value"]
    confidence = axes["evidence_confidence"]["value"]
    unknowns_axis = axes["unknowns_axis"]["value"]

    unknown_count = sum(
        1 for k, ax in axes.items()
        if k != "unknowns_axis" and ax["value"] == "unknown"
    )

    sig = fit.get("_signals_used", {}) or {}
    has_corpus = bool(sig.get("has_corpus"))

    # ---- Rule 1: INSUFFICIENT_DATA ---------------------------------
    # Reject early when we cannot judge.
    if confidence == "weak" and unknown_count >= 6:
        return ("insufficient_data", [
            f"confidence=weak, {unknown_count}/15 axes unknown",
        ])
    if not has_corpus and topic == "unknown":
        return ("insufficient_data", [
            "no corpus hull, topic_fit unknown — cannot judge",
        ])
    if unknown_count >= 8:
        return ("insufficient_data", [
            f"{unknown_count}/15 axes unknown — selection unsafe",
        ])
    # Russian venue without any RU support evidence and confidence weak
    if (sig.get("is_russian_venue") and confidence == "weak"
            and unknown_count >= 5):
        return ("insufficient_data", [
            "Russian venue with weak confidence and many unknowns",
        ])

    # ---- Rule 2: POOR_FIT ------------------------------------------
    # Structural mismatch — rewriting would destroy the article.
    if fcr == "bad":
        return ("poor_fit", [
            f"field_core_risk=bad (destructive): "
            f"{axes['field_core_risk']['note']}",
        ])
    if topic == "bad" and disc in ("bad", "weak"):
        return ("poor_fit", [
            "topic=bad and disciplinary=bad/weak — structural mismatch",
        ])

    # ---- Rule 3: SIBLING_MANUSCRIPT --------------------------------
    # The venue would require a different manuscript, not a rewrite.
    if arg_form == "bad":
        return ("sibling_manuscript", [
            "argument_form=bad: venue expects empirical/conceptual hybrid; "
            "produce sibling manuscript instead of adapting",
        ])
    if method == "weak" and genre == "weak":
        return ("sibling_manuscript", [
            "method=weak and genre=weak: empirical conversion required — "
            "sibling manuscript more honest than rewrite",
        ])
    if fcr == "weak" and arg_form in ("weak", "unknown"):
        return ("sibling_manuscript", [
            f"field_core_risk=weak and argument_form={arg_form}: "
            "preserving core requires a different article",
        ])

    # ---- Rule 4: GOOD_FIT ------------------------------------------
    # Strict: must be a near-native fit.
    if (topic in ("strong", "medium")
            and rewrite == "strong"
            and fcr == "strong"
            and cite in ("strong", "medium")
            and confidence in ("strong", "medium")):
        return ("good_fit", [
            f"topic={topic}, rewrite=strong, fcr=strong, "
            f"citation_ecology={cite}, confidence={confidence}",
        ])

    # ---- Rule 5: POSSIBLE_BUT_COSTLY -------------------------------
    # Plausible bounded path, core preserved.
    if (topic in ("strong", "medium", "weak")
            and disc in ("strong", "medium", "weak")
            and rewrite in ("strong", "medium")
            and fcr in ("strong", "medium")
            and arg_form != "bad"
            and confidence in ("strong", "medium")
            and (cite in ("strong", "medium") or cite_eff in ("strong", "medium", "weak"))):
        return ("possible_but_costly", [
            f"topic={topic}, rewrite={rewrite}, fcr={fcr}, "
            f"citation_effort={cite_eff}, confidence={confidence}",
        ])

    # ---- Rule 6: default to INSUFFICIENT_DATA, NOT possible_but_costly
    return ("insufficient_data", [
        f"no rule matched: topic={topic}, disc={disc}, arg_form={arg_form}, "
        f"fcr={fcr}, rewrite={rewrite}, confidence={confidence}, "
        f"unknown_axes={unknown_count}",
    ])


def select_shortlist(
    fits: list[dict[str, Any]], *, calibrated: bool = True,
) -> dict[str, list[dict[str, Any]]]:
    """Bucket fits.

    `calibrated=True` uses `_bucket_v2` (default; v2 rubric, no
    permissive catchall). `calibrated=False` falls back to the legacy
    `_bucket` (kept for one release for diffing).
    """
    buckets: dict[str, list[dict[str, Any]]] = {
        "good_fit": [], "possible_but_costly": [],
        "sibling_manuscript": [], "poor_fit": [],
        "insufficient_data": [],
    }
    for f in fits:
        if calibrated:
            b, reasons = _bucket_v2(f)
        else:
            b = _bucket(f)
            reasons = ["(legacy bucketer)"]
        buckets[b].append({
            "venue_profile_package_id": f["venue_profile_package_id"],
            "canonical_name": f["canonical_name"],
            "bucket": b,
            "label_reasons": reasons,
            "topic_fit": f["axes"]["topic_fit"]["value"],
            "rewrite_effort": f["axes"]["rewrite_effort"]["value"],
            "field_core_risk": f["axes"]["field_core_risk"]["value"],
            "evidence_confidence": f["axes"]["evidence_confidence"]["value"],
            "_signals_used": f["_signals_used"],
        })
    return buckets


def build_mismatch_map(
    article_model: dict[str, Any], fit: dict[str, Any]
) -> dict[str, Any]:
    """Preliminary MismatchMap per rubric v1 §9."""
    mismatches: list[dict[str, Any]] = []
    axes = fit["axes"]
    sig = fit["_signals_used"]

    if axes["citation_ecology_fit"]["value"] in ("weak", "bad"):
        mismatches.append({
            "article_side": "continental_canon (Deleuze/Foucault/Agamben)",
            "venue_side": "different canon",
            "mismatch_axis": "citation_ecology_fit",
            "severity": "high" if axes["citation_ecology_fit"]["value"] == "bad" else "medium",
            "evidence_refs": ["corpus_observation"],
            "possible_actions": [
                "add citation bridge",
                "translate concept into venue canon vocabulary",
            ],
            "field_core_risk": "medium",
            "requires_user_acceptance": True,
        })
    if axes["argument_form_fit"]["value"] == "bad":
        mismatches.append({
            "article_side": "concept reconstruction + concept introduction",
            "venue_side": "empirical-conceptual hybrid expected",
            "mismatch_axis": "argument_form_fit",
            "severity": "high",
            "evidence_refs": ["corpus_observation"],
            "possible_actions": [
                "create sibling empirical manuscript",
                "do not adapt main draft",
            ],
            "field_core_risk": "high",
            "requires_user_acceptance": True,
        })
    if axes["method_fit"]["value"] == "weak":
        mismatches.append({
            "article_side": "no explicit method (continental argument)",
            "venue_side": "empirical methods expected",
            "mismatch_axis": "method_fit",
            "severity": "medium",
            "evidence_refs": ["corpus_observation"],
            "possible_actions": [
                "clarify method status (conceptual analysis) section",
                "or: sibling manuscript",
            ],
            "field_core_risk": "medium",
            "requires_user_acceptance": True,
        })
    if axes["field_core_risk"]["value"] == "bad":
        mismatches.append({
            "article_side": "desire-as-excess ontology / dispositif framing",
            "venue_side": "UX / HCI framing",
            "mismatch_axis": "field_core_risk",
            "severity": "destructive",
            "evidence_refs": ["corpus_observation"],
            "possible_actions": [
                "do not submit",
                "or: create derivative HCI-shaped manuscript explicitly",
            ],
            "field_core_risk": "destructive",
            "requires_user_acceptance": True,
        })
    if axes["language_register_fit"]["value"] in ("medium", "weak"):
        if not fit["_signals_used"].get("is_russian_venue"):
            mismatches.append({
                "article_side": "primary language: RU",
                "venue_side": "EN required",
                "mismatch_axis": "language_register_fit",
                "severity": "medium",
                "evidence_refs": ["vpkg_evidence"],
                "possible_actions": ["translate to EN"],
                "field_core_risk": "low",
                "requires_user_acceptance": True,
            })

    return {
        "venue_profile_package_id": fit["venue_profile_package_id"],
        "canonical_name": fit["canonical_name"],
        "_lifecycle_status": "PRELIMINARY",
        "mismatches": mismatches,
        "summary": (
            f"{len(mismatches)} mismatches; "
            f"core_risk={axes['field_core_risk']['value']}; "
            f"signals: cont={sig['continental_hits']} pht={sig['philtech_hits']} "
            f"sts={sig['sts_hits']} hci={sig['hci_hits']}"
        ),
    }


# ---------------------------------------------------------------------------
# G. Stubs
# ---------------------------------------------------------------------------

def stub_rewrite_plan(article_model: dict[str, Any],
                       fit: dict[str, Any]) -> dict[str, Any]:
    axes = fit["axes"]
    actions: list[dict[str, Any]] = []
    if axes["topic_fit"]["value"] in ("medium", "weak"):
        actions.append({
            "target": "abstract+title",
            "action": "reposition: lead with greedy/generous interface distinction; "
                       "reduce desire-as-excess in title",
            "protected_core_impact": "minimal",
        })
    if axes["citation_ecology_fit"]["value"] in ("weak", "bad"):
        actions.append({
            "target": "introduction",
            "action": "add 1-2 paragraphs bridging to venue's canon (see CitationPlan)",
            "protected_core_impact": "minimal if Deleuze/Agamben kept central",
        })
    if axes["argument_form_fit"]["value"] in ("weak", "bad"):
        actions.append({
            "target": "section_architecture",
            "action": "consider sibling manuscript instead of adapting this one",
            "protected_core_impact": "high if forced",
        })
    if axes["method_fit"]["value"] in ("weak", "bad"):
        actions.append({
            "target": "method_status_section",
            "action": "add explicit 'on method' paragraph naming continental "
                       "argument as method-type",
            "protected_core_impact": "low",
        })
    return {
        "_lifecycle_status": "STUB",
        "venue_profile_package_id": fit["venue_profile_package_id"],
        "actions": actions,
        "protected_core_summary": (
            "Preserve: desire-as-excess shift; interface as dispositif/capture; "
            "greedy/generous as ontology not UX."
        ),
    }


def stub_citation_plan(article_model: dict[str, Any],
                        fit: dict[str, Any]) -> dict[str, Any]:
    sig = fit["_signals_used"]
    bridges: list[dict[str, Any]] = []
    if sig["philtech_hits"] >= 2 and sig["continental_hits"] == 0:
        bridges.append({
            "bridge_category": "philtech_canon",
            "likely_anchors": ["Simondon", "Stiegler", "Yuk Hui",
                                "Heidegger on technology"],
            "evidence_status": "inference_from_corpus_token_distribution",
        })
    if sig["sts_hits"] >= 2:
        bridges.append({
            "bridge_category": "STS_canon",
            "likely_anchors": ["Latour", "Callon", "platform studies"],
            "evidence_status": "inference_from_corpus_token_distribution",
        })
    if sig["hci_hits"] >= 2:
        bridges.append({
            "bridge_category": "HCI_canon",
            "likely_anchors": ["affordances", "dark patterns",
                                "persuasive technology"],
            "evidence_status": "inference_from_corpus_token_distribution",
        })
    return {
        "_lifecycle_status": "STUB",
        "venue_profile_package_id": fit["venue_profile_package_id"],
        "missing_bridge_categories": bridges,
        "references_to_verify": [
            "exact references must come from VPKG corpus reference data — "
            "not yet wired (deferred); do not fabricate"
        ],
        "dangerous_padding_warnings": [
            "do not cite STS empirical authors decoratively if article remains theoretical"
        ],
    }


def stub_risk_report(article_model: dict[str, Any],
                      fit: dict[str, Any]) -> dict[str, Any]:
    axes = fit["axes"]
    risks: list[dict[str, Any]] = []
    risks.append({
        "category": "formal_risk",
        "level": axes["formal_compliance_fit"]["value"],
        "note": "FormalSubmissionProfile unknown — verify before submission",
    })
    risks.append({
        "category": "scope_risk",
        "level": axes["topic_fit"]["value"],
        "note": "topic alignment derived from corpus token signal only",
    })
    risks.append({
        "category": "method_risk",
        "level": axes["method_fit"]["value"],
        "note": "no method in article; venue method-requirement unknown",
    })
    risks.append({
        "category": "citation_gap",
        "level": axes["citation_ecology_fit"]["value"],
        "note": "venue canon overlap with article continental canon",
    })
    risks.append({
        "category": "ai_policy_unknowns",
        "level": "unknown",
        "note": "AI disclosure policy not extracted",
    })
    risks.append({
        "category": "apc_oa_unknowns",
        "level": "unknown",
        "note": "OA/APC not extracted",
    })
    risks.append({
        "category": "field_core_loss_risk",
        "level": axes["field_core_risk"]["value"],
        "note": "destructive only on HCI; medium on philtech (needs bridge); low on continental",
    })
    risks.append({
        "category": "insufficient_data",
        "level": "high" if axes["evidence_confidence"]["value"] == "weak" else "medium",
        "note": f"unknowns={axes['unknowns_axis']['note']}",
    })
    return {
        "_lifecycle_status": "STUB",
        "venue_profile_package_id": fit["venue_profile_package_id"],
        "risks": risks,
    }


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------

def run_selection_over_registry(
    registry,
    *,
    output_dir: Path,
) -> dict[str, Any]:
    """Run the v1 selection over every VPKG in the registry. Persist results."""
    output_dir.mkdir(parents=True, exist_ok=True)
    article = mavrinsky_article_model()

    fits: list[dict[str, Any]] = []
    for vpkg in registry.list_all():
        vd = vpkg.to_dict() if hasattr(vpkg, "to_dict") else vpkg
        # We don't have direct access to mined works' titles here without
        # re-fetch; the corpus_titles arg stays empty. Real corpus signals
        # come from cluster names + venue scope text only at this layer.
        # Token detection still works because clusters carry the discipline
        # names ('continental_philosophy', 'philosophy_of_technology', etc.)
        is_ru = bool(vd.get("cyberleninka_source_id")) or "ru" in (vd.get("languages") or [])
        fit = assess_fit_for_vpkg(
            article, vd,
            corpus_titles=None,
            corpus_works_n=0,
            has_formal_profile=(
                vd.get("completeness", {}).get("FormalSubmissionProfile")
                in ("present", "partial")
            ),
            is_russian_venue=is_ru,
        )
        fits.append(fit)

    buckets = select_shortlist(fits)

    # Top candidates: union of good_fit + possible_but_costly, ranked
    # by strategic_value and field_core_risk
    top: list[dict[str, Any]] = []
    for bk in ("good_fit", "possible_but_costly"):
        top.extend(buckets[bk])
    # rank: prefer strong field_core_risk and strong evidence_confidence
    val = {"strong": 3, "medium": 2, "weak": 1, "bad": 0, "unknown": 0}
    top.sort(key=lambda r: -(val[r["field_core_risk"]] + val[r["evidence_confidence"]]))
    top_5 = top[:5]

    mismatch_maps: list[dict[str, Any]] = []
    rewrite_plans: list[dict[str, Any]] = []
    citation_plans: list[dict[str, Any]] = []
    risk_reports: list[dict[str, Any]] = []
    for entry in top_5:
        # Find the full fit
        fit = next(
            f for f in fits if f["venue_profile_package_id"]
            == entry["venue_profile_package_id"]
        )
        mismatch_maps.append(build_mismatch_map(article, fit))
        rewrite_plans.append(stub_rewrite_plan(article, fit))
        citation_plans.append(stub_citation_plan(article, fit))
        risk_reports.append(stub_risk_report(article, fit))

    artefacts = {
        "article_model": article,
        "fits": fits,
        "shortlist_buckets": buckets,
        "top_candidates": top_5,
        "mismatch_maps": mismatch_maps,
        "rewrite_plans": rewrite_plans,
        "citation_plans": citation_plans,
        "risk_reports": risk_reports,
        "_meta": {
            "total_vpkgs": len(fits),
            "bucket_counts": {k: len(v) for k, v in buckets.items()},
        },
    }
    for name, obj in (
        ("01_article_model.json", article),
        ("02_fits.json", fits),
        ("03_shortlist_buckets.json", buckets),
        ("04_top_candidates.json", top_5),
        ("05_mismatch_maps.json", mismatch_maps),
        ("06_rewrite_plans.json", rewrite_plans),
        ("07_citation_plans.json", citation_plans),
        ("08_risk_reports.json", risk_reports),
        ("00_summary.json", artefacts["_meta"]),
    ):
        (output_dir / name).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    return artefacts
