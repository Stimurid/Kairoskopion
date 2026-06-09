"""Tests for Sprint 8: WhiteCrow Patch Queue Bridge."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from kairoskopion.enums import FieldCoreImpact
from kairoskopion.integrations.whitecrow_bridge import (
    build_whitecrow_patch_queue,
    patches_from_compliance,
    patches_from_mismatches,
    patches_from_rewrite_plan,
    patches_from_risk,
    write_whitecrow_patches,
)
from kairoskopion.schema import (
    ComplianceChecklist,
    MismatchMap,
    RewritePlan,
    RiskReport,
)
from kairoskopion.ids import (
    compliance_checklist_id,
    mismatch_map_id,
    rewrite_plan_id,
    risk_report_id,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _mismatch_map(**kw) -> MismatchMap:
    defaults = dict(
        mismatch_map_id=mismatch_map_id(),
        fit_assessment_id="fit_test",
        mismatches=[
            {"axis": "topic", "description": "Topic mismatch with venue scope", "severity": "major"},
            {"axis": "method", "description": "Method not standard for venue", "severity": "minor"},
        ],
    )
    defaults.update(kw)
    return MismatchMap(**defaults)


def _rewrite_plan(**kw) -> RewritePlan:
    defaults = dict(
        rewrite_plan_id=rewrite_plan_id(),
        article_model_id="art_test",
        fit_assessment_id="fit_test",
        changes=[
            {"section": "abstract", "description": "Revise abstract focus", "type": "revision", "effort": "low"},
            {"section": "methods", "description": "Add methodology section", "type": "addition", "effort": "high"},
        ],
        estimated_effort="medium",
        field_core_risk=FieldCoreImpact.CORE_TOUCHING.value,
    )
    defaults.update(kw)
    return RewritePlan(**defaults)


def _compliance(**kw) -> ComplianceChecklist:
    defaults = dict(
        compliance_checklist_id=compliance_checklist_id(),
        venue_model_id="ven_test",
        article_model_id="art_test",
        checklist_items=[],
        missing_items=["data availability statement", "AI disclosure"],
        blocking_items=["word count exceeds limit"],
    )
    defaults.update(kw)
    return ComplianceChecklist(**defaults)


def _risk(**kw) -> RiskReport:
    defaults = dict(
        risk_report_id=risk_report_id(),
        article_model_id="art_test",
        venue_model_id="ven_test",
        overall_risk_label="moderate",
        risk_items=[
            {"risk_type": "desk_reject", "severity": "blocking", "description": "abstract too long", "mitigation": "trim to 250 words"},
            {"risk_type": "citation_gap", "severity": "major", "description": "missing key references"},
            {"risk_type": "formatting", "severity": "minor", "description": "minor formatting issues"},
        ],
        unknowns=[],
    )
    defaults.update(kw)
    return RiskReport(**defaults)


# ---------------------------------------------------------------------------
# Mismatch patches
# ---------------------------------------------------------------------------


class TestMismatchPatches:
    def test_generates_one_per_mismatch(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm)
        assert len(patches) == 2

    def test_patch_id_format(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm)
        for p in patches:
            assert p["patch_id"].startswith("patch_")

    def test_change_type_is_mismatch_fix(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm)
        for p in patches:
            assert p["change_type"] == "mismatch_fix"

    def test_blocking_severity_maps_to_high_impact(self):
        mm = _mismatch_map(mismatches=[
            {"axis": "topic", "description": "total mismatch", "severity": "blocking"},
        ])
        patches = patches_from_mismatches(mm)
        assert patches[0]["field_core_impact"] == FieldCoreImpact.CORE_TRANSFORMING.value

    def test_major_severity_maps_to_medium_impact(self):
        mm = _mismatch_map(mismatches=[
            {"axis": "topic", "description": "mismatch", "severity": "major"},
        ])
        patches = patches_from_mismatches(mm)
        assert patches[0]["field_core_impact"] == FieldCoreImpact.CORE_TOUCHING.value

    def test_target_document_ref_passed(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm, target_document_ref="doc_123")
        for p in patches:
            assert p["target_document_ref"] == "doc_123"

    def test_empty_mismatches_no_patches(self):
        mm = _mismatch_map(mismatches=[])
        patches = patches_from_mismatches(mm)
        assert patches == []

    def test_status_is_proposed(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm)
        for p in patches:
            assert p["status"] == "proposed"


# ---------------------------------------------------------------------------
# Rewrite plan patches
# ---------------------------------------------------------------------------


class TestRewritePlanPatches:
    def test_generates_one_per_change(self):
        plan = _rewrite_plan()
        patches = patches_from_rewrite_plan(plan)
        assert len(patches) == 2

    def test_effort_from_change(self):
        plan = _rewrite_plan()
        patches = patches_from_rewrite_plan(plan)
        efforts = {p["target_block_or_section"]: p["estimated_effort"] for p in patches}
        assert efforts["abstract"] == "low"
        assert efforts["methods"] == "high"

    def test_field_core_risk_propagated(self):
        plan = _rewrite_plan(field_core_risk=FieldCoreImpact.CORE_TRANSFORMING.value)
        patches = patches_from_rewrite_plan(plan)
        for p in patches:
            assert p["field_core_impact"] == FieldCoreImpact.CORE_TRANSFORMING.value

    def test_source_plan_id_set(self):
        plan = _rewrite_plan()
        patches = patches_from_rewrite_plan(plan)
        for p in patches:
            assert p["source_plan_id"] == plan.rewrite_plan_id

    def test_empty_changes_no_patches(self):
        plan = _rewrite_plan(changes=[])
        patches = patches_from_rewrite_plan(plan)
        assert patches == []


# ---------------------------------------------------------------------------
# Compliance patches
# ---------------------------------------------------------------------------


class TestCompliancePatches:
    def test_generates_for_missing_and_blocking(self):
        comp = _compliance()
        patches = patches_from_compliance(comp)
        # 2 missing + 1 blocking = 3
        assert len(patches) == 3

    def test_missing_items_low_impact(self):
        comp = _compliance(missing_items=["data statement"], blocking_items=[])
        patches = patches_from_compliance(comp)
        assert patches[0]["field_core_impact"] == FieldCoreImpact.CORE_PRESERVING.value

    def test_blocking_items_medium_impact(self):
        comp = _compliance(missing_items=[], blocking_items=["word count"])
        patches = patches_from_compliance(comp)
        assert patches[0]["field_core_impact"] == FieldCoreImpact.CORE_TOUCHING.value

    def test_blocking_items_marked_in_summary(self):
        comp = _compliance(missing_items=[], blocking_items=["word count"])
        patches = patches_from_compliance(comp)
        assert "[BLOCKING]" in patches[0]["change_summary"]

    def test_change_type_is_compliance_fix(self):
        comp = _compliance()
        patches = patches_from_compliance(comp)
        for p in patches:
            assert p["change_type"] == "compliance_fix"


# ---------------------------------------------------------------------------
# Risk patches
# ---------------------------------------------------------------------------


class TestRiskPatches:
    def test_only_blocking_and_major(self):
        """Minor risks should NOT generate patches."""
        risk = _risk()
        patches = patches_from_risk(risk)
        # 1 blocking + 1 major = 2 (minor skipped)
        assert len(patches) == 2

    def test_blocking_risk_high_impact(self):
        risk = _risk()
        patches = patches_from_risk(risk)
        blocking = [p for p in patches if "desk_reject" in p["target_block_or_section"]]
        assert blocking[0]["field_core_impact"] == FieldCoreImpact.CORE_TRANSFORMING.value

    def test_mitigation_in_summary(self):
        risk = _risk()
        patches = patches_from_risk(risk)
        blocking = [p for p in patches if "desk_reject" in p["target_block_or_section"]]
        assert "trim to 250 words" in blocking[0]["change_summary"]

    def test_change_type_is_risk_mitigation(self):
        risk = _risk()
        patches = patches_from_risk(risk)
        for p in patches:
            assert p["change_type"] == "risk_mitigation"


# ---------------------------------------------------------------------------
# Full patch queue
# ---------------------------------------------------------------------------


class TestBuildPatchQueue:
    def test_empty_returns_empty(self):
        patches = build_whitecrow_patch_queue()
        assert patches == []

    def test_combines_all_sources(self):
        mm = _mismatch_map()
        plan = _rewrite_plan()
        comp = _compliance()
        risk = _risk()
        patches = build_whitecrow_patch_queue(
            mismatch_map=mm,
            rewrite_plan=plan,
            compliance=comp,
            risk=risk,
        )
        # 2 mismatch + 2 rewrite + 3 compliance + 2 risk = 9
        assert len(patches) == 9

    def test_all_have_bridge_version(self):
        mm = _mismatch_map()
        patches = build_whitecrow_patch_queue(mismatch_map=mm)
        for p in patches:
            assert p["bridge_version"] == "kairoskopion-whitecrow-v1"

    def test_all_json_serializable(self):
        mm = _mismatch_map()
        plan = _rewrite_plan()
        patches = build_whitecrow_patch_queue(mismatch_map=mm, rewrite_plan=plan)
        for p in patches:
            json.dumps(p, default=str)  # Must not raise

    def test_target_doc_propagated(self):
        mm = _mismatch_map()
        patches = build_whitecrow_patch_queue(
            mismatch_map=mm, target_document_ref="doc_abc",
        )
        for p in patches:
            assert p["target_document_ref"] == "doc_abc"


# ---------------------------------------------------------------------------
# JSONL file writing
# ---------------------------------------------------------------------------


class TestWritePatches:
    def test_creates_file(self):
        patches = [{"patch_id": "patch_test", "change_summary": "test"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_whitecrow_patches(patches, Path(tmpdir))
            assert path.exists()
            assert path.name == "patch_queue.jsonl"

    def test_valid_jsonl(self):
        mm = _mismatch_map()
        patches = patches_from_mismatches(mm)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = write_whitecrow_patches(patches, Path(tmpdir))
            with open(path, encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
                assert len(lines) == 2
                for line in lines:
                    parsed = json.loads(line)
                    assert "patch_id" in parsed

    def test_append_mode(self):
        p1 = [{"patch_id": "patch_1", "summary": "a"}]
        p2 = [{"patch_id": "patch_2", "summary": "b"}]
        with tempfile.TemporaryDirectory() as tmpdir:
            write_whitecrow_patches(p1, Path(tmpdir))
            write_whitecrow_patches(p2, Path(tmpdir))
            with open(Path(tmpdir) / "patch_queue.jsonl", encoding="utf-8") as f:
                lines = [l for l in f if l.strip()]
            assert len(lines) == 2

    def test_no_whitecrow_import_required(self):
        """Bridge must not import whitecrow as a dependency."""
        import kairoskopion.integrations.whitecrow_bridge as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        assert "import whitecrow" not in source
        assert "from whitecrow" not in source
