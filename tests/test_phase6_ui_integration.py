"""Phase 6: UI integration — API client methods and component wiring checks."""

from __future__ import annotations

import unittest
from pathlib import Path


class TestAPIClientMethods(unittest.TestCase):
    """Verify that the TypeScript API client has all new methods."""

    def setUp(self):
        self.client_path = Path(__file__).resolve().parent.parent / "ui" / "src" / "api" / "client.ts"
        self.client_text = self.client_path.read_text(encoding="utf-8")

    def test_investigate_venue_by_url(self):
        self.assertIn("investigateVenueByUrl", self.client_text)

    def test_enrich_venue(self):
        self.assertIn("enrichVenue", self.client_text)

    def test_venue_profile_package(self):
        self.assertIn("getVenueProfilePackage", self.client_text)

    def test_compliance(self):
        self.assertIn("getCompliance", self.client_text)

    def test_build_submission_pack(self):
        self.assertIn("buildSubmissionPack", self.client_text)

    def test_set_discipline_intent(self):
        self.assertIn("setDisciplineIntent", self.client_text)

    def test_venue_family_context(self):
        self.assertIn("getVenueFamilyContext", self.client_text)

    def test_venue_matrix(self):
        self.assertIn("getVenueMatrix", self.client_text)

    def test_venue_memory(self):
        self.assertIn("listVenueMemory", self.client_text)
        self.assertIn("getVenueMemory", self.client_text)

    def test_depth_mode(self):
        self.assertIn("setDepthMode", self.client_text)

    def test_budget(self):
        self.assertIn("setBudget", self.client_text)

    def test_cost_estimate(self):
        self.assertIn("getCostEstimate", self.client_text)


class TestComponentFiles(unittest.TestCase):
    """Verify that new UI component files exist."""

    def test_depth_mode_panel_exists(self):
        p = Path(__file__).resolve().parent.parent / "ui" / "src" / "components" / "DepthModePanel.tsx"
        self.assertTrue(p.exists())

    def test_venue_memory_panel_exists(self):
        p = Path(__file__).resolve().parent.parent / "ui" / "src" / "components" / "VenueMemoryPanel.tsx"
        self.assertTrue(p.exists())


class TestCaseWorkspaceImports(unittest.TestCase):
    """Verify new components are imported and used in CaseWorkspace."""

    def setUp(self):
        p = Path(__file__).resolve().parent.parent / "ui" / "src" / "components" / "CaseWorkspace.tsx"
        self.text = p.read_text(encoding="utf-8")

    def test_imports_depth_mode_panel(self):
        self.assertIn("DepthModePanel", self.text)

    def test_imports_venue_memory_panel(self):
        self.assertIn("VenueMemoryPanel", self.text)


if __name__ == "__main__":
    unittest.main()
