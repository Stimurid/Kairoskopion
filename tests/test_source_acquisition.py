"""Tests for source acquisition layer."""

from pathlib import Path

from kairoskopion.adapters.source_intake import (
    SourceRole,
    create_evidence_from_source,
    register_local_source,
    register_text_input,
)
from kairoskopion.adapters.url_snapshot import (
    create_url_evidence_placeholder,
    create_url_snapshot_placeholder,
)
from kairoskopion.enums import EvidenceStatus

FIXTURES = Path(__file__).parent / "fixtures"


class TestRegisterLocalSource:
    def test_registers_markdown_file(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, text = register_local_source(path, role=SourceRole.ARTICLE_INPUT)
        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.extraction_status == "extracted"
        assert snapshot.content_type == "text/markdown"
        assert len(text) > 100
        assert snapshot.content_hash is not None

    def test_registers_json_file(self):
        path = FIXTURES / "submission_scenario_sample.json"
        snapshot, text = register_local_source(path, role=SourceRole.UNKNOWN)
        assert snapshot.extraction_status == "extracted"
        assert snapshot.content_type == "application/json"
        assert "goal" in text

    def test_missing_file_returns_error_status(self):
        snapshot, text = register_local_source("/nonexistent/file.md")
        assert snapshot.extraction_status == "file_not_found"
        assert text == ""
        assert len(snapshot.extraction_errors) > 0

    def test_source_id_assigned(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, _ = register_local_source(path, source_id="custom_src_123")
        assert snapshot.source_id == "custom_src_123"

    def test_auto_source_id(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, _ = register_local_source(path)
        assert snapshot.source_id.startswith("local:")

    def test_url_field_is_absolute(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, _ = register_local_source(path)
        assert Path(snapshot.url).is_absolute()


class TestCreateEvidenceFromSource:
    def test_basic(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, _ = register_local_source(path)
        evidence = create_evidence_from_source(
            snapshot,
            claim="Manuscript discusses category error",
            excerpt="artificial subjectivity is a category error",
            section="Abstract",
        )
        assert evidence.evidence_id.startswith("evi_")
        assert evidence.source_id == snapshot.source_id
        assert evidence.evidence_status == EvidenceStatus.FACT_FROM_SOURCE.value
        assert evidence.claim_supported == "Manuscript discusses category error"
        assert evidence.excerpt_or_locator is not None
        assert evidence.page_or_section == "Abstract"

    def test_user_note_status(self):
        path = FIXTURES / "manuscript_sample.md"
        snapshot, _ = register_local_source(path)
        evidence = create_evidence_from_source(
            snapshot,
            claim="Author prefers phenomenological stance",
            status=EvidenceStatus.USER_NOTE,
        )
        assert evidence.evidence_status == "USER_NOTE"
        assert evidence.confidence == "low"


class TestRegisterTextInput:
    def test_basic(self):
        snapshot = register_text_input(
            "This is a pasted abstract about AI subjectivity.",
            role=SourceRole.ARTICLE_INPUT,
            title="Pasted abstract",
        )
        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.extraction_status == "extracted"
        assert snapshot.content_hash is not None
        assert snapshot.text_ref == "Pasted abstract"

    def test_custom_source_id(self):
        snapshot = register_text_input("test", source_id="user_input_1")
        assert snapshot.source_id == "user_input_1"


class TestSourceRoles:
    def test_all_expected_roles(self):
        expected = {
            "article_input", "venue_guidelines", "author_guidelines",
            "aims_scope", "policy_page", "editorial_board",
            "submission_info", "issue_page", "special_issue_cfp",
            "published_article", "review_letter", "user_note",
            "compliance_guideline", "unknown",
        }
        actual = {r.value for r in SourceRole}
        assert expected.issubset(actual)


class TestUrlSnapshotPlaceholder:
    def test_creates_placeholder(self):
        snapshot = create_url_snapshot_placeholder(
            "https://journals.sagepub.com/home/sss",
            role=SourceRole.VENUE_GUIDELINES,
        )
        assert snapshot.snapshot_id.startswith("snap_")
        assert snapshot.url == "https://journals.sagepub.com/home/sss"
        assert snapshot.extraction_status == "not_fetched"
        assert any("disabled" in e.lower() for e in snapshot.extraction_errors)

    def test_evidence_placeholder(self):
        snapshot = create_url_snapshot_placeholder("https://example.com")
        evidence = create_url_evidence_placeholder(
            snapshot,
            expected_claim="Journal scope includes STS",
        )
        assert evidence.evidence_status == EvidenceStatus.INACCESSIBLE.value
        assert evidence.claim_supported == "Journal scope includes STS"

    def test_no_network_imports(self):
        """URL adapter must not import any HTTP libraries."""
        import kairoskopion.adapters.url_snapshot as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx",
                          "import aiohttp", "urlopen"]:
            assert forbidden not in source

    def test_no_network_in_source_intake(self):
        import kairoskopion.adapters.source_intake as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx",
                          "import aiohttp", "urlopen"]:
            assert forbidden not in source
