"""VF-C3 sub-model tests.

Covers the 10 new dataclasses added to schema.py:
  MethodExpectationProfile, GenreMoveProfile, StyleRegisterProfile,
  AuthorEligibilityProfile, TimeReviewProfile, APCAccessProfile,
  TacitVenueSignal, JournalModel, SectionModel, SpecialIssueModel.

Plus the new linking fields on VenueProfilePackage.

Each test verifies:
  - the rubric-standard four fields exist (evidence_refs, source_category,
    confidence, evidence_status) plus unknowns;
  - to_dict / from_dict roundtrip is exact;
  - defaults are honest unknowns, not silent values;
  - VenueProfilePackage carries the new link fields with safe defaults.
"""

from __future__ import annotations

import pytest

from kairoskopion.enums import VenueSourceCategory
from kairoskopion.schema import (
    APCAccessProfile,
    AuthorEligibilityProfile,
    GenreMoveProfile,
    JournalModel,
    MethodExpectationProfile,
    SectionModel,
    SpecialIssueModel,
    StyleRegisterProfile,
    TacitVenueSignal,
    TimeReviewProfile,
    VenueProfilePackage,
)


ALL_VFC3_MODELS = [
    MethodExpectationProfile,
    GenreMoveProfile,
    StyleRegisterProfile,
    AuthorEligibilityProfile,
    TimeReviewProfile,
    APCAccessProfile,
    TacitVenueSignal,
    JournalModel,
    SectionModel,
    SpecialIssueModel,
]


# ---------------------------------------------------------------------------
# Rubric-standard fields must exist on every VF-C3 sub-model
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cls", ALL_VFC3_MODELS)
def test_carries_rubric_standard_fields(cls):
    obj = cls()
    d = obj.to_dict()
    # Every sub-model must carry these four for evidence-honest population
    for fld in ("evidence_refs", "confidence", "evidence_status", "unknowns"):
        assert fld in d, f"{cls.__name__} missing rubric field {fld}"
    # source_category is rubric-required everywhere except TacitVenueSignal
    # where authority is the primary signal (still has source_category, just
    # commonly J)
    assert "source_category" in d, f"{cls.__name__} missing source_category"


@pytest.mark.parametrize("cls", ALL_VFC3_MODELS)
def test_defaults_to_honest_unknowns(cls):
    obj = cls()
    # confidence and evidence_status default to "unknown" or low,
    # never to optimistic values.
    if cls is TacitVenueSignal:
        # Per canon: tacit signals start "low" confidence and
        # "tacit_signal" evidence_status (NEVER "official_fact").
        assert obj.confidence == "low"
        assert obj.evidence_status == "tacit_signal"
        assert obj.authority == "tacit_signal"
    else:
        assert obj.confidence == "unknown"
        assert obj.evidence_status == "unknown"
    # evidence_refs starts empty (no fabricated trace)
    assert obj.evidence_refs == []


@pytest.mark.parametrize("cls", ALL_VFC3_MODELS)
def test_to_dict_from_dict_roundtrip(cls):
    obj = cls()
    d = obj.to_dict()
    rt = cls.from_dict(d)
    assert rt.to_dict() == d


# ---------------------------------------------------------------------------
# Each model gets a unique id with the expected prefix
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cls,prefix,id_field", [
    (MethodExpectationProfile, "mexp_", "method_expectation_profile_id"),
    (GenreMoveProfile, "gmove_", "genre_move_profile_id"),
    (StyleRegisterProfile, "style_", "style_register_profile_id"),
    (AuthorEligibilityProfile, "aelig_", "author_eligibility_profile_id"),
    (TimeReviewProfile, "trev_", "time_review_profile_id"),
    (APCAccessProfile, "apc_", "apc_access_profile_id"),
    (TacitVenueSignal, "tacit_", "tacit_venue_signal_id"),
    (JournalModel, "jrnl_", "journal_model_id"),
    (SectionModel, "sect_", "section_model_id"),
    (SpecialIssueModel, "spiss_", "special_issue_model_id"),
])
def test_id_prefix(cls, prefix, id_field):
    obj = cls()
    obj2 = cls()
    v1 = getattr(obj, id_field)
    v2 = getattr(obj2, id_field)
    assert v1.startswith(prefix)
    assert v2.startswith(prefix)
    assert v1 != v2, "ids must be unique per instance"


# ---------------------------------------------------------------------------
# Field-level shape checks (per canon §6.8–§6.10, §2.6, §6.16)
# ---------------------------------------------------------------------------

class TestJournalModel:
    def test_carries_canonical_identity_fields(self):
        j = JournalModel(
            canonical_title="Foucault Studies",
            issn_print="1832-5203",
            publisher="University of Copenhagen",
            homepage_url="https://rauli.cbs.dk/index.php/foucault-studies",
        )
        d = j.to_dict()
        assert d["canonical_title"] == "Foucault Studies"
        assert d["issn_print"] == "1832-5203"

    def test_declared_metrics_is_dict_not_silently_typed(self):
        j = JournalModel()
        assert j.declared_metrics == {}
        # No silent default like {"impact_factor": 0.0}
        assert "impact_factor" not in j.declared_metrics

    def test_indexing_claims_starts_empty(self):
        j = JournalModel()
        assert j.indexing_claims == []
        # We never claim "Scopus" or "VAK" by default


class TestSectionModel:
    def test_can_link_to_journal(self):
        j = JournalModel(canonical_title="Foo")
        s = SectionModel(
            journal_model_id=j.journal_model_id,
            section_name="Forum",
            article_type="essay",
        )
        assert s.journal_model_id == j.journal_model_id
        assert s.article_type == "essay"

    def test_fit_notes_are_explicit_list_not_silently_populated(self):
        s = SectionModel()
        assert s.fit_notes == []
        assert s.requirements == []


class TestSpecialIssueModel:
    def test_default_status_open(self):
        si = SpecialIssueModel()
        assert si.status == "open"

    def test_guest_editor_refs_vs_names_are_separate(self):
        si = SpecialIssueModel(
            title="AI & Continental Philosophy",
            guest_editor_names=["Yuk Hui"],
        )
        # No ref ids; names captured honestly (TacitVenueSignal-grade)
        assert si.guest_editor_refs == []
        assert si.guest_editor_names == ["Yuk Hui"]


class TestTacitVenueSignal:
    def test_tacit_authority_is_never_official_fact(self):
        t = TacitVenueSignal(
            signal_kind="review_time",
            statement="Editor told me decision in 4 weeks at last conference",
            reporter="operator",
            scope="single_anecdote",
        )
        assert t.authority == "tacit_signal"
        assert t.evidence_status == "tacit_signal"
        assert t.confidence == "low"


class TestMethodExpectationProfile:
    def test_distribution_starts_empty(self):
        m = MethodExpectationProfile()
        assert m.method_distribution == {}
        assert m.dominant_methods == []
        assert m.forbidden_methods == []

    def test_continental_acceptance_starts_unknown_not_assumed(self):
        m = MethodExpectationProfile()
        # Critical: must not silently assume venue accepts no-method continental
        assert m.accepts_no_method_continental is None
        assert m.accepts_textual_analysis_only is None


class TestGenreMoveProfile:
    def test_per_section_moves_is_empty_dict(self):
        g = GenreMoveProfile()
        assert g.per_section_moves == {}
        assert g.conspicuously_absent_moves == []


class TestStyleRegisterProfile:
    def test_jargon_density_is_none_by_default_not_zero(self):
        s = StyleRegisterProfile()
        # Critical: 0.0 would claim "no jargon" — we don't know yet
        assert s.jargon_density is None
        assert s.primary_language is None


class TestAuthorEligibilityProfile:
    def test_invitation_only_default_is_unknown_not_false(self):
        a = AuthorEligibilityProfile()
        # None = unknown; False would silently claim "venue accepts everyone"
        assert a.invitation_only is None
        assert a.requires_institutional_affiliation is None


class TestTimeReviewProfile:
    def test_review_metrics_default_unknown(self):
        t = TimeReviewProfile()
        assert t.desk_rejection_rate_pct is None
        assert t.avg_days_to_first_decision is None


class TestAPCAccessProfile:
    def test_apc_amounts_default_none_not_zero(self):
        a = APCAccessProfile()
        # 0.0 would imply "free" — must stay None until extracted
        assert a.apc_amount_min is None
        assert a.apc_amount_max is None
        assert a.open_access_model is None


# ---------------------------------------------------------------------------
# VenueProfilePackage backward compatibility + new link fields
# ---------------------------------------------------------------------------

class TestVenueProfilePackageVFC3Linking:
    def test_vpkg_carries_new_link_fields_with_safe_defaults(self):
        v = VenueProfilePackage()
        # New single-link fields default to None
        for fld in (
            "method_expectation_profile_id",
            "genre_move_profile_id",
            "style_register_profile_id",
            "author_eligibility_profile_id",
            "time_review_profile_id",
            "apc_access_profile_id",
            "journal_model_id",
        ):
            assert getattr(v, fld) is None, f"{fld} should default to None"
        # New multi-link fields default to []
        for fld in (
            "tacit_venue_signal_ids",
            "section_model_ids",
            "special_issue_model_ids",
        ):
            assert getattr(v, fld) == [], f"{fld} should default to []"

    def test_vpkg_from_dict_ignores_unknown_fields(self):
        # Old-format JSONL records (without VF-C3 fields) must still load
        old = {
            "venue_profile_package_id": "vpkg_legacy_001",
            "canonical_name": "Old Venue",
            "issns": ["1234-5678"],
        }
        v = VenueProfilePackage.from_dict(old)
        assert v.canonical_name == "Old Venue"
        assert v.method_expectation_profile_id is None
        assert v.section_model_ids == []

    def test_vpkg_to_dict_includes_vfc3_fields(self):
        v = VenueProfilePackage(
            canonical_name="V",
            journal_model_id="jrnl_xyz",
            section_model_ids=["sect_1", "sect_2"],
        )
        d = v.to_dict()
        assert d["journal_model_id"] == "jrnl_xyz"
        assert d["section_model_ids"] == ["sect_1", "sect_2"]

    def test_vpkg_roundtrip_with_vfc3_fields(self):
        v = VenueProfilePackage(
            canonical_name="V",
            method_expectation_profile_id="mexp_1",
            tacit_venue_signal_ids=["tacit_a", "tacit_b"],
            special_issue_model_ids=["spiss_x"],
        )
        rt = VenueProfilePackage.from_dict(v.to_dict())
        assert rt.method_expectation_profile_id == "mexp_1"
        assert rt.tacit_venue_signal_ids == ["tacit_a", "tacit_b"]
        assert rt.special_issue_model_ids == ["spiss_x"]


# ---------------------------------------------------------------------------
# Source category integration with VenueSourceCategory enum
# ---------------------------------------------------------------------------

class TestSourceCategoryIntegration:
    def test_can_store_venue_source_category_value(self):
        m = MethodExpectationProfile(
            source_category=VenueSourceCategory.D_CORPUS.value,
        )
        d = m.to_dict()
        # Value serialises as the enum's str value, NOT the enum object
        assert d["source_category"] == VenueSourceCategory.D_CORPUS.value
        # Can roundtrip
        rt = MethodExpectationProfile.from_dict(d)
        assert rt.source_category == VenueSourceCategory.D_CORPUS.value

    def test_journal_model_with_indexers_source_category(self):
        # Indexers are category C
        j = JournalModel(
            canonical_title="V",
            source_category=VenueSourceCategory.C_INDEXER_REGISTRY.value,
            indexing_claims=["DOAJ", "OpenAlex"],
        )
        assert j.source_category == VenueSourceCategory.C_INDEXER_REGISTRY.value
