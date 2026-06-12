"""Scenario Interview prompt family (spec §69.2).

Builds SubmissionScenario from user constraints: timeline, language,
target discipline, career goals, venue preferences, budget, co-author
requirements, and any hard constraints the user wants to impose.
"""

from __future__ import annotations

FAMILY_ID = "scenario_interview_v1"
FAMILY_NAME = "Scenario Interview"
VERSION = "1.0.0"
PURPOSE = (
    "Elicit and structure the user's submission constraints into a "
    "SubmissionScenario: timeline, language, target discipline, career "
    "goals, venue preferences, budget, co-author requirements."
)

INPUT_CONTRACT = {
    "user_brief": "Free-text description of submission goals and constraints",
    "article_model": "Optional ArticleModel dict for context",
}
OUTPUT_CONTRACT = {
    "submission_scenario": "SubmissionScenario dict with all constraint fields",
    "unknowns": "List of constraints user did not specify",
    "questions_for_user": "Follow-up questions to refine scenario",
}

SYSTEM_PROMPT = """\
You are Scenario Interviewer — a specialized analytical role within \
Kairoskopion, an evidence-first publication-positioning system.

Your task: given a user's free-text description of their submission \
goals and constraints (and optionally an ArticleModel), produce a \
structured SubmissionScenario that captures everything Kairoskopion \
needs to evaluate venue fit, plan adaptations, and assess risks.

## Fields to extract

1. **timeline** — submission deadline, desired publication date, \
   urgency level (immediate / 3-month / 6-month / no-rush / unknown)
2. **language_constraint** — required language(s) for submission, \
   whether translation is acceptable, bilingual options
3. **target_discipline** — preferred disciplinary home(s) if any, \
   or "open to recommendations"
4. **career_goals** — what the user hopes to achieve: tenure track, \
   PhD defense, visibility, citation, impact factor, Scopus/WoS \
   indexing, reaching a specific audience
5. **venue_preferences** — any named venues, venue types, \
   exclusions, indexing requirements
6. **co_author_constraints** — number of co-authors, affiliation \
   requirements, who needs to approve
7. **budget** — open access fees, page charges, whether funded
8. **hard_constraints** — non-negotiable requirements (e.g., must \
   be Scopus Q1, must be in English, must accept < 8000 words)
9. **soft_preferences** — nice-to-have but negotiable

## Rules

- Extract what the user says. Do NOT invent constraints they did not mention.
- Mark unspecified fields as unknown.
- If the user's brief is too vague to build a useful scenario, \
  generate specific follow-up questions.
- Do NOT recommend venues at this stage.
- Do NOT assess fit — that is a separate agent's job.
"""

USER_TEMPLATE = """\
Build a submission scenario from this user brief.

## User brief
{user_brief}

## ArticleModel (may be empty)
```json
{article_json}
```

Return a JSON object with the structured scenario and follow-up questions.
"""

OUTPUT_SCHEMA: dict = {
    "title": "ScenarioInterviewResult",
    "type": "object",
    "properties": {
        "timeline": {"type": ["string", "null"]},
        "urgency": {
            "type": "string",
            "enum": ["immediate", "3_month", "6_month", "no_rush", "unknown"],
        },
        "language_constraint": {"type": ["string", "null"]},
        "target_disciplines": {"type": "array", "items": {"type": "string"}},
        "career_goals": {"type": "array", "items": {"type": "string"}},
        "venue_preferences": {"type": "array", "items": {"type": "string"}},
        "venue_exclusions": {"type": "array", "items": {"type": "string"}},
        "indexing_requirements": {"type": "array", "items": {"type": "string"}},
        "co_author_count": {"type": ["integer", "null"]},
        "budget_notes": {"type": ["string", "null"]},
        "hard_constraints": {"type": "array", "items": {"type": "string"}},
        "soft_preferences": {"type": "array", "items": {"type": "string"}},
        "unknowns": {"type": "array", "items": {"type": "string"}},
        "questions_for_user": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
    },
    "required": ["unknowns", "questions_for_user", "confidence"],
    "additionalProperties": False,
}

FORBIDDEN_BEHAVIORS = [
    "Do not recommend venues",
    "Do not assess fit",
    "Do not invent constraints the user did not mention",
    "Do not guess timeline if not stated",
]

EVIDENCE_REQUIREMENTS = [
    "All constraints must trace to user brief text",
    "Unspecified constraints must be marked unknown",
]

UNKNOWN_HANDLING = "mark_unknown_and_ask"
VALIDATION_NOTES = "Check that unknowns list is not empty for short briefs"


def validate_scenario_interview(data: dict) -> list[str]:
    warnings: list[str] = []
    if not data.get("unknowns"):
        warnings.append("No unknowns — unlikely from a user brief")
    if not data.get("questions_for_user") and not data.get("hard_constraints"):
        warnings.append("No follow-up questions and no hard constraints — brief may be too vague")
    return warnings


SCENARIO_INTERVIEW_FAMILY = {
    "family_id": FAMILY_ID,
    "agent_role_id": "scenario_prober",
    "version": VERSION,
    "system_prompt": SYSTEM_PROMPT,
    "user_prompt_template": USER_TEMPLATE,
    "output_schema": OUTPUT_SCHEMA,
    "validator": validate_scenario_interview,
}
