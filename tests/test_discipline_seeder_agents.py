"""Tests for DisciplineSourceAcquisitionAgent + DisciplineSeederAgent
(Phase B integration commit 1).

LLM paths are exercised only indirectly via fallback paths — we don't
mock a live provider here. The point is to verify:
- Fallbacks emit honest stub packets / minimal cards (NOT fabricated
  ВАК codes, NOT pretend-LLM output).
- Provenance survives end-to-end: acquisition packets → seeder
  evidence_refs.
- Agents are wired into the registry and instantiable.
"""

from __future__ import annotations

import unittest

from kairoskopion.agents.contract import AgentInput
from kairoskopion.agents.discipline_seeder import DisciplineSeederAgent
from kairoskopion.agents.discipline_source_acquisition import (
    DisciplineSourceAcquisitionAgent,
)
from kairoskopion.agents.registry import (
    AGENT_SPEC_REGISTRY,
    get_agent_class,
    instantiate_agent,
)
from kairoskopion.services.discipline_registry import (
    DisciplineSourcePacket,
)


class TestSourceAcquisitionDeterministicFallback(unittest.TestCase):
    def test_returns_curator_stub_packet_no_fabricated_codes(self):
        agent = DisciplineSourceAcquisitionAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t",
            agent_role_id="discipline_source_acquisition",
            entities={
                "discipline_name": "Философия техники",
                "region": "ru",
            },
        ))
        self.assertIsNotNone(out.output_entity)
        packets = out.output_entity["packets"]
        self.assertEqual(len(packets), 1)
        p = packets[0]
        # NO invented ВАК code
        self.assertEqual(p["source_type"], "other")
        self.assertTrue(p["source_id"].startswith("manual:curator-stub:"))
        # Excerpt explicitly says LLM unavailable
        self.assertIn("LLM unavailable", p["raw_excerpt"])
        # Honest confidence
        self.assertEqual(out.confidence, "low")
        self.assertEqual(out.quality_gate_status, "preliminary")

    def test_handles_empty_name(self):
        agent = DisciplineSourceAcquisitionAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t",
            agent_role_id="discipline_source_acquisition",
            entities={"region": "international"},
        ))
        self.assertIsNotNone(out.output_entity)
        # Empty name still produces a stub but slug becomes "anon"
        p = out.output_entity["packets"][0]
        self.assertIn("anon", p["source_id"])


class TestSeederDeterministicFallback(unittest.TestCase):
    def _packet(self, source_type: str = "vak_passport", source_id: str = "5.7.8") -> DisciplineSourcePacket:
        return DisciplineSourcePacket(
            source_type=source_type,
            source_id=source_id,
            candidate_display_name_ru="Эстетика",
            candidate_region="ru",
            raw_excerpt="ВАК паспорт специальности 5.7.8 — Эстетика.",
        )

    def test_minimal_card_when_no_llm(self):
        agent = DisciplineSeederAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t",
            agent_role_id="discipline_seeder",
            entities={
                "discipline_name": "Эстетика",
                "region": "ru",
                "packets": [self._packet().to_dict()],
            },
        ))
        card = out.output_entity["card"]
        self.assertEqual(card["region"], "ru")
        self.assertEqual(card["source_status"], "llm_draft")
        self.assertIn("ru", card["display_names"])
        self.assertEqual(card["display_names"]["ru"], "Эстетика")
        # Provenance survives — evidence_refs is anchored in input packets
        self.assertEqual(len(card["evidence_refs"]), 1)
        self.assertEqual(card["evidence_refs"][0]["source_type"], "vak_passport")
        self.assertEqual(card["evidence_refs"][0]["source_id"], "5.7.8")
        # Working-tool fields empty + listed in unknowns
        self.assertEqual(card["legitimate_objects"], [])
        self.assertIn("legitimate_objects", card["unknowns"])
        self.assertIn("epistemic_regime", card["unknowns"])
        # Honest fallback confidence
        self.assertEqual(out.confidence, "low")

    def test_no_packets_still_produces_stub(self):
        agent = DisciplineSeederAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t",
            agent_role_id="discipline_seeder",
            entities={
                "discipline_name": "Unknown",
                "region": "international",
                "packets": [],
            },
        ))
        card = out.output_entity["card"]
        self.assertEqual(card["evidence_refs"], [])
        # Card is still llm_draft — never auto-promoted
        self.assertEqual(card["source_status"], "llm_draft")

    def test_multi_packet_provenance_preserved(self):
        agent = DisciplineSeederAgent()
        out = agent.execute_deterministic(AgentInput(
            operation_id="t",
            agent_role_id="discipline_seeder",
            entities={
                "discipline_name": "Эстетика",
                "region": "ru",
                "packets": [
                    self._packet("vak_passport", "5.7.8").to_dict(),
                    self._packet("oecd_ford", "6.3").to_dict(),
                ],
            },
        ))
        refs = out.output_entity["card"]["evidence_refs"]
        types = {r["source_type"] for r in refs}
        self.assertEqual(types, {"vak_passport", "oecd_ford"})


class TestAgentRegistryIntegration(unittest.TestCase):
    def test_acquisition_registered(self):
        self.assertIn("discipline_source_acquisition", AGENT_SPEC_REGISTRY)
        cls = get_agent_class("discipline_source_acquisition")
        self.assertEqual(cls, DisciplineSourceAcquisitionAgent)

    def test_seeder_registered(self):
        self.assertIn("discipline_seeder", AGENT_SPEC_REGISTRY)
        cls = get_agent_class("discipline_seeder")
        self.assertEqual(cls, DisciplineSeederAgent)

    def test_instantiable(self):
        a1 = instantiate_agent("discipline_source_acquisition")
        a2 = instantiate_agent("discipline_seeder")
        self.assertIsInstance(a1, DisciplineSourceAcquisitionAgent)
        self.assertIsInstance(a2, DisciplineSeederAgent)


class TestPromptsExposed(unittest.TestCase):
    def test_acquisition_family_exposed(self):
        from kairoskopion.prompts import DISCIPLINE_SOURCE_ACQUISITION_FAMILY
        self.assertEqual(
            DISCIPLINE_SOURCE_ACQUISITION_FAMILY["family_id"],
            "discipline_source_acquisition_v1",
        )

    def test_seeding_family_exposed(self):
        from kairoskopion.prompts import DISCIPLINE_SEEDING_FAMILY
        self.assertEqual(
            DISCIPLINE_SEEDING_FAMILY["family_id"],
            "discipline_seeding_v1",
        )


if __name__ == "__main__":
    unittest.main()
