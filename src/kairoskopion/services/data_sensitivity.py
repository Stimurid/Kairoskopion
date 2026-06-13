"""Data sensitivity model — classification and routing for sensitive fields.

Provides:
- DataSensitivityLevel enum for field-level classification
- Field sensitivity registry mapping schema fields to sensitivity levels
- Redaction helpers for LLM-bound data
- Storage routing decisions based on sensitivity
"""

from __future__ import annotations

import dataclasses as dc
import re
from enum import Enum
from typing import Any

from ..ids import generate_id
from ..schema import _DictMixin, _list, _now


class DataSensitivityLevel(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PII = "pii"


class StorageZone(str, Enum):
    SHARED_REGISTRY = "shared_registry"
    PRIVATE_VAULT = "private_vault"
    ENCRYPTED_VAULT = "encrypted_vault"


class RedactionPolicy(str, Enum):
    PASS_THROUGH = "pass_through"
    HASH = "hash"
    STRIP = "strip"
    PLACEHOLDER = "placeholder"


_FIELD_SENSITIVITY_MAP: dict[str, DataSensitivityLevel] = {
    # Article fields
    "title_current": DataSensitivityLevel.CONFIDENTIAL,
    "abstract_current": DataSensitivityLevel.CONFIDENTIAL,
    "problem_statement": DataSensitivityLevel.CONFIDENTIAL,
    "research_question": DataSensitivityLevel.CONFIDENTIAL,
    "core_claims": DataSensitivityLevel.CONFIDENTIAL,
    "object_of_inquiry": DataSensitivityLevel.CONFIDENTIAL,
    "method_description": DataSensitivityLevel.CONFIDENTIAL,
    "protected_core": DataSensitivityLevel.CONFIDENTIAL,
    # Author/PII fields
    "author_fragment": DataSensitivityLevel.PII,
    "author_names": DataSensitivityLevel.PII,
    "email": DataSensitivityLevel.PII,
    "orcid": DataSensitivityLevel.PII,
    "affiliation": DataSensitivityLevel.PII,
    # Venue fields (mostly public)
    "canonical_name": DataSensitivityLevel.PUBLIC,
    "issn": DataSensitivityLevel.PUBLIC,
    "publisher_or_owner": DataSensitivityLevel.PUBLIC,
    "official_urls": DataSensitivityLevel.PUBLIC,
    "scope_summary": DataSensitivityLevel.PUBLIC,
    "aims_scope_summary": DataSensitivityLevel.PUBLIC,
    # Internal processing
    "raw_text": DataSensitivityLevel.CONFIDENTIAL,
    "manuscript_text": DataSensitivityLevel.CONFIDENTIAL,
    "fit_assessment_id": DataSensitivityLevel.INTERNAL,
    "rewrite_plan_id": DataSensitivityLevel.INTERNAL,
    "mismatch_map_id": DataSensitivityLevel.INTERNAL,
}

_REDACTION_POLICIES: dict[DataSensitivityLevel, RedactionPolicy] = {
    DataSensitivityLevel.PUBLIC: RedactionPolicy.PASS_THROUGH,
    DataSensitivityLevel.INTERNAL: RedactionPolicy.PASS_THROUGH,
    DataSensitivityLevel.CONFIDENTIAL: RedactionPolicy.PLACEHOLDER,
    DataSensitivityLevel.PII: RedactionPolicy.HASH,
}

_STORAGE_ROUTING: dict[DataSensitivityLevel, StorageZone] = {
    DataSensitivityLevel.PUBLIC: StorageZone.SHARED_REGISTRY,
    DataSensitivityLevel.INTERNAL: StorageZone.SHARED_REGISTRY,
    DataSensitivityLevel.CONFIDENTIAL: StorageZone.PRIVATE_VAULT,
    DataSensitivityLevel.PII: StorageZone.ENCRYPTED_VAULT,
}


@dc.dataclass
class SensitivityAssessment(_DictMixin):
    """Assessment of data sensitivity for a set of fields."""
    assessment_id: str = dc.field(default_factory=lambda: generate_id("dsa"))
    entity_type: str = ""
    total_fields: int = 0
    public_count: int = 0
    internal_count: int = 0
    confidential_count: int = 0
    pii_count: int = 0
    max_sensitivity: str = DataSensitivityLevel.PUBLIC.value
    storage_zone: str = StorageZone.SHARED_REGISTRY.value
    fields_by_level: dict[str, list[str]] = dc.field(default_factory=dict)
    redaction_needed: bool = False
    assessed_at: str = dc.field(default_factory=_now)


def classify_field(field_name: str) -> DataSensitivityLevel:
    """Classify a field by its sensitivity level."""
    return _FIELD_SENSITIVITY_MAP.get(field_name, DataSensitivityLevel.INTERNAL)


def get_redaction_policy(level: DataSensitivityLevel) -> RedactionPolicy:
    """Get the redaction policy for a sensitivity level."""
    return _REDACTION_POLICIES.get(level, RedactionPolicy.PASS_THROUGH)


def get_storage_zone(level: DataSensitivityLevel) -> StorageZone:
    """Get the appropriate storage zone for a sensitivity level."""
    return _STORAGE_ROUTING.get(level, StorageZone.SHARED_REGISTRY)


def assess_entity_sensitivity(
    entity: dict[str, Any],
    entity_type: str = "",
) -> SensitivityAssessment:
    """Assess the sensitivity of all fields in an entity."""
    assessment = SensitivityAssessment(entity_type=entity_type)
    fields_by_level: dict[str, list[str]] = {
        "public": [], "internal": [], "confidential": [], "pii": [],
    }

    max_level = DataSensitivityLevel.PUBLIC
    level_order = [
        DataSensitivityLevel.PUBLIC,
        DataSensitivityLevel.INTERNAL,
        DataSensitivityLevel.CONFIDENTIAL,
        DataSensitivityLevel.PII,
    ]

    for field_name, value in entity.items():
        if value is None or field_name.startswith("_"):
            continue
        assessment.total_fields += 1
        level = classify_field(field_name)
        fields_by_level[level.value].append(field_name)

        if level == DataSensitivityLevel.PUBLIC:
            assessment.public_count += 1
        elif level == DataSensitivityLevel.INTERNAL:
            assessment.internal_count += 1
        elif level == DataSensitivityLevel.CONFIDENTIAL:
            assessment.confidential_count += 1
        elif level == DataSensitivityLevel.PII:
            assessment.pii_count += 1

        if level_order.index(level) > level_order.index(max_level):
            max_level = level

    assessment.max_sensitivity = max_level.value
    assessment.storage_zone = get_storage_zone(max_level).value
    assessment.fields_by_level = fields_by_level
    assessment.redaction_needed = max_level in (
        DataSensitivityLevel.CONFIDENTIAL, DataSensitivityLevel.PII,
    )
    return assessment


def redact_for_llm(
    entity: dict[str, Any],
    *,
    allow_confidential: bool = False,
) -> dict[str, Any]:
    """Redact sensitive fields from an entity before sending to LLM.

    By default, strips PII and replaces CONFIDENTIAL with placeholders.
    Set allow_confidential=True to pass CONFIDENTIAL fields through
    (e.g., when using a self-hosted LLM).
    """
    redacted: dict[str, Any] = {}
    for field_name, value in entity.items():
        if value is None:
            redacted[field_name] = None
            continue

        level = classify_field(field_name)
        policy = get_redaction_policy(level)

        if level == DataSensitivityLevel.PII:
            if policy == RedactionPolicy.HASH:
                redacted[field_name] = f"[REDACTED:PII:{field_name}]"
            else:
                redacted[field_name] = f"[REDACTED:{field_name}]"
        elif level == DataSensitivityLevel.CONFIDENTIAL and not allow_confidential:
            if policy == RedactionPolicy.PLACEHOLDER:
                redacted[field_name] = f"[CONFIDENTIAL:{field_name}]"
            else:
                redacted[field_name] = f"[REDACTED:{field_name}]"
        else:
            redacted[field_name] = value

    return redacted


def storage_zone_for_entity(entity: dict[str, Any]) -> StorageZone:
    """Determine the appropriate storage zone for an entity."""
    assessment = assess_entity_sensitivity(entity)
    return StorageZone(assessment.storage_zone)
