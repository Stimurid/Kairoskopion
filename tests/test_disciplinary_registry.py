"""Tests for the disciplinary landscape registry scaffold (Phase B0/B1).

Covers:
- DisciplineModel round-trip (to_dict/from_dict)
- Schema validation of seed files
- Loader: seeds + live registry, live overrides seed
- Region filter, including ru ← international cross-reference via
  ``international_mapping``
- Keyword pre-filter (recall-biased candidate selection)
- Matcher agent contract — deterministic fallback returns top-K keyword
  candidates so the seam exists from day 1 even without LLM
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from kairoskopion.services.discipline_registry import (
    DisciplineModel,
    DisciplineRegistry,
    load_default_registry,
    load_registry_from_paths,
)


# ---------------------------------------------------------------------------
# Repo-level constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS_DIR = REPO_ROOT / "data" / "disciplinary_landscape" / "seeds"
SCHEMA_PATH = (
    REPO_ROOT
    / "data"
    / "disciplinary_landscape"
    / "schema"
    / "discipline_model.schema.json"
)


def _all_seed_records() -> list[dict]:
    out: list[dict] = []
    for p in sorted(SEEDS_DIR.glob("*.jsonl")):
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class TestDisciplineModel(unittest.TestCase):
    def test_minimal_required_fields(self):
        d = DisciplineModel(
            discipline_id="test-stub",
            display_names={"en": "Test stub"},
            region="international",
            source_status="llm_draft",
            last_updated="2026-06-17",
        )
        self.assertEqual(d.region, "international")
        self.assertEqual(d.source_status, "llm_draft")
        # Optional working-tool fields default empty
        self.assertEqual(d.forms_of_evidence, [])
        self.assertEqual(d.canonical_questions, [])

    def test_round_trip_full_record(self):
        rec = {
            "schema_version": "1.0.0",
            "model_version": "0.1.0",
            "discipline_id": "ru-foo",
            "display_names": {"ru": "Тест", "en": "Test"},
            "region": "ru",
            "source_status": "llm_draft",
            "last_updated": "2026-06-17",
            "aliases": ["foo"],
            "paradigm": "Test paradigm.",
            "epistemic_regime": "test regime",
            "forms_of_evidence": ["test ev"],
            "canonical_questions": ["test q?"],
            "legitimate_objects": ["test obj"],
            "argument_styles": ["analysis"],
            "publication_genres": ["essay"],
            "international_mapping": ["intl-foo"],
            "key_authors": [
                {"name": "X", "role": "founder", "era": "20c", "discipline_relevance": "rel"},
            ],
            "evidence_refs": [{"source_type": "llm_pretraining"}],
            "times_seen": 0,
        }
        d = DisciplineModel.from_dict(rec)
        roundtripped = d.to_dict()
        # Required fields survive
        for k in (
            "discipline_id", "display_names", "region",
            "source_status", "last_updated",
        ):
            self.assertEqual(roundtripped[k], rec[k])
        self.assertEqual(roundtripped["paradigm"], rec["paradigm"])
        self.assertEqual(len(roundtripped["key_authors"]), 1)
        self.assertEqual(roundtripped["key_authors"][0]["name"], "X")


# ---------------------------------------------------------------------------
# Seed file invariants
# ---------------------------------------------------------------------------

class TestSeedFiles(unittest.TestCase):
    def test_at_least_20_seeds(self):
        records = _all_seed_records()
        self.assertGreaterEqual(
            len(records), 20,
            "Phase B0/B1 acceptance: at least 20–30 seed records required",
        )

    def test_ids_unique(self):
        ids = [r["discipline_id"] for r in _all_seed_records()]
        self.assertEqual(len(ids), len(set(ids)), "duplicate discipline_id in seeds")

    def test_id_pattern(self):
        import re
        pat = re.compile(r"^[a-z0-9]+(-[a-z0-9.]+)*$")
        for rec in _all_seed_records():
            self.assertRegex(rec["discipline_id"], pat)

    def test_required_fields_present(self):
        required = {
            "schema_version", "model_version", "discipline_id",
            "display_names", "region", "source_status", "last_updated",
        }
        for rec in _all_seed_records():
            missing = required - set(rec)
            self.assertFalse(
                missing,
                f"{rec.get('discipline_id')} missing fields: {missing}",
            )

    def test_region_values(self):
        allowed = {"ru", "international", "eu-fr", "eu-de", "en-us", "en-uk", "other"}
        for rec in _all_seed_records():
            self.assertIn(rec["region"], allowed)

    def test_source_status_is_llm_draft_for_seeds(self):
        # All seeds ship as llm_draft per Phase B policy — curator promotes later
        for rec in _all_seed_records():
            self.assertEqual(
                rec["source_status"], "llm_draft",
                f"{rec['discipline_id']}: seed records must ship as llm_draft",
            )

    def test_each_seed_loads_into_model(self):
        for rec in _all_seed_records():
            DisciplineModel.from_dict(rec)  # raises if shape wrong

    def test_international_mapping_targets_exist_when_present(self):
        # Cross-region references should resolve to real disciplines once we
        # add them all. For now: warn on dangling refs by collecting them
        # but don't fail (international_mapping may point to disciplines we
        # haven't seeded yet).
        records = _all_seed_records()
        all_ids = {r["discipline_id"] for r in records}
        dangling: list[str] = []
        for r in records:
            for ref in r.get("international_mapping", []):
                if ref not in all_ids:
                    dangling.append(f"{r['discipline_id']} → {ref}")
        # B0/B1 ships 25 seeds out of the eventual ~100; many
        # international_mapping targets are legitimately not seeded yet
        # (intl-ontology, intl-metaphysics, intl-systems-thinking, ...).
        # We only fail if a clear majority are dangling, which would
        # indicate typos rather than missing-coverage.
        if records:
            ratio = len(dangling) / max(1, sum(
                len(r.get("international_mapping", [])) for r in records
            ))
            self.assertLess(
                ratio, 0.8,
                f"too many dangling international_mapping refs: {dangling[:5]}...",
            )


# ---------------------------------------------------------------------------
# Loader + region filter
# ---------------------------------------------------------------------------

class TestRegistry(unittest.TestCase):
    def test_load_default_registry_non_empty(self):
        reg = load_default_registry()
        self.assertGreater(len(reg), 0)

    def test_by_region_ru_includes_international_with_ru_mapping(self):
        reg = load_default_registry()
        ru_pool = reg.by_region("ru")
        # Should include intl-philosophy-of-technology because its
        # international_mapping contains "ru-philosophy-of-technology"
        ids = {d.discipline_id for d in ru_pool}
        # Must include actual ru discipline
        self.assertIn("ru-philosophy-of-technology", ids)
        # And intl that maps back to ru
        self.assertTrue(
            any(i.startswith("intl-") for i in ids),
            "ru region should include international neighbours via mapping",
        )

    def test_by_region_international_no_ru_bleed(self):
        reg = load_default_registry()
        intl_pool = reg.by_region("international")
        for d in intl_pool:
            self.assertEqual(d.region, "international")

    def test_by_region_auto_returns_all(self):
        reg = load_default_registry()
        self.assertEqual(len(reg.by_region("auto")), len(reg))

    def test_candidates_keyword_recall(self):
        """Keyword pre-filter is recall-biased and substring-based; it
        cannot handle Russian morphology — that's the LLM matcher's
        job. Use the exact nominative form here to verify the seam."""
        reg = load_default_registry()
        cands = reg.candidates_keyword(
            "Статья по теме Философия техники и технические артефакты.",
            region="ru",
        )
        ids = {d.discipline_id for d in cands}
        self.assertIn("ru-philosophy-of-technology", ids)

    def test_candidates_keyword_english(self):
        reg = load_default_registry()
        cands = reg.candidates_keyword(
            "paper on actor-network theory and laboratory ethnography",
            region="international",
        )
        ids = {d.discipline_id for d in cands}
        # ANT or STS must appear
        self.assertTrue(
            "intl-actor-network-theory" in ids or "intl-sts" in ids,
            f"expected ANT/STS in candidates, got {ids}",
        )

    def test_candidates_keyword_empty_text_returns_empty(self):
        reg = load_default_registry()
        self.assertEqual(reg.candidates_keyword("   ", region="auto"), [])

    def test_adjacent_walk_one_hop(self):
        reg = load_default_registry()
        adj = reg.adjacent_of("ru-philosophy-of-technology")
        # Must contain at least one neighbour
        self.assertGreater(len(adj), 0)


# ---------------------------------------------------------------------------
# Live registry override
# ---------------------------------------------------------------------------

class TestLiveOverridesSeed(unittest.TestCase):
    def test_live_record_overrides_seed_by_id(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            seed = Path(tmp) / "seed.jsonl"
            live = Path(tmp) / "live.jsonl"
            seed.write_text(
                json.dumps({
                    "schema_version": "1.0.0",
                    "model_version": "0.1.0",
                    "discipline_id": "x-test",
                    "display_names": {"en": "Original"},
                    "region": "international",
                    "source_status": "llm_draft",
                    "last_updated": "2026-06-17",
                    "paradigm": "seed paradigm",
                }) + "\n",
                encoding="utf-8",
            )
            live.write_text(
                json.dumps({
                    "schema_version": "1.0.0",
                    "model_version": "0.2.0",
                    "discipline_id": "x-test",
                    "display_names": {"en": "Curated"},
                    "region": "international",
                    "source_status": "user_confirmed",
                    "last_updated": "2026-06-17",
                    "paradigm": "live paradigm",
                }) + "\n",
                encoding="utf-8",
            )
            reg = load_registry_from_paths([seed], live)
            d = reg.get("x-test")
            self.assertIsNotNone(d)
            self.assertEqual(d.source_status, "user_confirmed")
            self.assertEqual(d.paradigm, "live paradigm")


# ---------------------------------------------------------------------------
# Matcher agent — deterministic seam
# ---------------------------------------------------------------------------

class TestDisciplineMatcherAgent(unittest.TestCase):
    def test_deterministic_fallback_returns_candidates(self):
        from kairoskopion.agents.discipline_matcher import (
            DisciplineMatcherAgent,
        )
        from kairoskopion.agents.contract import AgentInput

        agent = DisciplineMatcherAgent()
        inp = AgentInput(
            operation_id="match-test",
            agent_role_id="discipline_matcher",
            raw_text=(
                # Use nominative form so the substring-based keyword
                # pre-filter (not the LLM matcher) catches the alias.
                "Статья — Философия техники и Heidegger."
            ),
            entities={"region": "ru"},
        )
        out = agent.execute_deterministic(inp)
        self.assertIsNotNone(out.output_entity)
        matched = out.output_entity.get("matched", [])
        self.assertGreater(len(matched), 0)
        ids = {m["discipline_id"] for m in matched}
        self.assertIn("ru-philosophy-of-technology", ids)
        # Honest fallback: marked low confidence, not pretending to be LLM
        self.assertEqual(out.output_entity.get("confidence"), "low")


if __name__ == "__main__":
    unittest.main()
