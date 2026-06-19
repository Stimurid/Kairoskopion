"""Arbitrary Manuscript x Venue Validation Matrix — behavioral tests.

These tests prove Kairoskopion behaves as a general evidence-first
article-to-venue trajectory engine, not as a system tuned to one trial
case or one uploaded manuscript.

All fixtures are synthetic and non-private. No Logos-specific data is used.
"""

from pathlib import Path

from kairoskopion.services.article_modeling import (
    build_article_model,
    build_manuscript_model,
)
from kairoskopion.services.compliance import build_compliance_checklist
from kairoskopion.services.fit_assessment import assess_fit
from kairoskopion.services.mismatch_mapping import build_mismatch_map
from kairoskopion.services.rewrite_planning import build_rewrite_plan
from kairoskopion.services.risk_reporting import build_risk_report
from kairoskopion.services.scenario import build_scenario_from_dict
from kairoskopion.services.submission_pack import build_submission_pack
from kairoskopion.services.venue_profiling import build_venue_model

VM = Path(__file__).parent / "fixtures" / "validation_matrix"
MS = VM / "manuscripts"
VN = VM / "venues"


def _load(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _pipeline(ms_path: Path, vn_path: Path):
    """Run the full pipeline chain and return all artifacts."""
    ms_text = _load(ms_path)
    gl_text = _load(vn_path)

    manuscript = build_manuscript_model(ms_text, source_ref="vm_test")
    article = build_article_model(manuscript, ms_text, source_ref="vm_test")
    venue, regime = build_venue_model(gl_text, source_ref="vm_test")
    scenario = build_scenario_from_dict(
        {"goal": "validation_matrix", "target_venue_type": "journal"},
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
    )

    fit = assess_fit(article, venue, scenario)
    mismatch = build_mismatch_map(fit)
    risk = build_risk_report(article, venue, scenario, fit, mismatch)
    rewrite = build_rewrite_plan(
        mismatch,
        article_model_id=article.article_model_id,
        venue_model_id=venue.venue_model_id,
    )
    compliance = build_compliance_checklist(article, manuscript, venue, gl_text)
    pack = build_submission_pack(
        article, venue, scenario,
        fit=fit, risk=risk, compliance=compliance,
    )

    return {
        "article": article,
        "venue": venue,
        "manuscript": manuscript,
        "fit": fit,
        "mismatch": mismatch,
        "risk": risk,
        "rewrite": rewrite,
        "compliance": compliance,
        "pack": pack,
    }


def _axis(fit, name: str) -> dict | None:
    for a in fit.axes:
        if a.get("axis") == name:
            return a
    return None


# ---------- Case 1: Good fit ----------

class TestGoodFit:
    """English theoretical article x English philosophy venue."""

    def setup_method(self):
        self.r = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "english_philosophy_venue_complete.md",
        )

    def test_language_no_blocker(self):
        ax = _axis(self.r["fit"], "language_register")
        assert ax is not None
        assert ax["value"] in ("strong", "medium")

    def test_discipline_assessed(self):
        ax = _axis(self.r["fit"], "discipline")
        assert ax is not None
        assert ax["value"] != "unknown"

    def test_genre_not_weak(self):
        ax = _axis(self.r["fit"], "genre")
        assert ax is not None
        assert ax["value"] != "weak"

    def test_no_blocking_language_mismatch(self):
        for mm in self.r["mismatch"].mismatches:
            if mm.get("axis") == "language_register":
                assert mm.get("severity") != "blocking"

    def test_overall_not_poor(self):
        assert self.r["fit"].overall_label != "poor_fit"


# ---------- Case 2: Language blocker ----------

class TestLanguageBlocker:
    """English article x Russian-only venue."""

    def setup_method(self):
        self.r = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "russian_only_humanities_venue.md",
        )

    def test_language_axis_bad(self):
        ax = _axis(self.r["fit"], "language_register")
        assert ax is not None
        assert ax["value"] == "bad"

    def test_blocking_mismatch_present(self):
        lang_mm = [
            m for m in self.r["mismatch"].mismatches
            if m.get("axis") == "language_register"
        ]
        assert lang_mm, "Expected language mismatch in mismatch map"
        assert lang_mm[0]["severity"] == "blocking"

    def test_blocking_mismatch_in_critical_list(self):
        assert any(
            "language" in c.lower()
            for c in self.r["mismatch"].critical_mismatches
        )

    def test_desk_reject_risk(self):
        blocking = self.r["risk"].blocking_risks
        assert len(blocking) > 0, "Expected blocking risk for language mismatch"

    def test_submission_not_ready(self):
        assert self.r["pack"].ready_status == "not_ready"

    def test_rewrite_plan_has_language_action(self):
        changes = self.r["rewrite"].changes
        lang_changes = [
            c for c in changes
            if c.get("target_block") == "language_register"
            or "language" in c.get("desired_state", "").lower()
            or "translat" in c.get("desired_state", "").lower()
        ]
        assert lang_changes, "Expected language adaptation action in rewrite plan"

    def test_overall_poor_fit(self):
        assert self.r["fit"].overall_label == "poor_fit"


# ---------- Case 3: Method/genre blocker ----------

class TestMethodGenreBlocker:
    """Theoretical article x empirical-only venue."""

    def setup_method(self):
        self.theoretical = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "empirical_social_science_venue.md",
        )
        self.empirical = _pipeline(
            MS / "empirical_social_science_article.md",
            VN / "empirical_social_science_venue.md",
        )

    def test_theoretical_at_empirical_method_axis_honest(self):
        # intake-routing-and-model-strategy: deterministic
        # _detect_method demoted to UNKNOWN — the validation matrix
        # exercises the deterministic build_article_model path, so
        # article.method_status is now "unknown" instead of the
        # keyword-inferred "conceptual_method". Fit assessor reports
        # "unknown" for method axis when method_status is unknown —
        # honest absence, not invented weakness. The LLM ArticleModeler
        # provides real method classification in production.
        ax = _axis(self.theoretical["fit"], "method")
        assert ax is not None
        assert ax["value"] in ("weak", "bad", "unknown"), (
            f"Method axis must report weak/bad/unknown for theoretical "
            f"article at empirical venue (honest), got {ax['value']}"
        )

    def test_empirical_at_empirical_method_axis_honest(self):
        # Same rationale: method_status is now "unknown" in
        # deterministic fallback; fit axis is consequently "unknown".
        ax = _axis(self.empirical["fit"], "method")
        assert ax is not None
        assert ax["value"] in ("strong", "medium", "unknown"), (
            f"Method axis at empirical venue must report "
            f"strong/medium/unknown, got {ax['value']}"
        )

    def test_language_ok_for_both(self):
        for label, r in [("theoretical", self.theoretical), ("empirical", self.empirical)]:
            ax = _axis(r["fit"], "language_register")
            assert ax is not None
            assert ax["value"] in ("strong", "medium"), (
                f"Language should be fine for {label} (both English), got {ax['value']}"
            )

    def test_theoretical_has_method_mismatch_entry(self):
        method_mm = [
            m for m in self.theoretical["mismatch"].mismatches
            if m.get("axis") == "method"
        ]
        assert method_mm, "Expected method mismatch for theoretical at empirical venue"


# ---------- Case 4: Missing evidence ----------

class TestMissingEvidence:
    """English article x mostly-UNKNOWN venue."""

    def setup_method(self):
        self.r = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "incomplete_unknown_venue.md",
        )

    def test_many_unknowns_preserved(self):
        unknown_axes = [
            a for a in self.r["fit"].axes if a.get("value") == "unknown"
        ]
        assert len(unknown_axes) >= 3, (
            f"Expected >= 3 unknown axes for incomplete venue, got {len(unknown_axes)}"
        )

    def test_unknowns_in_fit(self):
        assert len(self.r["fit"].unknowns) > 0

    def test_cautious_overall_label(self):
        assert self.r["fit"].overall_label in (
            "not_enough_data", "possible_but_costly", "poor_fit",
        )

    def test_conditional_evidence_actions_in_rewrite(self):
        changes = self.r["rewrite"].changes
        conditional = [
            c for c in changes
            if c.get("status") == "conditional"
            or "collect" in c.get("desired_state", "").lower()
            or "verify" in c.get("desired_state", "").lower()
            or "confirm" in c.get("desired_state", "").lower()
            or "guideline" in c.get("desired_state", "").lower()
        ]
        assert conditional, (
            "Expected conditional evidence-collection actions in rewrite plan"
        )

    def test_no_invented_word_limit(self):
        wc_items = [
            i for i in self.r["compliance"].checklist_items
            if i.get("category") == "word_count"
        ]
        for item in wc_items:
            assert item.get("status") != "non_compliant", (
                "Should not flag word count as non-compliant when venue limit is unknown"
            )


# ---------- Case 5: Formal compliance ----------

class TestFormalCompliance:
    """English article x venue with explicit abstract + article word limits."""

    def setup_method(self):
        self.r = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "formal_limits_venue.md",
        )

    def test_abstract_limit_not_applied_to_body(self):
        wc_items = [
            i for i in self.r["compliance"].checklist_items
            if i.get("category") == "word_count"
        ]
        assert wc_items, "Expected word count compliance item"
        for item in wc_items:
            notes = item.get("notes", "")
            if "200" in notes and "250" in notes:
                assert "abstract" in notes.lower() or item.get("status") != "non_compliant", (
                    "Abstract limit should not flag as body non-compliance"
                )

    def test_article_word_limit_present(self):
        wc_items = [
            i for i in self.r["compliance"].checklist_items
            if i.get("category") == "word_count"
        ]
        assert wc_items, "Expected word count compliance items when limits exist"

    def test_language_ok(self):
        ax = _axis(self.r["fit"], "language_register")
        assert ax is not None
        assert ax["value"] in ("strong", "medium")


# ---------- Case 6: Citation ecology weakness ----------

class TestCitationEcologyWeakness:
    """Thin-bibliography article vs robust-bibliography article at same venue."""

    def setup_method(self):
        self.thin = _pipeline(
            MS / "thin_citation_theoretical_article.md",
            VN / "english_philosophy_venue_complete.md",
        )
        self.robust = _pipeline(
            MS / "english_theoretical_article.md",
            VN / "english_philosophy_venue_complete.md",
        )

    def test_thin_citation_ecology_weak(self):
        ax = _axis(self.thin["fit"], "citation_ecology")
        assert ax is not None
        assert ax["value"] == "weak", (
            f"Expected citation_ecology weak for 3-ref article, got {ax['value']}"
        )

    def test_robust_citation_ecology_not_weak(self):
        ax = _axis(self.robust["fit"], "citation_ecology")
        assert ax is not None
        assert ax["value"] != "weak", (
            f"Expected citation_ecology not-weak for 12-ref article, got {ax['value']}"
        )

    def test_thin_has_citation_risk(self):
        citation_risks = [
            r for r in self.thin["risk"].risk_items
            if r.get("risk_type") == "citation_gap"
        ]
        assert citation_risks, "Expected citation_gap risk for thin bibliography"

    def test_thin_vs_robust_different_citation_verdict(self):
        thin_ax = _axis(self.thin["fit"], "citation_ecology")
        robust_ax = _axis(self.robust["fit"], "citation_ecology")
        assert thin_ax["value"] != robust_ax["value"], (
            "Thin and robust bibliographies should produce different citation assessments"
        )
