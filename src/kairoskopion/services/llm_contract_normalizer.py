"""Round III-E: structural shape normalizer for LLM semantic organs.

Sonnet does not always wrap its output under the exact top-level key
that our schemas declared. It may return:

  {"risks": [...]}              instead of {"risk_items": [...]}
  {"changes": [...]}            instead of {"actions": [...]}
  {"gaps": [...]}               instead of {"tradition_gaps": [...]}
  {"risk_report": {"risk_items": [...]}}   one-level nested envelope
  {"plan": {"actions": [...]}}             same idea
  [{...}, {...}]                           bare list at top level

The doctrine: container normalization is allowed (mechanical look-up
of a list under alternative known keys); semantic invention is not.
This helper only does the *container* search — it never decides what
a risk/change/gap means.

Pure function. No I/O. Returns the located list, the matched key path,
and a structural diagnostic.
"""

from __future__ import annotations

from typing import Any


# Alias sets per organ — ordered by preference (canonical first).
RISK_ITEM_ALIASES: tuple[str, ...] = (
    "risk_items",
    "risks",
    "items",
    "risk_list",
    "risk_report",
    "report",
    "analysis",
    "result",
)

REWRITE_ITEM_ALIASES: tuple[str, ...] = (
    "actions",
    "changes",
    "rewrite_actions",
    "rewrite_changes",
    "plan",
    "rewrite_plan",
    "items",
)

CITATION_BRIDGE_ALIASES: tuple[str, ...] = (
    "bridge_references_needed",
    "bridge_references",
    "bridges",
    "missing_bridge_categories",
)
CITATION_GAP_ALIASES: tuple[str, ...] = (
    "tradition_gaps",
    "citation_gap_categories",
    "gaps",
)
CITATION_TASK_ALIASES: tuple[str, ...] = (
    "recommended_reference_search_tasks",
    "source_work_tasks",
    "search_tasks",
    "tasks",
    "verification_tasks",
)
CITATION_RISK_ALIASES: tuple[str, ...] = (
    "risk_items",
    "risks",
)


def find_list_under_aliases(
    parsed: Any,
    aliases: tuple[str, ...],
    *,
    max_depth: int = 2,
) -> tuple[list[Any] | None, str | None]:
    """Search for a list under one of the alias keys, optionally
    nested up to ``max_depth`` levels.

    Returns (list, dotted_key_path) on success, (None, None) otherwise.

    Pure container lookup. Does not interpret content.
    """
    if isinstance(parsed, list):
        # Bare list at top level
        return parsed, "<root>"
    if not isinstance(parsed, dict):
        return None, None

    # Try each alias at top level first
    for k in aliases:
        if k in parsed and isinstance(parsed[k], list):
            return parsed[k], k
    # Try one nested level under envelope keys
    if max_depth >= 1:
        for env_key, env_val in parsed.items():
            if not isinstance(env_val, dict):
                continue
            for k in aliases:
                if k in env_val and isinstance(env_val[k], list):
                    return env_val[k], f"{env_key}.{k}"
    return None, None


def shape_summary(parsed: Any, max_keys: int = 12) -> dict[str, Any]:
    """Return a redacted shape summary of parsed LLM output for
    diagnostics. Contains only structural metadata, never values.
    """
    if parsed is None:
        return {"top_level_type": "null", "top_level_keys": []}
    if isinstance(parsed, list):
        return {
            "top_level_type": "list",
            "top_level_length": len(parsed),
            "item_0_type": type(parsed[0]).__name__ if parsed else None,
        }
    if isinstance(parsed, dict):
        keys = list(parsed.keys())[:max_keys]
        return {
            "top_level_type": "object",
            "top_level_keys": keys,
            "top_level_key_count": len(parsed),
        }
    return {"top_level_type": type(parsed).__name__}
