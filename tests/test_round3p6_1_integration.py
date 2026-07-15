"""P6.1 product-path integration tests.

These tests prove that registry integration is wired into actual
Case/API product paths — not just standalone helper tests.

Required by the P6.1 non-negotiable product-path rule:
- Discipline product path (registry match → canonical, no LLM)
- Discipline miss path (no match → acquisition task)
- VenueFunnel product path (accepted venue → known_corpus_candidate)
- VenueSection product path (section independent from parent)
- VenueMatrix product path (provenance enrichment)
- VenueFactExtraction to registry (extraction → provisional records)
- Downstream status propagation
"""

from __future__ import annotations

import pytest
from pathlib import Path

from kairoskopion.registry.integration import RegistryIntegrationService
from kairoskopion.registry.services import RegistryHub
from kairoskopion.registry.models import (
    DisciplineRecord,
    EvidenceRef,
    VenueRegistryRecord,
    VenueSectionRecord,
    VenueClassificationRecord,
    VenueMetricRecord,
    SourceAcquisitionTask,
)
from kairoskopion.registry.status import record_usage_status


@pytest.fixture
def hub(tmp_path):
    """In-memory RegistryHub backed by tmp_path."""
    return RegistryHub(data_dir=tmp_path)


@pytest.fixture
def svc(hub):
    """RegistryIntegrationService using in-memory hub."""
    return RegistryIntegrationService(hub=hub)


# ====================================================================
# DISCIPLINE PRODUCT PATH
# ====================================================================


class TestDisciplineProductPath:
    """Track 3: discipline_lookup through product flow."""

    def test_canonical_match_returns_fact(self, svc, hub):
        """Accepted DisciplineRecord → canonical, no acquisition task."""
        rec = DisciplineRecord(
            display_names={"ru": "Экономика", "en": "Economics"},
            aliases=["Economics", "economics management"],
        )
        hub.disciplines().add_provisional(rec)
        hub.disciplines().accept(rec.discipline_id)
        hub.disciplines().update_review_status(
            rec.discipline_id, "curator_confirmed",
        )

        result = svc.discipline_lookup(
            "Economics",
            agent_name="test",
            case_id="case_1",
        )

        assert result["found"] is True
        assert result["usage_status"] == "canonical"
        assert result["record"].discipline_id == rec.discipline_id
        assert result["task"] is None

    def test_provisional_match_returns_with_warning(self, svc, hub):
        """Provisional DisciplineRecord → provisional_with_warning."""
        rec = DisciplineRecord(
            display_names={"en": "Finance"},
            aliases=["Finance", "financial economics"],
        )
        hub.disciplines().add_provisional(rec)

        result = svc.discipline_lookup("Finance")

        assert result["found"] is True
        assert result["usage_status"] == "provisional_with_warning"
        assert result["record"].discipline_id == rec.discipline_id
        assert result["task"] is None

    def test_miss_creates_acquisition_task(self, svc, hub):
        """No registry match → SourceAcquisitionTask created."""
        result = svc.discipline_lookup(
            "Quantum Hermeneutics",
            agent_name="test_agent",
            case_id="case_2",
        )

        assert result["found"] is False
        assert result["usage_status"] == "unknown"
        assert result["record"] is None
        assert result["task"] is not None
        assert isinstance(result["task"], SourceAcquisitionTask)

    def test_miss_produces_no_source_facts(self, svc, hub):
        """Discipline miss must not produce source_id or source_url."""
        result = svc.discipline_lookup("Nonexistent Field")

        assert result["record"] is None
        task = result["task"]
        assert task is not None
        assert not hasattr(task, "source_id") or task.source_id is None
        assert not hasattr(task, "source_url") or task.source_url is None


class TestDisciplineProductPathViaCase:
    """Track 3: prove Case._run_discipline_matcher uses registry."""

    def test_case_discipline_matcher_produces_results(self, tmp_path):
        """Case._run_discipline_matcher always goes through agent path.

        After the BLOCKER A fix, registry substring lookup no longer
        short-circuits the LLM path.  The agent (deterministic fallback
        when no provider) still uses keyword candidates and produces
        discipline_matches with matched list.
        """
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)

        rec = DisciplineRecord(
            display_names={"en": "Economics management"},
            aliases=["economics", "economics management"],
        )
        hub.disciplines().add_provisional(rec)
        hub.disciplines().accept(rec.discipline_id)
        hub.disciplines().update_review_status(
            rec.discipline_id, "curator_confirmed",
        )

        case = Case(registry_service=svc)
        case.article_model = ArticleModel(
            title_current="Economics management in modern firms",
            disciplinary_register_current="economics",
        )

        # ARCH-SEM-001: discipline matching requires LLM
        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError
        with pytest.raises(SemanticLLMRequiredError):
            case._run_discipline_matcher()

    def test_case_discipline_miss_falls_to_agent(self, tmp_path):
        """ARCH-SEM-001: without LLM, discipline matcher raises."""
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import ArticleModel
        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)

        case = Case(registry_service=svc)
        case.article_model = ArticleModel(
            title_current="Study of unusual phenomena",
        )

        with pytest.raises(SemanticLLMRequiredError):
            case._run_discipline_matcher()


# ====================================================================
# VENUE FUNNEL PRODUCT PATH
# ====================================================================


class TestVenueFunnelProductPath:
    """Track 4: venue funnel registry candidates."""

    def test_accepted_venue_returns_as_known_corpus(self, svc, hub):
        """Accepted VenueRecord → known_corpus_candidate=True."""
        evidence = EvidenceRef(
            source_type="crossref",
            source_url="https://api.crossref.org/journals/1234-5678",
            evidence_status="adapter_result",
        )
        rec = VenueRegistryRecord(
            canonical_name="Вопросы философии",
            issn="0042-8744",
        )
        hub.venues().add_provisional(rec, evidence_refs=[evidence])
        hub.venues().accept(rec.venue_id)
        hub.venues().update_review_status(rec.venue_id, "curator_confirmed")

        candidates = svc.build_registry_candidates_for_funnel(
            query="Вопросы философии",
        )

        assert len(candidates) >= 1
        venue_cand = candidates[0]
        assert venue_cand["known_corpus_candidate"] is True
        assert venue_cand["record_id"] == rec.venue_id
        assert venue_cand["source_status"] == "accepted"
        assert venue_cand["review_status"] == "curator_confirmed"
        assert venue_cand["usage_status"] == "canonical"
        assert len(venue_cand["evidence_refs"]) >= 1

    def test_rejected_venue_excluded(self, svc, hub):
        """Rejected VenueRecord → not in candidates."""
        rec = VenueRegistryRecord(canonical_name="Bad Journal")
        hub.venues().add_provisional(rec)
        hub.venues().reject(rec.venue_id)

        candidates = svc.build_registry_candidates_for_funnel(
            query="Bad Journal",
        )

        ids = [c["record_id"] for c in candidates]
        assert rec.venue_id not in ids

    def test_provisional_venue_has_warning(self, svc, hub):
        """Provisional VenueRecord → included with warning."""
        rec = VenueRegistryRecord(canonical_name="New Journal")
        hub.venues().add_provisional(rec)

        candidates = svc.build_registry_candidates_for_funnel(
            query="New Journal",
        )

        assert len(candidates) >= 1
        cand = candidates[0]
        assert cand["usage_status"] == "provisional_with_warning"
        assert "warnings" in cand
        assert any("provisional" in w for w in cand["warnings"])

    def test_issn_lookup_for_funnel(self, svc, hub):
        """ISSN-based lookup returns exact match."""
        rec = VenueRegistryRecord(
            canonical_name="Test Journal", issn="1234-5678",
        )
        hub.venues().add_provisional(rec)
        hub.venues().accept(rec.venue_id)

        candidates = svc.build_registry_candidates_for_funnel(issn="1234-5678")

        assert len(candidates) >= 1
        assert candidates[0]["issn"] == "1234-5678"


# ====================================================================
# VENUE SECTION PRODUCT PATH
# ====================================================================


class TestVenueSectionProductPath:
    """Track 4: section candidates independent from parent."""

    def test_section_candidate_independent(self, svc, hub):
        """VenueSectionRecord → own candidate, not collapsed into parent."""
        venue_rec = VenueRegistryRecord(
            canonical_name="Вопросы философии", issn="0042-8744",
        )
        hub.venues().add_provisional(venue_rec)
        hub.venues().accept(venue_rec.venue_id)

        sec_rec = VenueSectionRecord(
            parent_venue_id=venue_rec.venue_id,
            section_name="Философия науки",
            section_type="section",
            scope="philosophy of science",
        )
        hub.venue_sections().add_provisional(sec_rec)
        hub.venue_sections().accept(sec_rec.section_id)

        candidates = svc.build_registry_candidates_for_funnel(
            query="Вопросы философии",
        )

        venue_cands = [c for c in candidates if c["candidate_type"] == "venue"]
        section_cands = [
            c for c in candidates if c["candidate_type"] == "venue_section"
        ]

        assert len(venue_cands) >= 1
        assert len(section_cands) >= 1

        sec_cand = section_cands[0]
        assert sec_cand["record_id"] == sec_rec.section_id
        assert sec_cand["section_name"] == "Философия науки"
        assert sec_cand["scope"] == "philosophy of science"
        assert sec_cand["parent_venue_id"] == venue_rec.venue_id

    def test_section_scope_not_substituted_by_parent(self, svc, hub):
        """Section scope must not be silently replaced by parent venue scope."""
        venue_rec = VenueRegistryRecord(canonical_name="Big Journal")
        hub.venues().add_provisional(venue_rec)

        sec_rec = VenueSectionRecord(
            parent_venue_id=venue_rec.venue_id,
            section_name="Narrow Section",
            scope="narrow specific scope",
        )
        hub.venue_sections().add_provisional(sec_rec)

        candidates = svc.build_registry_candidates_for_funnel(
            query="Big Journal",
        )

        section_cands = [
            c for c in candidates if c["candidate_type"] == "venue_section"
        ]
        assert len(section_cands) >= 1
        assert section_cands[0]["scope"] == "narrow specific scope"


# ====================================================================
# VENUE MATRIX PRODUCT PATH
# ====================================================================


class TestVenueMatrixProductPath:
    """Track 6: provenance enrichment."""

    def test_candidate_without_provenance_warned(self, svc):
        """Candidate without evidence_refs or source_ref gets warning."""
        candidates = [
            {"canonical_name": "Mystery Journal", "venue_candidate_id": "x"},
        ]

        enriched = svc.enrich_candidates_with_provenance(candidates)

        assert len(enriched) == 1
        assert enriched[0]["usage_status"] == "unknown"
        assert "warnings" in enriched[0]
        assert any("provenance" in w for w in enriched[0]["warnings"])

    def test_accepted_candidate_enriched_as_canonical(self, svc, hub):
        """Accepted venue candidate gets canonical usage_status."""
        rec = VenueRegistryRecord(canonical_name="Known Journal")
        hub.venues().add_provisional(
            rec, evidence_refs=[EvidenceRef(source_type="crossref")],
        )
        hub.venues().accept(rec.venue_id)
        hub.venues().update_review_status(rec.venue_id, "curator_confirmed")

        candidates = [{"record_id": rec.venue_id, "canonical_name": "Known"}]
        enriched = svc.enrich_candidates_with_provenance(candidates)

        assert enriched[0]["usage_status"] == "canonical"
        assert enriched[0]["source_status"] == "accepted"
        assert len(enriched[0]["evidence_refs"]) >= 1

    def test_provisional_candidate_enriched_with_warning_status(self, svc, hub):
        """Provisional candidate gets provisional_with_warning."""
        rec = VenueRegistryRecord(canonical_name="New Journal")
        hub.venues().add_provisional(rec)

        candidates = [{"record_id": rec.venue_id}]
        enriched = svc.enrich_candidates_with_provenance(candidates)

        assert enriched[0]["usage_status"] == "provisional_with_warning"


class TestVenueMatrixViaCase:
    """Track 6: prove Case.get_venue_matrix uses provenance enrichment."""

    def test_case_venue_matrix_enriches_candidates(self, tmp_path):
        """Case.get_venue_matrix enriches candidates with registry provenance."""
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import VenueCandidatePool

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)

        rec = VenueRegistryRecord(canonical_name="Enriched Journal")
        hub.venues().add_provisional(
            rec, evidence_refs=[EvidenceRef(source_type="doaj")],
        )
        hub.venues().accept(rec.venue_id)
        hub.venues().update_review_status(rec.venue_id, "curator_confirmed")

        case = Case(registry_service=svc)
        case.venue_pool = VenueCandidatePool(candidates=[
            {
                "venue_candidate_id": "vc_1",
                "canonical_name": "Enriched Journal",
                "record_id": rec.venue_id,
                "status": "discovered",
            },
            {
                "venue_candidate_id": "vc_2",
                "canonical_name": "Unknown Journal",
                "status": "discovered",
            },
        ])

        matrix = case.get_venue_matrix()

        assert matrix["status"] == "ok"
        candidates = matrix["candidates"]
        assert len(candidates) == 2

        enriched_cand = next(
            c for c in candidates if c.get("record_id") == rec.venue_id
        )
        assert enriched_cand["usage_status"] == "canonical"
        assert enriched_cand["source_status"] == "accepted"

        unknown_cand = next(
            c for c in candidates if c.get("venue_candidate_id") == "vc_2"
        )
        assert unknown_cand["usage_status"] == "unknown"
        assert "warnings" in unknown_cand


# ====================================================================
# VENUE FACT EXTRACTION TO REGISTRY
# ====================================================================


class TestVenueFactExtractionToRegistry:
    """Track 7: extraction output → provisional records."""

    def test_extraction_creates_venue_record(self, svc, hub):
        """Venue extraction creates provisional VenueRegistryRecord."""
        extraction = {
            "canonical_name": "Журнал Экономических Исследований",
            "issn": "2222-3333",
            "publisher_or_owner": "РАН",
        }

        result = svc.venue_extraction_to_provisional(
            extraction, source_url="https://example.com",
        )

        assert result["created_count"] >= 1
        venue_created = [
            r for r in result["records"] if r["type"] == "venue"
        ]
        assert len(venue_created) == 1
        assert result["parent_venue_id"] is not None

        rec = hub.venues().get(result["parent_venue_id"])
        assert rec is not None
        assert rec.source_status == "provisional"
        assert rec.canonical_name == "Журнал Экономических Исследований"

    def test_extraction_creates_sections(self, svc, hub):
        """Extraction with sections creates VenueSectionRecords."""
        extraction = {
            "canonical_name": "Test Journal",
            "sections": [
                {"name": "Research Articles", "type": "section", "scope": "original research"},
                {"name": "Reviews", "type": "section", "scope": "literature reviews"},
            ],
        }

        result = svc.venue_extraction_to_provisional(extraction)

        section_records = [
            r for r in result["records"] if r["type"] == "venue_section"
        ]
        assert len(section_records) == 2

    def test_metrics_per_db_year_category(self, svc, hub):
        """Metrics remain per database/year/category — no scalar collapse."""
        extraction = {
            "canonical_name": "Metric Journal",
            "metrics_claims": [
                {
                    "database": "Scopus",
                    "year": "2023",
                    "metric_type": "SJR",
                    "metric_value": "0.45",
                    "subject_category_id": "cat_1",
                },
                {
                    "database": "Scopus",
                    "year": "2024",
                    "metric_type": "SJR",
                    "metric_value": "0.52",
                    "subject_category_id": "cat_1",
                },
                {
                    "database": "WoS",
                    "year": "2023",
                    "metric_type": "JIF",
                    "metric_value": "1.2",
                    "subject_category_id": "cat_2",
                },
            ],
        }

        result = svc.venue_extraction_to_provisional(extraction)

        metric_records = [
            r for r in result["records"] if r["type"] == "venue_metric"
        ]
        assert len(metric_records) == 3

    def test_no_scalar_quartile(self, svc, hub):
        """No journal.quartile scalar created."""
        extraction = {
            "canonical_name": "Q Journal",
            "metrics_claims": [
                {"database": "Scopus", "year": "2023", "metric_type": "quartile", "metric_value": "Q1"},
            ],
        }

        result = svc.venue_extraction_to_provisional(extraction)

        venue_id = result["parent_venue_id"]
        rec = hub.venues().get(venue_id)
        assert not hasattr(rec, "quartile")

        metric_records = [
            r for r in result["records"] if r["type"] == "venue_metric"
        ]
        assert len(metric_records) == 1
        met_id = metric_records[0]["record_id"]
        met = hub.venue_metrics().get(met_id)
        assert met is not None
        assert met.database == "Scopus"
        assert met.year == "2023"

    def test_indexing_claims_as_classification_records(self, svc, hub):
        """Indexing claims create VenueClassificationRecord (vendor_claim)."""
        extraction = {
            "canonical_name": "Indexed Journal",
            "indexing_claims": ["Scopus", "WoS", "RSCI"],
        }

        result = svc.venue_extraction_to_provisional(extraction)

        clf_records = [
            r for r in result["records"] if r["type"] == "venue_classification"
        ]
        assert len(clf_records) == 3

    def test_duplicate_issn_reuses_venue(self, svc, hub):
        """Second extraction with same ISSN reuses existing venue record."""
        extraction1 = {
            "canonical_name": "Dual Journal",
            "issn": "5555-6666",
        }
        result1 = svc.venue_extraction_to_provisional(extraction1)
        venue_id_1 = result1["parent_venue_id"]

        extraction2 = {
            "canonical_name": "Dual Journal 2nd Name",
            "issn": "5555-6666",
        }
        result2 = svc.venue_extraction_to_provisional(extraction2)

        assert result2["parent_venue_id"] == venue_id_1
        venue_created_2 = [
            r for r in result2["records"] if r["type"] == "venue"
        ]
        assert len(venue_created_2) == 0


class TestVenueFactExtractionViaCase:
    """Track 7: prove Case.investigate_venue stores provisional records."""

    def _make_venue_text(self):
        """Create text the deterministic parser can extract a name from."""
        return (
            "# Вопросы философии\n\n"
            "Journal: Вопросы философии\n"
            "ISSN: 0042-8744\n"
            "Основан в 1947 году. Публикует оригинальные "
            "статьи по всем направлениям философии. Рубрики: Философия науки, "
            "Социальная философия, История философии. Индексируется в RSCI, "
            "Scopus. Требования к оформлению: 40000 знаков, сноски по "
            "ГОСТ Р 7.0.5-2008. Язык: русский, английский."
        )

    def test_case_investigate_venue_requires_llm(self, tmp_path):
        """ARCH-SEM-001: investigate_venue returns llm_required without LLM."""
        from kairoskopion.api.cases import Case

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)
        case = Case(registry_service=svc)

        result = case.investigate_venue(self._make_venue_text())

        assert result["status"] == "llm_required"
        assert case.investigated_venue is None

    def test_case_investigate_venue_sets_metadata_without_llm(self, tmp_path):
        """Even without LLM, venue_source_metadata is set (structural data)."""
        from kairoskopion.api.cases import Case

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)
        case = Case(registry_service=svc)

        case.investigate_venue(self._make_venue_text())

        assert case.venue_source_metadata is not None
        assert case.venue_source_metadata["source_type"] == "text_paste"
        assert "content_hash" in case.venue_source_metadata


# ====================================================================
# DOWNSTREAM STATUS PROPAGATION
# ====================================================================


class TestDownstreamStatusPropagation:
    """Track 8: status propagation in product output."""

    def test_propagate_status_annotates_venue_id(self, svc, hub):
        """Output dict with venue_id gets _registry_status."""
        rec = VenueRegistryRecord(canonical_name="Status Journal")
        hub.venues().add_provisional(rec)

        output = {"venue_id": rec.venue_id, "data": "value"}
        result = svc.propagate_status(output)

        assert "_registry_status" in result
        assert result["_registry_status"]["source_status"] == "provisional"
        assert result["_registry_status"]["usage_status"] == "provisional_with_warning"

    def test_propagate_status_recurses_into_candidates(self, svc, hub):
        """Status propagation recurses into candidates list."""
        rec = VenueRegistryRecord(canonical_name="Deep Journal")
        hub.venues().add_provisional(rec)
        hub.venues().accept(rec.venue_id)

        output = {
            "candidates": [
                {"venue_id": rec.venue_id, "name": "Deep"},
                {"name": "No Record"},
            ],
        }
        result = svc.propagate_status(output)

        assert "_registry_status" in result["candidates"][0]
        assert result["candidates"][0]["_registry_status"]["source_status"] == "accepted"
        assert "_registry_status" not in result["candidates"][1]

    def test_provisional_never_appears_canonical(self, svc, hub):
        """Provisional record usage_status is never 'canonical'."""
        rec = VenueRegistryRecord(canonical_name="Prov Journal")
        hub.venues().add_provisional(rec)

        output = {"venue_id": rec.venue_id}
        result = svc.propagate_status(output)

        assert result["_registry_status"]["usage_status"] != "canonical"
        assert result["_registry_status"]["usage_status"] == "provisional_with_warning"


# ====================================================================
# FAMILY CONTEXT
# ====================================================================


class TestFamilyContext:
    """Track 5: family context from registry evidence."""

    def test_family_with_sections(self, svc, hub):
        """Venue with sections returns evidence_based family."""
        venue_rec = VenueRegistryRecord(canonical_name="Parent Journal")
        hub.venues().add_provisional(venue_rec)

        sec_rec = VenueSectionRecord(
            parent_venue_id=venue_rec.venue_id,
            section_name="Section A",
        )
        hub.venue_sections().add_provisional(sec_rec)

        family = svc.build_family_context(venue_rec.venue_id)

        assert family["status"] == "evidence_based"
        assert len(family["sections"]) == 1
        assert family["sections"][0]["section_name"] == "Section A"

    def test_family_without_evidence(self, svc, hub):
        """Venue without sections/neighbors → insufficient_evidence."""
        venue_rec = VenueRegistryRecord(canonical_name="Lonely Journal")
        hub.venues().add_provisional(venue_rec)

        family = svc.build_family_context(venue_rec.venue_id)

        assert family["status"] == "insufficient_evidence"

    def test_family_unknown_venue(self, svc, hub):
        """Unknown venue_id → incomplete."""
        family = svc.build_family_context("nonexistent_venue_id")

        assert family["status"] == "incomplete"
        assert family["reason"] == "venue not in registry"

    def test_family_parent_child_neighbors(self, svc, hub):
        """Parent and child venues appear as neighbors."""
        parent = VenueRegistryRecord(canonical_name="Parent")
        hub.venues().add_provisional(parent)

        child = VenueRegistryRecord(
            canonical_name="Child",
            parent_venue_id=parent.venue_id,
        )
        hub.venues().add_provisional(child)

        family = svc.build_family_context(parent.venue_id)

        neighbor_relations = [n["relation"] for n in family["neighbors"]]
        assert "child" in neighbor_relations

    def test_rejected_section_excluded_from_family(self, svc, hub):
        """Rejected sections excluded from family context."""
        venue_rec = VenueRegistryRecord(canonical_name="Mixed Journal")
        hub.venues().add_provisional(venue_rec)

        good_sec = VenueSectionRecord(
            parent_venue_id=venue_rec.venue_id,
            section_name="Good Section",
        )
        hub.venue_sections().add_provisional(good_sec)

        bad_sec = VenueSectionRecord(
            parent_venue_id=venue_rec.venue_id,
            section_name="Bad Section",
        )
        hub.venue_sections().add_provisional(bad_sec)
        hub.venue_sections().reject(bad_sec.section_id)

        family = svc.build_family_context(venue_rec.venue_id)

        section_names = [s["section_name"] for s in family["sections"]]
        assert "Good Section" in section_names
        assert "Bad Section" not in section_names


# ====================================================================
# INVESTIGATE_VENUE REGISTRY-FIRST
# ====================================================================


class TestInvestigateVenueRegistryFirst:
    """Product-path: investigate_venue_registry_first."""

    def test_found_venue_returns_candidates_and_family(self, svc, hub):
        """Known venue → candidates + family context."""
        rec = VenueRegistryRecord(
            canonical_name="Known Venue", issn="1111-2222",
        )
        hub.venues().add_provisional(rec)
        hub.venues().accept(rec.venue_id)

        result = svc.investigate_venue_registry_first(
            venue_name="Known Venue", issn="1111-2222",
        )

        assert result["found"] is True
        assert result["usage_status"] != "unknown"
        assert result["family_context"] is not None

    def test_unknown_venue_returns_task(self, svc, hub):
        """Unknown venue → task created, no fake data."""
        result = svc.investigate_venue_registry_first(
            venue_name="Totally Unknown",
        )

        assert result["found"] is False
        assert result["usage_status"] == "unknown"
        assert result["candidates"] == []
        assert result.get("task") is not None


# ====================================================================
# BYPASS AUDIT (product-path enforcement)
# ====================================================================


class TestBypassAudit:
    """Verify that Case product paths call through integration service."""

    def test_case_has_registry_service(self, tmp_path):
        """Case always has a _registry service instance."""
        from kairoskopion.api.cases import Case

        case = Case()
        assert hasattr(case, "_registry")
        assert isinstance(case._registry, RegistryIntegrationService)

    def test_case_injected_registry_used(self, tmp_path):
        """Injected registry service is used — agent path produces matches."""
        from kairoskopion.api.cases import Case

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)

        rec = DisciplineRecord(
            display_names={"en": "Mathematics"},
            aliases=["math", "mathematical analysis"],
        )
        hub.disciplines().add_provisional(rec)
        hub.disciplines().accept(rec.discipline_id)
        hub.disciplines().update_review_status(
            rec.discipline_id, "curator_confirmed",
        )

        case = Case(registry_service=svc)
        from kairoskopion.schema import ArticleModel
        case.article_model = ArticleModel(
            title_current="Mathematical analysis",
            disciplinary_register_current="math",
        )

        from kairoskopion.llm.openai_compat import SemanticLLMRequiredError
        with pytest.raises(SemanticLLMRequiredError):
            case._run_discipline_matcher()

    def test_store_venue_extraction_requires_llm(self, tmp_path):
        """ARCH-SEM-001: investigate_venue returns llm_required without LLM."""
        from kairoskopion.api.cases import Case

        hub = RegistryHub(data_dir=tmp_path)
        svc = RegistryIntegrationService(hub=hub)
        case = Case(registry_service=svc)

        text = (
            "# Вестник МГУ Серия 7 Философия\n\n"
            "Journal: Вестник Московского университета. Серия 7. Философия\n"
            "ISSN: 0130-0091\n"
            "Публикует работы по всем направлениям философских наук. "
            "Индексируется в РИНЦ, ВАК, RSCI. Основан в 1946 году. "
            "Выходит 6 раз в год."
        )

        result = case.investigate_venue(text)

        assert result["status"] == "llm_required"
        assert len(hub.venues().list_all()) == 0
