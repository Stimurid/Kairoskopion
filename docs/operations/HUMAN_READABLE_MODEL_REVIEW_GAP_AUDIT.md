# Human-readable model review — gap audit

**Date:** 2026-06-15
**Trigger:** Mavrinsky reviewed his golden ArticleModel pass and could
not understand it. JSON output is unreadable for a non-technical
humanities author.

## A. What canonical spec requires

`docs/KAIRON_TECHNICAL_SPEC_FOR_CLAUDE_v0_1.md`:

- **§10 (line 1809–1818)** — *"Human-readable Vault cards should be
  generated for: ArticleModel; VenueModel; FitAssessment; RewritePlan;
  CitationPlan; RiskReport; SubmissionPack; VenueMemory."*
- **§12 line 1874** — defines `journal_yuga_artifact` as
  *"human-readable report or document: ArticleModel report,
  VenueProfile, FitAssessment report, MismatchMap, RewritePlan,
  CitationPlan, RiskReport, SubmissionPack, ReviewOutcome analysis."*
- **§12 line 1866** — `vault_card_ref` is the human-readable projection.
  Useful for navigation; canonical evidence stays in structured
  registries.
- **§16 line 2532** — *"Vault cards should make it possible for a
  human to browse Journal-Yuga work without opening raw registry
  JSON."* This is literally the Mavrinsky requirement.
- **§17 line 4280** — *"System writes human-readable report and Vault
  cards: ArticleModel card; …"*

The canon does **not** require prompt-level correction in this layer.
Per §11 line 1822 every operation must consume or produce explicit
entities; correction is **entity-level**, e.g. via
`Case.confirm_article_model(protected_core, corrections)`.

## B. What `vault.py` already does

- `src/kairoskopion/vault.py` — vault root + subdir scaffolding +
  index/manifest generators for `articles / venues / fits / risks
  / compliance / mismatches / citations / adapters / submissions
  / traces`.
- `src/kairoskopion/artifacts.py` — per-entity card writers
  (`write_article_card`, `write_venue_card`, …) that delegate body
  generation to:
- `src/kairoskopion/cards.py` — actual markdown body generators:
  `article_model_card`, `venue_model_card`, `fit_assessment_card`, etc.

So the **infrastructure exists**. The body content is minimal.

## C. Current ArticleModel card content (verified from a real card)

```markdown
---
id: art_b9b6fce012c4
type: ArticleModel
stage: full_manuscript
genre: theoretical_essay
lifecycle: preliminary
---

# The Impossibility of Artificial Subjectivity: A Conceptual Argument

## Method
conceptual_method

## Unknowns
- protected core not confirmed by user

## Sources
- fixture:manuscript_sample
```

What it lacks for a humanities author:

| canon-required item | current state |
|---|---|
| short summary "what the system thinks this article is" | **MISSING** |
| object of inquiry in prose | partial (`_section` bullet only if non-empty) |
| central problem / tension in prose | partial |
| core claims with extraction status | bullets, no extracted/inferred markers |
| genre / method / novelty explained in human terms | **MISSING** (enum value rendered raw) |
| disciplinary registers + tribes + why | **MISSING** |
| theoretical shoulders / opponents / vocabulary | **MISSING** |
| protected core with honest "missing" warning | partial |
| unknowns in plain language | partial (technical phrasing) |
| author questions for model review | **MISSING** |
| correction affordances | **MISSING** |

## D. Current Venue card content

```markdown
---
id: venue_..
type: VenueModel
venue_type: journal
lifecycle: preliminary
---

# <name>

## Scope
…

## Publisher
…

## Article types
- research_article
- review

## Language policy
…

## URLs
…

## Unknowns
…
```

Lacks for a humanities author:

| canon-required item | current state |
|---|---|
| plain-language identity sentence | partial |
| official self-description / aims & scope marked source-fact / vendor-claim / unknown | **MISSING** |
| what the corpus actually shows | **MISSING** |
| formal submission profile (article types, length, abstract, refs, OA, APC, AI policy) | partial |
| editorial board status (present / missing / inaccessible) | **MISSING** |
| inferred genre / method / theory / citation expectations | **MISSING** |
| plain-language unknowns / inaccessible | partial |
| author questions for venue review | **MISSING** |
| correction affordances | **MISSING** |

## E. Cards in cockpit — visibility

- Cards are written to disk under `.kairoskopion/vault/{articles,venues,…}/*.md`.
- They are designed for Obsidian browsing, NOT cockpit display.
- The cockpit UI (`ui/src/components/CaseWorkspace.tsx`) shows
  `ArticleCard` and `VenuePoolBoard` which render **structured
  fields**, not prose. No "Human view / Technical view" toggle exists.
- **No cockpit endpoint** returns the markdown card. There is no
  `/cases/{id}/article-model/human-view`.

## F. Existing correction loop

- `Case.confirm_article_model(protected_core: list[str], corrections:
  dict[str, Any])` exists and persists corrections into the case.
- `ArticleCard` has **Edit** / **Confirm Article Model** affordances
  that drive the same endpoint.
- The mechanism is entity-level (field corrections). Prompt-patch is
  not in scope (canon does not require it).

## G. What this pass implements

Per the new task spec:

1. New service `services/human_readable_card.py` with two functions:
   - `article_model_human_view(article_dict, pathways=None,
     case_context=None) -> str` — renders 11 prose sections per task
     spec §C.
   - `venue_human_view(vpkg_or_venue_dict) -> str` — renders 9 prose
     sections per task spec §D.
2. Both outputs are markdown with unobtrusive HTML comments holding
   machine-addressable field paths (per task spec §E) so a future
   UI surface can wire per-field correction without re-parsing.
3. Two new API endpoints (user-scoped):
   - `GET /cases/{case_id}/article-model/human-view` → markdown.
   - `GET /cases/{case_id}/venues/{venue_key}/human-view` → markdown.
4. Cockpit toggle on the Article view:
   - Two buttons: **Человеческая модель** / **Техническая модель**.
   - Human view (default after the toggle is selected) fetches the
     markdown endpoint and renders it as styled prose.
   - Technical view is the existing `ArticleCard`.
5. The same toggle on the `VenueProfile` view (visible when a venue is
   selected from the pool).
6. Correction affordances: piggyback on existing
   `Case.confirm_article_model(protected_core, corrections)` — the
   human view has a "Confirm model" CTA at the bottom + per-section
   "Это неверно" tag links.

## H. What this pass explicitly defers

| deferred item | reason |
|---|---|
| **LLM JSON repair** | This task spec's preamble explicitly says: *"This pass is about author-facing human model review. LLM JSON repair is a later hardening pass."* Honest failure-mode visibility will land then. |
| **Full PromptPatch / RuleUpdate infrastructure** | Canon does not require it. Entity-level correction is enough; prompt-level can come later if measurable need shows up. |
| **Full FitAssessment human view** | Out of scope for this pass; tasks §C, §D, §F only require ArticleModel + Venue. FitAssessment human view is the obvious next pass. |
| **MismatchMap / RewritePlan / CitationPlan / RiskReport / SubmissionPack / VenueMemory human views** | Same reason — defer; pattern from this pass is replicable. |
| **Cross-correction flow** ("if you change X here, system asks if Y in venue should also change") | Future when multiple human views exist together. |

End of audit.
