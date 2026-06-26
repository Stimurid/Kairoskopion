"""Phase 4: VenueMemory — cross-session venue knowledge persistence with review gate."""

from __future__ import annotations

import unittest
from pathlib import Path

from kairoskopion.services.venue_memory import VenueMemoryRecord, VenueMemoryRegistry


class TestVenueMemoryRecord(unittest.TestCase):
    def test_create_has_id(self):
        rec = VenueMemoryRecord(canonical_name="Logos")
        self.assertTrue(rec.venue_memory_id.startswith("vmem_"))

    def test_default_review_status_is_provisional(self):
        rec = VenueMemoryRecord(canonical_name="Test")
        self.assertEqual(rec.review_status, "provisional")
        self.assertFalse(rec.is_canonical)

    def test_to_from_dict_roundtrip(self):
        rec = VenueMemoryRecord(canonical_name="VF", issn="0042-8744")
        d = rec.to_dict()
        restored = VenueMemoryRecord.from_dict(d)
        self.assertEqual(restored.canonical_name, "VF")
        self.assertEqual(restored.issn, "0042-8744")
        self.assertEqual(restored.review_status, "provisional")

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

    def test_provenance_fields(self):
        rec = VenueMemoryRecord(
            canonical_name="Test",
            record_type="case_investigation",
            created_from_case_id="case_abc",
            source_refs=["src_1"],
        )
        d = rec.to_dict()
        self.assertEqual(d["record_type"], "case_investigation")
        self.assertEqual(d["created_from_case_id"], "case_abc")
        self.assertEqual(d["source_refs"], ["src_1"])


class TestVenueMemoryRegistry(unittest.TestCase):
    def _make_registry(self):
        import tempfile
        return VenueMemoryRegistry(Path(tempfile.mkdtemp()))

    def test_upsert_creates_new(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Logos", issn="1234-5678")
        self.assertEqual(rec.canonical_name, "Logos")
        self.assertEqual(rec.review_status, "provisional")
        self.assertEqual(len(reg.list_all()), 1)

    def test_upsert_deduplicates_by_issn(self):
        reg = self._make_registry()
        reg.upsert_from_venue("Logos", issn="1234-5678")
        reg.upsert_from_venue("Logos Journal", issn="1234-5678", facts=[{"note": "hi"}])
        self.assertEqual(len(reg.list_all()), 1)

    def test_upsert_deduplicates_by_name(self):
        reg = self._make_registry()
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

    def test_get_by_id(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Test Journal")
        found = reg.get(rec.venue_memory_id)
        self.assertIsNotNone(found)

    def test_get_unknown_returns_none(self):
        reg = self._make_registry()
        self.assertIsNone(reg.get("vmem_nonexistent"))

    def test_add_note_via_registry(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("NoteTest")
        result = reg.add_note(rec.venue_memory_id, "good turnaround")
        self.assertIsNotNone(result)
        self.assertEqual(len(result.tacit_signals), 1)

    def test_add_outcome_via_registry(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("OutcomeTest")
        result = reg.add_outcome(rec.venue_memory_id, {"result": "rejected"})
        self.assertIsNotNone(result)
        self.assertEqual(len(result.prior_outcomes), 1)

    def test_add_note_unknown_id_returns_none(self):
        reg = self._make_registry()
        self.assertIsNone(reg.add_note("vmem_nope", "test"))


class TestVenueMemoryReviewGate(unittest.TestCase):
    """Review gate invariants."""

    def _make_registry(self):
        import tempfile
        return VenueMemoryRegistry(Path(tempfile.mkdtemp()))

    def test_new_record_is_provisional(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("New Journal")
        self.assertEqual(rec.review_status, "provisional")
        self.assertFalse(rec.is_canonical)

    def test_promote_to_accepted(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Test")
        result = reg.set_review_status(rec.venue_memory_id, "accepted")
        self.assertIsNotNone(result)
        self.assertEqual(result.review_status, "accepted")
        self.assertTrue(result.is_canonical)

    def test_reject_record(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Bad")
        result = reg.set_review_status(rec.venue_memory_id, "rejected")
        self.assertEqual(result.review_status, "rejected")
        self.assertFalse(result.is_canonical)

    def test_invalid_review_status_returns_none(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Test")
        result = reg.set_review_status(rec.venue_memory_id, "bogus")
        self.assertIsNone(result)

    def test_tacit_notes_do_not_become_facts(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Test")
        reg.add_note(rec.venue_memory_id, "seems good")
        updated = reg.get(rec.venue_memory_id)
        self.assertEqual(len(updated.facts), 0)
        self.assertEqual(len(updated.tacit_signals), 1)

    def test_outcomes_do_not_become_facts(self):
        reg = self._make_registry()
        rec = reg.upsert_from_venue("Test")
        reg.add_outcome(rec.venue_memory_id, {"result": "accepted"})
        updated = reg.get(rec.venue_memory_id)
        self.assertEqual(len(updated.facts), 0)
        self.assertEqual(len(updated.prior_outcomes), 1)


class TestVenueMemoryAPI(unittest.TestCase):
    """Test the API endpoints."""

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
        resp = client.get("/venue-memory/vmem_nonexistent")
        self.assertEqual(resp.status_code, 404)

    def test_add_note_not_found(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.post(
            "/venue-memory/vmem_nonexistent/note",
            json={"text": "hello"},
        )
        self.assertEqual(resp.status_code, 404)

    def test_add_outcome_not_found(self):
        from kairoskopion.api.app import app
        from starlette.testclient import TestClient
        client = TestClient(app)
        resp = client.post(
            "/venue-memory/vmem_nonexistent/outcome",
            json={"result": "rejected"},
        )
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
