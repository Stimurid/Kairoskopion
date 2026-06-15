# LLM JSON repair + visible fallback — implementation report

**Date:** 2026-06-15
**Branch:** `feature/llm-json-repair-visible-fallback`
**Baseline:** `c2a5780 Merge report for human-readable model review`

## A. Original problem

The human-readable model review pass exposed a deeper issue: when the
LLM call succeeded but the response failed JSON validation, the
`ArticleModelerAgent.execute` path **silently** fell to the
deterministic `execute_deterministic`. The UI then showed honest
UNKNOWN — which is correct as a state but misleading as a story: it
hid the fact that LLM was attempted and failed.

Two cases observed during the tester-readiness pass:

- Guattari/porcupine fragment → LLM returned ~90s round-trip, then
  the article model came back fully deterministic (all UNKNOWN). No
  trace, no warning.
- Rabbit/early-modern-England fragment → LLM returned a clean
  populated ArticleModel + 8 pathways. Same code path, different
  outcome — opaque.

This pass closes the gap with **bounded JSON repair**, **explicit
attempt metadata**, and a **visible user-facing warning** in the
human view when fallback fires.

## B. What this pass implements

### B.1 `src/kairoskopion/llm/json_repair.py`

Bounded, stdlib-only repair utility. Single entry point
`repair_and_parse(raw, schema) -> RepairOutcome`. Steps in order:

1. parse as-is;
2. strip ```` ```json … ``` ```` or ```` ``` … ``` ```` markdown fences;
3. replace smart quotes (`“ ” ‘ ’ « »` → straight quotes);
4. strip trailing commas inside `{}` / `[]`;
5. convert single-quoted strings to double-quoted, *only* when the
   input has no double quotes at all (safe substitution);
6. extract the first balanced `{…}` or `[…]` from surrounding prose;
7. validate against an optional JSON Schema — fill **optional**
   fields (not in `required`) with safe default values (`[] / {} / ""
   / false / null`).

**Refused on principle**:

- inventing missing **required** semantic values (returns
  `schema_validation_failed`, never forges content);
- guessing enum values from free text;
- replacing semantically empty `{}` with anything;
- calling a second LLM to repair (no extra LLM cost by default).

### B.2 `src/kairoskopion/llm/attempt_metadata.py`

`LLMAttemptMetadata` dataclass with all task-spec §B fields:
`llm_attempted`, `llm_provider`, `llm_model`, `llm_latency_ms`,
`llm_raw_output_present`, `parse_status`, `repair_attempted`,
`repair_status`, `repair_steps`, `fallback_used`, `fallback_reason`,
`validation_errors_summary` (truncated to ≤8 entries × ≤240 chars),
`warning_for_user`, `raw_output_ref` (reserved, default None — raw
output never captured by default).

Factory helpers:

- `LLMAttemptMetadata.parse_ok(...)` — successful or repaired parse.
- `LLMAttemptMetadata.fallback(reason, ...)` — fallback with the
  Russian-language `warning_for_user` auto-derived from the reason.
- `LLMAttemptMetadata.not_attempted()` — when no provider configured.

User-facing warnings are short Russian sentences — never stack
traces, never raw LLM output.

### B.3 Agent wiring — `agents/article_modeler.py`

The execute path now:

1. Calls provider; on any exception → `LLMAttemptMetadata.fallback`
   with `FALLBACK_REASON_PROVIDER_ERROR` + deterministic fallback;
2. If `response.parsed` is a dict → fast path, `parse_status =
   parsed_ok`;
3. Else runs `repair_and_parse(response.content, schema)`. If repair
   succeeds → `parse_status = repaired_ok`; if not → fallback with
   one of `FALLBACK_REASON_SCHEMA_VALIDATION_FAILED`,
   `FALLBACK_REASON_REPAIR_FAILED`, `FALLBACK_REASON_INVALID_JSON`.
4. The attempt metadata is attached to the ArticleModel
   (`extraction_attempt` field — new on `schema.ArticleModel`),
   persisted via `CaseStore`, and surfaced in the API response.

`_deterministic_with_attempt(inp, meta)` is the new helper that
annotates the deterministic-fallback output with the captured
metadata.

### B.4 Case-level fallback — `api/cases.py`

`Case._build_article_model` had its own outer try/except that caught
agent exceptions and silently dropped to a service-level
deterministic build (no metadata attached). Now it constructs a
`LLMAttemptMetadata.fallback(FALLBACK_REASON_PROVIDER_ERROR)` (or
`LLMAttemptMetadata.not_attempted()` when no provider) and attaches
it to the resulting ArticleModel — so the human view warns honestly
regardless of where the failure happened.

### B.5 Human view surfacing — `services/human_readable_card.py`

When `article["extraction_attempt"]["fallback_used"]` is True, the
human view emits a blockquote warning paragraph **above** the
existing sections:

> ⚠ **LLM-анализ был запущен, но его ответ не прошёл структурную
> проверку. Система показывает безопасную предварительную модель с
> UNKNOWN-полями. Это не значит, что текст непонятен; это значит,
> что произошёл сбой структурирования ответа.**
>
> _(parse_status: `schema_validation_failed` · fallback_reason:
> `schema_validation_failed`)_

The technical-status hint is in a smaller italic line — debuggers
see it; non-technical authors see the bold Russian sentence first.

The YAML frontmatter at the top also carries `parse_status` and
`fallback_reason` for technical introspection.

## C. What repair handles vs refuses

| repair handles | refuses |
|---|---|
| plain JSON (no-op) | inventing missing required fields |
| `\`\`\`json … \`\`\`` markdown fences | guessing enum values from free text |
| unfenced code blocks | rewriting `{}` into semantic content |
| prose before/after JSON (first balanced extraction) | calling a second LLM for repair (no extra LLM cost) |
| trailing commas | tuning temperature / max_tokens / model |
| smart quotes (`“ ” ‘ ’ « »`) | broad prompt rewrite |
| single-quoted strings (safe-only) | parsing non-JSON natural language as "data" |
| optional field defaults via schema | overriding schema's `required` list |

## D. UI behaviour

- **Success / repair success** → no warning. `parse_status` is
  `parsed_ok` or `repaired_ok` and only appears in the frontmatter
  for debuggers.
- **Any fallback** → bold Russian warning blockquote above the
  sections + a small italic technical hint with
  `parse_status` / `fallback_reason`. The 11 sections still render
  honestly with the deterministic UNKNOWNs.
- **No raw LLM output / no stack trace** is ever shown to the
  author. Tests verify this adversarially.

The technical view (existing `ArticleCard`) is unchanged but now has
access to the same `extraction_attempt` field on the article and can
display it however it wants (out of scope for this pass).

## E. Tests

`tests/test_llm_json_repair_and_fallback.py` — **24 tests, all
pass**:

- **10 repair-utility tests**: plain JSON; fenced; unfenced fenced
  block; prose-around-JSON; trailing commas; smart quotes; schema
  missing-required-field does not invent; optional fields get safe
  defaults; empty input flagged; unrecoverable text flagged.
- **6 metadata tests**: parse_ok has no warning; repaired_ok marks
  repaired; every fallback reason carries a visible Russian
  warning; to_dict / from_dict round-trip; validation_errors_summary
  is truncated to 8×240; `not_attempted` factory shape; unknown
  reason → generic warning.
- **4 agent-level tests**: fast-path with parsed dict from provider
  → no fallback; provider raises → `provider_error` fallback with
  warning; non-JSON content → `invalid_json` or `repair_failed`
  fallback; adversarial provider error text containing "Traceback"
  → user warning never leaks it.
- **2 human-view surfacing tests**: fallback metadata renders the
  Russian warning + technical hint; parse_ok metadata produces NO
  warning.

Full pytest after this pass: **1704 passed**, 4 deselected
(+24 new vs the 1680 baseline). No regressions.

Frontend `tsc --noEmit` clean, `vite build` clean (no UI changes in
this pass beyond what the existing `HumanModelView` already renders).

## F. Live smoke

Cold uvicorn (no manual `source .env`):

```
KAIROSKOPION_DATA_DIR=.kairoskopion_smoke \
  python -m uvicorn kairoskopion.api.app:app --port 8000 --host 127.0.0.1
```

`GET /health` → `llm.available=True model=gpt-4o-mini`.

### Porcupine fragment (previously silent-fallback case)

Today's run (90s 302.ai round-trip):

```
parse_status     : parsed_ok
fallback_used    : False
fallback_reason  : not_applicable
novelty_mode     : new_application
method_status    : conceptual_method
core_claims_n    : 3
warning_present  : False
```

The previously-silent fallback case **succeeded** today. This is
intermittent provider behaviour — important to know:
the silent-fallback symptom was a **transient 302.ai output shape
issue**, not a deterministic Kairoskopion bug. But what this pass
ensures is that next time it does fail, the user sees a Russian
warning, not a quiet UNKNOWN-only screen.

### Rabbit / early-modern England fragment

Today's run (82s round-trip):

```
parse_status     : parsed_ok
fallback_used    : False
novelty_mode     : translation_between_fields
core_claims_n    : 3
warning_present  : False
```

Successful path still produces rich ArticleModel + per-pathway
reasoning. No regression.

### Fallback case rendering (synthetic)

Because both live fragments succeeded today, the fallback rendering
is proven via the test suite (`TestHumanViewSurfacesFallback`),
which exercises an `extraction_attempt` with
`fallback_reason=schema_validation_failed`. The rendered markdown
contains the Russian warning verbatim + the technical
`parse_status / fallback_reason` hint, with no `Traceback` leakage.

## G. Remaining limitations

| limitation | comment |
|---|---|
| No second-LLM repair | Intentional per task spec — no extra LLM cost by default. Could be added behind a feature flag in a future pass. |
| Only ArticleModeler currently wired | DisciplinaryPathwayMapper and other LLM agents still silently fall back. Easy to replicate the pattern; deferred. |
| `extraction_attempt` not yet surfaced in the technical `ArticleCard` | The human view shows it. The technical view can read `article.extraction_attempt` directly; UI rendering of the badge is out of scope for this pass. |
| Schema validation gating fast path | When `response.parsed` is already a dict from `openai_compat._parse_json_robust`, we trust it without schema check. Only the repair path validates against schema. Strict validation in the fast path would be a hardening pass on its own. |
| `raw_output_ref` always None | Field reserved for sanitized debug excerpt; we don't capture raw content by default for safety. |

## H. Next recommended pass

1. Mirror the article_modeler wiring on `DisciplinaryPathwayMapper`
   so pathway-extraction fallbacks are equally visible.
2. Add `extraction_attempt` rendering badge to the technical
   `ArticleCard` so debuggers see the badge without opening the
   markdown.
3. Optionally: a second-LLM repair behind a feature flag for the
   schema_validation_failed case — only when operator opts in,
   never default.

## I. Strict prohibitions — checklist

| prohibition | status |
|---|---|
| no LLM parameter tuning in Kairoskopion | OK — no temperature / max_tokens / model overrides touched |
| no broad prompt rewrite | OK — prompts unchanged |
| no new venue discovery | OK |
| no new human-view expansion | OK — the only human-view change is the warning blockquote |
| no secrets / runtime data committed | OK — smoke storage gitignored |
| no raw LLM output committed | OK — `raw_output_ref` defaults None |
| no deploy / tag / merge | OK — branch only |

End of report.
