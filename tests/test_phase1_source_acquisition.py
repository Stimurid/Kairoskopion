"""Phase 1: Source Acquisition Layer tests."""

from __future__ import annotations

import unittest
from unittest.mock import patch, MagicMock

from kairoskopion.api.cases import Case


class TestInvestigateVenueByUrl(unittest.TestCase):
    """1.1: URL → Snapshot → Text pipeline."""

    def _make_case(self):
        return Case(case_id="test_url", user_id="u1")

    def test_non_https_rejected(self):
        case = self._make_case()
        result = case.investigate_venue_by_url("http://example.com")
        self.assertEqual(result["status"], "invalid_url")

    def test_fetch_failure_returns_error(self):
        case = self._make_case()
        fake_result = MagicMock()
        fake_result.ok = False
        fake_result.error = "timeout_or_io: timed out"
        with patch(
            "kairoskopion.adapters.http_client.fetch_text_safe",
            return_value=fake_result,
        ):
            result = case.investigate_venue_by_url("https://example.com/journal")
        self.assertEqual(result["status"], "fetch_failed")
        self.assertIn("timeout", result["error"])

    def test_successful_url_intake(self):
        case = self._make_case()
        long_text = "This is a journal about philosophy and technology. " * 20
        fake_result = MagicMock()
        fake_result.ok = True
        fake_result.text = long_text
        with patch(
            "kairoskopion.adapters.http_client.fetch_text_safe",
            return_value=fake_result,
        ):
            result = case.investigate_venue_by_url("https://example.com/journal")
        self.assertIn("venue", result)
        self.assertIsNotNone(case.investigated_venue)

    def test_source_metadata_populated_on_url_intake(self):
        case = self._make_case()
        long_text = "This is a journal about philosophy and technology. " * 20
        fake_result = MagicMock()
        fake_result.ok = True
        fake_result.text = long_text
        with patch(
            "kairoskopion.adapters.http_client.fetch_text_safe",
            return_value=fake_result,
        ):
            case.investigate_venue_by_url("https://example.com/journal")
        self.assertIsNotNone(case.venue_source_metadata)
        self.assertEqual(case.venue_source_metadata["source_type"], "url_fetch")
        self.assertEqual(
            case.venue_source_metadata["source_url"],
            "https://example.com/journal",
        )
        self.assertIn("content_hash", case.venue_source_metadata)

    def test_short_content_returns_needs_more(self):
        case = self._make_case()
        fake_result = MagicMock()
        fake_result.ok = True
        fake_result.text = "Short page"
        with patch(
            "kairoskopion.adapters.http_client.fetch_text_safe",
            return_value=fake_result,
        ):
            result = case.investigate_venue_by_url("https://example.com/journal")
        self.assertEqual(result["status"], "needs_more_venue_text")


class TestSourceRegistration(unittest.TestCase):
    """1.2: Source registration in venue intake."""

    def test_text_paste_provenance(self):
        case = Case(case_id="test_src", user_id="u1")
        text = "Philosophy journal scope and aims. " * 20
        case.investigate_venue(text)
        self.assertIsNotNone(case.venue_source_metadata)
        self.assertEqual(case.venue_source_metadata["source_type"], "text_paste")
        self.assertIsNone(case.venue_source_metadata["source_url"])

    def test_content_hash_present(self):
        case = Case(case_id="test_hash", user_id="u1")
        text = "Philosophy journal scope and aims. " * 20
        case.investigate_venue(text)
        self.assertIn("content_hash", case.venue_source_metadata)
        self.assertEqual(len(case.venue_source_metadata["content_hash"]), 16)

    def test_reference_intake_sets_metadata_via_investigate(self):
        """investigate_venue_by_reference calls investigate_venue which sets metadata."""
        case = Case(case_id="test_ref_meta", user_id="u1")
        text = "Philosophy journal scope and aims. " * 20
        case.investigate_venue(text)
        self.assertIsNotNone(case.venue_source_metadata)


class TestAdapterModeToggle(unittest.TestCase):
    """1.3: Adapter mode toggle."""

    def test_default_mode_is_offline_stub(self):
        case = Case(case_id="test_mode", user_id="u1")
        self.assertEqual(case.adapter_mode, "offline_stub")

    def test_set_valid_mode(self):
        case = Case(case_id="test_mode2", user_id="u1")
        result = case.set_adapter_mode("live_api")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(case.adapter_mode, "live_api")

    def test_set_invalid_mode_rejected(self):
        case = Case(case_id="test_mode3", user_id="u1")
        result = case.set_adapter_mode("nonexistent")
        self.assertEqual(result["status"], "invalid_mode")
        self.assertIn("valid", result)
        self.assertEqual(case.adapter_mode, "offline_stub")


class TestPersistence(unittest.TestCase):
    """Serialization round-trip for new Phase 1 fields."""

    def test_venue_source_metadata_survives_roundtrip(self):
        from kairoskopion.api.cases import _case_to_snapshot, _case_from_snapshot
        case = Case(case_id="test_rt", user_id="u1")
        case.venue_source_metadata = {
            "source_url": "https://example.com",
            "source_type": "url_fetch",
            "content_hash": "abcdef1234567890",
        }
        case.adapter_mode = "live_api"

        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertEqual(restored.venue_source_metadata["source_url"], "https://example.com")
        self.assertEqual(restored.adapter_mode, "live_api")

    def test_default_adapter_mode_not_serialized(self):
        from kairoskopion.api.cases import _case_to_snapshot
        case = Case(case_id="test_def", user_id="u1")
        snap = _case_to_snapshot(case)
        self.assertNotIn("adapter_mode", snap)


if __name__ == "__main__":
    unittest.main()
