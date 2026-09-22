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


def test_target_world_store_round_trip(tmp_path=None):
    import tempfile
    from pathlib import Path
    from kairoskopion.kairon_provider.storage import TargetWorldStore

    root = Path(tempfile.mkdtemp()) if tmp_path is None else tmp_path
    store = TargetWorldStore(root)
    payload = {"snapshot_id": "snap:persistent:1", "target_id": "venue-1", "evidence_refs": ["src:1"]}
    store.put(payload)
    assert store.get("snap:persistent:1") == payload
    assert "snap:persistent:1" in store.list_ids()


def test_fulltext_fixture_upgrades_manifest_to_validated_artifact():
    import tempfile
    from pathlib import Path
    from kairoskopion.kairon_provider.fulltext import acquire_manifest_fulltexts
    from kairoskopion.kairon_provider.models import CorpusArtifact, CorpusArtifactManifest

    url = "https://example.org/paper.pdf"
    manifest = CorpusArtifactManifest(
        target_id="venue-1",
        selection_strategy="fixture",
        artifacts=[
            CorpusArtifact(
                source_ref="W1",
                title="Paper",
                acquisition_state="fulltext_locator",
                notes=[f"fulltext_locator:{url}"],
            )
        ],
    )
    root = Path(tempfile.mkdtemp())
    result = acquire_manifest_fulltexts(
        manifest,
        output_dir=root,
        fixtures={url: (b"%PDF-1.4\nfixture\n", "application/pdf")},
    )
    assert result["validated"] == 1
    assert manifest.artifacts[0].acquisition_state == "validated_artifact"
    assert manifest.artifacts[0].content_hash
    assert Path(manifest.artifacts[0].local_ref).is_file()


def test_target_page_bundle_extracts_guidelines_and_cfp_snapshot_from_fixtures():
    from kairoskopion.kairon_provider.target_pages import build_target_page_bundle

    g = "https://example.org/authors"
    c = "https://example.org/special-issue"
    html = """
    <html><body><h1>Author Guidelines</h1>
    <p>Maximum 8000 words. Abstract 200 words. APA style.
    Research article. Manuscripts must be submitted in English.
    Open access. Authors must disclose generative AI tools.</p>
    </body></html>
    """
    bundle = build_target_page_bundle(
        homepage_url="https://example.org",
        discovered={"guidelines": [g], "cfp_special_issue": [c]},
        provided_html={
            g: html,
            c: "<html><body><h1>Call for papers</h1><p>Special issue deadline.</p></body></html>",
        },
    )
    roles = {p.role for p in bundle.pages}
    assert "guidelines" in roles
    assert "cfp_special_issue" in roles
    gp = next(p for p in bundle.pages if p.role == "guidelines")
    assert "formal_submission_profile" in gp.extracted


def test_provider_run_store_round_trip():
    import tempfile
    from pathlib import Path
    from kairoskopion.kairon_provider.storage import ProviderRunStore

    store = ProviderRunStore(Path(tempfile.mkdtemp()))
    run = {"run_id": "run:1", "status": "running", "stage_status": {"target": "completed"}}
    store.put(run)
    assert store.get("run:1") == run
    assert store.list_ids() == ["run:1"]


def test_provider_api_exposes_deep_run_routes():
    from kairoskopion.api.kairon_provider import router
    paths = {route.path for route in router.routes}
    assert "/kairon/provider/target-world/{snapshot_id}/pages" in paths
    assert "/kairon/provider/target-world/{snapshot_id}/acquire-fulltext" in paths
    assert "/kairon/provider/runs" in paths
    assert "/kairon/provider/runs/{run_id}/stage" in paths


def test_article_fulltext_structural_model_detects_sections_and_moves():
    from kairoskopion.kairon_provider.fulltext_models import model_article_text

    text = """
    # Introduction
    This paper argues that the existing framework has a problem and a gap.
    # Literature Review
    Prior work is compared with our approach.
    # Methodology
    We use interviews and data from two case studies.
    # Results
    The findings show a contrast between cases.
    # Limitations
    A limitation is the bounded sample.
    # Conclusion
    Therefore, we propose a revised conceptual framework.
    """
    model = model_article_text(text, source_ref="fixture:article")
    kinds = {x["kind"] for x in model["section_sequence"]}
    assert "methods" in kinds
    assert "limitations" in kinds
    assert "conclusion" in kinds
    moves = {x["move"] for x in model["argument_moves"]}
    assert "claim" in moves
    assert "problem" in moves
    assert model["word_count"] > 20


def test_editor_identity_gate_rejects_wrong_people_and_accepts_affiliation():
    from kairoskopion.adapters.venue.editorial_board import (
        _name_identity_ok,
        _affiliation_identity_ok,
    )
    assert _name_identity_ok("Francesco Bianchini", "Francesco Bianchini")
    assert not _name_identity_ok("Francesco Bianchini", "Francesco Burzotta")
    assert _name_identity_ok("Matt Zook", "M. Zook")
    assert not _name_identity_ok("Dhiraj Murthy", "D. N. Prabhakar Murthy")
    assert _affiliation_identity_ok("Yale University", "Yale University")
    assert _affiliation_identity_ok("University of Texas at Austin", "The University of Texas at Austin")
    assert not _affiliation_identity_ok("University of Brighton", "University of Toronto")


def test_structured_editorial_board_parser_preserves_real_names():
    from kairoskopion.adapters.venue.editorial_board import _extract_structured_board_candidates

    springer = """
    <section>
      <h2 data-test="editorDisplayRole">Editor-in-Chief</h2>
      <div class="app-avatar-card__header">
        <h3 data-test="editorListing">Luciano Floridi PhD</h3>
        <div class="u-text-default u-line-height-tight">Yale University, New Haven, United States</div>
      </div>
    </section>
    <section>
      <h2 data-test="editorDisplayRole">Managing Editor</h2>
      <div class="app-avatar-card__header">
        <h3 data-test="editorListing">Elisabetta Bulla PhD</h3>
        <div class="u-text-default u-line-height-tight">Independent Scholar, Brescia, Italy</div>
      </div>
    </section>
    """
    rows = _extract_structured_board_candidates(springer)
    assert rows[0]["full_name"] == "Luciano Floridi"
    assert rows[0]["role_hint"] == "Editor-in-Chief"
    assert "Yale University" in rows[0]["affiliation_hint"]
    assert rows[1]["full_name"] == "Elisabetta Bulla"


def test_structured_pdc_editorial_team_parser():
    from kairoskopion.adapters.venue.editorial_board import _extract_structured_board_candidates

    pdc = """
    <b><p>Editors-in-Chief</b></p>
    <ul>
    <b>Levi Checketts</b><br>
    Centre for Applied Ethics<br>
    Hong Kong Baptist University<br>
    Kowloon Tong, Hong Kong SAR<br>
    <br>
    <b>Stacey O. Irwin</b><br>
    College of Arts, Humanities and Social Sciences<br>
    Millersville University of Pennsylvania<br>
    Millersville, PA 17551 - USA
    </ul>
    """
    rows = _extract_structured_board_candidates(pdc)
    names = [r["full_name"] for r in rows]
    assert names == ["Levi Checketts", "Stacey O. Irwin"]
    assert all(r["role_hint"] == "Editors-in-Chief" for r in rows)


def test_techne_guidelines_fixture_keeps_abstract_and_manuscript_limits_separate():
    from kairoskopion.adapters.venue.guidelines_extractor import extract_formal_submission_profile

    html = """
    <html><body>
    <h1>General Requirements</h1>
    <p>The first page should contain the title of the paper, an abstract
    (up to 150 words), and 4-5 keywords or phrases.</p>
    <p>Total length should not exceed 8,500 words.</p>
    <p>All references should follow the Chicago author/date citation style.</p>
    </body></html>
    """
    result = extract_formal_submission_profile(guidelines_html=html)
    assert result["fields_present"]["abstract_word_limit"]["max"] == 150
    assert result["fields_present"]["word_limit"]["max"] == 8500
    assert result["fields_present"]["reference_style"]["value"] == "chicago"


def test_techne_editorial_fixture_preserves_names_and_roles():
    from kairoskopion.adapters.venue.editorial_board import extract_candidate_members_html

    html = """
    <p><b>EDITORIAL TEAM</b></p>
    <b><p>Editors-in-Chief</p></b>
    <ul><b>Levi Checketts</b><br>Hong Kong Baptist University<br>
    <br><b>Stacey O. Irwin</b><br>Millersville University</ul>
    <b><p>Special Issues Editor</p></b>
    <ul><b>Marco Tamborini</b><br>Pegaso University</ul>
    <b><p>Editorial Advisory Board</p></b>
    <ul>
      <li>Vincent Blok, Erasmus University Rotterdam, The Netherlands
      <li>Philip Brey, University of Twente, The Netherlands
    </ul>
    """
    rows = extract_candidate_members_html(html)
    by_name = {x["full_name"]: x for x in rows}
    assert by_name["Levi Checketts"]["role_hint"] == "editor_in_chief"
    assert by_name["Stacey O. Irwin"]["role_hint"] == "editor_in_chief"
    assert by_name["Marco Tamborini"]["role_hint"] == "special_issue_editor"
    assert by_name["Vincent Blok"]["affiliation_hint"].startswith("Erasmus University")


def test_fulltext_heading_detector_rejects_pdf_headers_and_footnotes():
    from kairoskopion.kairon_provider.fulltext_models import model_article_text

    text = """
    1 Introduction
    Opening paragraph.
    18 Page 2 of 18
    3 This is a minimal sense of agency, which we compare to other accounts of agency in Sect. 7.
    2 LLMs and Minds
    Body.
    107 Page 4 of 27
    8 Conclusion
    Closing paragraph.
    """
    model = model_article_text(text, source_ref="fixture:pdf")
    assert model["headings"] == ["1 Introduction", "2 LLMs and Minds", "8 Conclusion"]


def test_transition_engine_matches_observed_p06_profiles():
    from kairoskopion.kairon_provider import propose_transition
    from kairoskopion.kairon_provider.models import TargetPressureItem, TargetPressurePack

    pnt = TargetPressurePack(
        target_id="philosophy_technology",
        snapshot_id="P06-TW-PNT-20260922-v1",
        items=[
            TargetPressureItem("PNT-LANG", "language_audience", "English target branch", severity="major", transformation_depth_hint="branch"),
            TargetPressureItem("PNT-FRAME", "problem_framing", "Target-facing reframe", severity="moderate", transformation_depth_hint="reframe"),
            TargetPressureItem("PNT-AI", "llm_disclosure", "Formal disclosure", severity="minor", transformation_depth_hint="local"),
        ],
    )
    d = propose_transition(
        call_id="P06-KAIRON-CALL-001",
        pressure_pack=pnt,
        protected_core=["governed bootstrapping", "generation/validation/adoption authority"],
        allowed_change_classes=[
            "PACKAGING", "LOCAL_EXPOSITION", "STRUCTURAL_RECONFIGURATION",
            "DISCIPLINARY_TRANSLATION", "ARTICLE_VARIANT_BRANCH",
        ],
    )
    assert d.primary_transition == "BRANCH"
    assert d.required_operations == ["BRANCH", "REFRAME", "LOCAL_ADAPT"]
    assert d.author_decision_required is False
    assert d.adoption_status == "PROPOSAL_ONLY"


def test_transition_engine_holds_on_major_target_evidence_debt():
    from kairoskopion.kairon_provider import propose_transition
    from kairoskopion.kairon_provider.models import TargetPressureItem, TargetPressurePack

    pack = TargetPressurePack(
        target_id="techne",
        snapshot_id="P06-TW-TECHNE-20260922-v1",
        items=[
            TargetPressureItem("TECH-LANG", "language_audience", "English branch", severity="major", transformation_depth_hint="branch"),
            TargetPressureItem("TECH-FRAME", "philosophy_of_technology_frame", "Reframe", severity="moderate", transformation_depth_hint="reframe"),
            TargetPressureItem("TECH-CORPUS", "corpus_confidence", "Need validated fulltext corpus", severity="major", transformation_depth_hint="evidence_needed"),
        ],
    )
    d = propose_transition(call_id="c-tech", pressure_pack=pack)
    assert d.primary_transition == "HOLD"
    assert d.blocking_evidence_debt == ["TECH-CORPUS"]
    assert "BRANCH" in d.required_operations


def test_transition_engine_escalates_deep_rearchitecture_for_identity_review():
    from kairoskopion.kairon_provider import propose_transition
    from kairoskopion.kairon_provider.models import TargetPressureItem, TargetPressurePack

    pack = TargetPressurePack(
        target_id="minds_machines",
        snapshot_id="P06-TW-MM-20260922-v1",
        items=[
            TargetPressureItem("MM-LANG", "language_audience", "English branch", severity="major", transformation_depth_hint="branch"),
            TargetPressureItem("MM-COG", "disciplinary_center", "Recenter on cognition/computation", severity="major", transformation_depth_hint="rearchitect_or_branch"),
        ],
    )
    d = propose_transition(
        call_id="c-mm",
        pressure_pack=pack,
        protected_core=["recursive infrastructure object"],
        allowed_change_classes=["ARTICLE_VARIANT_BRANCH"],
    )
    assert d.primary_transition == "BRANCH"
    assert "REARCHITECT" in d.required_operations
    assert d.requires_identity_review is True
    assert d.author_decision_required is True


def test_transition_engine_returns_keep_when_pressure_set_is_empty():
    from kairoskopion.kairon_provider import propose_transition
    from kairoskopion.kairon_provider.models import TargetPressurePack

    pack = TargetPressurePack(target_id="philosophy_technology", snapshot_id="snap", items=[])
    d = propose_transition(call_id="closed", pressure_pack=pack)
    assert d.primary_transition == "KEEP"
    assert d.required_operations == ["KEEP"]
    assert d.author_decision_required is False


def test_provider_api_exposes_transition_proposal_route():
    from kairoskopion.api.kairon_provider import router
    paths = {route.path for route in router.routes}
    assert "/kairon/provider/transition-proposal" in paths


def test_techne_shaped_guidelines_do_not_confuse_abstract_and_total_word_limit():
    from kairoskopion.adapters.venue.guidelines_extractor import extract_formal_submission_profile

    html = """
    <html><body>
    <p>The first page should contain an abstract (up to 150 words).</p>
    <p>Your manuscript should be double-spaced. Total length should not exceed 8,500 words.</p>
    <p>All references should follow the Chicago author/date citation style.</p>
    </body></html>
    """
    result = extract_formal_submission_profile(guidelines_html=html)
    assert result["fields_present"]["abstract_word_limit"]["max"] == 150
    assert result["fields_present"]["word_limit"]["max"] == 8500


def test_techne_shaped_editorial_page_extracts_clean_core_editor_names():
    from kairoskopion.adapters.venue.editorial_board import extract_candidate_members

    text = (
        "EDITORIAL TEAM Editors-in-Chief Levi Checketts Academy of Chinese, History, "
        "Religion and Philosophy Centre for Applied Ethics Hong Kong Baptist University "
        "[email protected] Stacey O. Irwin College of Arts, Humanities and Social Sciences "
        "Millersville University [email protected] Special Issues Editor Marco Tamborini "
        "Department of Literary, Linguistic, and Philosophical Studies Pegaso University "
        "[email protected] Managing Editor Michael Poznic Institute for Technology Assessment "
        "and Systems Analysis Karlsruhe Institute of Technology"
    )
    candidates = extract_candidate_members(text)
    names = {c["full_name"] for c in candidates}
    assert "Levi Checketts" in names
    assert "Stacey O. Irwin" in names
    assert "Marco Tamborini" in names
    assert "Michael Poznic" in names


def test_target_world_uses_crossref_fallback_when_openalex_empty(monkeypatch):
    import kairoskopion.kairon_provider.target_world as tw

    monkeypatch.setattr(tw, "fetch_works_for_venue", lambda *a, **k: [])
    monkeypatch.setattr(
        tw,
        "fetch_crossref_works_for_issn",
        lambda *a, **k: [{
            "id": "https://doi.org/10.1/x",
            "title": "Conceptual Technology",
            "publication_year": 2026,
            "doi": "https://doi.org/10.1/x",
            "_reconstructed_abstract": "We propose a conceptual framework for technology.",
            "referenced_works_count": 20,
            "authorships": [{"author": {"display_name": "A. Author"}}],
            "primary_location": {"landing_page_url": "https://doi.org/10.1/x"},
            "open_access": {},
            "_provider": "crossref",
        }],
    )
    snap = tw.build_target_world_snapshot(
        target_id="v1",
        openalex_source_id="S1",
        issn="1234-5678",
        max_editors=0,
    )
    assert len(snap.corpus_manifest.artifacts) == 1
    assert snap.freshness["corpus_provider"] == "crossref_fallback"
    assert any("Crossref fallback" in x for x in snap.freshness["unknowns"])


def test_explicit_journal_language_statement_beats_word_format_false_positive():
    from kairoskopion.adapters.venue.guidelines_extractor import extract_formal_submission_profile

    html = """
    <html><body>
    <h2>Language</h2><p>The journal's language is English.</p>
    <p>Manuscripts should be submitted in Word.</p>
    <p>Authors should prepare a complete manuscript with title, abstract, keywords,
    main text, references, declarations, and any supplementary information required
    by the journal. The submission page contains additional editorial instructions.</p>
    </body></html>
    """
    result = extract_formal_submission_profile(guidelines_html=html)
    assert result["fields_present"]["language"]["value"] == "english"


def test_generic_landing_page_is_not_promoted_to_fulltext_locator():
    from kairoskopion.kairon_provider.corpus import manifest_from_openalex_works

    works = [{
        "id": "https://doi.org/10.1/x",
        "title": "Metadata only paper",
        "publication_year": 2026,
        "doi": "https://doi.org/10.1/x",
        "primary_location": {"landing_page_url": "https://doi.org/10.1/x", "pdf_url": None},
        "open_access": {},
        "authorships": [],
    }]
    manifest = manifest_from_openalex_works(target_id="v1", works=works)
    art = manifest.artifacts[0]
    assert art.acquisition_state == "landing_locator"
    assert not any(n.startswith("fulltext_locator:") for n in art.notes)
    assert any(n.startswith("landing_locator:") for n in art.notes)


def test_artikl_projection_overrides_shallow_standalone_semantics():
    from kairoskopion.schema import ArticleModel
    from kairoskopion.kairon_provider import (
        ArtiklArticleProjection,
        ArtiklStatePointer,
        bind_artikl_projection,
    )

    base = ArticleModel(
        title_current="Shallow title",
        genre_current="unknown",
        protected_core=[],
        unknowns=["genre not detected", "protected core not confirmed by user"],
        word_count=5000,
    )
    projection = ArtiklArticleProjection(
        artikl_state=ArtiklStatePointer(
            state_id="P06",
            state_type="MANUSCRIPT",
            version="1.0",
            source_refs=["drive:manuscript"],
        ),
        title="Governed Bootstrapping",
        problem_statement="How can recursive infrastructure change itself under governance?",
        core_claims=["Re-entry distinguishes bootstrapping from ordinary improvement."],
        genre="conceptual_article",
        novelty_mode="new_synthesis",
        method_status="conceptual_method",
        protected_core=["RE_ENTRY", "authority separation"],
        language="en",
        evidence_refs=["drive:acceptance"],
    )
    article = bind_artikl_projection(base, projection)
    assert article.genre_current == "conceptual_article"
    assert article.method_status == "conceptual_method"
    assert article.protected_core == ["RE_ENTRY", "authority separation"]
    assert article.word_count == 5000
    assert article.extraction_status == "derived_from_artikl"
    assert "drive:manuscript" in article.source_refs
    assert all("genre not detected" not in u for u in article.unknowns)
