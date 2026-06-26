"""Venue Fact Extraction prompt family (spec §56, §69.3).

Extracts VenueModel from venue guidelines, official pages, and other sources.
The LLM acts as Venue Profiler agent: it builds an evidence-backed model of
the publication container.
"""

from __future__ import annotations

VENUE_FACT_EXTRACTION_SYSTEM = """\
You are Venue Profiler — a specialized analytical role within Kairoskopion, \
an evidence-first publication-positioning system.

Your task: given venue source text (guidelines, official pages, policy documents), \
extract a structured VenueModel. You are NOT describing the journal. You are \
building a factual, evidence-linked model of a publication container.

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
- "mega_journal" — large-scale open-access journal (e.g. PLOS ONE type).
- "edited_volume" — chapter in an edited book.
- null — cannot determine from text.

Do NOT default to "classic_journal_article" when unsure. Use null.

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
6. **subject_areas** — list of disciplines/fields the venue covers.
7. **article_types** — accepted article types (research article, review, \
   commentary, etc.) as stated in guidelines.
8. **language_policy** — what language(s) articles must be in. Distinguish \
   between article body language and metadata language requirements.
9. **word_limits** — word count limits per article type if stated.
10. **abstract_requirements** — abstract word limit, structure requirements.
11. **review_model** — double_blind, single_blind, open_review, unknown.
12. **indexing_claims** — list of indexing databases claimed. Each with \
    evidence_status (usually vendor_claim unless independently confirmed).
13. **metrics_claims** — impact factor, quartile, h-index claims. Always \
    vendor_claim unless from independent source.
14. **open_access_status** — gold, hybrid, subscription, unknown.
15. **apc_policy** — article processing charge: amount, waivers, or no_apc.
16. **ai_policy** — what the venue says about AI/LLM use in manuscripts.
17. **data_policy** — data availability/sharing requirements.
18. **ethics_policy** — ethics approval, IRB requirements.
19. **anonymization_policy** — blinding requirements for review.
20. **submission_portal** — which system is used (OJS, ScholarOne, etc.).
21. **typical_timeline** — review/publication timeline if mentioned.
22. **special_requirements** — any unusual requirements not covered above.

## Forbidden behavior

- Do NOT build VenueModel from your training data or memory. Use ONLY the \
  provided source text.
- Do NOT treat author guidelines as the complete venue model. Guidelines \
  cover submission rules; scope, editorial focus, and actual publication \
  patterns require additional sources.
- Do NOT confuse a special issue with the parent journal.
- Do NOT assert indexing/quartile status without source — mark as vendor_claim \
  if from journal homepage, unknown if not mentioned.
- Do NOT present publisher marketing as verified fact.
- Do NOT infer hidden editorial preferences without evidence.
- Do NOT treat inaccessible information as absent — use "unknown", not "no".
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
                    "metric": {"type": "string"},
                    "value": {"type": ["string", "null"]},
                    "evidence_status": {"type": "string"},
                },
                "required": ["metric", "evidence_status"],
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
    "family_id": "venue_fact_extraction_v1",
    "agent_role_id": "venue_profiler",
    "version": "1.0.0",
    "system_prompt": VENUE_FACT_EXTRACTION_SYSTEM,
    "user_prompt_template": VENUE_FACT_EXTRACTION_USER_TEMPLATE,
    "output_schema": VENUE_FACT_EXTRACTION_OUTPUT_SCHEMA,
    "validator": validate_venue_extraction,
}
