"""Sprint α tests — Publication Integrability Model v1 substrate.

Covers:
- EvidenceGranularity enum + SourceEvidencePacket schema
- build_packet_from_case deterministic builder
- ProtectedCorePolicy + EvidencePolicy round-trip
- policy_from_article derivation
- apply_policy_gate blocks forbidden_moves and leaves others
- Case snapshot round-trip preserves all three artefacts
"""

from __future__ import annotations

import unittest

from kairoskopion.api.cases import (
    Case,
    _case_from_snapshot,
    _case_to_snapshot,
)
from kairoskopion.enums import EvidenceGranularity, SourceAccessStatus
from kairoskopion.schema import (
    ArticleModel,
    EvidencePolicy,
    ProtectedCorePolicy,
    RewritePlan,
    SourceEvidencePacket,
    VenueModel,
)
from kairoskopion.services.protected_core import (
    apply_policy_gate,
    policy_from_article,
)
from kairoskopion.services.source_evidence_packet import build_packet_from_case


class TestEvidenceGranularityEnum(unittest.TestCase):
    def test_has_eight_values(self):
        values = {v.value for v in EvidenceGranularity}
        self.assertEqual(len(values), 8)
        for expected in (
            "source_fact", "text_extracted_claim", "inferred_pattern",
            "corpus_observation", "user_tacit_note", "vendor_claim",
            "unknown", "conflicting_evidence",
        ):
            self.assertIn(expected, values)


class TestSourceEvidencePacketSchema(unittest.TestCase):
    def test_default_construction(self):
        sep = SourceEvidencePacket(case_id="case_test")
        self.assertEqual(sep.case_id, "case_test")
        self.assertEqual(sep.input_sources, [])
        self.assertEqual(sep.granularity_summary, {})
        self.assertTrue(sep.source_evidence_packet_id.startswith("sep_"))

    def test_round_trip(self):
        sep = SourceEvidencePacket(
            case_id="case_test",
            input_sources=[{"source_id": "x", "granularity": "source_fact"}],
            granularity_summary={"source_fact": 1},
        )
        d = sep.to_dict()
        sep2 = SourceEvidencePacket.from_dict(d)
        self.assertEqual(sep2.case_id, "case_test")
        self.assertEqual(sep2.granularity_summary, {"source_fact": 1})


class TestBuildPacketFromCase(unittest.TestCase):
    def test_user_text_only(self):
        case = Case(title="t")
        case.input_text = "Hello world abstract"
        case.input_type = "abstract"
        sep = build_packet_from_case(case)
        self.assertEqual(len(sep.input_sources), 1)
        entry = sep.input_sources[0]
        self.assertEqual(entry["provenance"], "user_statement")
        self.assertEqual(entry["access_status"], SourceAccessStatus.FULL.value)
        self.assertEqual(entry["granularity"], EvidenceGranularity.USER_TACIT_NOTE.value)
        self.assertEqual(sep.granularity_summary.get("user_tacit_note"), 1)

    def test_with_venue_urls(self):
        case = Case(title="t")
        case.input_text = "manuscript body" * 50
        case.input_type = "manuscript"
        case.investigated_venue = VenueModel(
            canonical_name="V",
            official_urls=["https://example.org/v"],
        )
        sep = build_packet_from_case(case)
        self.assertEqual(len(sep.input_sources), 2)
        urls = [e["source_id"] for e in sep.input_sources if e["source_type"] == "journal_url"]
        self.assertEqual(urls, ["https://example.org/v"])

    def test_empty_case_records_unknown(self):
        case = Case(title="t")
        sep = build_packet_from_case(case)
        self.assertEqual(sep.input_sources, [])
        self.assertTrue(sep.unknowns)


class TestProtectedCorePolicyDerivation(unittest.TestCase):
    def test_policy_from_article(self):
        policy = policy_from_article(
            article_model_id="art_x",
            protected_core=["central thesis", "object of inquiry"],
            mutable_zones=["title", "bibliography"],
        )
        self.assertEqual(policy.article_model_id, "art_x")
        self.assertIn("central thesis", policy.protected_core)
        self.assertEqual(policy.mutable_zones, ["title", "bibliography"])
        # No moves authored yet
        self.assertEqual(policy.forbidden_moves, [])

    def test_policy_round_trip(self):
        policy = ProtectedCorePolicy(
            article_model_id="art_x",
            forbidden_moves=["reduce desire to behavioral addiction"],
            acceptable_loss=["original title"],
            unacceptable_loss=["dispositif/apparatus framing"],
        )
        d = policy.to_dict()
        policy2 = ProtectedCorePolicy.from_dict(d)
        self.assertEqual(policy2.forbidden_moves, policy.forbidden_moves)
        self.assertEqual(policy2.unacceptable_loss, policy.unacceptable_loss)


class TestEvidencePolicySchema(unittest.TestCase):
    def test_defaults(self):
        ep = EvidencePolicy(case_id="case_x")
        self.assertEqual(ep.unknown_handling, "preserve")
        self.assertEqual(ep.inaccessible_handling, "mark_blocking")
        self.assertTrue(ep.require_evidence_for_claims)

    def test_round_trip(self):
        ep = EvidencePolicy(
            case_id="case_x",
            unknown_handling="surface_to_user",
            allow_inference_when_no_source=False,
        )
        d = ep.to_dict()
        ep2 = EvidencePolicy.from_dict(d)
        self.assertEqual(ep2.unknown_handling, "surface_to_user")
        self.assertFalse(ep2.allow_inference_when_no_source)


class TestApplyPolicyGate(unittest.TestCase):
    def _plan_with(self, changes):
        return RewritePlan(
            rewrite_plan_id="rw_x",
            article_model_id="art_x",
            changes=changes,
        )

    def test_no_forbidden_moves_passes_through(self):
        plan = self._plan_with([{"change_id": "c1", "target_block": "title", "desired_state": "Better title"}])
        policy = ProtectedCorePolicy()
        gated, blocked = apply_policy_gate(plan, policy)
        self.assertEqual(blocked, [])
        # Empty forbidden_moves → pass-through, same object identity is fine.
        self.assertEqual(gated.changes[0].get("status"), None)

    def test_forbidden_move_blocks_matching_change(self):
        plan = self._plan_with([
            {
                "change_id": "c1",
                "target_block": "argument",
                "desired_state": "reduce desire to behavioral addiction",
                "reason": "venue norm",
            },
            {
                "change_id": "c2",
                "target_block": "bibliography",
                "desired_state": "add 5 missing references",
            },
        ])
        policy = ProtectedCorePolicy(
            forbidden_moves=["reduce desire behavioral addiction"],
        )
        gated, blocked = apply_policy_gate(plan, policy)
        self.assertEqual(len(blocked), 1)
        self.assertEqual(blocked[0]["change_id"], "c1")
        self.assertEqual(gated.changes[0].get("status"), "blocked_by_policy")
        self.assertIsNone(gated.changes[1].get("status"))
        self.assertTrue(gated.requires_user_acceptance)
        self.assertIn("POLICY GATE", gated.summary or "")

    def test_preserves_pre_blocked_changes(self):
        plan = self._plan_with([
            {
                "change_id": "c1",
                "target_block": "argument",
                "desired_state": "reduce desire to behavioral addiction",
                "status": "blocked_pending_consent",
            },
        ])
        policy = ProtectedCorePolicy(forbidden_moves=["reduce desire"])
        gated, blocked = apply_policy_gate(plan, policy)
        # Already blocked by core gate — not double-counted
        self.assertEqual(blocked, [])
        self.assertEqual(gated.changes[0].get("status"), "blocked_pending_consent")


class TestCaseSnapshotRoundTrip(unittest.TestCase):
    def test_round_trip_packet_and_policies(self):
        case = Case(title="t")
        case.article_model = ArticleModel(
            title_current="t",
            protected_core=["central thesis"],
        )
        # touch accessors to materialize
        case.get_source_evidence_packet()
        case.ensure_protected_core_policy()
        case.get_evidence_policy()
        case.policy_blocked_changes = [
            {"change_id": "c1", "matched_moves": ["reduce desire"]},
        ]

        snap = _case_to_snapshot(case)
        restored = _case_from_snapshot(snap)
        self.assertIsNotNone(restored.source_evidence_packet)
        self.assertIsNotNone(restored.protected_core_policy)
        self.assertIsNotNone(restored.evidence_policy)
        self.assertEqual(restored.policy_blocked_changes[0]["change_id"], "c1")


class TestCaseLevelPolicyAuthoring(unittest.TestCase):
    def test_set_protected_core_policy_extends_derived(self):
        case = Case(title="t")
        case.article_model = ArticleModel(
            title_current="t",
            protected_core=["thesis"],
        )
        case.set_protected_core_policy({
            "forbidden_moves": ["reduce to UX"],
            "unacceptable_loss": ["dispositif framing"],
        })
        self.assertIn("reduce to UX", case.protected_core_policy.forbidden_moves)
        self.assertIn("thesis", case.protected_core_policy.protected_core)
        self.assertIn("dispositif framing", case.protected_core_policy.unacceptable_loss)


if __name__ == "__main__":
    unittest.main()
