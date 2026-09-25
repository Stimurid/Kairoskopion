[Reading 60 lines from start (total: 60 lines, 0 remaining)]

import pytest
from kairoskopion.schema import ArticleModel
from kairoskopion.kairon_provider import (
    SourceCompletenessReport, project_verified_reference_count,
    source_completeness_debt,
)

def report(**kw):
    base=dict(report_id="sc1", article_id="A1", manuscript_revision="m1",
              bibliography_status="UNKNOWN", reference_count_status="UNAVAILABLE")
    base.update(kw)
    return SourceCompletenessReport(**base)

def test_sc01_verified_complete_projects_exact_count():
    a=ArticleModel(reference_count=None, unknowns=["article:reference_count"])
    r=report(bibliography_status="VERIFIED_COMPLETE",
             reference_count_status="VERIFIED", reference_count=37)
    project_verified_reference_count(a,r,current_manuscript_revision="m1")
    assert a.reference_count == 37
    assert "article:reference_count" not in a.unknowns
    assert "source_completeness:sc1" in a.evidence_refs

def test_sc02_incomplete_source_map_does_not_project():
    a=ArticleModel(reference_count=None)
    r=report(bibliography_status="SOURCE_MAP_ONLY", reference_count_status="UNAVAILABLE")
    assert project_verified_reference_count(a,r,current_manuscript_revision="m1").reference_count is None

def test_sc03_donor_source_traces_do_not_project():
    a=ArticleModel(reference_count=None)
    r=report(bibliography_status="SOURCE_TRACES_ONLY", reference_count_status="UNAVAILABLE")
    assert project_verified_reference_count(a,r,current_manuscript_revision="m1").reference_count is None

def test_sc04_stale_revision_does_not_project():
    a=ArticleModel(reference_count=None)
    r=report(bibliography_status="VERIFIED_COMPLETE",
             reference_count_status="VERIFIED", reference_count=12)
    assert project_verified_reference_count(a,r,current_manuscript_revision="m2").reference_count is None

def test_sc05_unknown_never_becomes_zero():
    a=ArticleModel(reference_count=None)
    r=report()
    project_verified_reference_count(a,r,current_manuscript_revision="m1")
    assert a.reference_count is None
    assert source_completeness_debt(r) == ["article:reference_count"]

def test_sc06_kairon_consumer_preserves_null_debt():
    r=report(bibliography_status="SOURCE_MAP_ONLY", reference_count_status="UNAVAILABLE")
    assert source_completeness_debt(r) == ["article:reference_count"]

def test_sc07_verified_status_requires_count():
    with pytest.raises(ValueError):
        report(bibliography_status="VERIFIED_COMPLETE", reference_count_status="VERIFIED")

def test_sc08_projection_does_not_mutate_semantic_fields():
    a=ArticleModel(reference_count=None, core_claims=["c1"], protected_core=["p1"])
    r=report(bibliography_status="VERIFIED_COMPLETE",
             reference_count_status="VERIFIED", reference_count=9)
    project_verified_reference_count(a,r,current_manuscript_revision="m1")
    assert a.core_claims == ["c1"]
    assert a.protected_core == ["p1"]