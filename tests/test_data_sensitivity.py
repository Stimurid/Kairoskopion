"""Tests for data sensitivity model."""

from __future__ import annotations

import unittest

from kairoskopion.services.data_sensitivity import (
    DataSensitivityLevel,
    RedactionPolicy,
    StorageZone,
    assess_entity_sensitivity,
    classify_field,
    get_redaction_policy,
    get_storage_zone,
    redact_for_llm,
    storage_zone_for_entity,
)


class TestClassifyField(unittest.TestCase):
    def test_public_field(self):
        self.assertEqual(classify_field("canonical_name"), DataSensitivityLevel.PUBLIC)

    def test_confidential_field(self):
        self.assertEqual(classify_field("title_current"), DataSensitivityLevel.CONFIDENTIAL)

    def test_pii_field(self):
        self.assertEqual(classify_field("author_fragment"), DataSensitivityLevel.PII)

    def test_internal_field(self):
        self.assertEqual(classify_field("fit_assessment_id"), DataSensitivityLevel.INTERNAL)

    def test_unknown_field_defaults_internal(self):
        self.assertEqual(classify_field("some_random_field"), DataSensitivityLevel.INTERNAL)


class TestRedactionPolicy(unittest.TestCase):
    def test_public_passes_through(self):
        self.assertEqual(
            get_redaction_policy(DataSensitivityLevel.PUBLIC),
            RedactionPolicy.PASS_THROUGH,
        )

    def test_pii_hashes(self):
        self.assertEqual(
            get_redaction_policy(DataSensitivityLevel.PII),
            RedactionPolicy.HASH,
        )

    def test_confidential_placeholders(self):
        self.assertEqual(
            get_redaction_policy(DataSensitivityLevel.CONFIDENTIAL),
            RedactionPolicy.PLACEHOLDER,
        )


class TestStorageZone(unittest.TestCase):
    def test_public_shared(self):
        self.assertEqual(
            get_storage_zone(DataSensitivityLevel.PUBLIC),
            StorageZone.SHARED_REGISTRY,
        )

    def test_confidential_private(self):
        self.assertEqual(
            get_storage_zone(DataSensitivityLevel.CONFIDENTIAL),
            StorageZone.PRIVATE_VAULT,
        )

    def test_pii_encrypted(self):
        self.assertEqual(
            get_storage_zone(DataSensitivityLevel.PII),
            StorageZone.ENCRYPTED_VAULT,
        )


class TestAssessEntitySensitivity(unittest.TestCase):
    def test_public_only(self):
        entity = {"canonical_name": "Test Journal", "issn": "1234-5678"}
        assessment = assess_entity_sensitivity(entity, "VenueModel")
        self.assertEqual(assessment.max_sensitivity, "public")
        self.assertEqual(assessment.public_count, 2)
        self.assertFalse(assessment.redaction_needed)

    def test_mixed_with_pii(self):
        entity = {
            "canonical_name": "Journal",
            "author_fragment": "Smith, J.",
            "title_current": "My Paper",
        }
        assessment = assess_entity_sensitivity(entity, "mixed")
        self.assertEqual(assessment.max_sensitivity, "pii")
        self.assertEqual(assessment.storage_zone, "encrypted_vault")
        self.assertTrue(assessment.redaction_needed)

    def test_confidential_article(self):
        entity = {
            "title_current": "My Thesis",
            "abstract_current": "About something",
            "core_claims": ["claim 1"],
        }
        assessment = assess_entity_sensitivity(entity, "ArticleModel")
        self.assertEqual(assessment.max_sensitivity, "confidential")
        self.assertEqual(assessment.confidential_count, 3)
        self.assertTrue(assessment.redaction_needed)

    def test_skips_none_and_private(self):
        entity = {"canonical_name": "X", "_internal": True, "issn": None}
        assessment = assess_entity_sensitivity(entity)
        self.assertEqual(assessment.total_fields, 1)

    def test_empty_entity(self):
        assessment = assess_entity_sensitivity({})
        self.assertEqual(assessment.total_fields, 0)
        self.assertEqual(assessment.max_sensitivity, "public")

    def test_serialization(self):
        assessment = assess_entity_sensitivity({"canonical_name": "X"})
        d = assessment.to_dict()
        self.assertIn("assessment_id", d)
        self.assertIn("max_sensitivity", d)


class TestRedactForLLM(unittest.TestCase):
    def test_pii_redacted(self):
        entity = {"author_fragment": "Smith, J.", "canonical_name": "Journal"}
        redacted = redact_for_llm(entity)
        self.assertIn("REDACTED:PII", redacted["author_fragment"])
        self.assertEqual(redacted["canonical_name"], "Journal")

    def test_confidential_redacted_by_default(self):
        entity = {"title_current": "My Paper", "canonical_name": "Journal"}
        redacted = redact_for_llm(entity)
        self.assertIn("CONFIDENTIAL", redacted["title_current"])
        self.assertEqual(redacted["canonical_name"], "Journal")

    def test_confidential_allowed_when_self_hosted(self):
        entity = {"title_current": "My Paper"}
        redacted = redact_for_llm(entity, allow_confidential=True)
        self.assertEqual(redacted["title_current"], "My Paper")

    def test_none_values_preserved(self):
        entity = {"title_current": None}
        redacted = redact_for_llm(entity)
        self.assertIsNone(redacted["title_current"])

    def test_public_passes_through(self):
        entity = {"canonical_name": "Journal", "issn": "1234"}
        redacted = redact_for_llm(entity)
        self.assertEqual(redacted["canonical_name"], "Journal")
        self.assertEqual(redacted["issn"], "1234")

    def test_internal_passes_through(self):
        entity = {"fit_assessment_id": "fit_123"}
        redacted = redact_for_llm(entity)
        self.assertEqual(redacted["fit_assessment_id"], "fit_123")


class TestStorageZoneForEntity(unittest.TestCase):
    def test_public_entity(self):
        zone = storage_zone_for_entity({"canonical_name": "X"})
        self.assertEqual(zone, StorageZone.SHARED_REGISTRY)

    def test_pii_entity(self):
        zone = storage_zone_for_entity({"author_fragment": "Smith"})
        self.assertEqual(zone, StorageZone.ENCRYPTED_VAULT)


if __name__ == "__main__":
    unittest.main()
