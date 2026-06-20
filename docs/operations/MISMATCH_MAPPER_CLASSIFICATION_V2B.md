# V2-B — `mismatch_mapper` classification & non-wiring decision

**Status:** documentation + tests. No chain wiring change.
**Authored:** 2026-06-20.
**Baseline commit:** `ddb9850` (= main/prod head after V2-A).
**Predecessor:** [`LEGACY_COMPATIBILITY_REUSE_AUDIT_V2.md`](LEGACY_COMPATIBILITY_REUSE_AUDIT_V2.md)
classified the mismatch chain as `DUPLICATE_MERGE_REQUIRED` and queued
"wire mismatch_mapper" as Pass B. After deeper inspection this pass
concludes the mapper should **not** be wired. This note records that
decision and the evidence.

## Modules inspected

| File | Role |
|---|---|
| [`services/mismatch_mapping.py`](../../src/kairoskopion/services/mismatch_mapping.py) | Deterministic `build_mismatch_map(fit) -> MismatchMap`. Empty `venue_side` by design (Track D fix). Always invoked in fit chain at `cases.py:1176`. |
| [`agents/fit/mismatch_mapper.py`](../../src/kairoskopion/agents/fit/mismatch_mapper.py) | Agent class wrapping LLM call + deterministic fallback. Never invoked outside tests. |
| [`agents/prompt_families/mismatch_mapping.py`](../../src/kairoskopion/agents/prompt_families/mismatch_mapping.py) | Prompt family with output schema `MismatchMappingResult`. |
| [`agents/mismatch_narrator.py`](../../src/kairoskopion/agents/mismatch_narrator.py) | Active enrichment layer; fills `venue_side` / `description` / `possible_actions` via batched LLM call on already-built mismatches. |

## Classification

**`agents/fit/mismatch_mapper.py` → `LLM_AGENT_USABLE` but
structurally incompatible with the active chain.**

Concretely:

1. **Schema mismatch.** The mapper's LLM output is
   `{axis, severity, description, venue_expectation, article_current,
   field_core_impact, adaptation_cost, adaptation_path}` per
   `OUTPUT_SCHEMA` in
   `agents/prompt_families/mismatch_mapping.py:97–127`. The
   `MismatchMap` schema actually consumed by snapshot persistence,
   narrator, DossierView and the WhiteCrow bridge uses
   `{axis, severity, article_side, venue_side, description,
   possible_actions, evidence_refs, field_core_risk,
   requires_user_acceptance}` per
   `services/mismatch_mapping.py:57–68`. The two are not drop-in
   compatible — wiring would require a translation layer that drops
   `venue_expectation` / `adaptation_cost` / `adaptation_path`.
2. **Semantic overlap with narrator.** The mapper's `venue_expectation`
   field is exactly the semantic claim
   [`MismatchNarratorAgent`](../../src/kairoskopion/agents/mismatch_narrator.py)
   already produces, with stronger anti-hallucination discipline
   (compact article/venue projection, per-axis batching, explicit
   `narrative_status` markers, honest empty-string fallback). Letting
   the mapper produce `venue_expectation` before the narrator would
   give us two LLM passes making the same kind of claim with weaker
   guardrails on the first.
3. **Deterministic fallback is a no-op.** `MismatchMapperAgent.execute_deterministic`
   delegates straight to `build_mismatch_map(fit)`
   (`agents/fit/mismatch_mapper.py:40-41`) — the same function the
   fit chain already calls directly. Wiring the deterministic path
   adds an indirection layer with zero behavioural change.
4. **No `evidence_refs` propagation.** The mapper's output schema has
   no `evidence_refs` field; downstream consumers (narrator,
   risk reporting, rewrite planning) read `evidence_refs` per
   mismatch. Wiring would silently drop evidence.

## Track B decision

Per the V2-B brief's Track B decision table:

- Rule 3 applies: the LLM path makes semantic claims overlapping the
  narrator with weaker contracts.
- Rule 4 also applies: as a deterministic option the mapper is
  structurally redundant with `build_mismatch_map`.

**Outcome:** Option 2 — leave mapper unused, document why, add focused
tests that prove the deterministic source-of-truth still emits
honest-empty `venue_side` and that the mapper's LLM contract is not
drop-in compatible. **Final report must say "not wired intentionally"**
(per Track B rule 4).

## What would change this decision

If a future pass wants the LLM-structured layer between deterministic
build and narrator that V2 §2.4 originally pictured, the right shape
is **not** to wire `MismatchMapperAgent` as it stands. It is to either:

- extend the existing `MISMATCH_NARRATIVE_FAMILY` schema with the
  fields the operator wants (`adaptation_cost`, `adaptation_path`,
  `field_core_impact`) so the narrator does the full job in one pass,
  while keeping its compact-input + per-axis batching discipline; **or**
- introduce a *new* agent whose output schema is exactly `MismatchMap`
  (not `MismatchMappingResult`) and whose prompt forbids fabricating
  `venue_expectation` from anything but the venue text.

Neither option is in scope for V2-B.

## What stays as-is

- Fit chain unchanged: deterministic `build_mismatch_map` → narrator
  enrichment, with honest empty `venue_side` until the narrator fills
  it. UI hint "требуется LLM-комментарий по площадке" continues to
  render when the narrator returned empty.
- `MismatchMapperAgent` remains registered. The class is kept as a
  spec-reference artefact and as scaffolding for a future redesign;
  removing it would break nothing today, but adding it back would
  cost more than keeping it.

## Confirmations

- ✅ No chain wiring change.
- ✅ No model / env / temperature / max_tokens / timeout / retries /
  base_url / API-key changes.
- ✅ No prompt edits.
- ✅ No agent deletions.
- ✅ `mismatch_narrator` remains the final venue-side narrative
  source.
- ✅ No fake venue claims introduced.
- ✅ Unknown stays unknown.
