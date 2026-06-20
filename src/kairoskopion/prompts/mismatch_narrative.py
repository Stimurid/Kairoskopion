"""Mismatch Narrative prompt family.

Replaces the deterministic placeholder for ``venue_side`` and the
static-template ``possible_actions`` in
``services/mismatch_mapping.py``. The previous deterministic code
emitted ``venue_side=""`` + an explicit unknown for every mismatch
axis — honest, but useless to the operator who wants to know *what*
the venue actually expects.

This agent reads the (already-computed) article model, venue model,
and the per-axis fit values, and generates a narrative for EVERY
mismatch in one batch call:

* ``venue_side`` — concrete statement about what the venue expects on
  this axis, grounded in venue.scope_summary / article_types_supported
  / regime / language_policy.
* ``description`` — short narrative of the mismatch (what's misaligned
  and why it matters).
* ``possible_actions`` — 1–3 article-grounded actions the author could
  take. NOT generic templates ("Reframe introduction…") but actions
  rooted in the article's specific claims/method/genre and the venue's
  specific expectations.

Hard constraints encoded in the system prompt:
- Do NOT invent venue expectations the venue text does not support.
  If the venue doesn't say anything about method, the venue_side must
  be ``"unknown — venue text doesn't specify"`` and possible_actions
  must include "ask editor".
- Do NOT recommend rewriting the manuscript whole. Actions are
  surgical: section-level, claim-level, citation-level.
- Do NOT suggest fake citations. Bibliography moves must be of the
  form "add citation to <named tradition or thinker>" not
  "cite <Smith 2024>".
- Do NOT collapse the mismatch severity. If axis value is "weak", say
  so; do not soften.
- Do NOT use raw LLM provider output (the agent strips it before
  returning).
"""

from __future__ import annotations

MISMATCH_NARRATIVE_SYSTEM = """\
You are Mismatch Narrator — a writing-and-editorial-judgment agent in \
Kairoskopion's fit-assessment pipeline.

Your input: a FitAssessment (per-axis labels: strong/medium/weak/bad/\
unknown) for an Article × Venue pairing, plus the Article and Venue \
models that produced it.

Your job: for EVERY mismatch (any axis with value != "strong"), generate:

1. **venue_side** — a concrete 1-sentence statement of what the venue \
   expects on this axis, grounded in venue.scope_summary, \
   article_types_supported, publication regime, language_policy, or \
   review process. If the venue text does NOT specify expectations on \
   this axis, say so honestly: "unknown — venue text does not specify".

2. **description** — a 1–2 sentence narrative naming WHAT is misaligned \
   between the article side and the venue side, and WHY it matters for \
   the operator's decision. Concrete, not boilerplate.

3. **possible_actions** — 1–3 article-grounded actions, each phrased \
   as an imperative. Anchored to the article's claims, sections, \
   method, or bibliography. NOT generic templates.

## Output rules

Return a JSON object with one key:
- ``narratives`` — list of objects, one per input mismatch. Each:
  ``{"axis": str, "venue_side": str, "description": str, "possible_actions": [str, str?, str?]}``

The list must cover EVERY axis in the input mismatch list. If an axis \
genuinely has nothing to say (e.g. value="unknown" and venue text is \
empty), still include it with venue_side="unknown — venue text does \
not specify" and possible_actions=["Provide more venue text or \
contact the editor for explicit expectations."].

## Anti-rules

- Do NOT invent venue expectations the venue text does not support. \
  If venue.scope_summary doesn't mention method, do NOT claim "venue \
  prefers empirical work" — say "unknown".
- Do NOT recommend a wholesale manuscript rewrite. Each action is \
  surgical: a section, a claim, a citation, a paragraph reframe.
- Do NOT invent specific citations. Allowed forms: "Add a citation to \
  the postphenomenological tradition (Verbeek, Ihde)" — naming the \
  tradition. NOT allowed: "Cite Smith 2024" (fake reference).
- Do NOT soften the severity of a "weak" or "bad" axis. If method is \
  weak because article is conceptual and venue is empirical, say so.
- Do NOT translate the article into a different genre to manufacture \
  fit. If the article is a theoretical essay and the venue wants \
  empirical research, that mismatch is real — flag it; don't \
  fictionally restructure the article.
- Do NOT include any meta-commentary about the LLM or prompt. Output \
  is only the JSON.

## Voice

Russian if the article language is Russian; English otherwise. \
Concise — operator is reading 12 cards.
"""

MISMATCH_NARRATIVE_USER_TEMPLATE = """\
Below are the inputs. Generate venue_side + description + \
possible_actions for every mismatch axis. Return the JSON object.

## Article (compact)
{article_compact}

## Venue (compact)
{venue_compact}

## Mismatch axes (one per object)
{mismatches_compact}
"""

MISMATCH_NARRATIVE_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "narratives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "axis": {"type": "string"},
                    "venue_side": {"type": "string"},
                    "description": {"type": "string"},
                    "possible_actions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "maxItems": 5,
                    },
                },
                "required": ["axis", "venue_side", "description", "possible_actions"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["narratives"],
    "additionalProperties": False,
}


def validate_mismatch_narrative(data: dict) -> list[str]:
    """Soft warnings only — does not gate fallback."""
    warnings: list[str] = []
    if not isinstance(data.get("narratives"), list):
        warnings.append("missing or non-list narratives")
        return warnings
    for i, n in enumerate(data["narratives"]):
        if not isinstance(n, dict):
            warnings.append(f"narrative[{i}] not an object")
            continue
        vs = n.get("venue_side") or ""
        if len(vs.strip()) < 5:
            warnings.append(f"narrative[{i}] venue_side suspiciously short")
        actions = n.get("possible_actions") or []
        if not actions:
            warnings.append(f"narrative[{i}] has no actions")
        # Anti-leak: model must not echo raw prompt or include
        # meta-strings.
        for s in (n.get("description", ""), vs):
            if "raw_output_ref" in s or "Traceback" in s:
                warnings.append(f"narrative[{i}] leaked internal markers")
    return warnings


MISMATCH_NARRATIVE_FAMILY = {
    "family_id": "mismatch_narrative_v1",
    "agent_role_id": "mismatch_narrator",
    "version": "1.0.0",
    "system_prompt": MISMATCH_NARRATIVE_SYSTEM,
    "user_prompt_template": MISMATCH_NARRATIVE_USER_TEMPLATE,
    "output_schema": MISMATCH_NARRATIVE_OUTPUT_SCHEMA,
    "validator": validate_mismatch_narrative,
}
