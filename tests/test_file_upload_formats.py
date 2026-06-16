"""File upload format coverage — .doc, .rtf, .json + clear errors."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from kairoskopion.api.source_intake_util import extract_text_from_file


class TestFileFormats(unittest.TestCase):
    def _write(self, suffix: str, content: bytes | str) -> Path:
        fd = tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix, mode="wb",
        )
        try:
            fd.write(content if isinstance(content, bytes) else content.encode("utf-8"))
            fd.close()
            return Path(fd.name)
        finally:
            pass

    def test_doc_gives_clear_russian_message(self):
        p = self._write(".doc", b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1binary doc header")
        text, status, errors = extract_text_from_file(p)
        self.assertEqual(text, "")
        self.assertEqual(status, "unsupported")
        # Message must say "сохраните как .docx" in plain Russian
        joined = " ".join(errors)
        self.assertIn(".docx", joined)
        self.assertTrue(
            ".doc" in joined and ("docx" in joined.lower()),
            "Error must explicitly recommend .docx conversion",
        )
        # No raw binary dump / no Traceback
        for e in errors:
            self.assertNotIn("Traceback", e)

    def test_rtf_strips_to_plaintext(self):
        # Minimal RTF: control words + groups + a simple ASCII payload
        body = (
            r"{\rtf1\ansi\ansicpg1252\deff0\nouicompat\deflang1033"
            r"{\fonttbl{\f0\fnil\fcharset0 Calibri;}}\n"
            r"{\*\generator Test;}\n"
            r"\viewkind4\uc1\pard\f0\fs22\lang9 Hello academic source list 1. Foucault.\par\n}"
        )
        p = self._write(".rtf", body)
        text, status, errors = extract_text_from_file(p)
        self.assertEqual(status, "extracted")
        self.assertIn("Hello academic source list", text)
        self.assertIn("Foucault", text)
        # No braces or control words leaking through
        self.assertNotIn("{", text)
        self.assertNotIn(r"\f0", text)

    def test_json_passes_through_as_text(self):
        p = self._write(".json", '{"a": 1, "claims": ["x"]}')
        text, status, errors = extract_text_from_file(p)
        self.assertEqual(status, "extracted")
        self.assertIn("claims", text)

    def test_md_still_works(self):
        p = self._write(".md", "# Title\n\nBody")
        text, status, errors = extract_text_from_file(p)
        self.assertEqual(status, "extracted")
        self.assertIn("Title", text)


if __name__ == "__main__":
    unittest.main()
