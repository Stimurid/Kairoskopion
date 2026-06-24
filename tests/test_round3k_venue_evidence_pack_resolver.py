"""Round III-K Track 4 — venue evidence pack resolver tests."""

from __future__ import annotations

import textwrap
import unittest
from pathlib import Path

from kairoskopion.services.venue_evidence_pack_resolver import (
    ResolvedPack,
    _extract_issn,
    _extract_name,
    resolve,
    resolve_by_issn,
    resolve_by_name,
    scan_evidence_packs,
)


class TestExtractISSN(unittest.TestCase):

    def test_extracts_issn(self):
        text = "- **ISSN:** 0042-8744 (print)"
        self.assertEqual(_extract_issn(text), "0042-8744")

    def test_extracts_issn_with_x(self):
        text = "- **ISSN:** 1811-833X"
        self.assertEqual(_extract_issn(text), "1811-833X")

    def test_no_issn(self):
        text = "No ISSN here"
        self.assertIsNone(_extract_issn(text))


class TestExtractName(unittest.TestCase):

    def test_extracts_name_with_slash(self):
        text = "# Venue Evidence Pack: Логос / Logos\n\n## Identity"
        self.assertEqual(_extract_name(text), "Логос")

    def test_extracts_name_without_slash(self):
        text = "# Venue Evidence Pack: Some Journal\n\n## Identity"
        self.assertEqual(_extract_name(text), "Some Journal")

    def test_no_header(self):
        text = "## Not a venue evidence pack"
        self.assertIsNone(_extract_name(text))


class TestScanAndResolve(unittest.TestCase):

    def _make_pack_dir(self, tmp: Path) -> Path:
        d = tmp / "data" / "venue_evidence_packs"
        d.mkdir(parents=True)
        (d / "test_evidence_pack.md").write_text(textwrap.dedent("""\
            # Venue Evidence Pack: Тестовый журнал / Test Journal

            ## Journal Identity

            - **ISSN:** 9999-0001 (print)
            - **Publisher:** Test Publisher
        """), encoding="utf-8")
        (d / "other_evidence_pack.md").write_text(textwrap.dedent("""\
            # Venue Evidence Pack: Другой журнал

            ## Journal Identity

            - **ISSN:** 9999-0002 (print)
        """), encoding="utf-8")
        (d / "not_a_pack.md").write_text("Random file", encoding="utf-8")
        return tmp

    def test_scan_finds_packs(self, tmp_path=None):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            packs = scan_evidence_packs(root)
            self.assertEqual(len(packs), 2)
            issns = {p.issn for p in packs}
            self.assertIn("9999-0001", issns)
            self.assertIn("9999-0002", issns)

    def test_resolve_by_issn(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve_by_issn("9999-0001", root)
            self.assertIsNotNone(pack)
            self.assertEqual(pack.issn, "9999-0001")
            self.assertEqual(pack.canonical_name, "Тестовый журнал")

    def test_resolve_by_issn_not_found(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve_by_issn("0000-0000", root)
            self.assertIsNone(pack)

    def test_resolve_by_name(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve_by_name("Другой журнал", root)
            self.assertIsNotNone(pack)
            self.assertEqual(pack.issn, "9999-0002")

    def test_resolve_by_name_case_insensitive(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve_by_name("другой журнал", root)
            self.assertIsNotNone(pack)

    def test_resolve_combined(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve(issn="9999-0001", project_root=root)
            self.assertIsNotNone(pack)
            pack2 = resolve(name="Другой журнал", project_root=root)
            self.assertIsNotNone(pack2)
            self.assertNotEqual(pack.issn, pack2.issn)

    def test_resolve_issn_takes_priority(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve(issn="9999-0001", name="Другой журнал", project_root=root)
            self.assertEqual(pack.issn, "9999-0001")

    def test_resolve_falls_back_to_name(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            root = self._make_pack_dir(Path(td))
            pack = resolve(issn="0000-0000", name="Другой журнал", project_root=root)
            self.assertIsNotNone(pack)
            self.assertEqual(pack.issn, "9999-0002")


class TestResolveFromRealPacks(unittest.TestCase):
    """Integration: resolve from actual evidence packs in the repo."""

    def test_logos_resolvable(self):
        pack = resolve(issn="0869-5377")
        self.assertIsNotNone(pack, "Logos evidence pack must resolve from data/venue_evidence_packs/")
        self.assertIn("Логос", pack.canonical_name or "")
        self.assertNotIn("private_inputs", str(pack.path))

    def test_voprosy_filosofii_resolvable(self):
        pack = resolve(issn="0042-8744")
        if pack is None:
            self.skipTest("Вопросы философии evidence pack not in expected location")
        self.assertIn("Вопросы философии", pack.canonical_name or "")

    def test_filosofskiy_zhurnal_resolvable(self):
        pack = resolve(issn="2072-0726")
        if pack is None:
            self.skipTest("Философский журнал evidence pack not in expected location")
        self.assertIn("Философский журнал", pack.canonical_name or "")

    def test_tsifrovoy_ucheny_resolvable(self):
        pack = resolve(issn="2618-9267")
        if pack is None:
            self.skipTest("Цифровой ученый evidence pack not in expected location")
        self.assertIn("Цифровой ученый", pack.canonical_name or "")


class TestCaseOrchestratorByReference(unittest.TestCase):
    """Test the case orchestrator method."""

    def test_investigate_by_reference_not_found(self):
        from kairoskopion.api.cases import Case
        case = Case(case_id="test", user_id="test")
        result = case.investigate_venue_by_reference(issn="0000-0000")
        self.assertEqual(result["status"], "evidence_pack_not_found")

    def test_investigate_by_issn_logos(self):
        from kairoskopion.api.cases import Case
        case = Case(case_id="test", user_id="test")
        result = case.investigate_venue_by_reference(issn="0869-5377")
        if result.get("status") == "evidence_pack_not_found":
            self.skipTest("Logos evidence pack not found")
        self.assertIn("venue", result)


if __name__ == "__main__":
    unittest.main()
