"""Input Classification prompt family.

Decides which intake pipeline branch handles the pasted/uploaded text:
manuscript / abstract / bibliography / journal_or_venue / review_letter
/ field_notes / mixed / unknown.

Why this list (intake-routing-and-model-strategy pass)
------------------------------------------------------
The previous 4-value set (manuscript / venue / review_letter / unknown)
collapsed three real-world failure modes into wrong routes:

1. A long Russian conceptual essay with a bibliography section was
   classified as ``review_letter`` because the bibliography happened to
   cite peer-review work (fixed in commit 3 of B0/B1).
2. Field notes / theses (тезисы) / a raw conceptual dump were
   classified as ``article`` and silently routed through the ArticleModeler
   pipeline, producing meaningless "article" output for non-article text.
3. A standalone bibliography was indistinguishable from a manuscript-
   with-bibliography — same downstream pipeline ran for both.

This prompt distinguishes **document FUNCTION** from academic vocabulary.
A document with a bibliography is not a bibliography; a document with
academic words is not necessarily an article.

Routing convention (consumed by ``api/cases.py::intake_text``):
- ``manuscript`` / ``article`` / ``abstract`` → ArticleModeler pipeline
- ``journal_or_venue`` (and legacy ``venue``) → venue investigation
- everything else → no pipeline; UI prompts the user to pick a type chip
  with ``needs_user_choice=true``.

The classifier MUST set ``needs_user_choice=true`` whenever it returns
``unknown`` / ``mixed`` / ``field_notes`` / ``bibliography`` OR whenever
confidence is ``low``. Better an explicit prompt than silent wrong route
through the whole pipeline.
"""

from __future__ import annotations

INPUT_CLASSIFICATION_SYSTEM = """\
You are Input Classifier — the first agent in Kairoskopion's intake \
pipeline. Your job is to read the opening of a text the user pasted or \
uploaded and decide which intake branch should handle it.

## Eight target categories

1. **manuscript** — a draft of an academic article, conference paper, \
   book chapter, or dissertation excerpt that has its OWN thesis, OWN \
   sections (introduction / argument / conclusion or equivalent), and \
   makes an authorial claim. Long-form. Any language. The presence of a \
   bibliography or citations does NOT change the classification — most \
   manuscripts have a bibliography section.

2. **article** — same as ``manuscript`` for routing purposes. Use \
   ``article`` when the text is clearly publication-ready (has title + \
   abstract + sections) and ``manuscript`` when it looks like a working \
   draft. Both route to the same ArticleModeler pipeline.

3. **abstract** — a standalone abstract or summary (typically 80–300 \
   words) presented WITHOUT the full article body. Has a thesis but no \
   developed argument. Use this only when the input is clearly \
   abstract-only, not a short article.

4. **bibliography** — a STANDALONE list of references / citations / \
   reading list with NO authorial argument, NO surrounding manuscript. \
   The text is essentially ``Author, A. (Year). Title. Source.`` lines \
   from start to end. A bibliography section INSIDE an article is NOT \
   this category — that's ``manuscript`` / ``article``.

5. **journal_or_venue** — a journal homepage, "About this journal" \
   page, author guidelines, special issue call, scope statement, or \
   editorial policy. Describes WHERE one would publish, not a piece to \
   be published. Often contains ISSN, editor names, publisher, \
   indexing, "scope", "for authors", "submission instructions".

6. **review_letter** — a short letter from author to editor (or editor \
   to author): cover letter for submission, response to reviewers, \
   rebuttal, decision letter. Usually under 5 000 chars. Discusses an \
   EXISTING submission, not new research. Starts with a salutation or \
   addresses an editor/reviewer by role. The presence of the word \
   "reviewer" in a long manuscript is NOT enough — that word appears \
   constantly in citations of peer-review research.

7. **field_notes** — research notes, theses (тезисы), raw conceptual \
   dump, lecture notes, working ideas, observations, fragments. May be \
   academic in vocabulary, may cite sources, may be sophisticated, but \
   does NOT have the structure of a publishable article (no clear \
   abstract / introduction / argument / conclusion arc; reads as \
   notes-to-self or staged thinking). Russian "тезисы" and "заметки" \
   typically fall here. **Critical:** academic style is NOT enough to \
   make something an article. Field notes can be academic, conceptual, \
   cited, and still not an article.

8. **mixed** — text that combines two or more types meaningfully \
   (e.g. article draft + author's notes about it; cover letter \
   prepended to a manuscript; venue scope + an article). Use this \
   when neither component is clearly dominant.

9. **unknown** — text whose intent you cannot reliably determine. \
   Examples: a fragment of bibliography with no thesis context; a \
   scraped HTML dump that mixes navigation with content; a single \
   paragraph that could be an abstract OR a venue scope statement; \
   gibberish. **Prefer this over guessing.**

## Disambiguation rules

- A manuscript with a bibliography section is **manuscript / article**, \
  never **bibliography**. The criterion for ``bibliography`` is "this \
  text is ONLY a list of references."
- Citations and references INSIDE a body of authorial argument do NOT \
  imply article — they support the argument. Look for the argument \
  structure itself: title → abstract → sections → claims → conclusion.
- Academic vocabulary alone does NOT make something an article. Russian \
  philosophical notes без формальной структуры → ``field_notes`` or \
  ``mixed``, NOT ``article``.
- If the input is short and could go either way (e.g. 200 words that \
  could be an abstract or could be opening of an article), pick the \
  closer category and set ``confidence=low`` + ``needs_user_choice=true``.
- For a chat-style instruction like "найди мне журнал под эту статью", \
  IF the input is just the instruction without the article — return \
  ``unknown`` + ``needs_user_choice=true``. The system will ask the user \
  to provide the actual article.

## Output rules

Return a JSON object with exactly these fields:

- ``input_type`` — one of: ``manuscript``, ``article``, ``abstract``, \
  ``bibliography``, ``journal_or_venue``, ``review_letter``, \
  ``field_notes``, ``mixed``, ``unknown``. No other values.
- ``confidence`` — ``high``, ``medium``, or ``low``. ``high`` means \
  multiple converging signals (title + abstract + body sections + bib \
  → article). ``low`` means a single weak signal or genuinely ambiguous.
- ``needs_user_choice`` — boolean. MUST be ``true`` when ``input_type`` \
  is ``unknown`` / ``mixed`` / ``bibliography`` / ``field_notes`` / \
  ``review_letter`` OR when ``confidence`` is ``low``. The UI then asks \
  the user to confirm.
- ``language_detected`` — ``ru``, ``en``, ``mixed``, or ``unknown``.
- ``reasoning`` — one or two sentences in the same language as the \
  text, naming the specific structural signals you read (title? \
  abstract? sections? thesis? bibliography pattern? notes style?). \
  This is shown to the user.

## Anti-rules

- Do NOT default to ``article`` / ``manuscript`` when truly unsure. Use \
  ``unknown`` or ``field_notes`` or ``mixed``.
- Do NOT classify a bibliography section that is part of an article as \
  ``bibliography``.
- Do NOT use single English words like "reviewer", "referee", \
  "revision" in a long text as a ``review_letter`` signal.
- Do NOT classify long well-cited Russian philosophical notes as \
  ``article`` purely because they're academic. Look for argument \
  structure.
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
            "enum": [
                "manuscript", "article", "abstract",
                "bibliography", "journal_or_venue", "review_letter",
                "field_notes", "mixed", "unknown",
            ],
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


# Types where the system has no automated downstream pipeline; user must
# pick a chip or paste different text. Routing also lives here (mirrored
# in api/cases.py::intake_text).
NEEDS_USER_CHOICE_TYPES = frozenset({
    "unknown",
    "mixed",
    "bibliography",
    "field_notes",
    "review_letter",
})

# Types that route into the article-modeling pipeline.
ARTICLE_PIPELINE_TYPES = frozenset({"article", "manuscript", "abstract"})

# Types that route into the venue-investigation pipeline.
VENUE_PIPELINE_TYPES = frozenset({"journal_or_venue", "venue"})


def validate_input_classification(data: dict) -> list[str]:
    """Return list of soft warnings; does not gate fallback."""
    warnings: list[str] = []
    itype = data.get("input_type")
    conf = data.get("confidence")
    needs_choice = data.get("needs_user_choice")

    # Invariant: any type without an automated pipeline + low confidence
    # MUST set needs_user_choice
    if itype in NEEDS_USER_CHOICE_TYPES and needs_choice is not True:
        warnings.append(
            f"input_type={itype} must set needs_user_choice=true "
            f"(no automated pipeline for this type)"
        )
    if conf == "low" and needs_choice is not True:
        warnings.append(
            "confidence=low must set needs_user_choice=true"
        )

    reasoning = data.get("reasoning") or ""
    if len(reasoning.strip()) < 8:
        warnings.append(
            "reasoning is suspiciously short — possible model laziness"
        )

    return warnings


INPUT_CLASSIFICATION_FAMILY = {
    "family_id": "input_classification_v2",
    "agent_role_id": "input_classifier",
    "version": "2.0.0",
    "system_prompt": INPUT_CLASSIFICATION_SYSTEM,
    "user_prompt_template": INPUT_CLASSIFICATION_USER_TEMPLATE,
    "output_schema": INPUT_CLASSIFICATION_OUTPUT_SCHEMA,
    "validator": validate_input_classification,
}
