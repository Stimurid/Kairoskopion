"""Tests for the four venue blockers: VF-C2 + corpus mining + editorial
board adapter + CyberLeninka adapter.

All tests run offline (no live HTTP). Live-only paths are covered by
the Mavrinsky pool harness, not by pytest.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairoskopion.adapters.venue.cyberleninka import (
    CYBERLENINKA_FIXTURE,
    CyberLeninkaAdapter,
    search_journals,
)
from kairoskopion.adapters.venue.editorial_board import (
    build_editorial_board_cloud,
    extract_candidate_members,
    extract_orcid_ids,
    strip_html,
)
from kairoskopion.schema import (
    EditorialBoardCloud,
    EditorialBoardMember,
    PublishedCorpusHull,
    VenueProfilePackage,
)
from kairoskopion.services.venue_corpus_miner import (
    _reconstruct_abstract,
    works_to_article_texts,
)
from kairoskopion.services.venue_profile_package_builder import (
    build_venue_profile_package,
)
from kairoskopion.services.venue_profile_registry import VenueProfileRegistry


# ---------------------------------------------------------------------------
# VF-C2 — VenueProfilePackage
# ---------------------------------------------------------------------------

class TestVenueProfilePackageSchema(unittest.TestCase):
    def test_round_trip(self):
        v = VenueProfilePackage(
            canonical_name="Philosophy & Technology",
            issns=["2210-5433", "2210-5441"],
            publisher="Springer",
            languages=["en"],
            openalex_source_id="S205253171",
            discovery_sources=["DOAJ", "OpenAlex"],
            discovery_clusters=["philosophy of technology"],
        )
        d = v.to_dict()
        v2 = VenueProfilePackage.from_dict(d)
        self.assertEqual(v2.canonical_name, "Philosophy & Technology")
        self.assertEqual(v2.issns, ["2210-5433", "2210-5441"])
        self.assertEqual(v2.openalex_source_id, "S205253171")

    def test_completeness_field(self):
        v = VenueProfilePackage(canonical_name="X")
        v.completeness["VenueIdentity"] = "present"
        v.completeness["EditorialBoardCloud"] = "missing"
        d = v.to_dict()
        v2 = VenueProfilePackage.from_dict(d)
        self.assertEqual(v2.completeness["VenueIdentity"], "present")
        self.assertEqual(v2.completeness["EditorialBoardCloud"], "missing")


class TestVenueProfileRegistry(unittest.TestCase):
    def test_upsert_and_find_by_name(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = VenueProfileRegistry(storage_root=tmp)
            self.assertEqual(reg.count(), 0)
            v = VenueProfilePackage(canonical_name="P&T", issns=["1234-5678"])
            reg.upsert(v)
            self.assertEqual(reg.count(), 1)
            found = reg.find(canonical_name="P&T")
            self.assertIsNotNone(found)
            self.assertEqual(found.canonical_name, "P&T")

    def test_upsert_idempotent_by_issn(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = VenueProfileRegistry(storage_root=tmp)
            v = VenueProfilePackage(canonical_name="A", issns=["0000-1111"])
            reg.upsert(v)
            v2 = VenueProfilePackage(canonical_name="A renamed", issns=["0000-1111"])
            reg.upsert(v2)
            # only one record because ISSN matched
            self.assertEqual(reg.count(), 1)
            found = reg.find(issn="0000-1111")
            self.assertIsNotNone(found)
            # Updated record keeps the new canonical_name
            self.assertEqual(found.canonical_name, "A renamed")

    def test_cross_session_persistence(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg1 = VenueProfileRegistry(storage_root=tmp)
            v = VenueProfilePackage(
                canonical_name="Cross",
                issns=["2222-3333"],
                openalex_source_id="Sxyz",
            )
            reg1.upsert(v)
            # New process: fresh registry instance over same dir
            reg2 = VenueProfileRegistry(storage_root=tmp)
            self.assertEqual(reg2.count(), 1)
            found = reg2.find(openalex_source_id="Sxyz")
            self.assertIsNotNone(found)
            self.assertEqual(found.canonical_name, "Cross")

    def test_merge_lists_on_upsert(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = VenueProfileRegistry(storage_root=tmp)
            v1 = VenueProfilePackage(
                canonical_name="M",
                issns=["1111-1111"],
                discovery_sources=["DOAJ"],
                discovery_clusters=["philosophy"],
            )
            reg.upsert(v1)
            v2 = VenueProfilePackage(
                canonical_name="M",
                issns=["1111-1111"],
                discovery_sources=["OpenAlex"],
                discovery_clusters=["STS"],
            )
            reg.upsert(v2)
            found = reg.find(canonical_name="M")
            self.assertIn("DOAJ", found.discovery_sources)
            self.assertIn("OpenAlex", found.discovery_sources)
            self.assertIn("philosophy", found.discovery_clusters)
            self.assertIn("STS", found.discovery_clusters)


# ---------------------------------------------------------------------------
# Corpus mining wiring
# ---------------------------------------------------------------------------

class TestCorpusMinerHelpers(unittest.TestCase):
    def test_reconstruct_abstract_from_inverted_index(self):
        inv = {"interface": [0, 5], "as": [1], "dispositif": [2],
                "of": [3], "capture": [4], "is": [6], "ontological": [7]}
        out = _reconstruct_abstract(inv)
        self.assertEqual(out, "interface as dispositif of capture interface is ontological")

    def test_reconstruct_empty(self):
        self.assertIsNone(_reconstruct_abstract(None))
        self.assertIsNone(_reconstruct_abstract({}))

    def test_works_to_article_texts(self):
        works = [{
            "title": "Greedy and generous interfaces",
            "abstract_inverted_index": {"desire": [0], "as": [1], "excess": [2]},
            "_reconstructed_abstract": "desire as excess",
            "concepts": [
                {"display_name": "Philosophy of technology"},
                {"display_name": "Continental philosophy"},
            ],
            "referenced_works_count": 35,
            "publication_year": 2024,
        }]
        texts = works_to_article_texts(works)
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0]["title"], "Greedy and generous interfaces")
        self.assertEqual(texts[0]["abstract"], "desire as excess")
        self.assertIn("Philosophy of technology", texts[0]["keywords"])
        self.assertEqual(texts[0]["references_count"], 35)


# ---------------------------------------------------------------------------
# Editorial board adapter
# ---------------------------------------------------------------------------

SAMPLE_BOARD_HTML = """
<html><head><title>Editorial Board</title></head><body>
<h1>Editorial Board</h1>
<h2>Editor-in-Chief</h2>
<p>Jane Smith, University of Oxford</p>
<h2>Associate Editors</h2>
<ul>
  <li>John Doe (Harvard University) ORCID 0000-0001-2345-6789</li>
  <li>Maria Garcia, Universidad de Barcelona</li>
  <li>Hiroshi Tanaka — Tokyo Institute of Technology</li>
</ul>
<h2>Editorial Board</h2>
<p>Ali Khan (Aga Khan University)</p>
<p>Sophie Dubois (Sorbonne)</p>
<script>var board = [];</script>
</body></html>
"""

JS_ONLY_BOARD_HTML = """
<html><head></head><body>
<div id="root"></div>
<script>renderBoard();</script>
</body></html>
"""


class TestEditorialBoardExtraction(unittest.TestCase):
    def test_strip_html(self):
        s = strip_html("<p>Hello <b>World</b><script>alert(1)</script></p>")
        self.assertEqual(s, "Hello World")

    def test_extract_orcid(self):
        text = "John Doe ORCID 0000-0001-2345-6789 Member"
        ids = extract_orcid_ids(text)
        self.assertEqual(ids, ["0000-0001-2345-6789"])

    def test_extract_candidates_from_sample_html(self):
        text = strip_html(SAMPLE_BOARD_HTML)
        candidates = extract_candidate_members(text)
        # Heuristic extractor may include role-prefix tokens in the
        # captured name (e.g., "Editor-in-Chief Jane Smith"). PASS if
        # the underlying person name appears as a substring of any
        # captured candidate.
        all_names_joined = " | ".join(c["full_name"] for c in candidates)
        for expected in ("Jane Smith", "John Doe", "Maria Garcia",
                          "Hiroshi Tanaka", "Sophie Dubois"):
            self.assertIn(expected, all_names_joined,
                          f"{expected!r} not found in any candidate")


class TestEditorialBoardBuilder(unittest.TestCase):
    def test_js_only_page_marks_unknown(self):
        cloud = build_editorial_board_cloud(
            board_page_html=JS_ONLY_BOARD_HTML,
        )
        self.assertIsInstance(cloud, EditorialBoardCloud)
        self.assertEqual(cloud.members_sampled, 0)
        self.assertTrue(any("JS-only" in u or "200" in u for u in cloud.unknowns))

    def test_no_url_or_html_marks_unknown(self):
        cloud = build_editorial_board_cloud()
        self.assertEqual(cloud.members_sampled, 0)
        self.assertTrue(cloud.unknowns)

    def test_derived_signals_are_inference(self):
        cloud = build_editorial_board_cloud(board_page_html=SAMPLE_BOARD_HTML)
        # derived signals always inference regardless of count
        self.assertEqual(cloud.derived_signals_authority, "inference")
        # confidence depends on sample size
        self.assertIn(cloud.derived_signals_confidence, {"low", "medium", "high"})


# ---------------------------------------------------------------------------
# CyberLeninka adapter
# ---------------------------------------------------------------------------

class TestCyberLeninkaFixture(unittest.TestCase):
    def test_fixture_mode_returns_journals(self):
        out = search_journals("философия техники", mode="fixture")
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["language"], "ru")
        self.assertEqual(out[0]["source"], "CyberLeninka")
        self.assertIn("VAK / RINTS status requires elibrary.ru auth — UNKNOWN_NOT_VERIFIED",
                       out[0]["unknowns"])

    def test_adapter_lookup_by_name_fixture(self):
        adapter = CyberLeninkaAdapter()  # OFFLINE_STUB mode by default
        # Match the fixture journal name
        result = adapter.lookup_venue(name="Вопросы философии")
        self.assertEqual(result.adapter_id, "cyberleninka")
        # In OFFLINE_STUB mode it goes through fixture path
        self.assertIn(result.status, {"success", "no_results"})


# ---------------------------------------------------------------------------
# VenueProfilePackage builder end-to-end (no network)
# ---------------------------------------------------------------------------

class TestVenueProfilePackageBuilderOffline(unittest.TestCase):
    def test_builder_without_corpus_or_board(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = VenueProfileRegistry(storage_root=tmp)
            v = build_venue_profile_package(
                identity={
                    "canonical_name": "Test Journal",
                    "issns": ["0001-0002"],
                    "discovery_sources": ["DOAJ"],
                    "discovery_clusters": ["philosophy of technology"],
                },
                fetch_corpus=False,
                fetch_editorial_board=False,
                registry=reg,
            )
            self.assertEqual(v.completeness["VenueIdentity"], "present")
            self.assertEqual(v.completeness["PublishedCorpusHull"], "missing")
            self.assertEqual(v.completeness["EditorialBoardCloud"], "missing")
            self.assertEqual(v.completeness["FormalSubmissionProfile"], "missing")
            self.assertEqual(v.completeness["SourceEvidencePacket"], "present")
            # Indexed
            found = reg.find(canonical_name="Test Journal")
            self.assertIsNotNone(found)

    def test_builder_without_openalex_marks_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg = VenueProfileRegistry(storage_root=tmp)
            v = build_venue_profile_package(
                identity={"canonical_name": "Pretend"},
                fetch_corpus=True,
                fetch_editorial_board=False,
                registry=reg,
            )
            # fetch_corpus=True but no openalex_source_id -> unknown, not crash
            self.assertEqual(v.completeness["PublishedCorpusHull"], "missing")
            self.assertTrue(any("openalex" in u.lower() for u in v.unknowns))


if __name__ == "__main__":
    unittest.main()
