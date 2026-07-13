"""Tests that the access and transport policy exists and that no active
instructions encourage SSH retries or treat SSH absence as a general blocker."""

from __future__ import annotations

import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent


class TestAccessTransportPolicyExists(unittest.TestCase):
    def test_policy_document_exists(self):
        path = ROOT / "docs" / "operations" / "ACCESS_AND_TRANSPORT_POLICY.md"
        self.assertTrue(path.exists(), f"Missing: {path}")

    def test_policy_contains_disabled_by_default(self):
        path = ROOT / "docs" / "operations" / "ACCESS_AND_TRANSPORT_POLICY.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("SSH_POLICY=DISABLED_BY_DEFAULT", text)
        self.assertIn("SSH_AUTOMATIC_RETRY_LIMIT=0", text)

    def test_claude_md_references_policy(self):
        path = ROOT / "CLAUDE.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("ACCESS_AND_TRANSPORT_POLICY.md", text)


FORBIDDEN_PATTERNS = [
    re.compile(r"(?i)\bretry\s+SSH\b"),
    re.compile(r"(?i)\btry\s+SSH\s+with\s+a\s+longer\s+timeout\b"),
    re.compile(r"(?i)\bSSH\s+is\s+intermittent\b"),
]

CHECKED_FILES = [
    "CLAUDE.md",
    "docs/operations/CURRENT_WORKING_STATE.md",
    "docs/operations/SESSION_HANDOFF.md",
    "docs/operations/ENVIRONMENT_INVARIANTS.md",
    "docs/operations/KAIROSKOPION_PRODUCTION_DEPLOY_RUNBOOK.md",
]

NEGATION_MARKERS = {"deprecated", "must not", "do not", "forbidden", "запрещ"}


def _is_negated(line: str) -> bool:
    lower = line.lower()
    return any(m in lower for m in NEGATION_MARKERS)


class TestNoActiveSSHRetryInstructions(unittest.TestCase):
    def test_no_forbidden_ssh_patterns_in_checked_docs(self):
        violations: list[str] = []
        for rel_path in CHECKED_FILES:
            path = ROOT / rel_path
            if not path.exists():
                continue
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1
            ):
                if _is_negated(line):
                    continue
                for pat in FORBIDDEN_PATTERNS:
                    if pat.search(line):
                        violations.append(
                            f"{rel_path}:{lineno}: '{line.strip()}'"
                        )
        self.assertEqual(
            violations, [],
            f"Active docs contain forbidden SSH patterns: {violations}",
        )


if __name__ == "__main__":
    unittest.main()
