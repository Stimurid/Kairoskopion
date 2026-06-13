"""Tests for Sherpa RoMEO venue adapter."""

from __future__ import annotations

import unittest

from kairoskopion.adapters.venue.sherpa import (
    SHERPA_FIXTURE,
    SherpaVenueAdapter,
)
from kairoskopion.adapters.venue.base import VenueAdapterMode, VenueAdapterStatus


class TestSherpaOfflineStub(unittest.TestCase):
    def setUp(self):
        self.adapter = SherpaVenueAdapter(VenueAdapterMode.OFFLINE_STUB)

    def test_lookup_returns_success(self):
        result = self.adapter.lookup_venue(name="test", issn="2210-5433")
        self.assertEqual(result.status, VenueAdapterStatus.SUCCESS.value)
        self.assertEqual(result.adapter_id, "sherpa_policy")

    def test_has_oa_prohibited_claim(self):
        result = self.adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("oa_prohibited", claim_paths)

    def test_has_archiving_versions(self):
        result = self.adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("self_archiving_versions", claim_paths)

    def test_has_embargo(self):
        result = self.adapter.lookup_venue(name="test")
        embargo_claims = [c for c in result.claims if c.claim_path == "embargo_months"]
        self.assertEqual(len(embargo_claims), 1)
        self.assertEqual(embargo_claims[0].claim_value, 12)

    def test_has_archiving_locations(self):
        result = self.adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("archiving_locations", claim_paths)

    def test_fixture_mode_same_as_offline(self):
        adapter = SherpaVenueAdapter(VenueAdapterMode.FIXTURE)
        result = adapter.lookup_venue(name="test")
        self.assertEqual(result.status, VenueAdapterStatus.SUCCESS.value)

    def test_live_api_degrades(self):
        adapter = SherpaVenueAdapter(VenueAdapterMode.LIVE_API)
        result = adapter.lookup_venue(name="test")
        self.assertEqual(result.status, VenueAdapterStatus.UNAVAILABLE.value)

    def test_to_dict(self):
        result = self.adapter.lookup_venue(name="test")
        d = result.to_dict()
        self.assertIn("claims", d)
        self.assertIn("adapter_id", d)


class TestSherpaParseResponse(unittest.TestCase):
    def test_empty_policies(self):
        adapter = SherpaVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        data = {"title": "Test Journal", "publisher_policy": []}
        result = adapter._parse_response(data, {})
        self.assertEqual(len(result.unknowns), 1)
        self.assertIn("No publisher policy", result.unknowns[0])

    def test_no_title(self):
        adapter = SherpaVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        data = {"publisher_policy": [{"permitted_oa": [], "open_access_prohibited": True}]}
        result = adapter._parse_response(data, {})
        name_claims = [c for c in result.claims if c.claim_path == "canonical_name"]
        self.assertEqual(len(name_claims), 0)


if __name__ == "__main__":
    unittest.main()
