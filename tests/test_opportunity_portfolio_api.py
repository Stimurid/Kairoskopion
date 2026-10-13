"""Real-store and HTTP read-model regression for the Indago research front."""
from fastapi.testclient import TestClient

from kairoskopion.api.app import app
from kairoskopion.api.auth import User, get_current_user
from kairoskopion.api.opportunities import _user_opportunity_root
from kairoskopion.kairon_provider.opportunity_graph import OpportunityGraphStore
from kairoskopion.kairon_provider.opportunity_portfolio import build_portfolio


def _store(tmp_path):
    return OpportunityGraphStore(tmp_path)


def _admit_minimal_graph(store):
    store.put("ArticleSeed", {
        "id": "MAI-E", "revision": "r1",
        "source_ref": "gdoc:MAI-E", "author_authority": "ARTIKL",
        "protected_core": ["problem-of-academic-judgment"],
    })
    store.put("ArticleOpportunity", {
        "id": "opp-e-1", "revision": "r1",
        "seed_id": "MAI-E", "scholarly_problem": "agency of university teachers",
        "independent_claim": "differentiated judgment under LLM mediation",
        "required_evidence": ["teacher practice rights"],
        "author_decision": "ACCEPT",
    })
    store.put("Journal", {
        "id": "venue-eje", "revision": "r1",
        "canonical_name": "European Journal of Education",
        "official_url": "https://journal.example/editorial",
    })
    store.put("Evidence", {
        "id": "policy-eje", "revision": "r1",
        "source_ref": "https://journal.example/call",
        "source_kind": "OFFICIAL_CFP", "official": True,
        "read_depth": "SECTIONS", "passage_anchors": ["section-2"],
    })
    for i in range(3):
        store.put("Evidence", {
            "id": f"paper-{i}", "revision": "r1",
            "source_ref": f"doi:paper-{i}", "source_kind": "PUBLISHED_ARTICLE",
            "read_depth": "FULL_TEXT", "passage_anchors": [f"section:{i}"],
        })
    store.put("VenueWorld", {
        "id": "eje-world", "revision": "r1",
        "journal_id": "venue-eje", "target_world_version": "tw-v1",
        "published_example_evidence_ids": ["paper-0", "paper-1", "paper-2"],
    })
    store.put("OpportunityRoute", {
        "id": "eje-proposal", "revision": "r1",
        "opportunity_id": "opp-e-1",
        "journal_id": "venue-eje", "target_world_version": "tw-v1",
        "route_type": "FORMAL_ABSTRACT_CFP",
        "policy_evidence_ids": ["policy-eje"],
        "deadline": "2026-12-20", "deadline_stage": "FORMAL_ABSTRACT_CFP",
        "submission_channel_kind": "OFFICIAL_FORM",
        "submission_channel_ref": "https://journal.example/submit",
        "fit": "FIT",
    })


def test_projection_refuses_to_invent_w12_import_even_with_registered_objects(tmp_path):
    store = _store(tmp_path)
    _admit_minimal_graph(store)
    result = build_portfolio(store)
    assert result["importStatus"] == "BLOCKED_SOURCE_BYTES_UNAVAILABLE"
    assert result["seedCount"] == 1
    assert result["independentOpportunityCount"] == 1
    assert result["distinctVenueCount"] == 1
    assert result["variantCount"] == 0
    assert len(result["rows"]) == 1
    row = result["rows"][0]
    assert row["journalName"] == "European Journal of Education"
    assert row["readDepth"] == "FULL_TEXT"
    assert row["fullTextExampleCount"] == 3
    assert row["fit"] == "FIT"
    assert row["gateStatus"] == "AUTHOR_APPROVED_FOR_REVIEW"
    assert row["deadlineStage"] == "FORMAL_ABSTRACT_CFP"


def test_negative_discoveries_and_reopen_level_survive_restart(tmp_path):
    store = _store(tmp_path)
    _admit_minimal_graph(store)
    event = {
        "event_id": "W12:NEG-01", "kind": "HUNT_RESULT",
        "subject_id": "opp-e-1", "source_ref": "doi:critical-2026",
        "at": "2026-10-13T00:00:00Z", "result": "NOVELTY_REJECTED",
        "reason": "rival paper established the old novelty claim",
        "intellectual_consequence": "cannot claim this pedagogical novelty",
        "reopen_level": "L2", "next_action": "revisit conceptual distinction",
    }
    store.append_event(event)
    second = _store(tmp_path)
    assert len(second.replay_events()) == 1
    assert second.append_event(event) == event
    result = build_portfolio(second)
    assert result["events"][0]["intellectualConsequence"] == event["intellectual_consequence"]
    assert result["events"][0]["reopenLevel"] == "L2"


def test_fulltext_requires_correct_persisted_evidence_source_kind(tmp_path):
    store = _store(tmp_path)
    _admit_minimal_graph(store)
    # Revision-ambiguous evidence is not silently treated as canonical.
    store.put("Evidence", {
        "id": "paper-1", "revision": "r2", "source_ref": "doi:paper-1",
        "source_kind": "PUBLISHED_ARTICLE", "read_depth": "ABSTRACT",
        "passage_anchors": [],
    })
    result = build_portfolio(store)
    row = result["rows"][0]
    assert row["fullTextExampleCount"] == 2
    assert "venue_world_partial_evidence" in row["blockers"]
    assert row["fit"] == "CONDITIONAL"


def test_unpinned_venue_world_revision_never_promotes_deep_evidence(tmp_path):
    store = _store(tmp_path)
    _admit_minimal_graph(store)
    # Second world revision yields ambiguous model for route pinned to tw-v1.
    store.put("VenueWorld", {
        "id": "another-world", "revision": "r2", "journal_id": "venue-eje",
        "target_world_version": "tw-v1",
        "published_example_evidence_ids": ["paper-0", "paper-1", "paper-2"],
    })
    row = build_portfolio(store)["rows"][0]
    assert row["fullTextExampleCount"] == 0
    assert "venue_world_revision_unpinned_or_ambiguous" in row["blockers"]
    assert row["fit"] == "CONDITIONAL"


def test_authenticated_http_portfolio_is_user_scoped_and_never_fakes_w12(tmp_path, monkeypatch):
    monkeypatch.setenv("KAIROSKOPION_DATA_DIR", str(tmp_path))
    a = User(user_id="user_aaaaaaaaaaaa", display_name="A")
    b = User(user_id="user_bbbbbbbbbbbb", display_name="B")
    _admit_minimal_graph(OpportunityGraphStore(_user_opportunity_root(a)))
    client = TestClient(app)

    app.dependency_overrides[get_current_user] = lambda: a
    try:
        response_a = client.get("/api/opportunities/portfolio")
        assert response_a.status_code == 200
        assert response_a.json()["seedCount"] == 1
        assert response_a.json()["importStatus"] == "BLOCKED_SOURCE_BYTES_UNAVAILABLE"
        app.dependency_overrides[get_current_user] = lambda: b
        response_b = client.get("/api/opportunities/portfolio")
        assert response_b.status_code == 200
        assert response_b.json()["rows"] == []
        assert response_b.json()["seedCount"] == 0
    finally:
        app.dependency_overrides.clear()


def test_unauthenticated_portfolio_is_forbidden():
    client = TestClient(app)
    assert client.get("/api/opportunities/portfolio").status_code == 401
