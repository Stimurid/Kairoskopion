"""Tests for Sprint 4: Venue Profile Builder (multi-source)."""

from __future__ import annotations

from pathlib import Path

import pytest

from kairoskopion.adapters.source_intake import SourceRole
from kairoskopion.services.venue_profile_builder import (
    VenueProfileResult,
    VenueProfileSource,
    _guess_role,
    build_venue_profile,
    register_venue_sources,
)


# ---------------------------------------------------------------------------
# Role guessing
# ---------------------------------------------------------------------------

class TestRoleGuessing:
    def test_guidelines_file(self, tmp_path):
        assert _guess_role(tmp_path / "author_guidelines.md") == SourceRole.AUTHOR_GUIDELINES

    def test_aims_file(self, tmp_path):
        assert _guess_role(tmp_path / "aims_and_scope.md") == SourceRole.AIMS_SCOPE

    def test_policy_file(self, tmp_path):
        assert _guess_role(tmp_path / "ethics_policy.md") == SourceRole.POLICY_PAGE

    def test_cfp_file(self, tmp_path):
        assert _guess_role(tmp_path / "cfp_special_issue.md") == SourceRole.SPECIAL_ISSUE_CFP

    def test_unknown_defaults_to_venue_guidelines(self, tmp_path):
        assert _guess_role(tmp_path / "random_file.md") == SourceRole.VENUE_GUIDELINES


# ---------------------------------------------------------------------------
# Source registration
# ---------------------------------------------------------------------------

class TestSourceRegistration:
    def test_registers_multiple_sources(self, tmp_path):
        f1 = tmp_path / "guidelines.md"
        f1.write_text("# Guidelines\n\nSubmission rules.", encoding="utf-8")
        f2 = tmp_path / "aims.md"
        f2.write_text("# Aims\n\nJournal scope.", encoding="utf-8")

        sources = register_venue_sources([f1, f2])
        assert len(sources) == 2
        assert sources[0].role == SourceRole.AUTHOR_GUIDELINES
        assert sources[1].role == SourceRole.AIMS_SCOPE
        assert all(s.extraction_status == "extracted" for s in sources)

    def test_role_override(self, tmp_path):
        f1 = tmp_path / "info.md"
        f1.write_text("Data.", encoding="utf-8")
        sources = register_venue_sources(
            [f1],
            roles={"info.md": SourceRole.EDITORIAL_BOARD},
        )
        assert sources[0].role == SourceRole.EDITORIAL_BOARD


# ---------------------------------------------------------------------------
# Single-source profile
# ---------------------------------------------------------------------------

class TestSingleSource:
    def test_builds_from_one_file(self, tmp_path):
        f = tmp_path / "guidelines.md"
        f.write_text("""# Journal of Test

**Journal:** Journal of Test Studies
**Publisher:** Test Press

## Aims and Scope

Research on testing methodology.

## Peer Review

Double-blind peer review process.
""", encoding="utf-8")
        result = build_venue_profile([f])
        assert isinstance(result, VenueProfileResult)
        assert result.source_count == 1
        assert result.extracted_count == 1
        assert result.venue.canonical_name == "Journal of Test Studies"
        assert result.venue.publisher_or_owner == "Test Press"
        assert result.regime.review_model == "double_blind"


# ---------------------------------------------------------------------------
# Multi-source merge
# ---------------------------------------------------------------------------

class TestMultiSourceMerge:
    def _write_guidelines(self, tmp_path):
        f = tmp_path / "guidelines.md"
        f.write_text("""# Author Guidelines

**Journal:** Journal of Merged Studies
**Publisher:** Merged Press

## Submission Requirements

Manuscripts should be in English.
Word count: 5000-8000 words.
""", encoding="utf-8")
        return f

    def _write_aims(self, tmp_path):
        f = tmp_path / "aims_scope.md"
        f.write_text("""# Journal Info

## Aims and Scope

This journal publishes research in science and technology studies.
We welcome both empirical and conceptual work.
Indexed in Scopus and Web of Science.
""", encoding="utf-8")
        return f

    def _write_policy(self, tmp_path):
        f = tmp_path / "policy.md"
        f.write_text("""# Policies

## AI Disclosure

Authors must disclose AI writing tool usage.

## Data Availability

All data must be available on request.

## Ethics

Research involving human subjects requires ethics committee approval.
""", encoding="utf-8")
        return f

    def test_merges_multiple_sources(self, tmp_path):
        f_guide = self._write_guidelines(tmp_path)
        f_aims = self._write_aims(tmp_path)
        f_policy = self._write_policy(tmp_path)

        result = build_venue_profile([f_guide, f_aims, f_policy])
        assert result.source_count == 3
        assert result.extracted_count == 3
        # Base comes from guidelines
        assert result.venue.canonical_name == "Journal of Merged Studies"
        assert result.venue.language_policy == "English"
        # Enriched from aims
        assert result.venue.scope_summary is not None
        assert "scopus" in result.venue.indexing_claims
        # Enriched from policy
        assert result.venue.ai_policy is not None
        assert result.venue.data_policy is not None
        assert result.venue.ethics_policy is not None

    def test_merge_log_tracks_enrichment(self, tmp_path):
        f_guide = self._write_guidelines(tmp_path)
        f_policy = self._write_policy(tmp_path)

        result = build_venue_profile([f_guide, f_policy])
        assert any("ai_policy" in entry for entry in result.merge_log)

    def test_does_not_overwrite_existing_fields(self, tmp_path):
        f1 = tmp_path / "main_guidelines.md"
        f1.write_text("**Journal:** First Name\n**Publisher:** First Press\n",
                       encoding="utf-8")
        f2 = tmp_path / "alt_guidelines.md"
        f2.write_text("**Journal:** Second Name\n**Publisher:** Second Press\n",
                       encoding="utf-8")

        result = build_venue_profile([f1, f2])
        # First source's name should win
        assert result.venue.canonical_name == "First Name"
        assert result.venue.publisher_or_owner == "First Press"

    def test_confidence_increases_with_data(self, tmp_path):
        f_guide = self._write_guidelines(tmp_path)
        f_aims = self._write_aims(tmp_path)
        f_policy = self._write_policy(tmp_path)

        result = build_venue_profile([f_guide, f_aims, f_policy])
        assert result.venue.confidence in ("medium", "high")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_no_extractable_sources(self, tmp_path):
        f = tmp_path / "empty.xlsx"
        f.write_bytes(b"binary data")
        result = build_venue_profile([f])
        assert result.source_count == 1
        assert result.extracted_count == 0
        assert result.venue.confidence == "none"

    def test_mixed_extractable_and_not(self, tmp_path):
        good = tmp_path / "guidelines.md"
        good.write_text("**Journal:** Good Journal\n", encoding="utf-8")
        bad = tmp_path / "diagram.xlsx"
        bad.write_bytes(b"binary")
        result = build_venue_profile([good, bad])
        assert result.source_count == 2
        assert result.extracted_count == 1
        assert result.venue.canonical_name == "Good Journal"

    def test_empty_file_list_returns_empty(self):
        result = build_venue_profile([])
        assert result.source_count == 0
        assert result.extracted_count == 0
        assert result.venue.confidence == "none"


# ---------------------------------------------------------------------------
# CLI command
# ---------------------------------------------------------------------------

class TestCLICommand:
    def test_build_venue_profile_cli(self, tmp_path, capsys):
        from kairoskopion.cli import main
        f = tmp_path / "guidelines.md"
        f.write_text("**Journal:** CLI Test\n**Publisher:** CLI Press\n", encoding="utf-8")

        code = main([
            "--storage-root", str(tmp_path / "store"),
            "build-venue-profile",
            "--files", str(f),
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "CLI Test" in out
        assert "Venue Profile Built" in out

    def test_build_venue_profile_multiple_files(self, tmp_path, capsys):
        from kairoskopion.cli import main
        f1 = tmp_path / "guidelines.md"
        f1.write_text("**Journal:** Multi Test\n", encoding="utf-8")
        f2 = tmp_path / "aims.md"
        f2.write_text("## Aims and Scope\n\nScience studies.\n", encoding="utf-8")

        code = main([
            "--storage-root", str(tmp_path / "store"),
            "build-venue-profile",
            "--files", str(f1), str(f2),
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "2 files" in out
