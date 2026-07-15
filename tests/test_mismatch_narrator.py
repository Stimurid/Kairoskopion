"""Tests for MismatchNarratorAgent."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock


def _input(mismatches=None, article=None, venue=None):
    from kairoskopion.agents.contract import AgentInput
    return AgentInput(
        operation_id="t",
        agent_role_id="mismatch_narrator",
        entities={
            "article": article or {
                "title_current": "Test Article",
                "problem_statement": "How does AI mediate learning?",
                "core_claims": ["LLMs amplify literacy gaps"],
                "method_status": "conceptual_method",
                "genre_current": "theoretical_essay",
            },
            "venue": venue or {
                "canonical_name": "JQER",
                "scope_summary": "Quantitative empirical research only",
                "article_types_supported": ["Empirical Research Article"],
            },
            "mismatches": mismatches if mismatches is not None else [
                {
                    "mismatch_id": "mm_0", "axis": "method",
                    "article_side": "Article is conceptual only",
                    "venue_side": "",
                    "severity": "blocking",
                    "evidence_refs": [], "possible_actions": [],
                },
                {
                    "mismatch_id": "mm_1", "axis": "genre",
                    "article_side": "Article is a theoretical essay",
                    "venue_side": "",
                    "severity": "major",
                    "evidence_refs": [], "possible_actions": [],
                },
            ],
        },
    )


class TestDeterministicFallback(unittest.TestCase):
    """No LLM → honest empty narratives with needs_llm marker."""

    def test_no_mismatches_returns_empty(self):
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        out = agent.execute_deterministic(_input(mismatches=[]))
        self.assertEqual(out.output_entity["narratives"], [])
        self.assertEqual(out.confidence, "low")

    def test_fallback_mirrors_axes(self):
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        out = agent.execute_deterministic(_input())
        narratives = out.output_entity["narratives"]
        self.assertEqual(len(narratives), 2)
        for n in narratives:
            self.assertEqual(n["venue_side"], "")
            self.assertEqual(n["possible_actions"], [])
            self.assertEqual(n["narrative_status"], "needs_llm")
        # Anti-leak: no Traceback strings, and raw_output_ref (which is
        # a metadata KEY) must be null — not carrying any provider output.
        flat = json.dumps(out.output_entity, ensure_ascii=False)
        self.assertNotIn("Traceback", flat)
        ea = out.output_entity["extraction_attempt"]
        self.assertIn(ea.get("raw_output_ref"), (None, ""))


class TestLLMPath(unittest.TestCase):
    def _mock_provider(self, payload: dict):
        provider = MagicMock()
        response = MagicMock()
        response.parsed = payload
        response.content = ""
        response.model = "claude-sonnet-4-5"
        response.latency_ms = 800.0
        provider.complete.return_value = response
        return provider

    def test_llm_filled_narratives(self):
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        provider = self._mock_provider({
            "narratives": [
                {
                    "axis": "method",
                    "venue_side": "Venue accepts only empirical work.",
                    "description": "Article is conceptual; venue rejects.",
                    "possible_actions": [
                        "Add a small empirical case study to ground claim 2.",
                        "Reframe as commentary on existing data.",
                    ],
                },
                {
                    "axis": "genre",
                    "venue_side": "Venue's typical article is IMRAD empirical.",
                    "description": "Theoretical essays out of scope.",
                    "possible_actions": ["Consider a sister theoretical venue."],
                },
            ],
        })
        out = agent.execute(_input(), provider)
        narratives = out.output_entity["narratives"]
        self.assertEqual(len(narratives), 2)
        self.assertEqual(narratives[0]["narrative_status"], "llm_filled")
        self.assertIn("Venue accepts only empirical", narratives[0]["venue_side"])
        self.assertEqual(len(narratives[0]["possible_actions"]), 2)

    def test_llm_partial_response_axis_missing_marked(self):
        """LLM forgot to cover one axis — agent marks it explicitly."""
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        provider = self._mock_provider({
            "narratives": [
                {
                    "axis": "method",
                    "venue_side": "Empirical only.",
                    "description": "Conceptual mismatch.",
                    "possible_actions": ["Add data."],
                },
                # No 'genre' axis
            ],
        })
        out = agent.execute(_input(), provider)
        narratives = out.output_entity["narratives"]
        self.assertEqual(len(narratives), 2)
        # Method covered
        self.assertEqual(narratives[0]["narrative_status"], "llm_filled")
        # Genre missing — explicitly marked
        self.assertEqual(narratives[1]["narrative_status"], "missing_from_llm_output")
        self.assertEqual(narratives[1]["venue_side"], "")

    def test_llm_exception_falls_back_honestly(self):
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        provider = MagicMock()
        provider.complete.side_effect = RuntimeError("boom")
        out = agent.execute(_input(), provider)
        narratives = out.output_entity["narratives"]
        self.assertEqual(len(narratives), 2)
        for n in narratives:
            self.assertEqual(n["narrative_status"], "needs_llm")
        # Provider-error attempt metadata preserved
        ea = out.output_entity["extraction_attempt"]
        self.assertEqual(ea["fallback_reason"], "provider_error")

    def test_anti_leak_in_llm_output(self):
        """Even if model writes weird strings, raw_output_ref / Traceback
        must not appear in agent output entity."""
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        agent = MismatchNarratorAgent()
        provider = self._mock_provider({
            "narratives": [
                {
                    "axis": "method", "venue_side": "Empirical.",
                    "description": "OK.", "possible_actions": ["Do X"],
                },
                {
                    "axis": "genre", "venue_side": "IMRAD.",
                    "description": "OK.", "possible_actions": ["Do Y"],
                },
            ],
        })
        out = agent.execute(_input(), provider)
        flat = json.dumps(out.output_entity, ensure_ascii=False)
        self.assertNotIn("Traceback", flat)
        # raw_output_ref key should NOT appear non-null
        ea = out.output_entity["extraction_attempt"]
        self.assertIn(ea.get("raw_output_ref"), (None, ""))


class TestEnrichMismatchMapInPlace(unittest.TestCase):
    def _make_map(self):
        from kairoskopion.schema import MismatchMap
        return MismatchMap(
            mismatch_map_id="mm",
            fit_assessment_id="fa",
            mismatches=[
                {"mismatch_id": "0", "axis": "method", "article_side": "x",
                 "venue_side": "", "description": "",
                 "possible_actions": []},
                {"mismatch_id": "1", "axis": "genre", "article_side": "y",
                 "venue_side": "", "description": "",
                 "possible_actions": []},
            ],
            summary="2 mismatches",
            critical_mismatches=[],
            unknowns=[],
        )

    def test_enriches_only_llm_filled(self):
        from kairoskopion.agents.mismatch_narrator import (
            enrich_mismatch_map_in_place,
        )
        mm = self._make_map()
        narratives = [
            {"axis": "method", "venue_side": "Empirical.",
             "description": "Conceptual mismatch.",
             "possible_actions": ["Add data"],
             "narrative_status": "llm_filled"},
            {"axis": "genre", "venue_side": "",
             "description": "", "possible_actions": [],
             "narrative_status": "needs_llm"},  # NOT llm_filled — skip
        ]
        n = enrich_mismatch_map_in_place(mm, narratives)
        self.assertEqual(n, 1)
        self.assertEqual(mm.mismatches[0]["venue_side"], "Empirical.")
        # Genre untouched — empty venue_side stays
        self.assertEqual(mm.mismatches[1]["venue_side"], "")

    def test_handles_none_safely(self):
        from kairoskopion.agents.mismatch_narrator import (
            enrich_mismatch_map_in_place,
        )
        self.assertEqual(enrich_mismatch_map_in_place(None, []), 0)


class TestPerRoleRoutingSeam(unittest.TestCase):
    """mismatch_narrator role is exposed in /health routing map."""

    def setUp(self):
        self._snap = {k: v for k, v in os.environ.items()
                       if k.startswith("KAIROSKOPION_LLM")}

    def tearDown(self):
        for k in list(os.environ):
            if k.startswith("KAIROSKOPION_LLM"):
                del os.environ[k]
        for k, v in self._snap.items():
            os.environ[k] = v

    def test_mismatch_narrator_in_routed_roles(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "sonnet"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        from kairoskopion.llm.config import provider_status
        st = provider_status()
        self.assertIn("mismatch_narrator", st["model_per_role"])
        self.assertEqual(st["model_per_role"]["mismatch_narrator"], "sonnet")

    def test_override_respected_for_mismatch_narrator(self):
        os.environ["KAIROSKOPION_LLM_MODEL"] = "sonnet"
        os.environ["KAIROSKOPION_LLM_API_KEY"] = "k"
        os.environ["KAIROSKOPION_LLM_MODEL_MISMATCH_NARRATOR"] = "haiku"
        from kairoskopion.llm.config import LLMConfig
        cfg = LLMConfig.for_role("mismatch_narrator")
        self.assertEqual(cfg.model, "haiku")


class TestFitChainWiring(unittest.TestCase):
    """When LLM unavailable, fit chain still produces a mismatch map
    where the narrator was attempted (deterministic path) and the
    mismatch venue_side stays honestly empty."""

    def setUp(self):
        self._tmpdir = tempfile.mkdtemp(prefix="kairon_narr_chain_")
        os.environ["KAIROSKOPION_DATA_DIR"] = self._tmpdir
        os.environ["KAIROSKOPION_LLM_PROVIDER"] = "none"
        from kairoskopion.api import auth as auth_mod
        auth_mod.reset_stores_for_tests(self._tmpdir)
        from kairoskopion.api import app as app_mod
        importlib.reload(app_mod)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        os.environ.pop("KAIROSKOPION_DATA_DIR", None)
        os.environ.pop("KAIROSKOPION_LLM_PROVIDER", None)

    def test_fit_chain_runs_narrator_deterministic(self):
        """Fit chain with manually-set venue (bypassing LLM-only
        investigate_venue) still runs narrator deterministically."""
        from kairoskopion.api.cases import Case
        from kairoskopion.schema import VenueModel
        case = Case(title="t")
        case.intake_text("Article body. " * 60, input_type="article")
        # ARCH-SEM-001: investigate_venue requires LLM, so set venue directly
        case.investigated_venue = VenueModel(canonical_name="Test Venue")
        case.select_venue("investigated")
        self.assertIsNotNone(case.mismatch_map)
        for m in case.mismatch_map.mismatches:
            vs = m.get("venue_side", "") if isinstance(m, dict) else getattr(m, "venue_side", "")
            self.assertEqual(vs, "")


if __name__ == "__main__":
    unittest.main()
