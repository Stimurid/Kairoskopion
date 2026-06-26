"""Tests for Round III-P5D final prompt/schema cleanup.

Covers:
- Track 1: semantic_profiling field renames in output schema + agent mapping
- Track 2: disciplinary_mapping no school/tradition section
- Track 3: venue_matrix confidence not a fit-axis
- Track 4: venue_funnel known_corpus_candidate enforcement
- Track 5: no runtime field examples in prompts
- Track 6: discipline_matching_v2 family + product path
- Track 7: field_positioning no bridge_traditions / intellectual_tradition_region
"""

from __future__ import annotations

import json

import pytest

# -- Track 1: semantic_profiling field renames --------------------------------

from kairoskopion.prompts.semantic_profiling import (
    SEMANTIC_PROFILING_FAMILY,
    SEMANTIC_PROFILING_OUTPUT_SCHEMA,
)


class TestTrack1SemanticProfilingRenames:
    def test_output_schema_uses_framework_affiliations(self):
        props = SEMANTIC_PROFILING_OUTPUT_SCHEMA["properties"]
        assert "framework_affiliations" in props
        assert "schools_and_traditions" not in props

    def test_output_schema_uses_foundational_anchors(self):
        props = SEMANTIC_PROFILING_OUTPUT_SCHEMA["properties"]
        assert "foundational_anchors" in props
        assert "theoretical_shoulders" not in props

    def test_system_prompt_no_schools_and_traditions_label(self):
        system = SEMANTIC_PROFILING_FAMILY["system_prompt"]
        assert "Schools and traditions" not in system
        assert "Framework affiliations" in system or "framework_affiliations" in system

    def test_system_prompt_no_theoretical_shoulders_label(self):
        system = SEMANTIC_PROFILING_FAMILY["system_prompt"]
        assert "Theoretical shoulders" not in system
        assert "Foundational anchors" in system or "foundational_anchors" in system

    def test_agent_maps_new_field_names_to_schema(self):
        from kairoskopion.agents.semantic_profiler import _build_from_llm

        parsed = {
            "disciplinary_registers": ["STS"],
            "primary_discipline": "STS",
            "framework_affiliations": ["ANT", "postphenomenology"],
            "foundational_anchors": ["Latour", "Ihde"],
            "argument_move_type": "model_building",
            "confidence": "medium",
        }
        profile = _build_from_llm(parsed, "art-001")
        assert profile.schools_and_traditions == ["ANT", "postphenomenology"]
        assert profile.theoretical_shoulders == ["Latour", "Ihde"]

    def test_agent_maps_old_field_names_backward_compat(self):
        from kairoskopion.agents.semantic_profiler import _build_from_llm

        parsed = {
            "disciplinary_registers": ["STS"],
            "schools_and_traditions": ["ANT"],
            "theoretical_shoulders": ["Latour"],
            "confidence": "medium",
        }
        profile = _build_from_llm(parsed, "art-002")
        assert profile.schools_and_traditions == ["ANT"]
        assert profile.theoretical_shoulders == ["Latour"]


# -- Track 2: disciplinary_mapping no school/tradition section ----------------

from kairoskopion.prompts.disciplinary_mapping import DISCIPLINARY_MAPPING_FAMILY


class TestTrack2DisciplinaryMappingCleanup:
    def test_no_school_tradition_section_header(self):
        system = DISCIPLINARY_MAPPING_FAMILY["system_prompt"]
        assert "## School/tradition awareness" not in system

    def test_has_framework_lineage_section(self):
        system = DISCIPLINARY_MAPPING_FAMILY["system_prompt"]
        assert "Framework" in system or "framework" in system


# -- Track 3: venue_matrix confidence not a fit-axis -------------------------

from kairoskopion.prompts.venue_matrix_assessment import (
    VENUE_MATRIX_FAMILY,
    _MATRIX_AXES,
)


class TestTrack3VenueMatrixConfidence:
    def test_confidence_not_in_matrix_axes(self):
        assert "confidence" not in _MATRIX_AXES

    def test_matrix_axes_count_is_15(self):
        assert len(_MATRIX_AXES) == 15

    def test_per_candidate_has_confidence_field(self):
        schema = VENUE_MATRIX_FAMILY["output_schema"]
        candidate_props = schema["properties"]["assessments"]["items"]["properties"]
        assert "confidence" in candidate_props
        assert "confidence_reasoning" in candidate_props
        assert "unknowns" in candidate_props

    def test_prompt_says_15_axes(self):
        system = VENUE_MATRIX_FAMILY["system_prompt"]
        assert "15 axes" in system or "15 semantic" in system


# -- Track 4: venue_funnel known_corpus_candidate ----------------------------

from kairoskopion.prompts.venue_funnel_planning import (
    VENUE_FUNNEL_FAMILY,
    validate_venue_funnel,
)


class TestTrack4VenueFunnelKnownCorpus:
    def test_schema_requires_known_corpus_candidate(self):
        schema = VENUE_FUNNEL_FAMILY["output_schema"]
        corpus_items = schema["properties"]["known_corpus_candidates"]["items"]
        assert "known_corpus_candidate" in corpus_items["properties"]
        assert "known_corpus_candidate" in corpus_items["required"]

    def test_known_corpus_candidate_is_boolean_true(self):
        schema = VENUE_FUNNEL_FAMILY["output_schema"]
        kcc = schema["properties"]["known_corpus_candidates"]["items"]["properties"]["known_corpus_candidate"]
        assert kcc["type"] == "boolean"
        assert kcc["enum"] == [True]

    def test_validator_warns_on_false_known_corpus_candidate(self):
        data = {
            "known_corpus_candidates": [
                {"venue_ref": "v1", "source_ref": "s1",
                 "evidence_status": "corpus_known",
                 "known_corpus_candidate": False},
            ],
            "discovery_needed": [],
            "reasoning": "test",
        }
        warnings = validate_venue_funnel(data)
        assert any("known_corpus_candidate" in w for w in warnings)


# -- Track 5: no runtime field examples -------------------------------------

class TestTrack5NoFieldExamples:
    def test_mismatch_narrative_no_specific_examples(self):
        from kairoskopion.prompts.mismatch_narrative import MISMATCH_NARRATIVE_FAMILY
        system = MISMATCH_NARRATIVE_FAMILY["system_prompt"]
        assert "graph neural network" not in system
        assert "convex optimization" not in system
        assert "postphenomenological" not in system

    def test_discipline_matching_no_memes_example(self):
        from kairoskopion.prompts.discipline_matching import DISCIPLINE_MATCHING_SYSTEM
        assert "Memes in education" not in DISCIPLINE_MATCHING_SYSTEM

    def test_field_positioning_no_framework_kinds_list(self):
        from kairoskopion.prompts.field_positioning import ARTICLE_FIELD_POSITION_FAMILY
        system = ARTICLE_FIELD_POSITION_FAMILY["system_prompt"]
        assert "philosophical traditions, theorem families" not in system
        assert "design paradigms, protocol standards" not in system


# -- Track 6: discipline_matching_v2 -----------------------------------------

from kairoskopion.prompts.discipline_matching import (
    DISCIPLINE_MATCHING_V2_FAMILY,
    DISCIPLINE_MATCHING_V2_OUTPUT_SCHEMA,
)


class TestTrack6DisciplineMatchingV2:
    def test_v2_family_exists(self):
        assert DISCIPLINE_MATCHING_V2_FAMILY["family_id"] == "discipline_matching_v2"
        assert DISCIPLINE_MATCHING_V2_FAMILY["version"] == "2.0.0"

    def test_v2_schema_has_source_acquisition_needed(self):
        nc_schema = DISCIPLINE_MATCHING_V2_OUTPUT_SCHEMA["properties"]["new_candidate"]
        obj_branch = nc_schema["anyOf"][1]
        assert "source_acquisition_needed" in obj_branch["properties"]
        assert obj_branch["properties"]["source_acquisition_needed"]["type"] == "boolean"

    def test_v2_system_prompt_has_open_field_doctrine(self):
        system = DISCIPLINE_MATCHING_V2_FAMILY["system_prompt"]
        assert "registry" in system.lower()
        assert "source_acquisition_needed" in system

    def test_v2_no_field_examples(self):
        system = DISCIPLINE_MATCHING_V2_FAMILY["system_prompt"]
        assert "Memes in education" not in system

    def test_agent_uses_v2_family(self):
        from kairoskopion.agents.discipline_matcher import DisciplineMatcherAgent
        import inspect
        source = inspect.getsource(DisciplineMatcherAgent.execute)
        assert "DISCIPLINE_MATCHING_V2_FAMILY" in source

    def test_v2_exported_from_init(self):
        from kairoskopion.prompts import DISCIPLINE_MATCHING_V2_FAMILY as exported
        assert exported["family_id"] == "discipline_matching_v2"


# -- Track 7: field_positioning renames --------------------------------------

from kairoskopion.schema import CitationNetworkSignature, GeographicAffinity


class TestTrack7FieldPositioningRenames:
    def test_citation_network_has_bridge_frameworks(self):
        fields = CitationNetworkSignature.__dataclass_fields__
        assert "bridge_frameworks" in fields
        assert "bridge_traditions" not in fields

    def test_geographic_affinity_has_framework_origin_region(self):
        fields = GeographicAffinity.__dataclass_fields__
        assert "framework_origin_region" in fields
        assert "intellectual_tradition_region" not in fields

    def test_field_positioning_prompt_no_bridge_traditions(self):
        from kairoskopion.prompts.field_positioning import ARTICLE_FIELD_POSITION_FAMILY
        system = ARTICLE_FIELD_POSITION_FAMILY["system_prompt"]
        assert "bridge_traditions" not in system
        assert "intellectual_tradition_region" not in system

    def test_field_positioning_prompt_has_new_names(self):
        from kairoskopion.prompts.field_positioning import ARTICLE_FIELD_POSITION_FAMILY
        system = ARTICLE_FIELD_POSITION_FAMILY["system_prompt"]
        assert "bridge_frameworks" in system
        assert "framework_origin_region" in system
