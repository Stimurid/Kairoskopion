"""Input Classification prompt family.

Decides which intake pipeline branch handles the pasted/uploaded text:
article (manuscript) / venue (journal page) / review_letter / unknown.

This REPLACES the prior 9-line Python keyword heuristic in
``api/cases.py::_classify_input`` which catastrophically misclassified
long humanities manuscripts as ``review_letter`` whenever the text
incidentally contained the substring "reviewer" / "revision" /
"referee" (e.g. a bibliography citing peer-review work).

Design notes
------------
- The classifier reads only the first ~6k characters of the text. That
  is enough to detect intent in 99% of real cases (a manuscript opens
  with title + abstract + intro; a venue page opens with journal name
  + ISSN + scope; a review letter opens with a salutation).
- The classifier returns ``confidence`` and ``language_detected`` so
  downstream agents can branch.
- The classifier explicitly refuses to guess when the signal is
  ambiguous: returns ``input_type = unknown`` with
  ``needs_user_choice = true``. Better an explicit prompt than a
  silent wrong route through the whole pipeline.
"""

from __future__ import annotations

INPUT_CLASSIFICATION_SYSTEM = """\
You are Input Classifier — the very first agent in Kairoskopion's intake \
pipeline.

Your job: read the opening of a text the user pasted or uploaded and \
decide which intake branch should handle it.

## Four target categories

1. **manuscript** — a draft of an academic article, conference paper, \
   book chapter, dissertation excerpt, or other research-bearing text \
   that has its own thesis and bibliography. Long-form. May be in any \
   language (Russian, English, mixed). A manuscript that contains a \
   bibliography section citing peer-review or editorial work is STILL \
   a manuscript — do not be misled by isolated keywords.
2. **venue** — a journal homepage, "About this journal" page, author \
   guidelines, special issue call, scope statement. Describes WHERE \
   one would publish, not a piece to be published. Often contains \
   ISSN, editor names, publisher, indexing, "scope", "for authors".
3. **review_letter** — a short letter from author to editor (or \
   editor to author): cover letter for submission, response to \
   reviewers, rebuttal, decision letter. Usually under 5 000 chars. \
   Starts with salutation ("Dear editor", "Уважаемый редактор"). \
   Discusses an EXISTING submission, not a piece of research.
4. **unknown** — text whose intent you cannot reliably determine \
   from the opening. Examples: a fragment of bibliography with no \
   thesis context; a scraped HTML dump that mixes navigation with \
   content; a single paragraph of free text that could be an \
   abstract OR a venue scope statement. **Prefer this over guessing.**

## Output rules

Return a JSON object with exactly these fields:

- ``input_type`` — one of: ``manuscript``, ``venue``, ``review_letter``, \
  ``unknown``. No other values.
- ``confidence`` — ``high``, ``medium``, or ``low``. ``high`` means you \
  have multiple converging signals. ``low`` means a single weak signal.
- ``needs_user_choice`` — boolean. Set to ``true`` when ``input_type`` \
  is ``unknown`` OR when ``confidence`` is ``low``. The UI will then \
  ask the user to confirm the type.
- ``language_detected`` — ``ru``, ``en``, ``mixed``, or ``unknown``. \
  Detect from the opening's dominant script and vocabulary.
- ``reasoning`` — one or two sentences in the same language as the \
  text, explaining the decision. This is shown to the user.

## Anti-rules

- Do NOT use the presence of single English words like "reviewer", \
  "referee", "revision" in a long text as a review_letter signal — \
  they appear constantly in citations of peer-review research.
- Do NOT classify a Russian-language academic essay as ``venue`` just \
  because it cites a journal name in its bibliography.
- Do NOT default to ``manuscript`` when truly unsure. Use ``unknown``.
- Do NOT invent content. Your output is metadata about the input, \
  never a summary of it.
"""

INPUT_CLASSIFICATION_USER_TEMPLATE = """\
Classify the following text. Read carefully and apply the rules from \
your system prompt.

---
TEXT (length: {full_length} characters; you are seeing the opening only)
---

{text_opening}

---

Return the JSON object now.
"""

INPUT_CLASSIFICATION_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "input_type": {
            "type": "string",
            "enum": ["manuscript", "venue", "review_letter", "unknown"],
        },
        "confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"],
        },
        "needs_user_choice": {"type": "boolean"},
        "language_detected": {
            "type": "string",
            "enum": ["ru", "en", "mixed", "unknown"],
        },
        "reasoning": {"type": "string"},
    },
    "required": [
        "input_type",
        "confidence",
        "needs_user_choice",
        "language_detected",
        "reasoning",
    ],
    "additionalProperties": False,
}


def validate_input_classification(data: dict) -> list[str]:
    """Return list of soft warnings; does not gate fallback."""
    warnings: list[str] = []
    itype = data.get("input_type")
    conf = data.get("confidence")
    needs_choice = data.get("needs_user_choice")

    # Invariant: unknown OR low must trigger needs_user_choice
    if (itype == "unknown" or conf == "low") and needs_choice is not True:
        warnings.append(
            "input_type=unknown or confidence=low must set needs_user_choice=true"
        )

    reasoning = data.get("reasoning") or ""
    if len(reasoning.strip()) < 8:
        warnings.append("reasoning is suspiciously short — possible model laziness")

    return warnings


INPUT_CLASSIFICATION_FAMILY = {
    "family_id": "input_classification_v1",
    "agent_role_id": "input_classifier",
    "version": "1.0.0",
    "system_prompt": INPUT_CLASSIFICATION_SYSTEM,
    "user_prompt_template": INPUT_CLASSIFICATION_USER_TEMPLATE,
    "output_schema": INPUT_CLASSIFICATION_OUTPUT_SCHEMA,
    "validator": validate_input_classification,
}
