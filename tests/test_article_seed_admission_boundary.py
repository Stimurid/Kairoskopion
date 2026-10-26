"""ArticleSeed research storage cannot impersonate Factory author/science admission."""
import pytest

from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore


def seed(**changes):
    value = {
        "id": "AI4SCI-C01", "revision": "r2", "source_ref": "gdoc:C01-R2",
        "author_authority": "UNVERIFIED", "protected_core": ["evaluator provenance"],
    }
    value.update(changes)
    return value


def test_legacy_research_seed_remains_readable_and_unverified(tmp_path):
    graph = OpportunityGraphStore(tmp_path)
    stored = graph.put("ArticleSeed", seed())
    assert stored["id"] == "AI4SCI-C01"
    assert stored.get("admission_status", "LEGACY_UNVERIFIED") == "LEGACY_UNVERIFIED"
    assert graph.get("ArticleSeed", "AI4SCI-C01", "r2") == stored


@pytest.mark.parametrize("status", [
    "ACCEPTED", "ADMITTED", "SCIENCE_PASSED", "AUTHOR_APPROVED",
    "SUBMISSION_READY", "MANUSCRIPT_GO",
])
def test_graph_cannot_admit_article_seed_by_status(tmp_path, status):
    graph = OpportunityGraphStore(tmp_path)
    with pytest.raises(ValueError, match="admission requires trusted"):
        graph.put("ArticleSeed", seed(admission_status=status))
    assert graph.list_records("ArticleSeed") == []


@pytest.mark.parametrize("patch", [
    {"author_decision": "ACCEPT"},
    {"publication_authority": "APPROVED"},
    {"author_approved": True},
    {"coauthor_consent_verified": True},
    {"empirical_claim_admitted": True},
    {"scientific_evidence_admitted": True},
    {"send_status": "SENT"},
])
def test_self_declared_author_or_science_rights_are_rejected(tmp_path, patch):
    graph = OpportunityGraphStore(tmp_path)
    with pytest.raises(ValueError):
        graph.put("ArticleSeed", seed(**patch))
    assert graph.list_records("ArticleSeed") == []


@pytest.mark.parametrize("status", [
    "PROPOSED", "RESEARCH_HOLD", "AUTHOR_HOLD", "REJECTED",
])
def test_unapproved_research_states_retained(tmp_path, status):
    graph = OpportunityGraphStore(tmp_path)
    assert graph.put("ArticleSeed", seed(admission_status=status))["admission_status"] == status
