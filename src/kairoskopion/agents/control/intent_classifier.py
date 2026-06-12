"""Intent Classifier — determines what the user wants to do.

Deterministic: keyword/pattern matching on user input.
LLM: structured intent classification.
"""

from __future__ import annotations

import re

from ..base_shell import service_output
from ..contract import AgentInput, AgentOutput, AgentRole
from ...llm.provider import LLMProvider

_INTENT_PATTERNS = {
    "analyze_article": r"(?i)(analyz|model|profil|assess)\b.*\b(article|manuscript|draft|paper)",
    "venue_search": r"(?i)(find|search|discover|recommend)\b.*\b(venue|journal|conference)",
    "fit_check": r"(?i)(fit|match|suit|compar)\b.*\b(venue|journal)",
    "submission_prep": r"(?i)(submit|submission|pack|checklist|compliance)",
    "review_response": r"(?i)(review|revision|rebuttal|reviewer)",
    "status": r"(?i)(status|progress|state|overview)",
}


class IntentClassifierAgent(AgentRole):
    role_id = "intent_classifier"

    def execute(self, inp: AgentInput, provider: LLMProvider) -> AgentOutput:
        return self.execute_deterministic(inp)

    def execute_deterministic(self, inp: AgentInput) -> AgentOutput:
        text = (inp.raw_text or "").strip()
        if not text:
            return service_output(
                "Intent", {"intent": "unknown", "text": ""},
                unknowns=["No input text provided"],
                confidence="none",
            )

        matches = []
        for intent, pattern in _INTENT_PATTERNS.items():
            if re.search(pattern, text):
                matches.append(intent)

        chosen = matches[0] if matches else "unknown"
        return service_output(
            "Intent",
            {"intent": chosen, "all_matches": matches, "text": text[:200]},
            confidence="medium" if matches else "low",
            unknowns=[] if matches else ["Could not classify intent from text"],
            trace_notes=[f"pattern_match: {chosen}"],
        )
