# ArticleModel schema invariants

**Status:** classification doc — no code changes in this commit.
**Authored:** 2026-06-19 during `feature/intake-choice-and-routing-seam`.
**Schema source of truth:** `src/kairoskopion/prompts/article_modeling.py`
(`ARTICLE_MODELING_OUTPUT_SCHEMA`).
**Dataclass source of truth:** `src/kairoskopion/schema.py::ArticleModel`.

## Purpose

When deciding whether a field can move `required` → optional with a
safe default (and which provider models can satisfy it), this map is
the criterion. Cheap-model compatibility is allowed ONLY when the
field falls into `DERIVED_OR_DEFAULTABLE`, `DISPLAY_METADATA`,
`OPERATOR_HINT`, or `OBSERVABILITY_ONLY` — never for
`CORE_SEMANTIC_INVARIANT`.

## Categories

- **CORE_SEMANTIC_INVARIANT** — missing/null means the LLM failed at
  reading the text. Schema MUST require; missing = `schema_validation_failed`.
- **DERIVED_OR_DEFAULTABLE** — can be reconstructed from other fields
  or from manuscript text by deterministic code; schema MAY require
  the key but value-null is acceptable.
- **DISPLAY_METADATA** — used only by UI / human view; safe defaults
  exist; not part of any pipeline invariant.
- **OPERATOR_HINT** — fields the operator can edit/confirm; LLM
  output is advisory only.
- **OBSERVABILITY_ONLY** — for the audit trail, not for downstream
  reasoning.

## Field-by-field map

| Field | Category | Required? | Downstream consumers | Fallback / safe default | Missing → |
|---|---|---|---|---|---|
| `title` | DISPLAY_METADATA | **optional** (loosened in `030fda4`) | `litops_bridge.py:59` (`or "(untitled)"`), `submission_pack.py:36` (`or "[TITLE]"`), human view | Manuscript extractor's `title` if present; otherwise empty string | warn-only; pipeline runs |
| `abstract_summary` | DERIVED_OR_DEFAULTABLE | optional | semantic profiler, human view | Manuscript `abstract` field if present | warn-only |
| `language` | CORE_SEMANTIC_INVARIANT | **required** | semantic profiler, discipline matcher (RU vs intl matrix), venue language fit | Deterministic fallback: `"en"` | `schema_validation_failed` |
| `article_stage` | CORE_SEMANTIC_INVARIANT | **required** | quality gates, lifecycle status, abstract-vs-manuscript routing | none — operator must distinguish abstract from full | `schema_validation_failed` |
| `problem_statement` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment topic axis, semantic profiler, disciplinary mapper, human view | none | `schema_validation_failed` |
| `research_question` | CORE_SEMANTIC_INVARIANT | **required** | same as above | none | `schema_validation_failed` |
| `object_of_inquiry` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment topic axis, semantic profiler, protected_core_candidates | none | `schema_validation_failed` |
| `core_claims` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment, semantic profiler, citation_ecology bridge detection | none | `schema_validation_failed` |
| `secondary_claims` | DERIVED_OR_DEFAULTABLE | optional (not in required list) | citation_ecology, human view | empty list | warn-only |
| `argument_structure` | CORE_SEMANTIC_INVARIANT | **required** | semantic profiler, fit_assessment argument_structure axis, rewrite planner | none | `schema_validation_failed` |
| `method_status` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment method axis, venue_candidate_screening (empirical vs conceptual mismatch) | enum default `"unknown"` is allowed | `schema_validation_failed` (key absent), warn-only if value=unknown |
| `method_description` | DISPLAY_METADATA | optional | human view, submission pack | empty | warn-only |
| `genre_current` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment genre axis, venue_candidate_screening | enum default `"unknown"` allowed | `schema_validation_failed` if missing |
| `disciplinary_register_current` | CORE_SEMANTIC_INVARIANT | **required** | disciplinary_mapper, discipline_matcher, venue_candidate_screening discipline axis | none — required for B-pipeline to fire usefully | `schema_validation_failed` |
| `novelty_mode` | CORE_SEMANTIC_INVARIANT | **required** | fit_assessment novelty axis, rewrite planner | enum default `"unknown"` allowed | `schema_validation_failed` if missing |
| `theoretical_shoulders` | CORE_SEMANTIC_INVARIANT | **required** | semantic profiler schools_and_traditions, citation ecology | empty list ⇒ "no shoulders identified" — semantically meaningful | `schema_validation_failed` |
| `opponents_or_contrasts` | DERIVED_OR_DEFAULTABLE | optional | semantic profiler, mismatch mapper | empty list | warn-only |
| `key_terms` | CORE_SEMANTIC_INVARIANT | **required** | semantic profiler, discipline_matcher keyword pre-filter, venue corpus matching | empty list ⇒ "no key terms surfaced" — semantically meaningful | `schema_validation_failed` |
| `citation_ecology_description` | DERIVED_OR_DEFAULTABLE | optional | citation_ecology service, human view | manuscript `bibliography_refs` summary | warn-only |
| `protected_core_candidate` | OPERATOR_HINT | **required** | protected_core_policy, WhiteCrow bridge | empty list ⇒ "operator must declare" — semantically meaningful | `schema_validation_failed` |
| `mutable_zones` | OPERATOR_HINT | **required** | rewrite planner, WhiteCrow patch queue | empty list | `schema_validation_failed` |
| `high_risk_zones` | OPERATOR_HINT | **required** | risk_reporting, protected_core_policy | empty list | `schema_validation_failed` |
| `unknowns` | OBSERVABILITY_ONLY | **required** | human view, fit audit, quality gate | empty list | `schema_validation_failed` if key absent; value `[]` valid |
| `assumptions` | OBSERVABILITY_ONLY | **required** | human view, fit audit | empty list | `schema_validation_failed` if key absent |
| `confidence` | OBSERVABILITY_ONLY | **optional** (loosened in `030fda4`) | UI badge, human view; agent consumes via `parsed.get("confidence", "medium")` | `"medium"` | warn-only; `extraction_attempt.parse_status` is the authoritative audit signal |
| `questions_for_user` | OPERATOR_HINT | **optional** (loosened in `030fda4`) | Not persisted to ArticleModel dataclass; only flows into AgentOutput | empty list | warn-only |

## Why the 3 currently-optional fields are justified

- **`title`** — dataclass already `title_current: str \| None`; 3
  distinct downstream fallbacks (`litops_bridge.py:59`,
  `submission_pack.py:36`, manuscript title). Cheap models that follow
  the body of the schema but skip the title key produce no downstream
  damage.
- **`confidence`** — pure observability metadata. The authoritative
  audit signal is `extraction_attempt.parse_status` /
  `fallback_reason` / `repair_steps`, which are set by the agent based
  on the parse outcome, not by trusting `parsed["confidence"]`. The
  LLM's own confidence string is advisory at best.
- **`questions_for_user`** — never persisted to `ArticleModel`. Only
  flows into `AgentOutput.questions_for_user` for the UI to surface
  "follow-up" hints. Empty list is semantically identical to "model
  had no follow-up questions". Phase B B0/B1 `AgentOutput.questions_for_user`
  defaults to `[]`.

## Strictness summary

- **18 required, 4 optional** in current schema (after `030fda4`).
- All 18 are `CORE_SEMANTIC_INVARIANT` or `OPERATOR_HINT` with
  semantically-meaningful empty-list defaults.
- Cheap models that miss any of the 18 → legitimate
  `schema_validation_failed` → deterministic fallback. That's the
  desired safety net.

## Acceptance criteria for any future "loosen field N"

A field may move required → optional only if:

1. Its category in this map is NOT `CORE_SEMANTIC_INVARIANT`.
2. Every downstream consumer (citations required) has a documented
   safe-default behavior.
3. The downstream behavior with the default produces the SAME pipeline
   verdict as with a missing-but-required outcome — i.e. loosening
   doesn't silently turn a `schema_validation_failed` into a
   `parsed_ok` with subtly wrong output.
4. `_fill_optional_defaults` in `json_repair.py` produces an
   appropriate type-aware default (`""` / `[]` / `{}` / `None`).
5. New test in `tests/test_article_model_json_hardening.py` proves
   the field is filled by the defaulter.

## Acceptance criteria for any future "tighten field M"

A currently-optional field may move back to required only if:

1. A downstream consumer is found that crashes or produces silently
   wrong output without the value (citations).
2. The fix isn't "default the field" but "force the LLM to provide it".
3. Tests prove cheaper models can still satisfy the field (or are
   explicitly rejected from that call-site via per-call routing).

## Out of scope

- Field renames (would break `ArticleModel.from_dict` round-trip).
- Adding new fields (separate schema-version bump).
- Per-field LLM coaching prompts (the system prompt already specifies
  all fields).
