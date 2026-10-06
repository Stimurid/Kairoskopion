"""TRM-071 / Journal-Yuga 26.7 - Citation Ecology Profiling."""

FAMILY_ID = "target_citation_ecology_v1"
VERSION = "1.0.0"
AGENT_ROLE_ID = "target_citation_ecologist"

SYSTEM_PROMPT = """You are the target-venue Citation Ecology Profiler.

Input is a set of PublishedArticlePattern records grounded in complete article
texts from one venue. Reconstruct only citation practices observed in this
sample. Do not invent references and do not convert absence into prohibition.

Report observed author, tradition, and journal clusters, citation roles,
recency and classic-reference signals, plus bridge categories for article
comparison. If the per-article cards do not preserve enough reference
evidence, keep affected fields unknown.

Rules:
- corpus observation is not editorial intention;
- absence means only not observed in sampled corpus;
- no invented DOI, title, or author;
- preserve sample size, source pattern ids, and uncertainty;
- return JSON only.
"""

USER_TEMPLATE = """Target: {target_id}
Published corpus id: {published_corpus_id}

Fulltext-grounded article patterns:
{patterns_json}

Build sampled-corpus citation ecology evidence.
"""

OUTPUT_SCHEMA = {
    "title": "TargetCitationEcology",
    "type": "object",
    "properties": {
        "dominant_cited_authors": {"type": "array", "items": {"type": "string"}},
        "dominant_cited_journals": {"type": "array", "items": {"type": "string"}},
        "dominant_theoretical_traditions": {"type": "array", "items": {"type": "string"}},
        "citation_roles": {"type": "array", "items": {"type": "string"}},
        "reference_count_observation": {"type": ["string", "null"]},
        "recentness_observation": {"type": ["string", "null"]},
        "classic_reference_observation": {"type": ["string", "null"]},
        "bridge_opportunities": {"type": "array", "items": {"type": "string"}},
        "not_observed_traditions": {"type": "array", "items": {"type": "string"}},
        "evidence_pattern_ids": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": [
        "dominant_cited_authors", "dominant_cited_journals",
        "dominant_theoretical_traditions", "citation_roles",
        "bridge_opportunities", "not_observed_traditions",
        "evidence_pattern_ids", "unknowns", "warnings", "confidence"
    ],
    "additionalProperties": False,
}

TARGET_CITATION_ECOLOGY_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": AGENT_ROLE_ID,
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
}
