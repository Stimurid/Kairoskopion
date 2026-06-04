"""Tests for minimal CLI."""

import json
import os
import subprocess
import sys
from pathlib import Path

from kairoskopion.cli import main


class TestCLIStatus:
    def test_exits_zero(self, tmp_path):
        code = main(["--storage-root", str(tmp_path / "s"), "status"])
        assert code == 0

    def test_shows_version(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "status"])
        out = capsys.readouterr().out
        assert "Kairoskopion" in out
        assert "0.1.0" in out

    def test_shows_storage_root(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "status"])
        out = capsys.readouterr().out
        assert "Storage root" in out

    def test_shows_registries_exist_false(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "status"])
        out = capsys.readouterr().out
        assert "Registries exist:  False" in out


class TestCLIRunFixture:
    def test_exits_zero(self, tmp_path):
        code = main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        assert code == 0

    def test_creates_registries(self, tmp_path):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        reg_dir = tmp_path / "s" / "registries"
        assert reg_dir.exists()
        jsonl_files = list(reg_dir.glob("*.jsonl"))
        assert len(jsonl_files) >= 10

    def test_creates_vault_cards(self, tmp_path):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        vault_dir = tmp_path / "s" / "vault"
        assert vault_dir.exists()
        md_files = list(vault_dir.rglob("*.md"))
        assert len(md_files) >= 4

    def test_output_contains_key_ids(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        out = capsys.readouterr().out
        assert "ArticleModel:" in out
        assert "VenueModel:" in out
        assert "FitAssessment:" in out
        assert "Overall label:" in out
        assert "art_" in out
        assert "ven_" in out
        assert "fit_" in out

    def test_output_contains_paths(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        out = capsys.readouterr().out
        assert "Registry root:" in out
        assert "Vault root:" in out

    def test_registries_contain_valid_json(self, tmp_path):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        reg_dir = tmp_path / "s" / "registries"
        for f in reg_dir.glob("*.jsonl"):
            for i, line in enumerate(f.read_text(encoding="utf-8").splitlines()):
                if line.strip():
                    json.loads(line)  # raises on invalid JSON

    def test_status_after_run_shows_registries(self, tmp_path, capsys):
        main(["--storage-root", str(tmp_path / "s"), "run-fixture"])
        capsys.readouterr()  # clear
        main(["--storage-root", str(tmp_path / "s"), "status"])
        out = capsys.readouterr().out
        assert "Registries exist:  True" in out
        assert "Vault exists:      True" in out

    def test_no_network_calls(self):
        """CLI module must not import network libraries."""
        import kairoskopion.cli as mod
        source = Path(mod.__file__).read_text(encoding="utf-8")
        for forbidden in ["import requests", "import urllib", "import httpx", "import aiohttp"]:
            assert forbidden not in source

    def test_env_var_storage_root(self, tmp_path, monkeypatch):
        env_root = tmp_path / "env_store"
        monkeypatch.setenv("KAIROSKOPION_STORAGE_ROOT", str(env_root))
        code = main(["run-fixture"])
        assert code == 0
        assert (env_root / "registries").exists()
        assert (env_root / "vault").exists()


class TestCLINoCommand:
    def test_no_args_exits_zero(self, tmp_path):
        code = main(["--storage-root", str(tmp_path / "s")])
        assert code == 0
