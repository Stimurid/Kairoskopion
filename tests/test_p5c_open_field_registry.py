"""P5C tests: open-field ontology, registry record types, acquisition
pipeline, section-aware extraction, catalog version fallback.

These tests verify the P5C invariants:
- No field-list attractors in prompts
- Registry records are data structures, not prompt examples
- Acquisition tasks carry no LLM-recalled codes
- Section-level metrics never collapsed
- Prompt catalog resolves bare names to v2 before v1
"""

from __future__ import annotations

import json
import unittest

from kairoskopion.prompts.discipline_intent_parsing import (
    _OPEN_FIELD_DOCTRINE,
    _DOMAIN_AGNOSTIC_DOCTRINE,
)
from kairoskopion.prompts.discipline_source_acquisition import (
    DISCIPLINE_SOURCE_ACQUISITION_FAMILY,
    DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA,
    validate_source_acquisition,
)
from kairoskopion.prompts.venue_fact_extraction import (
    VENUE_FACT_EXTRACTION_FAMILY,
)
from kairoskopion.schema import (
    ClassificationSystemRecord,
    DisciplineRecord,
    SubjectCategoryRecord,
    TribeOrFrameworkRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    VenueSectionRecord,
)
from kairoskopion.agents.prompt_families.catalog import (
    get_prompt_family,
    list_prompt_families,
)


# ── 1. Open-field doctrine ────────────────────────────────────────

class TestOpenFieldDoctrineMarkers(unittest.TestCase):
    def test_no_field_list_attractor(self):
        for banned in [
            "mathematics", "biology", "medicine",
            "semiconductor physics", "philosophy", "STS", "law",
        ]:
            self.assertNotIn(
                banned, _OPEN_FIELD_DOCTRINE,
                f"Doctrine must not list '{banned}' as an example field",
            )

    def test_doctrine_contains_core_principles(self):
        self.assertIn("open publication field", _OPEN_FIELD_DOCTRINE)
        self.assertIn("Do not use examples as taxonomy", _OPEN_FIELD_DOCTRINE)
        self.assertIn("Never convert unknown into absence", _OPEN_FIELD_DOCTRINE)
        self.assertIn("Never convert model memory into fact", _OPEN_FIELD_DOCTRINE)

    def test_doctrine_lists_authoritative_sources(self):
        for source in [
            "article evidence",
            "registry records",
            "source packets",
        ]:
            self.assertIn(source, _OPEN_FIELD_DOCTRINE)

    def test_backward_compat_alias(self):
        self.assertIs(_DOMAIN_AGNOSTIC_DOCTRINE, _OPEN_FIELD_DOCTRINE)


# ── 2. Registry record instantiation ─────────────────────────────

class TestDisciplineRecord(unittest.TestCase):
    def test_minimal_instantiation(self):
        r = DisciplineRecord(display_name="Test Discipline")
        self.assertEqual(r.display_name, "Test Discipline")
        self.assertEqual(r.source_status, "provisional")
        self.assertEqual(r.review_status, "pending")
        self.assertTrue(r.discipline_record_id.startswith("drec_"))

    def test_round_trip(self):
        r = DisciplineRecord(
            display_name="Эстетика",
            display_names={"ru": "Эстетика", "en": "Aesthetics"},
            aliases=["Philosophy of Art"],
            parent_discipline_id="disrec_parent",
            provenance="adapter:vak_search",
        )
        d = r.to_dict()
        r2 = DisciplineRecord.from_dict(d)
        self.assertEqual(r2.display_name, "Эстетика")
        self.assertEqual(r2.display_names["en"], "Aesthetics")
        self.assertEqual(r2.provenance, "adapter:vak_search")

    def test_defaults_not_accepted(self):
        r = DisciplineRecord()
        self.assertNotEqual(r.source_status, "accepted")
        self.assertNotEqual(r.review_status, "curator_confirmed")


class TestEpistemicFrameworkRecord(unittest.TestCase):
    def test_minimal(self):
        r = TribeOrFrameworkRecord(
            display_name="Actor-Network Theory",
            framework_kind="framework",
        )
        self.assertEqual(r.framework_kind, "framework")
        self.assertTrue(r.framework_record_id.startswith("efrec_"))

    def test_backward_compat_alias(self):
        from kairoskopion.schema import EpistemicFrameworkRecord
        self.assertIs(TribeOrFrameworkRecord, EpistemicFrameworkRecord)

    def test_discipline_link(self):
        r = TribeOrFrameworkRecord(
            display_name="Test",
            discipline_record_ids=["disrec_abc", "disrec_def"],
        )
        self.assertEqual(len(r.discipline_record_ids), 2)


class TestVenueSectionRecord(unittest.TestCase):
    def test_minimal(self):
        r = VenueSectionRecord(
            parent_venue_id="ven_123",
            section_type="section",
            display_name="Philosophy & Technology",
        )
        self.assertEqual(r.section_type, "section")
        self.assertTrue(r.venue_section_record_id.startswith("vsrec_"))

    def test_section_with_own_issn(self):
        r = VenueSectionRecord(
            parent_venue_id="ven_123",
            section_type="track",
            display_name="Track B",
            issn="1234-5678",
            target_disciplines=["disrec_a"],
        )
        self.assertEqual(r.issn, "1234-5678")
        self.assertEqual(len(r.target_disciplines), 1)

    def test_valid_section_types(self):
        for st in ["section", "track", "special_issue", "proceedings_track"]:
            r = VenueSectionRecord(section_type=st)
            self.assertEqual(r.section_type, st)


class TestClassificationSystemRecord(unittest.TestCase):
    def test_minimal(self):
        r = ClassificationSystemRecord(system_name="OECD")
        self.assertEqual(r.system_name, "OECD")
        self.assertTrue(r.classification_system_record_id.startswith("csrec_"))

    def test_with_publisher(self):
        r = ClassificationSystemRecord(
            system_name="ASJC",
            publisher="Scopus",
            version="2024",
        )
        self.assertEqual(r.publisher, "Scopus")


class TestSubjectCategoryRecord(unittest.TestCase):
    def test_minimal(self):
        r = SubjectCategoryRecord(
            classification_system_id="clsys_x",
            code="5.7.7",
            display_name="Социальная и политическая философия",
        )
        self.assertEqual(r.code, "5.7.7")
        self.assertTrue(r.subject_category_record_id.startswith("screc_"))

    def test_hierarchy(self):
        parent = SubjectCategoryRecord(code="5.7")
        child = SubjectCategoryRecord(
            code="5.7.7",
            parent_category_id=parent.subject_category_record_id,
        )
        self.assertIsNotNone(child.parent_category_id)


class TestVenueClassificationRecord(unittest.TestCase):
    def test_minimal(self):
        r = VenueClassificationRecord(
            venue_id="ven_1",
            classification_system_id="clsys_1",
            subject_category_id="subcat_1",
            year=2024,
        )
        self.assertEqual(r.year, 2024)
        self.assertTrue(
            r.venue_classification_record_id.startswith("vcrec_"),
        )

    def test_section_level(self):
        r = VenueClassificationRecord(
            venue_id="ven_1",
            venue_section_id="vsec_1",
            classification_system_id="clsys_1",
            subject_category_id="subcat_1",
            year=2023,
        )
        self.assertIsNotNone(r.venue_section_id)


class TestVenueMetricRecord(unittest.TestCase):
    def test_minimal(self):
        r = VenueMetricRecord(
            venue_id="ven_1",
            metric_type="quartile",
            metric_value="Q1",
            metric_source="Scopus",
            year=2024,
        )
        self.assertEqual(r.metric_value, "Q1")
        self.assertTrue(r.venue_metric_record_id.startswith("vmrec_"))

    def test_per_section_per_category_not_collapsed(self):
        q1 = VenueMetricRecord(
            venue_id="ven_1",
            venue_section_id=None,
            subject_category_id="subcat_phil",
            year=2024,
            metric_type="quartile",
            metric_value="Q1",
            metric_source="Scopus",
        )
        q3 = VenueMetricRecord(
            venue_id="ven_1",
            venue_section_id=None,
            subject_category_id="subcat_sts",
            year=2024,
            metric_type="quartile",
            metric_value="Q3",
            metric_source="Scopus",
        )
        self.assertNotEqual(q1.metric_value, q3.metric_value)
        self.assertNotEqual(
            q1.venue_metric_record_id,
            q3.venue_metric_record_id,
        )

    def test_multi_year_records(self):
        ids = set()
        for y in [2022, 2023, 2024]:
            r = VenueMetricRecord(venue_id="ven_1", year=y, metric_type="impact_factor")
            ids.add(r.venue_metric_record_id)
        self.assertEqual(len(ids), 3)


# ── 3. Acquisition task validation ───────────────────────────────

class TestAcquisitionTaskValidation(unittest.TestCase):
    def test_valid_tasks(self):
        data = {
            "acquisition_tasks": [
                {
                    "target_system": "OECD FORD",
                    "search_query": "philosophy of technology",
                    "search_hints": None,
                    "expected_result_type": "subject_category",
                    "confidence": "medium",
                },
            ],
            "reasoning": "OECD FORD is the standard classification.",
        }
        warnings = validate_source_acquisition(data)
        self.assertEqual(warnings, [])

    def test_empty_tasks_without_reasoning_warns(self):
        data = {"acquisition_tasks": [], "reasoning": ""}
        warnings = validate_source_acquisition(data)
        self.assertTrue(any("substantive" in w for w in warnings))

    def test_empty_tasks_with_reasoning_ok(self):
        data = {
            "acquisition_tasks": [],
            "reasoning": "No classification systems are known for this novel interdisciplinary area. Manual curator input required.",
        }
        warnings = validate_source_acquisition(data)
        self.assertEqual(warnings, [])

    def test_empty_search_query_warns(self):
        data = {
            "acquisition_tasks": [
                {
                    "target_system": "ASJC",
                    "search_query": "",
                    "expected_result_type": "subject_category",
                    "confidence": "low",
                },
            ],
            "reasoning": "Test.",
        }
        warnings = validate_source_acquisition(data)
        self.assertTrue(any("search_query" in w for w in warnings))

    def test_schema_forbids_source_id(self):
        schema = DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA
        task_props = schema["properties"]["acquisition_tasks"]["items"]["properties"]
        self.assertNotIn("source_id", task_props)
        self.assertNotIn("source_url", task_props)

    def test_schema_max_3_tasks(self):
        schema = DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA
        self.assertEqual(
            schema["properties"]["acquisition_tasks"]["maxItems"], 3,
        )

    def test_no_hardcoded_codes_in_prompt(self):
        family = DISCIPLINE_SOURCE_ACQUISITION_FAMILY
        system_prompt = family["system_prompt"]
        for code in ["5.7.7", "5.7.8", "3312", "6.3"]:
            self.assertNotIn(
                code, system_prompt,
                f"Prompt must not contain hardcoded code '{code}'",
            )


# ── 4. Doctrine injection into P5C-modified families ─────────────

class TestDoctrineInjection(unittest.TestCase):
    def test_acquisition_family_has_doctrine(self):
        fam = DISCIPLINE_SOURCE_ACQUISITION_FAMILY
        self.assertIn("open publication field", fam["system_prompt"])

    def test_venue_extraction_family_has_doctrine(self):
        fam = VENUE_FACT_EXTRACTION_FAMILY
        self.assertIn("open publication field", fam["system_prompt"])


# ── 5. Venue extraction sections schema ──────────────────────────

class TestVenueExtractionSections(unittest.TestCase):
    def test_sections_in_schema(self):
        schema = VENUE_FACT_EXTRACTION_FAMILY["output_schema"]
        props = schema["properties"]
        self.assertIn("sections", props)
        section_items = props["sections"]["items"]
        self.assertIn("section_name", section_items["properties"])
        self.assertIn("section_type", section_items["properties"])
        self.assertIn("evidence_status", section_items["properties"])

    def test_section_type_enum(self):
        schema = VENUE_FACT_EXTRACTION_FAMILY["output_schema"]
        section_props = schema["properties"]["sections"]["items"]["properties"]
        section_type = section_props["section_type"]
        expected_types = {"section", "track", "special_issue", "proceedings_track", "unknown"}
        self.assertEqual(set(section_type["enum"]), expected_types)

    def test_evidence_status_required_on_section(self):
        schema = VENUE_FACT_EXTRACTION_FAMILY["output_schema"]
        section_items = schema["properties"]["sections"]["items"]
        self.assertIn("evidence_status", section_items.get("required", []))


# ── 6. Catalog version fallback ──────────────────────────────────

class TestCatalogVersionFallback(unittest.TestCase):
    def test_bare_name_resolves_to_v2_first(self):
        fam = get_prompt_family("semantic_profiling")
        self.assertIsNotNone(fam, "bare 'semantic_profiling' must resolve")

    def test_bare_name_resolves_to_v1_if_no_v2(self):
        fam = get_prompt_family("scenario_interview")
        self.assertIsNotNone(fam, "bare 'scenario_interview' must resolve to v1")

    def test_explicit_v2_resolves(self):
        fam = get_prompt_family("semantic_profiling_v2")
        self.assertIsNotNone(fam)

    def test_explicit_v1_resolves(self):
        fam = get_prompt_family("scenario_interview_v1")
        self.assertIsNotNone(fam)

    def test_nonexistent_returns_none(self):
        fam = get_prompt_family("totally_bogus_family")
        self.assertIsNone(fam)

    def test_article_modeling_bare_resolves(self):
        fam = get_prompt_family("article_modeling")
        self.assertIsNotNone(fam, "bare 'article_modeling' must resolve to v2")

    def test_catalog_has_both_v1_and_v2_families(self):
        families = list_prompt_families()
        v1_families = [f for f in families if f.endswith("_v1")]
        v2_families = [f for f in families if f.endswith("_v2")]
        self.assertGreater(len(v1_families), 0)
        self.assertGreater(len(v2_families), 0)


# ── 7. Tradition rename (school → tradition) ─────────────────────

class TestFrameworkRename(unittest.TestCase):
    def test_schema_uses_framework_not_school_or_tradition(self):
        from kairoskopion.schema import FieldPositionModel
        fpm = FieldPositionModel(
            entity_type="article",
            entity_id="art_test",
            framework_affiliation_vector={"ANT": 0.7},
        )
        self.assertEqual(fpm.framework_affiliation_vector["ANT"], 0.7)
        self.assertFalse(hasattr(fpm, "school_affiliation_vector"))
        self.assertFalse(hasattr(fpm, "tradition_affiliation_vector"))

    def test_venue_fpm_framework_envelope(self):
        from kairoskopion.schema import FieldPositionModel
        fpm = FieldPositionModel(
            entity_type="venue",
            entity_id="ven_test",
            framework_envelope={"ANT": [0.2, 0.9]},
        )
        self.assertIsNotNone(fpm.framework_envelope)
        self.assertFalse(hasattr(fpm, "school_envelope"))
        self.assertFalse(hasattr(fpm, "tradition_envelope"))

    def test_field_position_fit_uses_framework(self):
        from kairoskopion.logic.field_position_fit import compute_field_position_fit
        article = {
            "discipline_vector": {"test_field": 0.7},
            "framework_affiliation_vector": {"tradition_A": 0.8},
            "argument_move_vector": {"analysis": 0.5},
            "evidence_type_profile": {"theoretical": 0.7},
            "method_stance": {"explicit_method": False},
            "formalization_level": 0.3,
            "audience_level": {"accessibility_index": 0.3},
            "language_register": {"language": "en", "jargon_density": 0.5},
            "genre_position": {"genre_formality": 0.5},
            "geographic_affinity": {"language_of_publication": "en"},
        }
        venue = {
            "discipline_vector": {"test_field": 0.6},
            "framework_affiliation_vector": {"tradition_A": 0.7},
            "framework_envelope": {"tradition_A": [0.3, 0.9]},
            "argument_move_vector": {"analysis": 0.5},
            "evidence_type_profile": {"theoretical": 0.6},
            "method_stance": {"requires_explicit_method": False},
            "formalization_level": 0.3,
            "audience_level": {"accessibility_index": 0.3},
            "language_register": {"language": "en", "jargon_density": 0.5},
            "genre_position": {"genre_formality": 0.5},
            "geographic_affinity": {"language_of_publication": "en"},
        }
        result = compute_field_position_fit(article, venue)
        school_axis = [a for a in result["axes"] if a["axis"] == "school_fit"]
        self.assertEqual(len(school_axis), 1)
        self.assertEqual(school_axis[0]["status"], "contained")


# ── 8. Track 1 P5C-fix: no tradition_affiliation_vector in runtime ─

class TestTrack1NoTraditionInRuntime(unittest.TestCase):
    def test_no_tradition_affiliation_vector_in_schema_fields(self):
        import dataclasses
        from kairoskopion.schema import FieldPositionModel
        field_names = {f.name for f in dataclasses.fields(FieldPositionModel)}
        self.assertNotIn("tradition_affiliation_vector", field_names)
        self.assertNotIn("tradition_envelope", field_names)
        self.assertIn("framework_affiliation_vector", field_names)
        self.assertIn("framework_envelope", field_names)

    def test_no_tradition_affiliation_vector_in_prompt_text(self):
        from kairoskopion.prompts.field_positioning import (
            ARTICLE_FIELD_POSITION_FAMILY,
            VENUE_FIELD_POSITION_FAMILY,
        )
        for family_name, family in [
            ("article", ARTICLE_FIELD_POSITION_FAMILY),
            ("venue", VENUE_FIELD_POSITION_FAMILY),
        ]:
            system = family["system_prompt"]
            user_tpl = family["user_prompt_template"]
            self.assertNotIn("tradition_affiliation_vector", system,
                             f"{family_name} system prompt still has tradition_affiliation_vector")
            self.assertNotIn("tradition_affiliation_vector", user_tpl,
                             f"{family_name} user template still has tradition_affiliation_vector")

    def test_no_tradition_envelope_in_output_schema(self):
        from kairoskopion.prompts.field_positioning import (
            ARTICLE_FIELD_POSITION_FAMILY,
            VENUE_FIELD_POSITION_FAMILY,
        )
        for name, family in [
            ("article", ARTICLE_FIELD_POSITION_FAMILY),
            ("venue", VENUE_FIELD_POSITION_FAMILY),
        ]:
            schema_str = json.dumps(family["output_schema"])
            self.assertNotIn("tradition_affiliation_vector", schema_str,
                             f"{name} output schema has tradition_affiliation_vector")
            self.assertNotIn("tradition_envelope", schema_str,
                             f"{name} output schema has tradition_envelope")

    def test_framework_affiliation_vector_in_output_schema(self):
        from kairoskopion.prompts.field_positioning import (
            ARTICLE_FIELD_POSITION_FAMILY,
            VENUE_FIELD_POSITION_FAMILY,
        )
        for name, family in [
            ("article", ARTICLE_FIELD_POSITION_FAMILY),
            ("venue", VENUE_FIELD_POSITION_FAMILY),
        ]:
            schema_str = json.dumps(family["output_schema"])
            self.assertIn("framework_affiliation_vector", schema_str,
                          f"{name} output schema missing framework_affiliation_vector")

    def test_epistemic_framework_record_has_open_kind(self):
        from kairoskopion.schema import EpistemicFrameworkRecord
        r = EpistemicFrameworkRecord(
            display_name="Actor-Network Theory",
            framework_kind="method_family",
        )
        self.assertEqual(r.framework_kind, "method_family")
        r2 = EpistemicFrameworkRecord(
            display_name="Finite Element Method",
            framework_kind="design_paradigm",
        )
        self.assertEqual(r2.framework_kind, "design_paradigm")

    def test_math_article_no_humanities_tradition_by_default(self):
        from kairoskopion.agents.article_field_positioner import ArticleFieldPositionerAgent
        from kairoskopion.agents.contract import AgentInput
        agent = ArticleFieldPositionerAgent()
        inp = AgentInput(
            operation_id="t",
            agent_role_id="article_field_positioner",
            entities={
                "article": {
                    "article_model_id": "art_math",
                    "disciplinary_register_current": "algebraic_topology",
                    "language": "en",
                },
                "semantic_profile": {
                    "disciplinary_registers": ["algebraic_topology", "homological_algebra"],
                    "schools_and_traditions": [],
                    "argument_move_type": "proof",
                },
            },
        )
        out = agent.execute_deterministic(inp)
        fpm_dict = out.output_entity
        fav = fpm_dict.get("framework_affiliation_vector", {})
        for humanities_label in [
            "continental_phenomenology", "Deleuze", "Foucault",
            "Heidegger", "Frankfurt_School", "poststructuralism",
        ]:
            self.assertNotIn(humanities_label, fav,
                             f"Math article got humanities framework '{humanities_label}' by default")


# ── 9. Track 2 P5C-fix: no field-list examples in runtime prompts ─

class TestTrack2NoFieldListAttractors(unittest.TestCase):
    def test_no_field_list_examples_in_citation_ecology_prompt(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_ANALYSIS_FAMILY,
        )
        system = CITATION_ECOLOGY_ANALYSIS_FAMILY["system_prompt"]
        for banned in [
            "theorems for math",
            "seminal experiments for biology",
            "canonical cases for law",
            "key thinkers for philosophy",
        ]:
            self.assertNotIn(banned, system,
                             f"Citation ecology prompt still has attractor '{banned}'")


# ── 10. Track 3 P5C-fix: source_id/source_url provenance gates ────

class TestTrack3SourceProvenanceGates(unittest.TestCase):
    def test_acquisition_schema_forbids_source_id(self):
        schema = DISCIPLINE_SOURCE_ACQUISITION_OUTPUT_SCHEMA
        task_props = schema["properties"]["acquisition_tasks"]["items"]["properties"]
        self.assertNotIn("source_id", task_props)
        self.assertNotIn("source_url", task_props)

    def test_validator_accepts_null_search_hints(self):
        data = {
            "acquisition_tasks": [
                {
                    "target_system": "OECD FORD",
                    "search_query": "algebraic topology",
                    "search_hints": None,
                    "expected_result_type": "subject_category",
                    "confidence": "high",
                },
            ],
            "reasoning": "OECD FORD is the standard classification.",
        }
        warnings = validate_source_acquisition(data)
        self.assertEqual(warnings, [])

    def test_no_source_id_field_in_prompt_instructions(self):
        family = DISCIPLINE_SOURCE_ACQUISITION_FAMILY
        system = family["system_prompt"]
        self.assertIn("Do NOT produce source_id values from LLM memory", system)
        self.assertIn("Do NOT produce source_url values from LLM memory", system)


# ── 11. Track 4 P5C-fix: citation anchor safety ──────────────────

class TestTrack4CitationAnchorSafety(unittest.TestCase):
    def test_citation_ecology_schema_has_anchor_status(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_ANALYSIS_FAMILY,
        )
        schema = CITATION_ECOLOGY_ANALYSIS_FAMILY["output_schema"]
        schema_str = json.dumps(schema)
        self.assertIn("anchor_status", schema_str,
                      "Citation ecology schema must include anchor_status field")

    def test_anchor_status_values_documented(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_ANALYSIS_FAMILY,
        )
        system = CITATION_ECOLOGY_ANALYSIS_FAMILY["system_prompt"]
        for level in ["source_grounded", "corpus_grounded", "role_level"]:
            self.assertIn(level, system,
                          f"System prompt must document anchor_status level '{level}'")


# ── 12. Track 5 P5C-fix: venue metric/quartile invariants ────────

class TestTrack5VenueMetricQuartileInvariants(unittest.TestCase):
    def test_same_venue_different_databases_distinct_records(self):
        scopus = VenueMetricRecord(
            venue_id="ven_1", metric_type="quartile",
            metric_value="Q1", metric_source="Scopus", year=2024,
            subject_category_id="subcat_phil",
        )
        wos = VenueMetricRecord(
            venue_id="ven_1", metric_type="quartile",
            metric_value="Q2", metric_source="WoS", year=2024,
            subject_category_id="subcat_phil",
        )
        self.assertNotEqual(scopus.venue_metric_record_id, wos.venue_metric_record_id)
        self.assertNotEqual(scopus.metric_value, wos.metric_value)

    def test_same_database_different_years_distinct(self):
        r2023 = VenueMetricRecord(
            venue_id="ven_1", metric_type="impact_factor",
            metric_value="2.5", metric_source="Scopus", year=2023,
        )
        r2024 = VenueMetricRecord(
            venue_id="ven_1", metric_type="impact_factor",
            metric_value="3.1", metric_source="Scopus", year=2024,
        )
        self.assertNotEqual(r2023.venue_metric_record_id, r2024.venue_metric_record_id)

    def test_same_database_different_categories_distinct(self):
        phil = VenueMetricRecord(
            venue_id="ven_1", metric_type="quartile",
            metric_value="Q1", metric_source="Scopus", year=2024,
            subject_category_id="subcat_philosophy",
        )
        sts = VenueMetricRecord(
            venue_id="ven_1", metric_type="quartile",
            metric_value="Q3", metric_source="Scopus", year=2024,
            subject_category_id="subcat_sts",
        )
        self.assertNotEqual(phil.venue_metric_record_id, sts.venue_metric_record_id)
        self.assertNotEqual(phil.metric_value, sts.metric_value)

    def test_section_level_metric_carries_section_id(self):
        r = VenueMetricRecord(
            venue_id="ven_1", venue_section_id="vsrec_track_a",
            metric_type="quartile", metric_value="Q2",
            metric_source="Scopus", year=2024,
        )
        self.assertEqual(r.venue_section_id, "vsrec_track_a")

    def test_never_single_prestige_tier(self):
        records = [
            VenueMetricRecord(
                venue_id="ven_1", metric_type="quartile",
                metric_value=f"Q{q}", metric_source=src, year=2024,
                subject_category_id=f"subcat_{cat}",
            )
            for q, src, cat in [
                (1, "Scopus", "phil"), (3, "Scopus", "sts"),
                (2, "WoS", "phil"), (4, "WoS", "sts"),
            ]
        ]
        ids = {r.venue_metric_record_id for r in records}
        self.assertEqual(len(ids), 4, "All 4 records must have unique IDs")
        values = {r.metric_value for r in records}
        self.assertGreater(len(values), 1, "Must not collapse to single prestige tier")


# ── 13. Track 6 P5C-fix: runtime v2 invariant ───────────────────

class TestTrack6RuntimeV2Invariant(unittest.TestCase):
    def test_agents_import_directly_from_prompt_modules(self):
        from kairoskopion.agents.article_field_positioner import (
            ARTICLE_FIELD_POSITION_FAMILY,
        )
        from kairoskopion.agents.venue_field_positioner import (
            VENUE_FIELD_POSITION_FAMILY,
        )
        self.assertIn("v2", ARTICLE_FIELD_POSITION_FAMILY.get("family_id", ""))
        self.assertIn("v2", VENUE_FIELD_POSITION_FAMILY.get("family_id", ""))

    def test_citation_ecology_agent_uses_v2(self):
        from kairoskopion.prompts.citation_ecology_analysis import (
            CITATION_ECOLOGY_FAMILY,
        )
        self.assertIn("v2", CITATION_ECOLOGY_FAMILY.get("family_id", ""))

    def test_catalog_bare_name_resolves_v2_before_v1(self):
        for bare_name in [
            "semantic_profiling", "article_modeling",
            "venue_fact_extraction",
        ]:
            fam = get_prompt_family(bare_name)
            self.assertIsNotNone(fam, f"bare '{bare_name}' must resolve")
            fid = fam.get("family_id", "")
            if get_prompt_family(f"{bare_name}_v2") is not None:
                self.assertIn("v2", fid,
                              f"bare '{bare_name}' must resolve to v2 when v2 exists")


if __name__ == "__main__":
    unittest.main()
