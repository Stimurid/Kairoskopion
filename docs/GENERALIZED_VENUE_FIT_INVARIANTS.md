# Generalized Venue-Fit Invariants

**Purpose:** Product-level invariants extracted from trial experience. These are
general principles that apply to ANY manuscript-venue pair, not to any specific
journal or article.

**Anti-overfitting warning:** These invariants were discovered through a
target-known trial (Logos journal). They must NOT be interpreted as
Logos-specific rules. Every invariant below applies to arbitrary venues and
arbitrary manuscripts. If an invariant only holds for one journal, it is not
an invariant — it is a bug.

---

## Invariant 1 — Evidence upgrade can change verdict

An UNKNOWN venue seed may yield `possible_but_costly` because the system
cannot detect blocking mismatches without evidence. When real evidence is
collected and the pipeline reruns, the verdict may:

- **Downgrade** (e.g., language policy mismatch surfaces → `poor_fit`)
- **Upgrade** (e.g., venue scope aligns better than guessed → `good_fit`)
- **Remain unchanged** (evidence confirms initial heuristic guess)

A verdict shift after evidence upgrade is **expected behavior**, not a system
failure. The system is designed to produce increasingly accurate assessments
as evidence quality improves.

**Corollary:** A `possible_but_costly` verdict on an UNKNOWN seed should
never be interpreted as "submission is viable." It means "we don't know enough
to say it's bad."

## Invariant 2 — Missing venue evidence is not a manuscript defect

The system must distinguish four categories of problem:

| Category | Example | Who fixes it |
|----------|---------|-------------|
| **Manuscript weakness** | No abstract, weak bibliography | Author |
| **Venue mismatch** | Wrong language, wrong discipline | Author (venue choice) |
| **Missing evidence** | Word limit unknown, AI policy unknown | Evidence collector |
| **Tool defect** | Parser fails on numbered lists | Developer |

A missing venue word limit must produce `UNKNOWN` on the formal_compliance axis,
not a manufactured compliance failure. Missing evidence must never be silently
converted into a negative verdict about the manuscript.

## Invariant 3 — Language policy is a generic blocker

Any manuscript language vs venue body-language mismatch can block submission.
This is not specific to any language pair.

Rules:
- Metadata language requirements (bilingual abstracts, English keywords for
  indexing) must NOT be mistaken for article-body-language acceptance.
- "Metadata must be in English" does NOT mean the journal accepts English articles.
- If the venue says "Russian-language journal" and requires "metadata in English,"
  the venue accepts Russian articles with English metadata — not English articles.
- The same logic applies to any language: a Chinese journal requiring English
  abstracts does not accept English articles.
- If body-language policy is genuinely ambiguous, mark as UNKNOWN — do not guess.

## Invariant 4 — Submission readiness requires resolved blocking requirements

A submission pack cannot be marked `ready` if any of the following are unresolved
and blocking:

| Requirement | Blocking if |
|-------------|-------------|
| Language policy | Manuscript language ≠ venue body language |
| Article type | Venue does not list manuscript's genre |
| Word limit | Manuscript exceeds stated limit |
| Citation style | Unknown — conditional (collect guidelines) |
| Peer review / anonymization | Double-blind but manuscript not anonymized |
| Ethics / data / AI policy | Required but missing from manuscript |
| Author eligibility | Venue restricts by affiliation/geography |
| File requirements | Wrong format, missing components |

If a requirement is UNKNOWN (not enough venue evidence), the submission pack
should be `needs_file_update` (action items exist), not `ready`.

## Invariant 5 — RewritePlan must produce conditional actions under incomplete evidence

When venue evidence is incomplete:

- **Proposed actions** address known mismatches (e.g., weak topic overlap → reframe intro)
- **Conditional actions** address unknown axes (e.g., unknown citation style → collect guidelines)

Conditional actions must:
- Use `status: "conditional"` to distinguish from proposed changes
- Recommend evidence collection, not invented requirements
- Not fabricate venue policies that were not found
- Include axis-specific guidance (what to look for, where to look)

A rewrite plan with only proposed actions and no conditionals under incomplete
evidence is a system bug — it implies false certainty.

## Invariant 6 — Venue profile must distinguish evidence quality

Every claim in a VenueModel must carry implicit or explicit evidence status:

| Status | Meaning |
|--------|---------|
| FACT_FROM_OFFICIAL_SOURCE | From the venue's own website/guidelines |
| EXTERNAL_CLAIM | From indexers, Wikipedia, third-party databases |
| INFERENCE | Assembled from multiple sources, no single authoritative statement |
| UNKNOWN | Not found in any source |
| CONFLICTING_OR_STALE | Sources disagree or data may be outdated |

The system must not treat EXTERNAL_CLAIM as FACT_FROM_OFFICIAL_SOURCE.
Wikipedia claims about indexing are not equivalent to the venue's own
indexing page.

## Invariant 7 — Trial reports must separate code defects from evidence gaps

A trial report must clearly state:

1. **What changed** after better evidence (verdict shift, new mismatches, new risks)
2. **What remains unknown** (axes still unassessed, policies still missing)
3. **What is a code defect** (parser bug, wrong extraction logic)
4. **What is an evidence gap** (information not available from any source)

A trial that surfaces a code defect (e.g., language policy parser confusing
metadata with body language) is a product improvement opportunity.
A trial that surfaces an evidence gap (e.g., venue word limit not published)
is an information boundary — the system correctly marks it UNKNOWN.

---

## How to use these invariants

- **Before adding a new extraction rule:** Does it generalize to arbitrary venues,
  or does it only fix one trial case? If the latter, it may be overfitting.
- **Before interpreting a verdict:** Is the verdict based on evidence or on absence
  of evidence? A poor_fit with evidence is more reliable than a possible_but_costly
  without evidence.
- **Before reporting a defect:** Is it a code bug (parser fails), a data gap
  (venue doesn't publish the info), or a design limitation (system can't assess
  this axis without external API)?
