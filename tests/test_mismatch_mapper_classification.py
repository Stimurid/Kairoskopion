"""V2-B: classification tests for orphan ``MismatchMapperAgent``.

These tests do NOT wire the mapper into the chain. They lock in the
evidence behind the V2-B decision to leave it unwired
(see docs/operations/MISMATCH_MAPPER_CLASSIFICATION_V2B.md):

1. The deterministic source-of-truth (``build_mismatch_map``) still
   emits honest-empty ``venue_side`` per mismatch and never injects a
   placeholder "Venue expectation on X" string. Active chain depends
   on this.
2. The deterministic path of ``MismatchMapperAgent`` is a literal
   delegate to ``build_mismatch_map`` — same output, no novel claims.
3. The mapper's *LLM* output schema (``MismatchMappingResult``) is
   structurally incompatible with the ``MismatchMap`` shape consumed
   by snapshot persistence, narrator, DossierView and the WhiteCrow
   bridge — so the agent cannot be drop-in chained without a
   translator.
4. No deterministic mapper output contains generic ``possible_actions``
   beyond the small per-axis hint dictionary in
   ``services/mismatch_mapping.py:_suggest_actions``, and no entry
   fabricates citation/reference actions outside that dictionary.
"""

from __future__ import annotations

import unittest


def _make_fit_with_axes(axis_values: dict[str, str]):
    """Build a minimal FitAssessment dict whose ``from_dict`` succeeds."""
    from kairoskopion.schema import FitAssessment
    axes = [
        {
            "axis": axis,
            "value": value,
            "evidence_refs": [],
            "confidence": "low",
            "notes": "",
            "unknowns": [],
        }
        for axis, value in axis_values.items()
    ]
    fit_dict = {
        "fit_assessment_id": "fa_test",
        "article_model_id": "am_test",
        "venue_model_id": "vm_test",
        "submission_scenario_id": None,
        "overall_label": "possible",
        "assessment_level": "preliminary",
        "axes": axes,
        "confidence": "low",
        "mismatch_map_id": "",
        "recommendation": "",
        "unknowns": [],
        "evidence_refs": [],
    }
    return FitAssessment.from_dict(fit_dict)


class TestDeterministicSourceHonest(unittest.TestCase):
    """Active chain depends on ``build_mismatch_map`` emitting empty
    venue_side. Lock that in."""

    def test_venue_side_empty_for_every_mismatch(self):
        from kairoskopion.services.mismatch_mapping import build_mismatch_map
        fit = _make_fit_with_axes(
            {"topic": "bad", "method": "weak", "discipline": "unknown"}
        )
        mm = build_mismatch_map(fit)
        self.assertGreater(len(mm.mismatches), 0)
        for m in mm.mismatches:
            self.assertEqual(
                m["venue_side"], "",
                "deterministic mapper must not fabricate venue_side — "
                "narrator owns that field",
            )

    def test_no_placeholder_venue_expectation_text(self):
        """Regression guard: previously hardcoded 'Venue expectation on X'."""
        from kairoskopion.services.mismatch_mapping import build_mismatch_map
        fit = _make_fit_with_axes({"topic": "bad", "genre": "weak"})
        mm = build_mismatch_map(fit)
        flat = " ".join(
            (m.get("venue_side", "") + " " + m.get("description", ""))
            for m in mm.mismatches
        ).lower()
        self.assertNotIn("venue expectation on", flat)

    def test_unknown_axes_marked_in_unknowns_not_as_semantic_claim(self):
        from kairoskopion.services.mismatch_mapping import build_mismatch_map
        fit = _make_fit_with_axes({"discipline": "unknown"})
        mm = build_mismatch_map(fit)
        self.assertTrue(
            any("not assessed" in u or "venue-side" in u for u in mm.unknowns),
            "unknown axis must surface as honest 'not assessed' note",
        )

    def test_possible_actions_from_known_dict_only(self):
        """No generic ad-hoc actions for unseen axes beyond the small
        dictionary in _suggest_actions."""
        from kairoskopion.services.mismatch_mapping import build_mismatch_map
        fit = _make_fit_with_axes(
            {"some_unknown_axis_name": "bad"}
        )
        mm = build_mismatch_map(fit)
        actions = mm.mismatches[0]["possible_actions"]
        # Fallback: "Address {axis} mismatch" — single deterministic
        # action keyed on axis name, NOT a generic citation/reference
        # fabrication. Guard against future drift.
        for a in actions:
            low = a.lower()
            self.assertNotIn("doi", low)
            self.assertNotIn("cite", low)
            self.assertNotIn("reference", low)


class TestMapperDeterministicIsNoop(unittest.TestCase):
    """``MismatchMapperAgent.execute_deterministic`` adds no novel
    claims beyond ``build_mismatch_map``. Wiring it would be an
    indirection with zero behaviour delta — and that's exactly why
    V2-B does not wire it."""

    def test_mapper_deterministic_matches_service_output(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.fit.mismatch_mapper import MismatchMapperAgent
        from kairoskopion.services.mismatch_mapping import build_mismatch_map

        fit = _make_fit_with_axes(
            {"topic": "bad", "method": "weak", "discipline": "unknown"}
        )
        agent = MismatchMapperAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="op_test",
            agent_role_id="mismatch_mapper",
            entities={"fit_assessment": fit.to_dict()},
        ))
        service_mm = build_mismatch_map(fit)

        agent_mismatches = out.output_entity["mismatches"]
        service_mismatches = service_mm.to_dict()["mismatches"]
        # Counts identical, venue_side stays empty in both paths, axes match.
        self.assertEqual(len(agent_mismatches), len(service_mismatches))
        for a, s in zip(agent_mismatches, service_mismatches):
            self.assertEqual(a["axis"], s["axis"])
            self.assertEqual(a["venue_side"], "")
            self.assertEqual(s["venue_side"], "")


class TestMapperLLMSchemaIncompatibility(unittest.TestCase):
    """The mapper's LLM output schema differs from the MismatchMap
    shape the rest of the chain consumes. Proves that wiring it as-is
    would require a translation layer that drops fields like
    ``adaptation_cost`` and that doesn't surface ``possible_actions``
    or ``evidence_refs``."""

    def test_llm_schema_misses_chain_fields(self):
        from kairoskopion.agents.prompt_families.mismatch_mapping import (
            MISMATCH_MAPPING_FAMILY,
        )
        schema = MISMATCH_MAPPING_FAMILY["output_schema"]
        item_props = schema["properties"]["mismatches"]["items"]["properties"]
        # Mapper emits these — the chain doesn't carry them anywhere.
        self.assertIn("venue_expectation", item_props)
        self.assertIn("adaptation_cost", item_props)
        self.assertIn("adaptation_path", item_props)
        # Chain consumes these — mapper schema lacks them.
        self.assertNotIn("possible_actions", item_props)
        self.assertNotIn("evidence_refs", item_props)
        self.assertNotIn("article_side", item_props)
        self.assertNotIn("venue_side", item_props)
        self.assertNotIn("requires_user_acceptance", item_props)


class TestNarratorRemainsFinalSemanticSource(unittest.TestCase):
    """When LLM is unavailable, the chain must NOT pretend the
    venue_side was inferred — it must stay empty so the UI hint
    'требуется LLM-комментарий по площадке' renders honestly."""

    def test_narrator_fallback_leaves_venue_side_empty(self):
        from kairoskopion.agents.contract import AgentInput
        from kairoskopion.agents.mismatch_narrator import MismatchNarratorAgent
        mismatches = [
            {"axis": "topic", "severity": "blocking", "article_side": "X"},
            {"axis": "method", "severity": "major", "article_side": "Y"},
        ]
        out = MismatchNarratorAgent().execute_deterministic(
            AgentInput(
                operation_id="op_test",
                agent_role_id="mismatch_narrator",
                entities={
                    "article": {}, "venue": {}, "mismatches": mismatches,
                },
            )
        )
        narratives = out.output_entity["narratives"]
        self.assertEqual(len(narratives), 2)
        for n in narratives:
            self.assertEqual(n["venue_side"], "")
            self.assertEqual(n["description"], "")
            self.assertEqual(n["possible_actions"], [])
            self.assertEqual(n["narrative_status"], "needs_llm")


if __name__ == "__main__":
    unittest.main()
