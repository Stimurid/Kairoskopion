"""Tests for rewrite planning service."""

from kairoskopion.enums import FieldCoreImpact, MismatchSeverity
from kairoskopion.services.rewrite_planning import build_rewrite_plan
from kairoskopion.schema import MismatchMap


def _make_mismatch_map(mismatches: list[dict], **kw) -> MismatchMap:
    return MismatchMap(
        mismatch_map_id="mm_test",
        fit_assessment_id="fit_test",
        mismatches=mismatches,
        summary="test",
        critical_mismatches=[],
        unknowns=[],
        **kw,
    )


class TestConditionalRewriteUnderUncertainty:
    """D6: When all mismatches are informational (venue data missing),
    generate conditional trajectory actions instead of empty plan."""

    def test_all_informational_produces_conditional_changes(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "topic", "severity": "informational",
             "possible_actions": ["Collect evidence for topic"]},
            {"mismatch_id": "mm_2", "axis": "citation_ecology", "severity": "informational",
             "possible_actions": ["Collect evidence for citation_ecology"]},
            {"mismatch_id": "mm_3", "axis": "language_register", "severity": "informational",
             "possible_actions": ["Collect evidence for language_register"]},
        ])
        plan = build_rewrite_plan(mm)
        assert len(plan.changes) > 0
        assert all(c["status"] == "conditional" for c in plan.changes)

    def test_conditional_changes_have_evidence_collection_actions(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "formal_compliance",
             "severity": "informational", "possible_actions": []},
        ])
        plan = build_rewrite_plan(mm)
        assert len(plan.changes) >= 1
        actions_text = " ".join(c["desired_state"] for c in plan.changes).lower()
        assert "guideline" in actions_text or "collect" in actions_text

    def test_summary_mentions_conditional(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "topic", "severity": "informational",
             "possible_actions": []},
        ])
        plan = build_rewrite_plan(mm)
        assert "conditional" in plan.summary.lower()

    def test_mixed_severity_has_both(self):
        """When there are real + informational mismatches, both types appear."""
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "topic", "severity": "major",
             "possible_actions": ["Reframe intro"],
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value},
            {"mismatch_id": "mm_2", "axis": "method", "severity": "informational",
             "possible_actions": []},
        ])
        plan = build_rewrite_plan(mm)
        assert any(c["status"] == "proposed" for c in plan.changes)
        assert any(c["status"] == "conditional" for c in plan.changes)

    def test_many_informational_axes_produce_many_actions(self):
        axes = ["topic", "discipline", "genre", "method", "citation_ecology",
                "language_register", "formal_compliance", "publication_regime",
                "audience"]
        mm = _make_mismatch_map([
            {"mismatch_id": f"mm_{i}", "axis": ax, "severity": "informational",
             "possible_actions": []}
            for i, ax in enumerate(axes, 1)
        ])
        plan = build_rewrite_plan(mm)
        assert len(plan.changes) >= len(axes)

    def test_conditional_changes_have_unknown_core_impact(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "topic", "severity": "informational",
             "possible_actions": []},
        ])
        plan = build_rewrite_plan(mm)
        for c in plan.changes:
            assert c["field_core_risk"] == FieldCoreImpact.UNKNOWN_CORE_IMPACT.value

    def test_mixed_summary_mentions_both(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "topic", "severity": "major",
             "possible_actions": ["Reframe intro"],
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value},
            {"mismatch_id": "mm_2", "axis": "method", "severity": "informational",
             "possible_actions": []},
        ])
        plan = build_rewrite_plan(mm)
        assert "proposed" in plan.summary.lower()
        assert "conditional" in plan.summary.lower()

    def test_no_mismatches_empty_plan(self):
        mm = _make_mismatch_map([])
        plan = build_rewrite_plan(mm)
        assert len(plan.changes) == 0


class TestStandardRewritePlan:
    """Existing behavior: major/blocking mismatches produce proposed changes."""

    def test_major_mismatch_produces_change(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "citation_ecology",
             "severity": "major",
             "possible_actions": ["Add venue-relevant refs"],
             "field_core_risk": FieldCoreImpact.CORE_PRESERVING.value,
             "article_side": "10 refs", "description": "citation gap"},
        ])
        plan = build_rewrite_plan(mm)
        assert len(plan.changes) == 1
        assert plan.changes[0]["status"] == "proposed"
        assert plan.changes[0]["change_type"] == "citation_bridge"

    def test_blocking_mismatch_sets_core_risk(self):
        mm = _make_mismatch_map([
            {"mismatch_id": "mm_1", "axis": "discipline",
             "severity": "blocking",
             "possible_actions": ["Add bridge"],
             "field_core_risk": FieldCoreImpact.CORE_TOUCHING.value},
        ])
        plan = build_rewrite_plan(mm)
        assert plan.requires_user_acceptance is True
        assert plan.field_core_risk == FieldCoreImpact.CORE_TOUCHING.value
