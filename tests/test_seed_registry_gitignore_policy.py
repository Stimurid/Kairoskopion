"""P7.2C: Regression test for .gitignore seed registry tracking policy.

Ensures that:
- data/seed_registry/ outputs are NOT blocked by gitignore
- data/private_work/ remains ignored
- data/input/ remains ignored
- No bare `data/` rule that blocks curated subtrees
"""

import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
GITIGNORE = REPO_ROOT / ".gitignore"


def _check_ignore(path: str) -> bool:
    """Return True if the path IS ignored by git."""
    result = subprocess.run(
        ["git", "check-ignore", "-q", path],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    return result.returncode == 0


class TestGitignoreSeedPolicy:

    def test_gitignore_exists(self):
        assert GITIGNORE.exists()

    def test_no_bare_data_slash_rule(self):
        lines = GITIGNORE.read_text(encoding="utf-8").splitlines()
        bare_data_rules = [
            ln.strip() for ln in lines
            if ln.strip() == "data/" and not ln.strip().startswith("#")
        ]
        assert not bare_data_rules, (
            "Found bare 'data/' rule which blocks negation of curated subtrees. "
            "Use 'data/*' instead."
        )

    def test_has_seed_registry_allow(self):
        text = GITIGNORE.read_text(encoding="utf-8")
        assert "!data/seed_registry/" in text
        assert "!data/seed_registry/**" in text

    def test_has_private_work_ignore(self):
        text = GITIGNORE.read_text(encoding="utf-8")
        assert "data/private_work/" in text or "data/private_work/**" in text

    def test_has_input_ignore(self):
        text = GITIGNORE.read_text(encoding="utf-8")
        assert "data/input/" in text or "data/input/private/" in text

    def test_seed_registry_not_ignored(self):
        assert not _check_ignore("data/seed_registry/new_run/output.json"), (
            "data/seed_registry/ path is ignored — seed outputs would need force-add"
        )

    def test_private_work_ignored(self):
        assert _check_ignore("data/private_work/article.md"), (
            "data/private_work/ should be ignored"
        )

    def test_data_input_ignored(self):
        assert _check_ignore("data/input/private/raw.txt"), (
            "data/input/private/ should be ignored"
        )

    def test_venue_evidence_packs_not_ignored(self):
        assert not _check_ignore("data/venue_evidence_packs/test_pack.md"), (
            "data/venue_evidence_packs/ should not be ignored"
        )

    def test_disciplinary_landscape_not_ignored(self):
        assert not _check_ignore("data/disciplinary_landscape/seeds/test.jsonl"), (
            "data/disciplinary_landscape/ should not be ignored"
        )

    def test_data_registry_ignored(self):
        assert _check_ignore("data/registry/venues.jsonl"), (
            "data/registry/ (runtime store) should be ignored"
        )
