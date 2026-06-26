"""Venue Fact Extraction prompt family (spec §56, §69.3, P5C rewrite).

Extracts VenueModel from venue guidelines, official pages, and other sources.
The LLM acts as Venue Profiler agent: it builds an evidence-backed model of
the publication container.

P5C changes:
- Sections, tracks, special issues are first-class records
- Indexing claims are per-database with year/category where stated
- Metrics claims are per-database/year/category, never collapsed
- Open-field doctrine injected
"""

from __future__ import annotations

from .discipline_intent_parsing import _OPEN_FIELD_DOCTRINE

VENUE_FACT_EXTRACTION_SYSTEM = """\
You are Venue Profiler — a specialized analytical role within Kairoskopion, \
an evidence-first publication-positioning system.

Your task: given venue source text (guidelines, official pages, policy documents), \
extract a structured VenueModel. You are NOT describing the journal. You are \
building a factual, evidence-linked model of a publication container.
""" + _OPEN_FIELD_DOCTRINE + """\

## Output rules

Return a JSON object with the fields listed in the schema. Every field must \
be present. Use null for fields you cannot determine from the source text.

## Evidence status rules

Every extracted fact has an evidence status:
- "fact_from_source" — directly stated in the provided text, can be quoted.
- "vendor_claim" — stated by the publisher/journal itself (marketing, self-description). \
  Most journal homepage content is vendor_claim, not independent fact.
- "inference" — you inferred it from context but it is not directly stated.
- "unknown" — the source does not contain this information.

You MUST assign the correct evidence status to each claim. Publisher statements \
about indexing, impact factor, or quality are VENDOR_CLAIM unless independently \
verified. Author guidelines about formatting, word limits, and submission \
process are FACT_FROM_SOURCE (they define the rules).

## Regime classification (important)

Classify the venue's **publication regime** — the type of publication \
container:
- "classic_journal_article" — standard peer-reviewed journal.
- "special_issue_article" — a special/themed issue within a journal.
- "conference_proceedings" — published conference papers.
- "mega_journal" — large-scale open-access journal.
- "edited_volume" — chapter in an edited book.
- null — cannot determine from text.

Do NOT default to "classic_journal_article" when unsure. Use null.

## Sections, tracks, and special issues (P5C — first-class records)

A venue may have **sections**, **tracks**, or **special issues** that \
target different fields from the parent journal. Extract them as separate \
records in the ``sections`` array:

- Each section has its own scope, editor(s), and may have its own ISSN.
- A section may target a different discipline than the parent venue.
- Special issues are time-bounded sections with specific themes.
- Conference proceedings tracks are sections within a proceedings venue.

Do NOT treat the venue as monolithic. If the source text mentions sections \
or tracks, extract each one separately.

## Indexing and metrics (P5C — per-record, not flat)

Indexing and metrics are **per-database, per-year, per-category**:

- ``indexing_claims``: each claim specifies which database, which \
  subject category (if stated), and year (if stated). A venue may be \
  indexed in multiple categories with different positions.
- ``metrics_claims``: each metric specifies database, metric type, \
  value, year, and subject category. Do NOT collapse "Q1 in Scopus \
  and Q2 in WoS" into a single quartile. Do NOT omit the year.
- A section or special issue may have different indexing from parent.

## Policy extraction (important)

For each policy field below, extract what the venue TEXT actually says. \
Do NOT infer policies from venue type alone. If the text doesn't mention \
a policy, use null — not a guess. Negation matters: "no APC" is different \
from no mention of APC.

## Extraction targets

1. **canonical_name** — the full official name of the journal/venue.
2. **venue_type** — journal, conference_proceedings, book_series, edited_volume, \
   special_issue, unknown.
3. **publisher_or_owner** — who publishes/owns the venue.
4. **official_urls** — list of official URLs found in the text.
5. **scope_summary** — what the venue publishes, its thematic focus. \
   Extract from aims/scope section, not from marketing blurbs.
6. **subject_areas** — list of disciplines/fields the venue covers \
   as stated in the text.
7. **sections** — list of sections/tracks/special issues found in the text.
8. **article_types** — accepted article types as stated in guidelines.
9. **language_policy** — what language(s) articles must be in.
10. **word_limits** — word count limits per article type if stated.
11. **abstract_requirements** — abstract word limit, structure requirements.
12. **review_model** — double_blind, single_blind, open_review, unknown.
13. **indexing_claims** — list of indexing claims. Each with database, \
    subject_category (if stated), year (if stated), evidence_status.
14. **metrics_claims** — list of metric claims. Each with database, \
    metric_type, value, year, subject_category, evidence_status.
15. **open_access_status** — gold, hybrid, subscription, unknown.
16. **apc_policy** — article processing charge: amount, waivers, or no_apc.
17. **ai_policy** — what the venue says about AI/LLM use in manuscripts.
18. **data_policy** — data availability/sharing requirements.
19. **ethics_policy** — ethics approval, IRB requirements.
20. **anonymization_policy** — blinding requirements for review.
21. **submission_portal** — which system is used (OJS, ScholarOne, etc.).
22. **typical_timeline** — review/publication timeline if mentioned.
23. **special_requirements** — any unusual requirements not covered above.

## Forbidden behavior

- Do NOT build VenueModel from your training data or memory. Use ONLY the \
  provided source text.
- Do NOT treat author guidelines as the complete venue model.
- Do NOT confuse a special issue with the parent journal.
- Do NOT assert indexing/quartile status without source — mark as vendor_claim \
  if from journal homepage, unknown if not mentioned.
- Do NOT present publisher marketing as verified fact.
- Do NOT infer hidden editorial preferences without evidence.
- Do NOT treat inaccessible information as absent — use "unknown", not "no".
- Do NOT collapse per-database or per-year metrics into a single value.
"""

VENUE_FACT_EXTRACTION_USER_TEMPLATE = """\
Analyze the following venue source text and extract a VenueModel.

The source type is: {source_type}
Source URL (if known): {source_url}

---
{venue_text}
---

Return a JSON object matching the required schema. Every field must be present. \
Use null for fields you cannot determine. Use empty lists [] for list fields \
with no items found. Assign correct evidence_status to each claim.
"""

VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA: dict = {
    "title": "VenueModelExtraction",
    "type": "object",
    "properties": {
        "canonical_name": {"type": ["string", "null"]},
        "venue_type": {
            "type": "string",
            "enum": [
                "journal", "conference_proceedings", "book_series",
                "edited_volume", "special_issue", "unknown",
            ],
        },
        "regime_type": {
            "type": ["string", "null"],
            "enum": [
                "classic_journal_article", "special_issue_article",
                "conference_proceedings", "mega_journal",
                "edited_volume", None,
            ],
        },
        "publisher_or_owner": {"type": ["string", "null"]},
        "official_urls": {"type": "array", "items": {"type": "string"}},
        "scope_summary": {"type": ["string", "null"]},
        "subject_areas": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "section_name": {"type": "string"},
                    "section_type": {
                        "type": "string",
                        "enum": [
                            "section", "track", "special_issue",
                            "proceedings_track", "unknown",
                        ],
                    },
                    "scope_description": {"type": ["string", "null"]},
                    "target_disciplines": {
                        "type": "array", "items": {"type": "string"},
                    },
                    "editors": {
                        "type": "array", "items": {"type": "string"},
                    },
                    "issn": {"type": ["string", "null"]},
                    "status": {"type": ["string", "null"]},
                    "evidence_status": {"type": "string"},
                },
                "required": [
                    "section_name", "section_type", "evidence_status",
                ],
                "additionalProperties": False,
            },
        },
        "article_types": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "evidence_status": {"type": "string"},
                },
                "required": ["name", "evidence_status"],
                "additionalProperties": False,
            },
        },
        "language_policy": {
            "type": ["object", "null"],
            "properties": {
                "article_body": {"type": ["string", "null"]},
                "metadata": {"type": ["string", "null"]},
                "evidence_status": {"type": "string"},
            },
            "required": ["article_body", "evidence_status"],
            "additionalProperties": False,
        },
        "word_limits": {
            "type": ["object", "null"],
            "properties": {
                "min_words": {"type": ["integer", "null"]},
                "max_words": {"type": ["integer", "null"]},
                "abstract_max_words": {"type": ["integer", "null"]},
                "notes": {"type": ["string", "null"]},
                "evidence_status": {"type": "string"},
            },
            "required": ["evidence_status"],
            "additionalProperties": False,
        },
        "review_model": {
            "type": ["object", "null"],
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["double_blind", "single_blind", "open_review", "unknown"],
                },
                "evidence_status": {"type": "string"},
            },
            "required": ["type", "evidence_status"],
            "additionalProperties": False,
        },
        "indexing_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "database": {"type": "string"},
                    "subject_category": {"type": ["string", "null"]},
                    "year": {"type": ["integer", "null"]},
                    "section_name": {"type": ["string", "null"]},
                    "evidence_status": {"type": "string"},
                    "details": {"type": ["string", "null"]},
                },
                "required": ["database", "evidence_status"],
                "additionalProperties": False,
            },
        },
        "metrics_claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "database": {"type": "string"},
                    "metric_type": {"type": "string"},
                    "value": {"type": ["string", "null"]},
                    "year": {"type": ["integer", "null"]},
                    "subject_category": {"type": ["string", "null"]},
                    "section_name": {"type": ["string", "null"]},
                    "evidence_status": {"type": "string"},
                },
                "required": ["database", "metric_type", "evidence_status"],
                "additionalProperties": False,
            },
        },
        "open_access_status": {
            "type": ["object", "null"],
            "properties": {
                "status": {"type": "string"},
                "evidence_status": {"type": "string"},
            },
            "required": ["status", "evidence_status"],
            "additionalProperties": False,
        },
        "apc_policy": {
            "type": ["object", "null"],
            "properties": {
                "has_apc": {"type": ["boolean", "null"]},
                "amount": {"type": ["string", "null"]},
                "waivers": {"type": ["string", "null"]},
                "evidence_status": {"type": "string"},
            },
            "required": ["evidence_status"],
            "additionalProperties": False,
        },
        "ai_policy": {"type": ["string", "null"]},
        "data_policy": {"type": ["string", "null"]},
        "ethics_policy": {"type": ["string", "null"]},
        "anonymization_policy": {"type": ["string", "null"]},
        "submission_portal": {"type": ["string", "null"]},
        "typical_timeline": {"type": ["string", "null"]},
        "special_requirements": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
    },
    "required": [
        "canonical_name", "venue_type", "scope_summary",
        "article_types", "indexing_claims", "metrics_claims",
        "unknowns", "warnings", "confidence",
    ],
    "additionalProperties": False,
}


def validate_venue_extraction(data: dict) -> list[str]:
    """Check forbidden claims and structural issues."""
    warnings: list[str] = []

    for claim in data.get("indexing_claims", []):
        if claim.get("evidence_status") == "fact_from_source":
            warnings.append(
                f"Indexing claim '{claim.get('database')}' marked as fact_from_source "
                f"— journal self-claims should be vendor_claim"
            )

    for claim in data.get("metrics_claims", []):
        if claim.get("evidence_status") == "fact_from_source":
            warnings.append(
                f"Metric '{claim.get('metric')}' marked as fact_from_source "
                f"— self-reported metrics should be vendor_claim"
            )

    if not data.get("unknowns"):
        warnings.append("No unknowns reported — unlikely for a single-source extraction")

    return warnings


VENUE_FACT_EXTRACTION_FAMILY = {
    "family_id": "venue_fact_extraction_v2",
    "agent_role_id": "venue_profiler",
    "version": "2.0.0",
    "system_prompt": VENUE_FACT_EXTRACTION_SYSTEM,
    "user_prompt_template": VENUE_FACT_EXTRACTION_USER_TEMPLATE,
    "output_schema": VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA,
    "validator": validate_venue_extraction,
}
