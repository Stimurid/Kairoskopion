"""Tests for source authority domain models and service."""

import unittest

from kairoskopion.enums import (
    AuthorityStrength,
    ConflictResolutionStatus,
    ConflictSeverity,
    ConflictType,
    PriorVersionType,
    RetractionStatus,
    SourceAccessMode,
    SourceAuthorityScope,
)
from kairoskopion.source_authority import (
    CitationIntegrityCheck,
    EvidenceConflict,
    EvidenceReconciliationResult,
    PriorVersion,
    PublicationHistoryModel,
    ReportingGuidelineSelection,
    SourceAuthorityAssessment,
    SourceAuthorityClaim,
)
from kairoskopion.services.source_authority import (
    assess_source_authority,
    check_claim_authority,
    detect_conflicts,
    reconcile_evidence,
)


# ---------------------------------------------------------------------------
# Enum serialization
# ---------------------------------------------------------------------------

class TestEnumSerialization(unittest.TestCase):

    def test_source_access_mode_values(self):
        self.assertEqual(SourceAccessMode.METADATA_API.value, "metadata_api")
        self.assertEqual(SourceAccessMode.FULL_TEXT_PDF.value, "full_text_pdf")
        self.assertEqual(SourceAccessMode.USER_MEMORY.value, "user_memory")

    def test_source_authority_scope_values(self):
        self.assertEqual(SourceAuthorityScope.VENUE_IDENTITY.value, "venue_identity")
        self.assertEqual(SourceAuthorityScope.FORMAL_REQUIREMENTS.value, "formal_requirements")
        self.assertEqual(SourceAuthorityScope.TACIT_SIGNAL.value, "tacit_signal")

    def test_authority_strength_values(self):
        self.assertEqual(AuthorityStrength.AUTHORITATIVE.value, "authoritative")
        self.assertEqual(AuthorityStrength.PROHIBITED.value, "prohibited")

    def test_conflict_type_values(self):
        self.assertEqual(ConflictType.VALUE_MISMATCH.value, "value_mismatch")

    def test_retraction_status_values(self):
        self.assertEqual(RetractionStatus.RETRACTED.value, "retracted")
        self.assertEqual(RetractionStatus.NOT_CHECKED.value, "not_checked")

    def test_prior_version_type_values(self):
        self.assertEqual(PriorVersionType.PREPRINT.value, "preprint")
        self.assertEqual(PriorVersionType.THESIS_CHAPTER.value, "thesis_chapter")


# ---------------------------------------------------------------------------
# Model round-trip tests
# ---------------------------------------------------------------------------

class TestModelRoundTrip(unittest.TestCase):

    def test_source_authority_claim_round_trip(self):
        claim = SourceAuthorityClaim(
            source_ref="openalex:S123",
            access_mode=SourceAccessMode.METADATA_API.value,
            authority_scope=SourceAuthorityScope.VENUE_IDENTITY.value,
            claim_key="venue_name",
            claim_value="Nature",
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        d = claim.to_dict()
        self.assertEqual(d["access_mode"], "metadata_api")
        self.assertEqual(d["claim_value"], "Nature")
        restored = SourceAuthorityClaim.from_dict(d)
        self.assertEqual(restored.claim_key, "venue_name")
        self.assertEqual(restored.source_ref, "openalex:S123")

    def test_source_authority_assessment_round_trip(self):
        assessment = SourceAuthorityAssessment(
            source_ref="crossref:J456",
            access_modes=[SourceAccessMode.METADATA_API.value],
            authority_scopes=[SourceAuthorityScope.VENUE_IDENTITY.value],
            prohibited_scopes=[SourceAuthorityScope.CORPUS_PATTERN.value],
        )
        d = assessment.to_dict()
        restored = SourceAuthorityAssessment.from_dict(d)
        self.assertEqual(restored.source_ref, "crossref:J456")
        self.assertIn("venue_identity", restored.authority_scopes)

    def test_evidence_conflict_round_trip(self):
        conflict = EvidenceConflict(
            entity_id="ven_123",
            field_name="apc_amount",
            conflict_type=ConflictType.VALUE_MISMATCH.value,
            severity=ConflictSeverity.BLOCKING.value,
        )
        d = conflict.to_dict()
        self.assertEqual(d["severity"], "blocking")
        restored = EvidenceConflict.from_dict(d)
        self.assertEqual(restored.entity_id, "ven_123")

    def test_reconciliation_result_round_trip(self):
        result = EvidenceReconciliationResult(
            entity_id="ven_456",
            resolved_claims=[{"claim_key": "name"}],
            unresolved_conflicts=[{"field_name": "apc"}],
            authority_notes=["Downgraded corpus claim"],
        )
        d = result.to_dict()
        restored = EvidenceReconciliationResult.from_dict(d)
        self.assertEqual(len(restored.resolved_claims), 1)
        self.assertEqual(len(restored.unresolved_conflicts), 1)

    def test_publication_history_round_trip(self):
        pv = PriorVersion(
            version_type=PriorVersionType.PREPRINT.value,
            title="Early draft",
            doi="10.1234/preprint",
        )
        hist = PublicationHistoryModel(
            article_model_id="art_123",
            prior_versions=[pv.to_dict()],
            preprint_status="posted",
            thesis_overlap="none",
        )
        d = hist.to_dict()
        self.assertEqual(d["preprint_status"], "posted")
        restored = PublicationHistoryModel.from_dict(d)
        self.assertEqual(len(restored.prior_versions), 1)

    def test_citation_integrity_check_round_trip(self):
        check = CitationIntegrityCheck(
            reference_id="ref_abc",
            citation_key="Smith2024",
            retraction_status=RetractionStatus.NOT_RETRACTED.value,
            doi_resolution_status="resolved",
        )
        d = check.to_dict()
        self.assertEqual(d["retraction_status"], "not_retracted")
        restored = CitationIntegrityCheck.from_dict(d)
        self.assertEqual(restored.citation_key, "Smith2024")

    def test_reporting_guideline_selection_round_trip(self):
        sel = ReportingGuidelineSelection(
            article_model_id="art_456",
            article_type="systematic_review",
            candidate_guidelines=[
                {"name": "PRISMA", "applicable": True},
                {"name": "CONSORT", "applicable": False},
            ],
            selected_guidelines=["PRISMA"],
            rationale="Systematic review requires PRISMA",
        )
        d = sel.to_dict()
        restored = ReportingGuidelineSelection.from_dict(d)
        self.assertEqual(restored.selected_guidelines, ["PRISMA"])

    def test_prior_version_round_trip(self):
        pv = PriorVersion(
            version_type=PriorVersionType.CONFERENCE_PAPER.value,
            title="Conference version",
            url="https://conf.example.org/paper123",
        )
        d = pv.to_dict()
        restored = PriorVersion.from_dict(d)
        self.assertEqual(restored.version_type, "conference_paper")


# ---------------------------------------------------------------------------
# Source authority assessment
# ---------------------------------------------------------------------------

class TestSourceAuthorityAssessment(unittest.TestCase):

    def test_metadata_api_supports_venue_identity(self):
        assessment = assess_source_authority(
            "openalex:S123",
            [SourceAccessMode.METADATA_API.value],
        )
        self.assertIn(
            SourceAuthorityScope.VENUE_IDENTITY.value,
            assessment.authority_scopes,
        )

    def test_metadata_api_prohibits_corpus_pattern(self):
        assessment = assess_source_authority(
            "openalex:S123",
            [SourceAccessMode.METADATA_API.value],
        )
        self.assertIn(
            SourceAuthorityScope.CORPUS_PATTERN.value,
            assessment.prohibited_scopes,
        )

    def test_full_text_pdf_cannot_support_issn(self):
        assessment = assess_source_authority(
            "pdf:paper.pdf",
            [SourceAccessMode.FULL_TEXT_PDF.value],
        )
        self.assertIn(
            SourceAuthorityScope.ISSN_IDENTITY.value,
            assessment.prohibited_scopes,
        )

    def test_full_text_pdf_cannot_support_formal_policy(self):
        assessment = assess_source_authority(
            "pdf:paper.pdf",
            [SourceAccessMode.FULL_TEXT_PDF.value],
        )
        self.assertIn(
            SourceAuthorityScope.FORMAL_REQUIREMENTS.value,
            assessment.prohibited_scopes,
        )

    def test_full_text_pdf_cannot_support_indexing(self):
        assessment = assess_source_authority(
            "pdf:paper.pdf",
            [SourceAccessMode.FULL_TEXT_PDF.value],
        )
        self.assertIn(
            SourceAuthorityScope.INDEXING_STATUS.value,
            assessment.prohibited_scopes,
        )

    def test_official_webpage_supports_formal_requirements(self):
        assessment = assess_source_authority(
            "url:journal.org",
            [SourceAccessMode.OFFICIAL_WEBPAGE.value],
        )
        self.assertIn(
            SourceAuthorityScope.FORMAL_REQUIREMENTS.value,
            assessment.authority_scopes,
        )

    def test_official_webpage_cannot_verify_indexing_independently(self):
        assessment = assess_source_authority(
            "url:journal.org",
            [SourceAccessMode.OFFICIAL_WEBPAGE.value],
        )
        self.assertIn(
            SourceAuthorityScope.INDEXING_STATUS.value,
            assessment.prohibited_scopes,
        )

    def test_corpus_sample_supports_corpus_pattern(self):
        assessment = assess_source_authority(
            "corpus:techne",
            [SourceAccessMode.CORPUS_SAMPLE.value],
        )
        self.assertIn(
            SourceAuthorityScope.CORPUS_PATTERN.value,
            assessment.authority_scopes,
        )

    def test_corpus_sample_cannot_support_submission_eligibility(self):
        assessment = assess_source_authority(
            "corpus:techne",
            [SourceAccessMode.CORPUS_SAMPLE.value],
        )
        self.assertIn(
            SourceAuthorityScope.SUBMISSION_POLICY.value,
            assessment.prohibited_scopes,
        )

    def test_user_memory_supports_prior_outcome(self):
        assessment = assess_source_authority(
            "user:memory",
            [SourceAccessMode.USER_MEMORY.value],
        )
        self.assertIn(
            SourceAuthorityScope.PRIOR_OUTCOME.value,
            assessment.authority_scopes,
        )

    def test_user_memory_cannot_support_venue_identity(self):
        assessment = assess_source_authority(
            "user:memory",
            [SourceAccessMode.USER_MEMORY.value],
        )
        self.assertIn(
            SourceAuthorityScope.VENUE_IDENTITY.value,
            assessment.prohibited_scopes,
        )

    def test_no_access_modes_prohibits_all(self):
        assessment = assess_source_authority("empty", [])
        self.assertEqual(len(assessment.authority_scopes), 0)
        self.assertTrue(len(assessment.prohibited_scopes) > 0)

    def test_multiple_access_modes_union_scopes(self):
        assessment = assess_source_authority(
            "multi",
            [
                SourceAccessMode.METADATA_API.value,
                SourceAccessMode.OFFICIAL_WEBPAGE.value,
            ],
        )
        self.assertIn(SourceAuthorityScope.VENUE_IDENTITY.value, assessment.authority_scopes)
        self.assertIn(SourceAuthorityScope.FORMAL_REQUIREMENTS.value, assessment.authority_scopes)
        self.assertIn(SourceAuthorityScope.ARTICLE_METADATA.value, assessment.authority_scopes)


# ---------------------------------------------------------------------------
# Claim authority checking
# ---------------------------------------------------------------------------

class TestClaimAuthorityCheck(unittest.TestCase):

    def test_valid_claim_unchanged(self):
        claim = SourceAuthorityClaim(
            source_ref="openalex:S1",
            access_mode=SourceAccessMode.METADATA_API.value,
            authority_scope=SourceAuthorityScope.VENUE_IDENTITY.value,
            claim_key="name",
            claim_value="Nature",
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.AUTHORITATIVE.value)
        self.assertEqual(len(result.limitations), 0)

    def test_prohibited_claim_downgraded(self):
        claim = SourceAuthorityClaim(
            source_ref="pdf:paper.pdf",
            access_mode=SourceAccessMode.FULL_TEXT_PDF.value,
            authority_scope=SourceAuthorityScope.ISSN_IDENTITY.value,
            claim_key="issn",
            claim_value="1234-5678",
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.PROHIBITED.value)
        self.assertEqual(result.confidence, "none")
        self.assertTrue(any("cannot support" in l for l in result.limitations))

    def test_overclaimed_strength_downgraded(self):
        claim = SourceAuthorityClaim(
            source_ref="corpus:sample",
            access_mode=SourceAccessMode.CORPUS_SAMPLE.value,
            authority_scope=SourceAuthorityScope.PUBLICATION_REGIME.value,
            claim_key="regime",
            claim_value="classic",
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.WEAK.value)
        self.assertTrue(any("Downgraded" in l for l in result.limitations))

    def test_fulltext_as_metadata_authority_blocked(self):
        claim = SourceAuthorityClaim(
            access_mode=SourceAccessMode.FULL_TEXT_PDF.value,
            authority_scope=SourceAuthorityScope.FORMAL_REQUIREMENTS.value,
            claim_key="word_limit",
            claim_value=8000,
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.PROHIBITED.value)

    def test_metadata_api_as_corpus_pattern_blocked(self):
        claim = SourceAuthorityClaim(
            access_mode=SourceAccessMode.METADATA_API.value,
            authority_scope=SourceAuthorityScope.CORPUS_PATTERN.value,
            claim_key="avg_article_length",
            claim_value=7500,
            authority_strength=AuthorityStrength.SUPPORTED.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.PROHIBITED.value)

    def test_official_venue_not_independent_indexing_verification(self):
        claim = SourceAuthorityClaim(
            access_mode=SourceAccessMode.OFFICIAL_WEBPAGE.value,
            authority_scope=SourceAuthorityScope.INDEXING_STATUS.value,
            claim_key="scopus_indexed",
            claim_value=True,
            authority_strength=AuthorityStrength.AUTHORITATIVE.value,
        )
        result = check_claim_authority(claim)
        self.assertEqual(result.authority_strength, AuthorityStrength.PROHIBITED.value)


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------

class TestConflictDetection(unittest.TestCase):

    def test_no_conflict_with_single_claim(self):
        claims = [SourceAuthorityClaim(claim_key="name", claim_value="A")]
        conflict = detect_conflicts("ven_1", "name", claims)
        self.assertIsNone(conflict)

    def test_no_conflict_when_values_agree(self):
        claims = [
            SourceAuthorityClaim(claim_key="name", claim_value="Nature"),
            SourceAuthorityClaim(claim_key="name", claim_value="Nature"),
        ]
        conflict = detect_conflicts("ven_1", "name", claims)
        self.assertIsNone(conflict)

    def test_conflict_detected_on_value_mismatch(self):
        claims = [
            SourceAuthorityClaim(claim_key="apc", claim_value=1500),
            SourceAuthorityClaim(claim_key="apc", claim_value=2000),
        ]
        conflict = detect_conflicts("ven_1", "apc", claims)
        self.assertIsNotNone(conflict)
        self.assertEqual(conflict.conflict_type, ConflictType.VALUE_MISMATCH.value)
        self.assertEqual(conflict.resolution_status, ConflictResolutionStatus.UNRESOLVED.value)

    def test_conflict_severity_blocking_when_authoritative(self):
        claims = [
            SourceAuthorityClaim(
                claim_key="name", claim_value="A",
                authority_strength=AuthorityStrength.AUTHORITATIVE.value,
            ),
            SourceAuthorityClaim(
                claim_key="name", claim_value="B",
                authority_strength=AuthorityStrength.WEAK.value,
            ),
        ]
        conflict = detect_conflicts("ven_1", "name", claims)
        self.assertEqual(conflict.severity, ConflictSeverity.BLOCKING.value)

    def test_unresolved_conflicts_stay_unresolved(self):
        claims = [
            SourceAuthorityClaim(claim_key="x", claim_value=1),
            SourceAuthorityClaim(claim_key="x", claim_value=2),
        ]
        conflict = detect_conflicts("ven_1", "x", claims)
        self.assertEqual(
            conflict.resolution_status,
            ConflictResolutionStatus.UNRESOLVED.value,
        )


# ---------------------------------------------------------------------------
# Reconciliation
# ---------------------------------------------------------------------------

class TestReconciliation(unittest.TestCase):

    def test_valid_claims_resolved(self):
        claims = [
            SourceAuthorityClaim(
                access_mode=SourceAccessMode.METADATA_API.value,
                authority_scope=SourceAuthorityScope.VENUE_IDENTITY.value,
                claim_key="name",
                claim_value="Nature",
                authority_strength=AuthorityStrength.AUTHORITATIVE.value,
            ),
        ]
        result = reconcile_evidence("ven_1", claims, [])
        self.assertEqual(len(result.resolved_claims), 1)
        self.assertEqual(len(result.downgraded_claims), 0)

    def test_prohibited_claims_downgraded(self):
        claims = [
            SourceAuthorityClaim(
                access_mode=SourceAccessMode.FULL_TEXT_PDF.value,
                authority_scope=SourceAuthorityScope.ISSN_IDENTITY.value,
                claim_key="issn",
                claim_value="1234-5678",
                authority_strength=AuthorityStrength.AUTHORITATIVE.value,
            ),
        ]
        result = reconcile_evidence("ven_1", claims, [])
        self.assertEqual(len(result.downgraded_claims), 1)
        self.assertTrue(any("prohibited" in n.lower() for n in result.authority_notes))

    def test_unresolved_conflicts_tracked(self):
        conflict = EvidenceConflict(
            entity_id="ven_1",
            field_name="apc",
            resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
        )
        result = reconcile_evidence("ven_1", [], [conflict])
        self.assertEqual(len(result.unresolved_conflicts), 1)
        self.assertTrue(any("unresolved" in u for u in result.unknowns))


# ---------------------------------------------------------------------------
# Evidence Auditor integration
# ---------------------------------------------------------------------------

class TestEvidenceAuditorIntegration(unittest.TestCase):

    def _make_minimal_entities(self):
        from kairoskopion.schema import (
            ArticleModel,
            ComplianceChecklist,
            FitAssessment,
            MismatchMap,
            RiskReport,
            VenueModel,
        )
        return dict(
            article=ArticleModel(source_refs=["src1"]),
            venue=VenueModel(source_refs=["src2"]),
            fit=FitAssessment(
                overall_label="strong_candidate",
                axes=[{"axis": "scope", "value": "strong", "evidence_refs": ["e1"]}],
            ),
            mismatch_map=MismatchMap(),
            risk=RiskReport(risk_items=[{"risk": "test"}]),
            compliance=ComplianceChecklist(checklist_items=[{"item": "test"}]),
        )

    def test_auditor_warns_on_unsupported_authority(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        entities = self._make_minimal_entities()
        assessment = SourceAuthorityAssessment(
            source_ref="pdf:paper.pdf",
            unsupported_claims=[{
                "claim_key": "issn",
                "authority_scope": "issn_identity",
                "authority_strength": "weak",
            }],
        )
        result = audit_pipeline_evidence(
            **entities,
            authority_assessments=[assessment],
        )
        self.assertTrue(any("Unsupported" in u for u in result.unsupported_claims))

    def test_auditor_blocks_on_prohibited_authority(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        entities = self._make_minimal_entities()
        assessment = SourceAuthorityAssessment(
            source_ref="pdf:paper.pdf",
            unsupported_claims=[{
                "claim_key": "issn",
                "authority_scope": "issn_identity",
                "authority_strength": AuthorityStrength.PROHIBITED.value,
            }],
        )
        result = audit_pipeline_evidence(
            **entities,
            authority_assessments=[assessment],
        )
        self.assertEqual(result.status, "failed_blocking")
        self.assertTrue(any("Prohibited" in b for b in result.blocking_issues))

    def test_auditor_flags_unresolved_conflict(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        entities = self._make_minimal_entities()
        conflict = EvidenceConflict(
            entity_id="ven_1",
            field_name="apc",
            severity=ConflictSeverity.WARNING.value,
            resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
        )
        result = audit_pipeline_evidence(
            **entities,
            evidence_conflicts=[conflict],
        )
        self.assertTrue(any("Unresolved" in w for w in result.warnings))

    def test_auditor_blocks_on_blocking_conflict(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        entities = self._make_minimal_entities()
        conflict = EvidenceConflict(
            entity_id="ven_1",
            field_name="name",
            severity=ConflictSeverity.BLOCKING.value,
            resolution_status=ConflictResolutionStatus.UNRESOLVED.value,
        )
        result = audit_pipeline_evidence(
            **entities,
            evidence_conflicts=[conflict],
        )
        self.assertEqual(result.status, "failed_blocking")

    def test_auditor_passes_without_authority_data(self):
        from kairoskopion.services.evidence_audit import audit_pipeline_evidence
        entities = self._make_minimal_entities()
        result = audit_pipeline_evidence(**entities)
        self.assertIn(result.status, ("passed", "passed_with_warnings"))
        self.assertEqual(len(result.blocking_issues), 0)


# ---------------------------------------------------------------------------
# ID generation
# ---------------------------------------------------------------------------

class TestIdGeneration(unittest.TestCase):

    def test_source_authority_claim_has_id(self):
        claim = SourceAuthorityClaim()
        self.assertTrue(claim.claim_id.startswith("sacl_"))

    def test_assessment_has_id(self):
        a = SourceAuthorityAssessment()
        self.assertTrue(a.assessment_id.startswith("saas_"))

    def test_conflict_has_id(self):
        c = EvidenceConflict()
        self.assertTrue(c.conflict_id.startswith("econ_"))

    def test_reconciliation_has_id(self):
        r = EvidenceReconciliationResult()
        self.assertTrue(r.reconciliation_id.startswith("erec_"))

    def test_publication_history_has_id(self):
        h = PublicationHistoryModel()
        self.assertTrue(h.history_id.startswith("phist_"))

    def test_citation_integrity_check_has_id(self):
        c = CitationIntegrityCheck()
        self.assertTrue(c.check_id.startswith("cint_"))

    def test_reporting_guideline_selection_has_id(self):
        s = ReportingGuidelineSelection()
        self.assertTrue(s.selection_id.startswith("rgsel_"))


if __name__ == "__main__":
    unittest.main()
