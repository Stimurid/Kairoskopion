"""Tests for run-local CLI command."""

import json
from pathlib import Path

from kairoskopion.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def _run_local(tmp_path, ms_path=None, vg_path=None, sc_path=None):
    ms_path = ms_path or str(FIXTURES / "manuscript_sample.md")
    vg_path = vg_path or str(FIXTURES / "venue_guidelines_sample.md")
    sc_path = sc_path or str(FIXTURES / "submission_scenario_sample.json")
    storage = str(tmp_path / "s")
    return main([
        "--storage-root", storage,
        "run-local",
        "--manuscript", ms_path,
        "--venue-guidelines", vg_path,
        "--scenario", sc_path,
    ])


class TestRunLocalSuccess:
    def test_exits_zero(self, tmp_path):
        assert _run_local(tmp_path) == 0

    def test_creates_registries(self, tmp_path):
        _run_local(tmp_path)
        reg_dir = tmp_path / "s" / "registries"
        assert reg_dir.exists()
        jsonl_files = list(reg_dir.glob("*.jsonl"))
        assert len(jsonl_files) >= 10

    def test_creates_vault_cards(self, tmp_path):
        _run_local(tmp_path)
        vault_dir = tmp_path / "s" / "vault"
        assert vault_dir.exists()
        md_files = list(vault_dir.rglob("*.md"))
        assert len(md_files) >= 4

    def test_output_contains_key_ids(self, tmp_path, capsys):
        _run_local(tmp_path)
        out = capsys.readouterr().out
        assert "Pipeline complete (local files)" in out
        assert "ArticleModel:" in out
        assert "VenueModel:" in out
        assert "FitAssessment:" in out
        assert "Overall label:" in out
        assert "art_" in out
        assert "ven_" in out
        assert "fit_" in out

    def test_output_shows_source_files(self, tmp_path, capsys):
        _run_local(tmp_path)
        out = capsys.readouterr().out
        assert "Manuscript:" in out
        assert "Venue:" in out
        assert "Scenario:" in out

    def test_source_snapshots_persisted(self, tmp_path):
        _run_local(tmp_path)
        ss_file = tmp_path / "s" / "registries" / "source_snapshots.jsonl"
        assert ss_file.exists()
        lines = [l for l in ss_file.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert len(lines) == 3
        for line in lines:
            rec = json.loads(line)
            assert "snapshot_id" in rec
            assert rec["snapshot_id"].startswith("snap_")
            assert rec["extraction_status"] == "extracted"

    def test_registries_contain_valid_json(self, tmp_path):
        _run_local(tmp_path)
        reg_dir = tmp_path / "s" / "registries"
        for f in reg_dir.glob("*.jsonl"):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    json.loads(line)

    def test_source_refs_are_local(self, tmp_path):
        _run_local(tmp_path)
        am_file = tmp_path / "s" / "registries" / "article_models.jsonl"
        rec = json.loads(am_file.read_text(encoding="utf-8").splitlines()[0])
        source_refs = rec.get("source_refs", [])
        assert any("local:" in ref for ref in source_refs)


class TestRunLocalWithCustomFiles:
    def test_custom_manuscript(self, tmp_path):
        ms = tmp_path / "my_paper.md"
        ms.write_text("# My Paper\n\nAbstract about philosophy.\n\n## Introduction\n\nSome text.\n\n## Method\n\nConceptual analysis of categories.\n\n## Results\n\nFindings here with enough words to pass threshold for full manuscript detection in the modeling service pipeline.\n", encoding="utf-8")
        assert _run_local(tmp_path, ms_path=str(ms)) == 0

    def test_txt_extension(self, tmp_path):
        ms = tmp_path / "paper.txt"
        ms.write_text("# Paper\n\nAbstract text.\n\n## Introduction\n\nContent.\n\n## Method\n\nApproach.\n\n## Conclusion\n\nEnd.\n", encoding="utf-8")
        assert _run_local(tmp_path, ms_path=str(ms)) == 0


class TestRunLocalErrors:
    def test_missing_manuscript_file(self, tmp_path):
        code = _run_local(tmp_path, ms_path="/nonexistent/paper.md")
        assert code == 1

    def test_missing_venue_file(self, tmp_path):
        code = _run_local(tmp_path, vg_path="/nonexistent/guidelines.md")
        assert code == 1

    def test_missing_scenario_file(self, tmp_path):
        code = _run_local(tmp_path, sc_path="/nonexistent/scenario.json")
        assert code == 1

    def test_unsupported_extension(self, tmp_path, capsys):
        """Truly unsupported extension (.xyz) is rejected."""
        bad = tmp_path / "paper.xyz"
        bad.write_bytes(b"binary data")
        code = _run_local(tmp_path, ms_path=str(bad))
        assert code == 1
        err = capsys.readouterr().err
        assert "unsupported extension" in err

    def test_corrupted_docx(self, tmp_path, capsys):
        """Corrupted DOCX is accepted by validator but extraction fails."""
        bad = tmp_path / "paper.docx"
        bad.write_bytes(b"PK\x03\x04fake")
        code = _run_local(tmp_path, ms_path=str(bad))
        assert code == 1
        err = capsys.readouterr().err
        assert "could not read text" in err

    def test_invalid_scenario_json(self, tmp_path, capsys):
        bad_json = tmp_path / "bad.json"
        bad_json.write_text("not valid json {{{", encoding="utf-8")
        code = _run_local(tmp_path, sc_path=str(bad_json))
        assert code == 1
        err = capsys.readouterr().err
        assert "invalid JSON" in err

    def test_missing_file_error_message(self, tmp_path, capsys):
        code = _run_local(tmp_path, ms_path="/nonexistent/paper.md")
        assert code == 1
        err = capsys.readouterr().err
        assert "file not found" in err

    def test_multiple_missing_files_all_reported(self, tmp_path, capsys):
        code = main([
            "--storage-root", str(tmp_path / "s"),
            "run-local",
            "--manuscript", "/no/ms.md",
            "--venue-guidelines", "/no/vg.md",
            "--scenario", "/no/sc.json",
        ])
        assert code == 1
        err = capsys.readouterr().err
        assert "manuscript" in err
        assert "venue-guidelines" in err
        assert "scenario" in err


class TestRunLocalNoNetwork:
    def test_no_network_imports(self):
        import kairoskopion.cli as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import aiohttp"]:
            assert forbidden not in source
