"""Tests for Semantic Scholar venue adapter."""

from __future__ import annotations

import unittest

from kairoskopion.adapters.venue.semantic_scholar import (
    SEMANTIC_SCHOLAR_FIXTURE,
    SemanticScholarVenueAdapter,
)
from kairoskopion.adapters.venue.base import VenueAdapterMode, VenueAdapterStatus


class TestSemanticScholarOfflineStub(unittest.TestCase):
    def setUp(self):
        self.adapter = SemanticScholarVenueAdapter(VenueAdapterMode.OFFLINE_STUB)

    def test_lookup_returns_success(self):
        result = self.adapter.lookup_venue(name="test")
        self.assertEqual(result.status, VenueAdapterStatus.SUCCESS.value)
        self.assertEqual(result.adapter_id, "semantic_scholar_recommendations")

    def test_has_paper_count(self):
        result = self.adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("paper_count", claim_paths)

    def test_has_h_index(self):
        result = self.adapter.lookup_venue(name="test")
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("h_index", claim_paths)

    def test_has_recommended_venues(self):
        result = self.adapter.lookup_venue(name="test")
        rec_claims = [c for c in result.claims if c.claim_path == "recommended_venues"]
        self.assertEqual(len(rec_claims), 1)
        recs = rec_claims[0].claim_value
        self.assertEqual(len(recs), 3)
        self.assertIn("similarity", recs[0])

    def test_has_fields_of_study(self):
        result = self.adapter.lookup_venue(name="test")
        fields_claims = [c for c in result.claims if c.claim_path == "fields_of_study"]
        self.assertEqual(len(fields_claims), 1)
        self.assertIn("Philosophy", fields_claims[0].claim_value)

    def test_fixture_mode_same_as_offline(self):
        adapter = SemanticScholarVenueAdapter(VenueAdapterMode.FIXTURE)
        result = adapter.lookup_venue(name="test")
        self.assertEqual(result.status, VenueAdapterStatus.SUCCESS.value)

    def test_live_api_degrades(self):
        adapter = SemanticScholarVenueAdapter(VenueAdapterMode.LIVE_API)
        result = adapter.lookup_venue(name="test")
        self.assertEqual(result.status, VenueAdapterStatus.UNAVAILABLE.value)

    def test_to_dict(self):
        result = self.adapter.lookup_venue(name="test")
        d = result.to_dict()
        self.assertIn("claims", d)


class TestSemanticScholarParseResponse(unittest.TestCase):
    def test_empty_data(self):
        adapter = SemanticScholarVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        result = adapter._parse_response({}, {})
        self.assertEqual(result.status, VenueAdapterStatus.NO_RESULTS.value)

    def test_partial_data(self):
        adapter = SemanticScholarVenueAdapter(VenueAdapterMode.OFFLINE_STUB)
        data = {"name": "Test Journal", "h_index": 25}
        result = adapter._parse_response(data, {})
        self.assertEqual(result.status, VenueAdapterStatus.SUCCESS.value)
        claim_paths = [c.claim_path for c in result.claims]
        self.assertIn("canonical_name", claim_paths)
        self.assertIn("h_index", claim_paths)


if __name__ == "__main__":
    unittest.main()
