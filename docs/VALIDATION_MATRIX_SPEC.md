# Validation Matrix Spec — Arbitrary Manuscript × Venue

**Created:** 2026-06-10
**Base:** `v0.2.0-alpha-rc4` at `b8a94bb`
**Purpose:** Prove Kairoskopion behaves as a general evidence-first article-to-venue
trajectory engine, not as a system tuned to one trial case or one uploaded manuscript.

## Scope

These are **generic behavioral validation cases**, not Logos cases.
All fixtures are synthetic and non-private.
The goal is behavioral validation, not realistic journal discovery.

## Acceptance Matrix

### Case 1 — Good fit

- **Manuscript:** English theoretical/conceptual article on philosophy of AI.
- **Venue:** English-language philosophy/social-theory venue with matching scope.
- **Expected:**
  - No language blocker (`language_register` is `strong` or `medium`).
  - Discipline is not `unknown` if scope and article match.
  - Genre is not `weak` (venue accepts theoretical essays).
  - Submission may still require file updates (compliance items).

### Case 2 — Language blocker

- **Manuscript:** English-language article.
- **Venue:** Russian-only humanities venue with explicit Russian-only language policy.
- **Expected:**
  - `language_register` axis is `bad`.
  - Mismatch map contains a blocking language/register mismatch.
  - Risk report contains `desk_reject_risk` or equivalent blocking risk.
  - Submission pack readiness is `not_ready`.
  - Rewrite plan suggests translation/adaptation.

### Case 3 — Method/genre blocker

- **Manuscript:** Empirical social-science article with methods section, data,
  and quantitative references.
- **Venue:** Empirical social-science venue requiring quantitative methods.
- **Cross-check:** Run the theoretical manuscript against this empirical venue.
- **Expected:**
  - Theoretical manuscript at empirical venue: method and/or genre mismatch appears.
  - Empirical manuscript at empirical venue: method axis is `strong` or `medium`.
  - Language axis remains acceptable in both (both English).

### Case 4 — Missing evidence

- **Manuscript:** Any English article.
- **Venue:** Venue profile with most fields explicitly UNKNOWN.
- **Expected:**
  - Many unknowns preserved in fit assessment.
  - Rewrite plan contains conditional evidence-collection actions.
  - System does not invent requirements from missing data.
  - Overall fit label is cautious (`not_enough_data` or equivalent).

### Case 5 — Formal compliance

- **Manuscript:** Any English article.
- **Venue:** Venue with both abstract word limit (200-250 words) and article body
  word limit (6000-12000 words) explicitly stated.
- **Expected:**
  - Abstract limit is not applied as article body limit.
  - Article word limit applies to manuscript body.
  - Compliance checklist distinguishes abstract vs body items.

### Case 6 — Citation ecology weakness

- **Manuscript:** Theoretical article with only 3 references (thin bibliography).
- **Venue:** Philosophy venue expecting substantial citations.
- **Expected:**
  - `citation_ecology` axis is `weak`.
  - Risk report contains citation-related risk.
  - A manuscript with 10+ references at the same venue should NOT get the
    same citation weakness.

## Non-goals

- This is not a Logos pass.
- This is not a venue discovery or journal crawler pass.
- This is not an article adaptation or rewrite pass.
- No live external adapters. No LLM calls. No mass web search.
