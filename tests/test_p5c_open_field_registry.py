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


class TestTribeOrFrameworkRecord(unittest.TestCase):
    def test_minimal(self):
        r = TribeOrFrameworkRecord(
            display_name="Actor-Network Theory",
            record_type="framework",
        )
        self.assertEqual(r.record_type, "framework")
        self.assertTrue(r.tribe_record_id.startswith("tfrec_"))

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

class TestTraditionRename(unittest.TestCase):
    def test_schema_uses_tradition_not_school(self):
        from kairoskopion.schema import FieldPositionModel
        fpm = FieldPositionModel(
            entity_type="article",
            entity_id="art_test",
            tradition_affiliation_vector={"ANT": 0.7},
        )
        self.assertEqual(fpm.tradition_affiliation_vector["ANT"], 0.7)
        self.assertFalse(hasattr(fpm, "school_affiliation_vector"))

    def test_venue_fpm_tradition_envelope(self):
        from kairoskopion.schema import FieldPositionModel
        fpm = FieldPositionModel(
            entity_type="venue",
            entity_id="ven_test",
            tradition_envelope={"ANT": [0.2, 0.9]},
        )
        self.assertIsNotNone(fpm.tradition_envelope)
        self.assertFalse(hasattr(fpm, "school_envelope"))

    def test_field_position_fit_uses_tradition(self):
        from kairoskopion.logic.field_position_fit import compute_field_position_fit
        article = {
            "discipline_vector": {"test_field": 0.7},
            "tradition_affiliation_vector": {"tradition_A": 0.8},
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
            "tradition_affiliation_vector": {"tradition_A": 0.7},
            "tradition_envelope": {"tradition_A": [0.3, 0.9]},
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


if __name__ == "__main__":
    unittest.main()
