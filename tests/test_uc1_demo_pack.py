"""Tests for UC-1 demo pack: loader, runner, report, CLI."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kairoskopion.demo.uc1_demo_loader import (
    DEMO_PACK_DIR,
    UC1DemoPack,
    load_uc1_demo_pack,
)
from kairoskopion.demo.uc1_runner import UC1DemoResult, run_uc1_demo
from kairoskopion.demo.uc1_report import generate_uc1_demo_report


class TestDemoPackDir(unittest.TestCase):
    def test_bundled_pack_dir_exists(self):
        self.assertTrue(DEMO_PACK_DIR.exists(), f"Expected {DEMO_PACK_DIR}")

    def test_bundled_pack_has_draft(self):
        self.assertTrue((DEMO_PACK_DIR / "draft_article.md").exists())

    def test_bundled_pack_has_scenario(self):
        self.assertTrue((DEMO_PACK_DIR / "scenario.json").exists())

    def test_bundled_pack_has_venue_seeds(self):
        self.assertTrue((DEMO_PACK_DIR / "venue_seeds.json").exists())

    def test_bundled_pack_has_guidelines(self):
        gdir = DEMO_PACK_DIR / "venue_guidelines"
        self.assertTrue(gdir.exists())
        self.assertTrue(len(list(gdir.iterdir())) >= 1)

    def test_bundled_pack_has_corpus(self):
        cdir = DEMO_PACK_DIR / "corpus"
        self.assertTrue(cdir.exists())
        self.assertTrue(len(list(cdir.iterdir())) >= 1)


class TestDemoLoader(unittest.TestCase):
    def test_load_bundled_pack(self):
        pack = load_uc1_demo_pack()
        self.assertIsInstance(pack, UC1DemoPack)
        self.assertTrue(pack.is_valid, f"Errors: {pack.errors}")

    def test_draft_text_length(self):
        pack = load_uc1_demo_pack()
        self.assertGreater(len(pack.draft_text), 800)

    def test_venue_seeds_count(self):
        pack = load_uc1_demo_pack()
        self.assertGreaterEqual(len(pack.venue_seeds), 4)

    def test_venue_seeds_have_names(self):
        pack = load_uc1_demo_pack()
        for v in pack.venue_seeds:
            self.assertIn("name", v)

    def test_venue_names(self):
        pack = load_uc1_demo_pack()
        names = pack.venue_names()
        self.assertGreaterEqual(len(names), 4)
        self.assertIn("Techné: Research in Philosophy and Technology", names)

    def test_guidelines_loaded(self):
        pack = load_uc1_demo_pack()
        self.assertGreater(len(pack.venue_guidelines), 0)

    def test_corpus_loaded(self):
        pack = load_uc1_demo_pack()
        self.assertGreater(len(pack.corpus), 0)
        for key, articles in pack.corpus.items():
            self.assertIsInstance(articles, list)
            self.assertGreater(len(articles), 0)

    def test_scenario_fields(self):
        pack = load_uc1_demo_pack()
        self.assertIn("scenario_id", pack.scenario)
        self.assertIn("scenario_type", pack.scenario)
        self.assertTrue(pack.scenario.get("offline", False))

    def test_to_dict(self):
        pack = load_uc1_demo_pack()
        d = pack.to_dict()
        self.assertIn("venue_count", d)
        self.assertIn("is_valid", d)
        self.assertTrue(d["is_valid"])

    def test_load_missing_dir(self):
        pack = load_uc1_demo_pack(Path("/nonexistent/demo_pack"))
        self.assertFalse(pack.is_valid)
        self.assertGreater(len(pack.errors), 0)

    def test_load_empty_dir(self):
        with tempfile.TemporaryDirectory() as td:
            pack = load_uc1_demo_pack(Path(td))
            self.assertFalse(pack.is_valid)

    def test_load_partial_dir(self):
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            (td_path / "draft_article.md").write_text("x" * 300, encoding="utf-8")
            (td_path / "venue_seeds.json").write_text('[{"name":"A"},{"name":"B"}]', encoding="utf-8")
            (td_path / "scenario.json").write_text('{"ok": true}', encoding="utf-8")
            pack = load_uc1_demo_pack(td_path)
            self.assertIn("Missing venue_guidelines/ directory", pack.errors)


class TestDemoRunner(unittest.TestCase):
    def test_run_bundled_demo(self):
        result = run_uc1_demo()
        self.assertIsInstance(result, UC1DemoResult)
        self.assertIn(result.workflow_status, ("completed", "partial"))

    def test_run_produces_step_results(self):
        result = run_uc1_demo()
        self.assertGreater(len(result.step_results), 0)
        statuses = {sr["status"] for sr in result.step_results}
        self.assertTrue(statuses & {"completed", "skipped"})

    def test_run_produces_entities(self):
        result = run_uc1_demo()
        self.assertIn("article", result.entities)

    def test_run_has_trace(self):
        result = run_uc1_demo()
        self.assertGreater(len(result.trace_log), 0)

    def test_run_with_output_dir(self):
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "demo_output"
            result = run_uc1_demo(output_dir=output_dir)
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "workflow_trace.json").exists())
            self.assertTrue((output_dir / "UC1_DEMO_REPORT.md").exists())

            trace = json.loads((output_dir / "workflow_trace.json").read_text(encoding="utf-8"))
            self.assertIn("workflow_id", trace)
            self.assertEqual(trace["workflow_id"], "uc1_draft_to_venue_pool_positioning")

    def test_run_output_article_json(self):
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "demo_output"
            result = run_uc1_demo(output_dir=output_dir)
            if "article" in result.entities:
                self.assertTrue((output_dir / "article.json").exists())

    def test_run_bad_pack_fails_gracefully(self):
        result = run_uc1_demo(pack_dir=Path("/nonexistent"))
        self.assertEqual(result.workflow_status, "load_failed")
        self.assertFalse(result.is_success)

    def test_to_dict(self):
        result = run_uc1_demo()
        d = result.to_dict()
        self.assertIn("workflow_status", d)
        self.assertIn("step_results", d)
        self.assertIn("entity_keys", d)


class TestDemoReport(unittest.TestCase):
    def test_report_generation(self):
        result = run_uc1_demo()
        report = generate_uc1_demo_report(result)
        self.assertIsInstance(report, str)
        self.assertIn("# UC-1 Demo Report", report)
        self.assertIn("## Demo Pack", report)
        self.assertIn("## Workflow Execution", report)
        self.assertIn("## Step Results", report)
        self.assertIn("## Evidence Gaps", report)

    def test_report_contains_venue_names(self):
        result = run_uc1_demo()
        report = generate_uc1_demo_report(result)
        self.assertIn("Techné", report)

    def test_report_contains_step_table(self):
        result = run_uc1_demo()
        report = generate_uc1_demo_report(result)
        self.assertIn("article_modeler", report)
        self.assertIn("| Step |", report)

    def test_report_with_output_dir(self):
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "demo_output"
            run_uc1_demo(output_dir=output_dir)
            report_path = output_dir / "UC1_DEMO_REPORT.md"
            self.assertTrue(report_path.exists())
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("# UC-1 Demo Report", text)


class TestCLIRunUC1Demo(unittest.TestCase):
    def test_cli_run_uc1_demo(self):
        from kairoskopion.cli import main
        with tempfile.TemporaryDirectory() as td:
            output_dir = Path(td) / "cli_demo_output"
            rc = main(["run-uc1-demo", "--output-dir", str(output_dir)])
            self.assertIn(rc, (0, 1))
            self.assertTrue(output_dir.exists())
            self.assertTrue((output_dir / "workflow_trace.json").exists())
            self.assertTrue((output_dir / "UC1_DEMO_REPORT.md").exists())

    def test_cli_run_uc1_demo_no_output(self):
        from kairoskopion.cli import main
        rc = main(["run-uc1-demo"])
        self.assertIn(rc, (0, 1))

    def test_cli_run_uc1_demo_bad_pack(self):
        from kairoskopion.cli import main
        rc = main(["run-uc1-demo", "--pack-dir", "/nonexistent/pack"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
