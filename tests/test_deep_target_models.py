import json

from kairoskopion.kairon_provider.deep_target_models import (
    aggregate_deep_target_model,
    build_published_article_patterns,
    simulate_article_against_deep_model,
)
from kairoskopion.kairon_provider.models import (
    CorpusArtifact,
    CorpusArtifactManifest,
)
from kairoskopion.llm.response import LLMResponse
from kairoskopion.schema import PublishedArticlePattern


class QueueProvider:
    def __init__(self, responses):
        self.responses = list(responses)

    def complete(
        self,
        messages,
        *,
        response_schema=None,
        temperature=0.2,
        max_tokens=4096,
        agent_role="",
    ):
        if not self.responses:
            raise AssertionError("unexpected LLM call")
        parsed = self.responses.pop(0)
        return LLMResponse(
            content=json.dumps(parsed),
            parsed=parsed,
            model="fixture-model",
            input_tokens=100,
            output_tokens=50,
            latency_ms=1.0,
            agent_role=agent_role,
        )


def _pattern_response():
    return {
        "abstract_pattern": "problem -> distinction -> contribution",
        "section_structure": ["Introduction", "Argument", "Conclusion"],
        "intro_moves": ["establish problem", "locate gap"],
        "method_moves": ["conceptual reconstruction"],
        "argument_moves": ["distinction", "objection", "refinement"],
        "conclusion_moves": ["restate contribution"],
        "method_presence": "implicit_conceptual",
        "theory_presence": ["philosophy of technology"],
        "empirical_presence": "absent",
        "citation_features": {
            "observed_traditions": ["philosophy of technology"],
            "citation_roles": ["positioning", "objection"],
        },
        "novelty_moves": ["reframe known problem"],
        "evidence_anchors": [
            {"locator": "Introduction", "observation": "problem and gap"},
            {"locator": "Conclusion", "observation": "refined contribution"},
        ],
        "unknowns": [],
        "warnings": [],
        "confidence": "medium",
    }


def _semantic_patterns(n):
    rows = []
    for i in range(n):
        rows.append({
            "published_article_pattern_id": f"papat_{i}",
            "published_corpus_id": "deepcorpus:test",
            "article_source_id": f"src:{i}",
            "semantic_status": "llm_grounded_fulltext",
            "argument_moves": ["problem", "claim"],
            "theory_presence": ["technology studies"],
            "citation_features": {},
            "structural_observation": {"word_count": 8000 + i},
        })
    return rows


def _genre_response(patterns, invalid_member=False):
    ids = [p["published_article_pattern_id"] for p in patterns]
    left = ids[: max(1, len(ids) // 2)]
    right = ids[max(1, len(ids) // 2):] or ids[-1:]
    if invalid_member:
        left = left + ["papat_missing"]
    return {
        "observed_moves": {"problem": 1.0, "claim": 1.0},
        "dominant_moves": ["problem", "claim"],
        "rare_moves": [],
        "absent_in_sample_moves": ["empirical_test"],
        "archetypes": [
            {
                "archetype_id": "arch_conceptual",
                "label": "conceptual reconstruction",
                "member_pattern_ids": left,
                "defining_moves": ["problem", "claim"],
                "structure_signature": ["Introduction", "Argument", "Conclusion"],
                "method_signature": "conceptual",
                "theory_signature": ["technology studies"],
                "limitations": [],
            },
            {
                "archetype_id": "arch_critical",
                "label": "critical argument",
                "member_pattern_ids": right,
                "defining_moves": ["critique", "claim"],
                "structure_signature": ["Introduction", "Critique", "Conclusion"],
                "method_signature": "conceptual",
                "theory_signature": ["technology studies"],
                "limitations": [],
            },
        ],
        "countermodels": [
            {
                "label": "minority form",
                "member_pattern_ids": [ids[-1]],
                "contrast": "less standard sectioning",
            }
        ],
        "article_comparison_dimensions": ["argument moves", "method", "theory"],
        "unknowns": [],
        "warnings": [],
        "confidence": "medium",
    }


def _citation_response(patterns):
    return {
        "dominant_cited_authors": [],
        "dominant_cited_journals": [],
        "dominant_theoretical_traditions": ["technology studies"],
        "citation_roles": ["positioning", "objection"],
        "reference_count_observation": None,
        "recentness_observation": "mixed",
        "classic_reference_observation": "present",
        "bridge_opportunities": ["technology ethics"],
        "not_observed_traditions": [],
        "evidence_pattern_ids": [
            p["published_article_pattern_id"] for p in patterns
        ],
        "unknowns": ["exact bibliography counts not normalized"],
        "warnings": [],
        "confidence": "medium",
    }


def test_published_article_pattern_schema_restored():
    p = PublishedArticlePattern(
        article_source_id="src:1",
        argument_moves=["claim"],
        semantic_status="llm_grounded_fulltext",
    )
    data = p.to_dict()
    assert data["published_article_pattern_id"].startswith("papat_")
    assert data["article_source_id"] == "src:1"


def test_complete_text_can_become_fulltext_grounded_pattern(tmp_path):
    article = tmp_path / "article.txt"
    article.write_text(
        "Introduction\nThis paper argues a problem.\n"
        "Argument\nWe distinguish two positions.\n"
        "Conclusion\nTherefore the distinction matters.\n",
        encoding="utf-8",
    )
    manifest = CorpusArtifactManifest(
        target_id="venue-1",
        selection_strategy="fixture",
        artifacts=[
            CorpusArtifact(
                source_ref="src:1",
                title="Fixture article",
                local_ref=str(article),
                acquisition_state="validated_artifact",
            )
        ],
    )
    result = build_published_article_patterns(
        target_id="venue-1",
        manifest=manifest,
        provider=QueueProvider([_pattern_response()]),
        max_chars=10_000,
    )
    assert result["modeled"] == 1
    assert result["failures"] == []
    assert result["patterns"][0]["semantic_status"] == "llm_grounded_fulltext"
    assert result["patterns"][0]["published_corpus_id"].startswith(
        "deepcorpus:venue-1:"
    )


def test_oversize_text_is_not_counted_as_semantically_read(tmp_path):
    article = tmp_path / "large.txt"
    article.write_text("A" * 5000, encoding="utf-8")
    manifest = CorpusArtifactManifest(
        target_id="venue-1",
        selection_strategy="fixture",
        artifacts=[
            CorpusArtifact(
                source_ref="src:large",
                local_ref=str(article),
                acquisition_state="validated_artifact",
            )
        ],
    )
    result = build_published_article_patterns(
        target_id="venue-1",
        manifest=manifest,
        provider=QueueProvider([]),
        max_chars=1000,
    )
    assert result["modeled"] == 0
    assert result["complete_fulltexts_seen"] == 1
    assert result["failures"][0]["status"] == "input_too_large_requires_chunking"


def test_nine_semantic_fulltexts_do_not_close_hs016_target_gate():
    patterns = _semantic_patterns(9)
    model = aggregate_deep_target_model(
        target_id="venue-1",
        pattern_result={
            "published_corpus_id": "deepcorpus:test",
            "patterns": patterns,
            "failures": [],
        },
        selection_strategy="recent_articles",
        bias_notes=[],
        editor_profiles=[{"name": "Editor"}],
        provider=QueueProvider([
            _genre_response(patterns),
            _citation_response(patterns),
        ]),
        min_fulltexts=10,
    )
    assert model["deep_model_gate"]["status"] == "BLOCKED"
    assert "min_fulltext_semantic_patterns" in model["deep_model_gate"]["blockers"]


def test_ten_fulltexts_with_two_real_archetypes_can_close_target_gate():
    patterns = _semantic_patterns(10)
    model = aggregate_deep_target_model(
        target_id="venue-1",
        pattern_result={
            "published_corpus_id": "deepcorpus:test",
            "patterns": patterns,
            "failures": [],
        },
        selection_strategy="recent_articles",
        bias_notes=["recent sample"],
        editor_profiles=[{"name": "Editor"}],
        provider=QueueProvider([
            _genre_response(patterns),
            _citation_response(patterns),
        ]),
        min_fulltexts=10,
    )
    assert model["deep_model_gate"]["status"] == "READY"
    assert len(model["archetypes"]) == 2
    assert model["published_article_corpus"]["corpus_size"] == 10


def test_unknown_archetype_member_fails_closed():
    patterns = _semantic_patterns(10)
    model = aggregate_deep_target_model(
        target_id="venue-1",
        pattern_result={
            "published_corpus_id": "deepcorpus:test",
            "patterns": patterns,
            "failures": [],
        },
        selection_strategy="recent_articles",
        bias_notes=[],
        editor_profiles=[{"name": "Editor"}],
        provider=QueueProvider([
            _genre_response(patterns, invalid_member=True),
            _citation_response(patterns),
        ]),
        min_fulltexts=10,
    )
    assert model["deep_model_gate"]["status"] == "BLOCKED"
    assert any(
        "unknown_members" in item for item in model["deep_model_gate"]["blockers"]
    )


def test_article_simulation_refuses_blocked_deep_model():
    result = simulate_article_against_deep_model(
        article={"article_id": "P06"},
        deep_target_model={
            "deep_target_model_id": "deep-target:x",
            "deep_model_gate": {"status": "BLOCKED"},
        },
        provider=QueueProvider([]),
    )
    assert result["status"] == "BLOCKED"
    assert result["blockers"] == ["deep_target_model_not_ready"]
