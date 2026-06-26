"""Phase 4: VenueMemory — cross-session venue knowledge persistence."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kairoskopion.services.venue_memory import VenueMemoryRecord, VenueMemoryRegistry


class TestVenueMemoryRecord(unittest.TestCase):
    def test_create_has_id(self):
        rec = VenueMemoryRecord(canonical_name="Logos")
        self.assertTrue(rec.venue_memory_id.startswith("vmem_"))

    def test_to_from_dict_roundtrip(self):
        rec = VenueMemoryRecord(canonical_name="VF", issn="0042-8744")
        d = rec.to_dict()
        restored = VenueMemoryRecord.from_dict(d)
        self.assertEqual(restored.canonical_name, "VF")
        self.assertEqual(restored.issn, "0042-8744")

    def test_add_note(self):
        rec = VenueMemoryRecord(canonical_name="Test")
        rec.add_note("fast review turnaround")
        self.assertEqual(len(rec.tacit_signals), 1)
        self.assertIn("fast review", rec.tacit_signals[0]["text"])

    def test_add_outcome(self):
        rec = VenueMemoryRecord(canonical_name="Test")
        rec.add_outcome({"result": "accepted", "notes": "minor revisions"})
        self.assertEqual(len(rec.prior_outcomes), 1)
        self.assertEqual(rec.prior_outcomes[0]["result"], "accepted")


class TestVenueMemoryRegistry(unittest.TestCase):
    def test_upsert_creates_new(self, tmp_path=None):
        if tmp_path is None:
            import tempfile
            tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        rec = reg.upsert_from_venue("Logos", issn="1234-5678")
        self.assertEqual(rec.canonical_name, "Logos")
        self.assertEqual(len(reg.list_all()), 1)

    def test_upsert_deduplicates_by_issn(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        reg.upsert_from_venue("Logos", issn="1234-5678")
        reg.upsert_from_venue("Logos Journal", issn="1234-5678", facts=[{"note": "hi"}])
        self.assertEqual(len(reg.list_all()), 1)
        self.assertEqual(len(reg.list_all()[0].facts), 1)

    def test_upsert_deduplicates_by_name(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        reg.upsert_from_venue("Вопросы философии")
        reg.upsert_from_venue("Вопросы философии", facts=[{"note": "vak"}])
        self.assertEqual(len(reg.list_all()), 1)

    def test_persistence_across_reloads(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg1 = VenueMemoryRegistry(tmp_path)
        reg1.upsert_from_venue("Logos", issn="1234-5678")
        reg2 = VenueMemoryRegistry(tmp_path)
        self.assertEqual(len(reg2.list_all()), 1)
        self.assertEqual(reg2.list_all()[0].canonical_name, "Logos")

    def test_get_by_id(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        rec = reg.upsert_from_venue("Test Journal")
        found = reg.get(rec.venue_memory_id)
        self.assertIsNotNone(found)
        self.assertEqual(found.canonical_name, "Test Journal")

    def test_get_unknown_returns_none(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        self.assertIsNone(reg.get("vmem-nonexistent"))

    def test_add_note_via_registry(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        rec = reg.upsert_from_venue("NoteTest")
        result = reg.add_note(rec.venue_memory_id, "good turnaround")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.tacit_signals), 1)

    def test_add_outcome_via_registry(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        rec = reg.upsert_from_venue("OutcomeTest")
        result = reg.add_outcome(rec.venue_memory_id, {"result": "rejected"})
        self.assertIsNotNone(result)
        self.assertEqual(len(result.prior_outcomes), 1)

    def test_add_note_unknown_id_returns_none(self):
        import tempfile
        tmp_path = Path(tempfile.mkdtemp())
        reg = VenueMemoryRegistry(tmp_path)
        self.assertIsNone(reg.add_note("vmem-nope", "test"))


class TestVenueMemoryAPI(unittest.TestCase):
    """Test the API endpoints via Case + app integration."""

    def test_list_empty(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/venue-memory")
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)

    def test_get_not_found(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.get("/venue-memory/vmem-nonexistent")
        self.assertEqual(resp.status_code, 404)

    def test_add_note_not_found(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.post(
            "/venue-memory/vmem-nonexistent/note",
            json={"text": "hello"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_add_outcome_not_found(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.post(
            "/venue-memory/vmem-nonexistent/outcome",
            json={"result": "rejected"},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
