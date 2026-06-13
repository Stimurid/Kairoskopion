"""Web enrichment pipeline for ArticleModel.

Three modes:
  none  — skip (default)
  light — 1 round, top unknowns, 3-5 searches, 1 LLM synthesis
  deep  — up to 3 rounds, all gaps, 10+ searches, verification queries
"""

from __future__ import annotations

import json
import logging
from typing import Any

from ..llm.provider import LLMProvider
from ..search.provider import SearchDepth, SearchResult, WebSearchProvider

logger = logging.getLogger(__name__)

_LIGHT_MAX_QUERIES = 5
_LIGHT_RESULTS_PER_QUERY = 3

_DEEP_MAX_QUERIES = 10
_DEEP_RESULTS_PER_QUERY = 5
_DEEP_MAX_ROUNDS = 3

_GAP_PROMPT = """\
You are an extraction quality analyst. Given an ArticleModel JSON, \
identify fields that are unknown, null, empty, or low-confidence and \
would benefit from a web search to verify or fill in.

For each gap, generate a concise search query (in the language of the \
article's domain — use English for English articles, etc.).

## ArticleModel
```json
{article_json}
```

Return a JSON object:
{{
  "gaps": [
    {{
      "field": "theoretical_shoulders",
      "reason": "Author mentions 'Simondon' but no details extracted",
      "query": "Gilbert Simondon philosophy individuation technical objects"
    }}
  ],
  "total_confidence": "low"
}}

Rules:
- Focus on fields where a web search could actually help (names, \
  theories, venues, methodologies — not structural fields like word_count).
- Generate specific, targeted queries, not vague ones.
- Maximum {max_queries} gaps.
"""

_SYNTHESIS_PROMPT = """\
You are an academic research analyst. Given an ArticleModel and web \
search results, update specific fields where the search results \
provide verified information.

## Current ArticleModel
```json
{article_json}
```

## Search Results
{search_context}

Return a JSON object with ONLY the fields you want to update, plus \
metadata:
{{
  "updates": {{
    "theoretical_shoulders": ["Gilbert Simondon", "Jacques Ellul"],
    "disciplinary_register_current": "philosophy of technology"
  }},
  "verification_notes": [
    "Confirmed Simondon is a philosopher of technology (Wikipedia)",
    "Added Ellul as related thinker based on search context"
  ],
  "unknowns_resolved": ["theoretical_shoulders"],
  "remaining_unknowns": ["citation_ecology_current"],
  "confidence_delta": "+0.1"
}}

Rules:
- Only update fields where search results provide EVIDENCE.
- Do NOT invent information not found in search results.
- Mark what was verified vs. what was newly discovered.
- Keep existing values if search doesn't contradict them.
"""

_VERIFICATION_PROMPT = """\
You are a fact-checker. Given a claim from an article model and web \
search results, assess whether the claim is supported, contradicted, \
or unverifiable.

## Claim
{claim}

## Search Results
{search_context}

Return a JSON object:
{{
  "supported": true/false/null,
  "evidence": "brief explanation",
  "correction": null or "corrected value if claim is wrong"
}}
"""


def enrich_article_model(
    article_dict: dict[str, Any],
    search_provider: WebSearchProvider,
    llm_provider: LLMProvider,
    depth: SearchDepth,
) -> dict[str, Any]:
    """Enrich ArticleModel dict via web search + LLM synthesis.

    Returns the (possibly updated) article dict with enrichment metadata.
    """
    if depth == SearchDepth.NONE:
        return article_dict

    logger.info("Starting web enrichment (depth=%s) via %s", depth.value, search_provider.name)

    if depth == SearchDepth.LIGHT:
        return _enrich_light(article_dict, search_provider, llm_provider)
    else:
        return _enrich_deep(article_dict, search_provider, llm_provider)


def _enrich_light(
    article: dict[str, Any],
    search: WebSearchProvider,
    llm: LLMProvider,
) -> dict[str, Any]:
    """Single-round enrichment: top gaps → search → synthesize."""
    gaps = _identify_gaps(article, llm, max_queries=_LIGHT_MAX_QUERIES)
    if not gaps:
        logger.info("No enrichment gaps found")
        article.setdefault("_enrichment", {})["status"] = "no_gaps"
        return article

    all_results = _run_searches(gaps, search, max_per_query=_LIGHT_RESULTS_PER_QUERY)
    if not all_results:
        logger.info("No search results found")
        article.setdefault("_enrichment", {})["status"] = "no_results"
        return article

    return _synthesize(article, all_results, llm, round_num=1)


def _enrich_deep(
    article: dict[str, Any],
    search: WebSearchProvider,
    llm: LLMProvider,
) -> dict[str, Any]:
    """Multi-round enrichment with verification."""
    all_enrichment_notes: list[str] = []

    for round_num in range(1, _DEEP_MAX_ROUNDS + 1):
        logger.info("Deep enrichment round %d/%d", round_num, _DEEP_MAX_ROUNDS)

        gaps = _identify_gaps(article, llm, max_queries=_DEEP_MAX_QUERIES)
        if not gaps:
            logger.info("No more gaps at round %d", round_num)
            break

        all_results = _run_searches(gaps, search, max_per_query=_DEEP_RESULTS_PER_QUERY)
        if not all_results:
            logger.info("No search results at round %d", round_num)
            break

        article = _synthesize(article, all_results, llm, round_num=round_num)

        enrichment = article.get("_enrichment", {})
        notes = enrichment.get("verification_notes", [])
        all_enrichment_notes.extend(notes)

        remaining = enrichment.get("remaining_unknowns", [])
        if not remaining:
            logger.info("All unknowns resolved at round %d", round_num)
            break

    # Verification pass: check key claims
    claims_to_verify = _extract_verifiable_claims(article)
    if claims_to_verify:
        logger.info("Verifying %d claims", len(claims_to_verify))
        for claim in claims_to_verify[:5]:  # cap at 5
            _verify_claim(article, claim, search, llm)

    enrichment = article.setdefault("_enrichment", {})
    enrichment["depth"] = "deep"
    enrichment["rounds_completed"] = round_num  # type: ignore[possibly-undefined]
    enrichment["all_notes"] = all_enrichment_notes
    return article


def _identify_gaps(
    article: dict[str, Any],
    llm: LLMProvider,
    max_queries: int,
) -> list[dict[str, str]]:
    """Use LLM to identify fields that need web search."""
    prompt = _GAP_PROMPT.format(
        article_json=json.dumps(article, ensure_ascii=False, indent=2),
        max_queries=max_queries,
    )
    messages = [
        {"role": "system", "content": "You are an extraction quality analyst."},
        {"role": "user", "content": prompt},
    ]
    try:
        response = llm.complete(messages, temperature=0.1, max_tokens=2048)
    except Exception as exc:
        logger.warning("Gap identification LLM call failed: %s", exc)
        return []

    parsed = response.parsed
    if not parsed:
        try:
            parsed = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            return []

    return parsed.get("gaps", [])


def _run_searches(
    gaps: list[dict[str, str]],
    search: WebSearchProvider,
    max_per_query: int,
) -> dict[str, list[SearchResult]]:
    """Run web searches for each gap. Returns {field: [results]}."""
    all_results: dict[str, list[SearchResult]] = {}

    for gap in gaps:
        query = gap.get("query", "")
        field = gap.get("field", "unknown")
        if not query:
            continue

        try:
            results = search.search(query, max_results=max_per_query)
            if results:
                all_results[field] = results
                logger.debug("Search '%s' → %d results", query[:60], len(results))
        except Exception as exc:
            logger.warning("Search failed for '%s': %s", query[:60], exc)

    return all_results


def _synthesize(
    article: dict[str, Any],
    search_results: dict[str, list[SearchResult]],
    llm: LLMProvider,
    round_num: int,
) -> dict[str, Any]:
    """Feed search results to LLM to update ArticleModel."""
    context_parts: list[str] = []
    for field, results in search_results.items():
        context_parts.append(f"\n### Search results for field: {field}")
        for r in results:
            context_parts.append(f"- **{r.title}** ({r.url})\n  {r.snippet}")

    search_context = "\n".join(context_parts)
    prompt = _SYNTHESIS_PROMPT.format(
        article_json=json.dumps(article, ensure_ascii=False, indent=2),
        search_context=search_context,
    )
    messages = [
        {"role": "system", "content": "You are an academic research analyst."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = llm.complete(messages, temperature=0.1, max_tokens=4096)
    except Exception as exc:
        logger.warning("Synthesis LLM call failed: %s", exc)
        return article

    parsed = response.parsed
    if not parsed:
        try:
            parsed = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            return article

    # Apply updates
    updates = parsed.get("updates", {})
    for field, value in updates.items():
        if field.startswith("_"):
            continue
        article[field] = value

    # Record enrichment metadata
    enrichment = article.setdefault("_enrichment", {})
    enrichment["depth"] = "light" if round_num == 1 else "deep"
    enrichment["round"] = round_num
    enrichment["fields_updated"] = list(updates.keys())
    enrichment["verification_notes"] = parsed.get("verification_notes", [])
    enrichment["unknowns_resolved"] = parsed.get("unknowns_resolved", [])
    enrichment["remaining_unknowns"] = parsed.get("remaining_unknowns", [])
    enrichment["search_provider"] = "web"

    # Update unknowns list
    resolved = set(parsed.get("unknowns_resolved", []))
    if resolved and "unknowns" in article:
        article["unknowns"] = [u for u in article["unknowns"] if u not in resolved]

    logger.info(
        "Enrichment round %d: updated %d fields, resolved %d unknowns",
        round_num, len(updates), len(resolved),
    )
    return article


def _extract_verifiable_claims(article: dict[str, Any]) -> list[str]:
    """Extract claims from ArticleModel that can be fact-checked."""
    claims: list[str] = []
    for shoulder in article.get("theoretical_shoulders", []):
        claims.append(f"This article builds on the work of {shoulder}")
    if article.get("disciplinary_register_current"):
        claims.append(f"This article belongs to the field of {article['disciplinary_register_current']}")
    if article.get("novelty_mode") and article["novelty_mode"] != "unknown":
        claims.append(f"The novelty mode is {article['novelty_mode']}")
    return claims


def _verify_claim(
    article: dict[str, Any],
    claim: str,
    search: WebSearchProvider,
    llm: LLMProvider,
) -> None:
    """Verify a single claim via web search."""
    try:
        results = search.search(claim, max_results=3)
    except Exception:
        return

    if not results:
        return

    context = "\n".join(f"- {r.title}: {r.snippet}" for r in results)
    prompt = _VERIFICATION_PROMPT.format(claim=claim, search_context=context)
    messages = [
        {"role": "system", "content": "You are a fact-checker."},
        {"role": "user", "content": prompt},
    ]

    try:
        response = llm.complete(messages, temperature=0.0, max_tokens=512)
    except Exception:
        return

    parsed = response.parsed
    if not parsed:
        try:
            parsed = json.loads(response.content)
        except (json.JSONDecodeError, TypeError):
            return

    verification = article.setdefault("_enrichment", {}).setdefault("verifications", [])
    verification.append({
        "claim": claim,
        "supported": parsed.get("supported"),
        "evidence": parsed.get("evidence", ""),
        "correction": parsed.get("correction"),
    })
