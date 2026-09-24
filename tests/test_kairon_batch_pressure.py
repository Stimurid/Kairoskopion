from kairoskopion.schema import ArticleModel
from kairoskopion.kairon_provider import ArtiklStatePointer
from kairoskopion.kairon_provider.batch import BatchArticleInput, BatchTargetInput
from kairoskopion.kairon_provider.batch_pressure import (
    assess_corpus_temporal_adequacy,
    derive_batch_target_pressure,
)
from kairoskopion.kairon_provider.transition import propose_transition


def _snapshot(years=(2026, 2026), conceptual=.4, method=.4, median=20):
    return {
        "snapshot_id": "snap:1",
        "evidence_refs": ["e:1"],
        "corpus_manifest": {
            "artifacts": [
                {"year": y, "title": "Human Technology and Artificial Systems"}
                for y in years
            ]
        },
        "target_models": {
            "genre_patterns": [{"label": "conceptual_article", "share": conceptual}],
            "method_patterns": [{"label": "conceptual", "share": method}],
            "citation_patterns": {"median_reference_count": median},
        },
    }


def _article_input(hint="discipline:philosophy-of-technology"):
    return BatchArticleInput(
        article_id="a",
        artikl_state=ArtiklStatePointer(state_id="s", state_type="MANUSCRIPT"),
        academic_world_path_hints=[["world:w", hint]],
    )


def test_temporal_adequacy_separates_old_corpus_from_new_snapshot():
    result = assess_corpus_temporal_adequacy(
        _snapshot(years=(1999, 2013)), current_year=2026
    )
    assert result["status"] == "stale"
    assert result["median_year"] == 2006


def test_english_target_creates_sibling_variant_pressure():
    article = ArticleModel(
        language="ru",
        genre_current="conceptual_article",
        method_status="theoretical",
        reference_count=25,
    )
    target = BatchTargetInput(
        target_id="t",
        snapshot_id="snap:1",
        academic_world_path=["world:w", "discipline:philosophy-of-technology"],
    )
    pack = derive_batch_target_pressure(
        article_input=_article_input(), article=article, target=target,
        snapshot=_snapshot(), current_year=2026,
    )
    ids = {x.pressure_id for x in pack.items}
    assert "target:corpus:language:english_realization" in ids
    assert "target:disciplinary_path:translation" not in ids


def test_off_path_target_adds_reframe_pressure():
    article = ArticleModel(
        language="en", genre_current="conceptual_article",
        method_status="conceptual", reference_count=25,
    )
    target = BatchTargetInput(
        target_id="t", snapshot_id="snap:1",
        academic_world_path=["world:w", "discipline:philosophy-of-mind-ai"],
    )
    pack = derive_batch_target_pressure(
        article_input=_article_input(), article=article, target=target,
        snapshot=_snapshot(), current_year=2026,
    )
    assert any(x.dimension == "disciplinary_path" for x in pack.items)


def test_missing_target_citation_baseline_stays_unknown():
    article = ArticleModel(
        language="en", genre_current="conceptual_article",
        method_status="conceptual", reference_count=20,
    )
    snap = _snapshot(median=0)
    target = BatchTargetInput(
        target_id="t", snapshot_id="snap:1",
        academic_world_path=["discipline:philosophy-of-technology"],
    )
    pack = derive_batch_target_pressure(
        article_input=_article_input(), article=article, target=target,
        snapshot=snap, current_year=2026,
    )
    assert "target:corpus:citation" in pack.unknowns


def test_target_variant_branch_pressure_maps_to_branch_transition():
    article = ArticleModel(
        language="ru", genre_current="conceptual_article",
        method_status="conceptual", reference_count=25,
    )
    target = BatchTargetInput(
        target_id="t", snapshot_id="snap:1",
        academic_world_path=["discipline:philosophy-of-technology"],
    )
    pack = derive_batch_target_pressure(
        article_input=_article_input(), article=article, target=target,
        snapshot=_snapshot(), current_year=2026,
    )
    decision = propose_transition(
        call_id="c", pressure_pack=pack,
        protected_core=["core"],
        allowed_change_classes=["PACKAGING", "LOCAL_EXPOSITION"],
    )
    assert decision.primary_transition == "BRANCH"
    assert "BRANCH" in decision.required_operations
    assert decision.author_decision_required is False