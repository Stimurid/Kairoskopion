"""Round III-H: upload metadata persistence across save/load.

Pins:
  - Case has a settable upload_metadata slot.
  - Case snapshot persists it.
  - Case loaded from snapshot recovers it byte-equal.
  - build_dossier() surfaces upload_metadata at the dossier top level.
"""

from __future__ import annotations

import json
import unittest

from kairoskopion.api.cases import Case, _case_from_snapshot, _case_to_snapshot


class TestUploadMetadataPersistence(unittest.TestCase):
    def _meta(self) -> dict:
        return {
            "original_filename": "статья.docx",
            "original_extension": "docx",
            "upload_source_type": "docx",
            "original_file_size_bytes": 12345,
            "content_hash_prefix": "abcdef1234567890",
            "text_hash_prefix": "0fedcba987654321",
            "uploaded_at": "2026-06-23T10:00:00+00:00",
            "extraction_status": "ok",
            "text_char_count": 1024,
            "text_word_count": 200,
        }

    def test_case_slot_default_none(self):
        c = Case()
        self.assertIsNone(c.upload_metadata)

    def test_roundtrip_through_snapshot(self):
        c = Case(title="case-x")
        c.upload_metadata = self._meta()
        snap = _case_to_snapshot(c)
        # Round-trip via JSON to mimic CaseStore behaviour
        snap = json.loads(json.dumps(snap, default=str))
        restored = _case_from_snapshot(snap)
        self.assertEqual(restored.upload_metadata, self._meta())

    def test_legacy_snapshot_without_field_loads_as_none(self):
        c = Case(title="legacy")
        snap = _case_to_snapshot(c)
        snap.pop("upload_metadata", None)  # simulate old persistence
        restored = _case_from_snapshot(snap)
        self.assertIsNone(restored.upload_metadata)

    def test_build_dossier_surfaces_upload_metadata(self):
        c = Case(title="case-x")
        c.upload_metadata = self._meta()
        d = c.build_dossier()
        self.assertEqual(d.get("upload_metadata"), self._meta())


if __name__ == "__main__":
    unittest.main()
