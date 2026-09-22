from kairoskopion.kairon_provider import (
    ArtiklStatePointer,
    KaironProviderRequest,
    KaironProviderResponse,
    TargetWorldSnapshot,
    pressure_pack_from_diagnostics,
)


def test_provider_request_keeps_artikl_authority_pointer():
    state = ArtiklStatePointer(
        state_id="state-1",
        state_type="MANUSCRIPT",
        article_seed_pointer="seed-1",
    )
    req = KaironProviderRequest(
        call_id="call-1",
        artikl_state=state,
        target_request={"venue": "Example Journal"},
    )
    assert req.to_dict()["artikl_state"]["authority"] == "ARTIKL"
    assert req.to_dict()["artikl_state"]["article_seed_pointer"] == "seed-1"


def test_pressure_pack_omits_strong_axes_and_preserves_unknowns():
    fit = {
        "axes": [
            {"axis": "topic", "value": "strong"},
            {"axis": "genre", "value": "weak", "notes": "genre mismatch", "evidence_refs": ["src:g"]},
            {"axis": "method", "value": "unknown"},
        ]
    }
    pack = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        fit=fit,
        evidence_refs=["src:root"],
    )
    assert [p.dimension for p in pack.items] == ["genre", "method"]
    assert pack.items[0].evidence_refs == ["src:root", "src:g"]
    assert "fit:method" in pack.unknowns


def test_core_touching_mismatch_escalates_depth():
    mismatch_map = {
        "mismatches": [
            {
                "mismatch_id": "mm-1",
                "axis": "argument_structure",
                "severity": "major",
                "field_core_risk": "core_touching",
                "description": "Target expects a different argumentative object.",
            }
        ]
    }
    pack = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        mismatch_map=mismatch_map,
    )
    assert pack.items[0].transformation_depth_hint == "identity_or_reseed_review"


def test_provider_response_can_carry_partial_snapshot_without_erasing_errors():
    snap = TargetWorldSnapshot(snapshot_id="snap-1", target_id="venue-1")
    response = KaironProviderResponse(
        call_id="call-1",
        run_id="run-1",
        status="partial",
        target_snapshot=snap,
        errors=["editor_profile_timeout"],
    )
    data = response.to_dict()
    assert data["target_snapshot"]["snapshot_id"] == "snap-1"
    assert data["errors"] == ["editor_profile_timeout"]


def test_target_world_builds_editor_corpus_and_models_from_fixtures():
    from kairoskopion.kairon_provider.target_world import build_target_world_snapshot

    works = [
        {
            "id": "https://openalex.org/W1",
            "title": "A conceptual framework for responsible AI",
            "publication_year": 2025,
            "doi": "https://doi.org/10.1/example",
            "_reconstructed_abstract": "We propose a conceptual framework and critique existing models.",
            "referenced_works_count": 42,
            "authorships": [{"author": {"display_name": "A. Author"}}],
            "open_access": {"oa_url": "https://example.org/paper.pdf"},
        },
        {
            "id": "https://openalex.org/W2",
            "title": "Case study of algorithmic governance",
            "publication_year": 2024,
            "_reconstructed_abstract": "This empirical case study uses interviews and comparison.",
            "referenced_works_count": 31,
            "authorships": [{"author": {"display_name": "B. Author"}}],
        },
    ]
    editor_members = [
        {"full_name": "Jane Editor", "role": "editor_in_chief", "affiliation": "Example University"}
    ]
    editor_fixtures = {
        "Jane Editor": {
            "author": {
                "id": "https://openalex.org/A1",
                "display_name": "Jane Editor",
                "works_count": 50,
                "cited_by_count": 1000,
                "last_known_institution": {"display_name": "Example University"},
                "x_concepts": [
                    {"display_name": "Philosophy of Technology"},
                    {"display_name": "Artificial Intelligence"},
                ],
            },
            "works": [
                {
                    "id": "https://openalex.org/EW1",
                    "title": "Technology and responsibility",
                    "publication_year": 2023,
                    "doi": "https://doi.org/10.1/editor",
                    "cited_by_count": 12,
                    "type": "article",
                }
            ],
        }
    }

    snap = build_target_world_snapshot(
        target_id="venue-1",
        openalex_source_id="S1",
        fixture_works=works,
        editor_members=editor_members,
        editor_fixtures=editor_fixtures,
        provider_commit="test",
    )
    assert snap.corpus_manifest is not None
    assert len(snap.corpus_manifest.artifacts) == 2
    assert snap.corpus_manifest.artifacts[0].acquisition_state == "fulltext_locator"
    assert snap.target_models is not None
    assert snap.target_models.genre_patterns
    assert snap.editor_profiles[0].name == "Jane Editor"
    assert snap.editor_profiles[0].key_works[0]["title"] == "Technology and responsibility"


def test_round_trip_resolves_pressure_on_same_snapshot():
    from kairoskopion.kairon_provider import compare_round_trip

    prior_state = ArtiklStatePointer(state_id="s1", state_type="MANUSCRIPT")
    current_state = ArtiklStatePointer(state_id="s2", state_type="TARGET_VARIANT")
    prior = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        fit={"axes": [
            {"axis": "genre", "value": "weak"},
            {"axis": "method", "value": "weak"},
        ]},
    )
    current = pressure_pack_from_diagnostics(
        target_id="venue-1",
        snapshot_id="snap-1",
        fit={"axes": [
            {"axis": "genre", "value": "strong"},
            {"axis": "method", "value": "weak"},
        ]},
    )
    diff = compare_round_trip(
        call_id="c1",
        prior_state=prior_state,
        current_state=current_state,
        prior_pack=prior,
        current_pack=current,
    )
    assert "fit:genre:0" in diff.resolved_pressure_ids
    assert "fit:method:1" in diff.persistent_pressure_ids
    assert "same frozen target snapshot" in diff.notes[0]


def test_provider_api_router_imports():
    from kairoskopion.api.kairon_provider import router
    paths = {route.path for route in router.routes}
    assert "/kairon/provider/pressure-pack" in paths
    assert "/kairon/provider/target-world" in paths
    assert "/kairon/provider/re-evaluate" in paths
