"""Tests for agentic CLI commands."""

from __future__ import annotations

import unittest

from kairoskopion.cli import main


class TestListAgentsCLI(unittest.TestCase):
    def test_list_all(self):
        rc = main(["list-agents"])
        self.assertEqual(rc, 0)

    def test_list_by_layer(self):
        rc = main(["list-agents", "--layer", "control"])
        self.assertEqual(rc, 0)

    def test_list_unknown_layer(self):
        rc = main(["list-agents", "--layer", "nonexistent"])
        self.assertEqual(rc, 0)


class TestInspectAgentCLI(unittest.TestCase):
    def test_known_agent(self):
        rc = main(["inspect-agent", "article_modeler"])
        self.assertEqual(rc, 0)

    def test_unknown_agent(self):
        rc = main(["inspect-agent", "nonexistent"])
        self.assertEqual(rc, 1)


class TestListPromptFamiliesCLI(unittest.TestCase):
    def test_list(self):
        rc = main(["list-prompt-families"])
        self.assertEqual(rc, 0)


class TestInspectPromptFamilyCLI(unittest.TestCase):
    def test_known(self):
        rc = main(["inspect-prompt-family", "semantic_profiling"])
        self.assertEqual(rc, 0)

    def test_unknown(self):
        rc = main(["inspect-prompt-family", "nonexistent_family"])
        self.assertEqual(rc, 1)


class TestListWorkflowsCLI(unittest.TestCase):
    def test_list(self):
        rc = main(["list-workflows"])
        self.assertEqual(rc, 0)


class TestInspectWorkflowCLI(unittest.TestCase):
    def test_known(self):
        rc = main(["inspect-workflow", "venue_deep_profile"])
        self.assertEqual(rc, 0)

    def test_unknown(self):
        rc = main(["inspect-workflow", "nonexistent"])
        self.assertEqual(rc, 1)


if __name__ == "__main__":
    unittest.main()
