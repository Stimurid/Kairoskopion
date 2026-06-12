"""Tests for Venue Evidence Stack V1-V2 foundation.

Covers: depth model, vault backend, venue adapters, evidence stack service,
corpus sampler/analyzer.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Phase 2 — Depth model tests
# ---------------------------------------------------------------------------


class TestVenueDepthModel:
    def test_depth_level_enum_round_trip(self):
        from kairoskopion.venue_depth import VenueEvidenceDepthLevel

        for level in VenueEvidenceDepthLevel:
            assert VenueEvidenceDepthLevel(level.value) == level

    def test_analysis_purpose_enum_round_trip(self):
        from kairoskopion.venue_depth import VenueAnalysisPurpose

        for p in VenueAnalysisPurpose:
            assert VenueAnalysisPurpose(p.value) == p

    def test_depth_level_order(self):
        from kairoskopion.venue_depth import DEPTH_LEVEL_ORDER, VenueEvidenceDepthLevel

        assert len(DEPTH_LEVEL_ORDER) == 8
        assert DEPTH_LEVEL_ORDER[0] == VenueEvidenceDepthLevel.L0_IDENTITY
        assert DEPTH_LEVEL_ORDER[-1] == VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES

    def test_default_policies_exist(self):
        from kairoskopion.venue_depth import DEFAULT_POLICIES

        assert "quick_look" in DEFAULT_POLICIES
        assert "fit_assessment" in DEFAULT_POLICIES
        assert "submission_ready" in DEFAULT_POLICIES

    def test_quick_look_stops_at_l2(self):
        from kairoskopion.venue_depth import VenueEvidenceDepthLevel, get_depth_policy

        policy = get_depth_policy("quick_look")
        assert policy.target_depth == VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL
        assert policy.max_depth == VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL

    def test_fit_assessment_targets_at_least_l4(self):
        from kairoskopion.venue_depth import VenueEvidenceDepthLevel, get_depth_policy, depth_level_index

        policy = get_depth_policy("fit_assessment")
        assert depth_level_index(policy.target_depth) >= depth_level_index(
            VenueEvidenceDepthLevel.L4_EDITORIAL_INTELLIGENCE
        )

    def test_submission_ready_targets_l7(self):
        from kairoskopion.venue_depth import VenueEvidenceDepthLevel, get_depth_policy

        policy = get_depth_policy("submission_ready")
        assert policy.target_depth == VenueEvidenceDepthLevel.L7_USER_MEMORY_AND_OUTCOMES

    def test_unknown_purpose_raises(self):
        from kairoskopion.venue_depth import get_depth_policy

        with pytest.raises(ValueError, match="Unknown purpose"):
            get_depth_policy("nonexistent_purpose")

    def test_policy_to_dict_round_trip(self):
        from kairoskopion.venue_depth import VenueDepthPolicy, get_depth_policy

        policy = get_depth_policy("quick_look")
        d = policy.to_dict()
        restored = VenueDepthPolicy.from_dict(d)
        assert restored.purpose == policy.purpose
        assert restored.target_depth == policy.target_depth

    def test_levels_in_range(self):
        from kairoskopion.venue_depth import VenueEvidenceDepthLevel, levels_in_range

        levels = levels_in_range(
            VenueEvidenceDepthLevel.L0_IDENTITY,
            VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL,
        )
        assert len(levels) == 3

    def test_depth_coverage_reports_gaps(self):
        from kairoskopion.venue_depth import VenueDepthCoverage, VenueEvidenceDepthLevel

        coverage = VenueDepthCoverage(
            venue_id="test",
            purpose="fit_assessment",
            reached_depth=VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL,
            missing_required_sources=["openalex_works_sample"],
        )
        assert coverage.has_coverage_gaps

    def test_depth_coverage_no_gaps(self):
        from kairoskopion.venue_depth import VenueDepthCoverage, VenueEvidenceDepthLevel

        coverage = VenueDepthCoverage(
            venue_id="test",
            purpose="quick_look",
            reached_depth=VenueEvidenceDepthLevel.L2_PUBLICATION_MODEL,
        )
        assert not coverage.has_coverage_gaps

    def test_level_source_roles_defined(self):
        from kairoskopion.venue_depth import LEVEL_SOURCE_ROLES, VenueEvidenceDepthLevel

        for level in VenueEvidenceDepthLevel:
            assert level in LEVEL_SOURCE_ROLES


# ---------------------------------------------------------------------------
# Phase 3 — Vault backend tests
# ---------------------------------------------------------------------------


class TestLocalFsVault:
    def test_write_read_text(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            ref = vault.write_text(
                "test/doc.md", "# Hello World", VaultObjectKind.VENUE_CARD_MD.value,
            )
            assert ref.content_hash
            assert ref.size_bytes == len("# Hello World".encode("utf-8"))
            assert vault.read_text("test/doc.md") == "# Hello World"

    def test_write_read_json(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            data = {"key": "value", "nested": {"a": 1}}
            ref = vault.write_json(
                "test/data.json", data, VaultObjectKind.ADAPTER_SNAPSHOT_JSON.value,
            )
            assert ref.content_hash
            loaded = vault.read_json("test/data.json")
            assert loaded["key"] == "value"
            assert loaded["nested"]["a"] == 1

    def test_content_hash_stable(self):
        from kairoskopion.storage.vault_backend import compute_content_hash

        content = b"stable content for hashing"
        h1 = compute_content_hash(content)
        h2 = compute_content_hash(content)
        assert h1 == h2
        assert len(h1) == 16

    def test_content_hash_differs(self):
        from kairoskopion.storage.vault_backend import compute_content_hash

        h1 = compute_content_hash(b"content A")
        h2 = compute_content_hash(b"content B")
        assert h1 != h2

    def test_exists(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            assert not vault.exists("missing.txt")
            vault.write_text("found.txt", "data", VaultObjectKind.ARTICLE_TEXT.value)
            assert vault.exists("found.txt")

    def test_list_by_prefix(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            vault.write_text("venues/a.md", "a", VaultObjectKind.VENUE_CARD_MD.value)
            vault.write_text("venues/b.md", "b", VaultObjectKind.VENUE_CARD_MD.value)
            vault.write_text("other/c.md", "c", VaultObjectKind.VENUE_CARD_MD.value)
            items = vault.list_by_prefix("venues/")
            assert len(items) == 2

    def test_metadata_sidecar(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            vault.write_text(
                "test.md", "content", VaultObjectKind.VENUE_CARD_MD.value,
                metadata={"source_url": "https://example.com"},
            )
            meta = vault.get_metadata("test.md")
            assert meta["source_url"] == "https://example.com"
            assert "content_hash" in meta

    def test_delete(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault
        from kairoskopion.storage.vault_backend import VaultObjectKind

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            vault.write_text("del.txt", "data", VaultObjectKind.ARTICLE_TEXT.value)
            assert vault.exists("del.txt")
            assert vault.delete("del.txt")
            assert not vault.exists("del.txt")

    def test_read_missing_raises(self):
        from kairoskopion.storage.local_fs_vault import LocalFsVault

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            with pytest.raises(FileNotFoundError):
                vault.read_bytes("missing")

    def test_vault_object_kind_enum(self):
        from kairoskopion.storage.vault_backend import VaultObjectKind

        assert len(VaultObjectKind) == 8
        for kind in VaultObjectKind:
            assert VaultObjectKind(kind.value) == kind

    def test_vault_object_ref_round_trip(self):
        from kairoskopion.storage.vault_backend import VaultObjectRef

        ref = VaultObjectRef(
            vault_path="test/file.md",
            content_hash="abc123",
            content_type="text/markdown",
            size_bytes=100,
            kind="venue_card_md",
        )
        d = ref.to_dict()
        restored = VaultObjectRef.from_dict(d)
        assert restored.vault_path == ref.vault_path
        assert restored.content_hash == ref.content_hash


# ---------------------------------------------------------------------------
# Phase 4 — Adapter tests
# ---------------------------------------------------------------------------


class TestVenueAdapters:
    def test_openalex_offline_stub(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter

        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(name="Philosophy & Technology")
        assert result.is_available
        assert result.status == "success"
        assert len(result.claims) > 0
        assert result.evidence_status == "FACT_FROM_API_METADATA"

    def test_openalex_parse_fixture(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter

        adapter = OpenAlexVenueAdapter()
        fixture = {
            "display_name": "Test Journal",
            "issn_l": "1234-5678",
            "publisher": "Test Publisher",
            "type": "journal",
        }
        result = adapter.parse_response(fixture)
        assert result.status == "success"
        names = [c.claim_path for c in result.claims]
        assert "canonical_name" in names
        assert "issn" in names

    def test_crossref_offline_stub(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter

        adapter = CrossrefVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        assert result.is_available
        assert len(result.claims) > 0

    def test_crossref_parse_fixture(self):
        from kairoskopion.adapters.venue.crossref import CrossrefVenueAdapter

        adapter = CrossrefVenueAdapter()
        fixture = {
            "title": "Custom Journal",
            "ISSN": ["9999-0001"],
            "publisher": "Custom Publisher",
        }
        result = adapter.parse_response(fixture)
        assert result.status == "success"

    def test_opencitations_offline_stub(self):
        from kairoskopion.adapters.venue.opencitations import OpenCitationsVenueAdapter

        adapter = OpenCitationsVenueAdapter()
        result = adapter.lookup_venue(issn="2210-5433")
        assert result.is_available
        assert len(result.claims) > 0

    def test_snapshot_crawler_offline_stub(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler

        crawler = VenueSnapshotCrawler()
        result = crawler.lookup_venue(url="https://example.com/guidelines")
        assert result.is_available
        assert result.evidence_status == "FACT_FROM_SOURCE"

    def test_snapshot_crawler_with_vault(self):
        from kairoskopion.adapters.venue.snapshot_crawler import VenueSnapshotCrawler
        from kairoskopion.storage.local_fs_vault import LocalFsVault

        with tempfile.TemporaryDirectory() as tmp:
            vault = LocalFsVault(Path(tmp))
            crawler = VenueSnapshotCrawler(vault=vault)
            result = crawler.store_provided_html(
                "<html><body>Test</body></html>",
                "https://example.com/test",
            )
            assert result.is_available
            assert result.vault_ref is not None
            assert vault.exists(result.vault_ref)

    def test_adapter_degrade_gracefully(self):
        from kairoskopion.adapters.venue.base import VenueAdapterMode
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter

        adapter = OpenAlexVenueAdapter(VenueAdapterMode.LIVE_API)
        result = adapter.lookup_venue(name="test")
        assert not result.is_available
        assert result.status == "unavailable"
        assert result.error

    def test_adapter_result_to_dict(self):
        from kairoskopion.adapters.venue.openalex import OpenAlexVenueAdapter

        adapter = OpenAlexVenueAdapter()
        result = adapter.lookup_venue(name="test")
        d = result.to_dict()
        assert "adapter_id" in d
        assert "claims" in d
        assert isinstance(d["claims"], list)

    def test_venue_adapter_mode_enum(self):
        from kairoskopion.adapters.venue.base import VenueAdapterMode

        assert VenueAdapterMode.OFFLINE_STUB.value == "offline_stub"
        assert VenueAdapterMode.LIVE_API.value == "live_api"
        assert VenueAdapterMode.CACHED_SNAPSHOT.value == "cached_snapshot"


# ---------------------------------------------------------------------------
# Phase 5 — Evidence stack service tests
# ---------------------------------------------------------------------------


class TestVenueEvidenceStack:
    def test_quick_look_uses_low_depth(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test Journal",
            purpose="quick_look",
            offline=True,
        )
        assert result.purpose == "quick_look"
        coverage = result.depth_coverage
        # Quick look should have L0 and L1 at minimum
        assert "L0_IDENTITY" in coverage.level_coverage
        # Should NOT have deep levels completed
        l3 = coverage.level_coverage.get("L3_CORPUS_SAMPLE")
        if l3:
            assert l3.status == "never_run"

    def test_fit_assessment_reports_missing_corpus(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test Journal",
            purpose="fit_assessment",
            offline=True,
        )
        assert result.has_coverage_gaps or any(
            "L3" in u or "corpus" in u.lower()
            for u in result.depth_coverage.unknowns
        )

    def test_fit_assessment_with_corpus_fixture(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test Journal",
            purpose="fit_assessment",
            offline=True,
            adapter_fixtures={
                "corpus": {"articles": [{"title": "Test", "year": 2024}]},
            },
        )
        l3 = result.depth_coverage.level_coverage.get("L3_CORPUS_SAMPLE")
        assert l3 is not None
        assert l3.status != "never_run"

    def test_evidence_pack_populated(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test",
            purpose="quick_look",
            offline=True,
        )
        pack = result.evidence_pack
        assert pack is not None
        total = len(pack.official_facts) + len(pack.external_claims) + len(pack.inferences)
        assert total > 0

    def test_build_log_present(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test",
            purpose="quick_look",
            offline=True,
        )
        assert len(result.build_log) > 0

    def test_result_to_dict(self):
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        result = build_venue_evidence_stack(
            venue_name="Test",
            purpose="quick_look",
            offline=True,
        )
        d = result.to_dict()
        assert "venue_id" in d
        assert "depth_coverage" in d
        assert "evidence_pack" in d

    def test_with_existing_venue_model(self):
        from kairoskopion.schema import VenueModel
        from kairoskopion.services.venue_evidence_stack import build_venue_evidence_stack

        vm = VenueModel(canonical_name="Known Journal", official_urls=["https://example.com"])
        result = build_venue_evidence_stack(
            venue_model=vm,
            purpose="quick_look",
            offline=True,
        )
        assert result.venue_id == vm.venue_model_id


# ---------------------------------------------------------------------------
# Phase 7 — Corpus sampler/analyzer tests
# ---------------------------------------------------------------------------


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "venue_evidence"


class TestCorpusSampler:
    def _load_corpus_fixture(self) -> list[dict]:
        path = FIXTURES_DIR / "synthetic_corpus.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_sample_from_fixtures(self):
        from kairoskopion.services.corpus_sampler import sample_venue_corpus

        articles = self._load_corpus_fixture()
        result = sample_venue_corpus(
            venue_model_id="test_venue",
            article_fixtures=articles,
        )
        assert result.corpus.corpus_size == len(articles)
        assert result.fixture_source
        assert result.selection_strategy_used == "recent_first"

    def test_empty_corpus_handled(self):
        from kairoskopion.services.corpus_sampler import sample_venue_corpus

        result = sample_venue_corpus(venue_model_id="empty")
        assert result.corpus.corpus_size == 0
        assert "No articles provided" in result.representativeness_notes[0]

    def test_small_sample_warning(self):
        from kairoskopion.services.corpus_sampler import sample_venue_corpus

        result = sample_venue_corpus(
            venue_model_id="test",
            article_fixtures=[{"title": "One", "genre": "conceptual_article"}],
        )
        assert any("small" in n.lower() or "Small" in n for n in result.bias_notes)

    def test_distributions_computed(self):
        from kairoskopion.services.corpus_sampler import sample_venue_corpus

        articles = self._load_corpus_fixture()
        result = sample_venue_corpus(
            venue_model_id="test",
            article_fixtures=articles,
        )
        assert result.corpus.genre_distribution
        assert result.corpus.method_distribution
        assert result.corpus.average_word_count is not None
        assert result.corpus.average_reference_count is not None

    def test_missing_fulltext_tracked(self):
        from kairoskopion.services.corpus_sampler import sample_venue_corpus

        articles = self._load_corpus_fixture()
        result = sample_venue_corpus(
            venue_model_id="test",
            article_fixtures=articles,
        )
        assert len(result.missing_fulltext_notes) > 0


class TestCorpusAnalyzer:
    def _load_corpus_fixture(self) -> list[dict]:
        path = FIXTURES_DIR / "synthetic_corpus.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def test_analyze_detects_methods(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        articles = self._load_corpus_fixture()
        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=len(articles))

        result = analyze_venue_corpus(corpus, article_texts=articles)
        assert len(result.method_patterns) > 0
        method_keys = [p.pattern_key for p in result.method_patterns]
        assert "conceptual" in method_keys or "empirical" in method_keys

    def test_analyze_detects_schools(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        articles = self._load_corpus_fixture()
        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=len(articles))

        result = analyze_venue_corpus(corpus, article_texts=articles)
        assert len(result.school_patterns) > 0
        school_keys = [p.pattern_key for p in result.school_patterns]
        # Fixture has postphenomenology, STS, AI ethics content
        assert any(s in school_keys for s in ["postphenomenology", "sts", "ai_ethics", "phenomenology"])

    def test_empty_corpus_analysis(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=0)
        result = analyze_venue_corpus(corpus)
        assert result.confidence == "none"
        assert len(result.unknowns) > 0

    def test_citation_stats_computed(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        articles = self._load_corpus_fixture()
        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=len(articles))
        result = analyze_venue_corpus(corpus, article_texts=articles)
        assert "median_references" in result.citation_stats

    def test_does_not_overclaim(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        articles = self._load_corpus_fixture()
        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=len(articles))
        result = analyze_venue_corpus(corpus, article_texts=articles)
        # Small corpus should not claim high confidence
        assert result.confidence in ("low", "medium")

    def test_result_to_dict(self):
        from kairoskopion.schema import PublishedArticleCorpus
        from kairoskopion.services.corpus_analyzer import analyze_venue_corpus

        articles = self._load_corpus_fixture()
        corpus = PublishedArticleCorpus(venue_model_id="test", corpus_size=len(articles))
        result = analyze_venue_corpus(corpus, article_texts=articles)
        d = result.to_dict()
        assert "method_patterns" in d
        assert "school_patterns" in d
        assert "confidence" in d
