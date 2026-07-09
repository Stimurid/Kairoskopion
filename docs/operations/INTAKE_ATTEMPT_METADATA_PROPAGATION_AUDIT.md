# Intake Attempt Metadata Propagation Audit

**Date:** 2026-07-09
**Base:** main @ `30a504d`

## Defect

Normal article intake via `/cases/{case_id}/article-model` returns:
- `agent_role`: empty
- `attempts`: empty

P11 replay returns all fields correctly.

## Root cause

`article_modeler.py` builds `LLMAttemptMetadata` directly at three call sites
without passing the new attempt history fields from the response object:

### Call site 1 — success path (line 159)

```python
meta = LLMAttemptMetadata.parse_ok(
    provider="openai_compatible",
    model=provider_model,
    latency_ms=latency_ms,
    content_present=content_present,
    repaired=repaired,
    repair_steps=outcome_steps,
    # MISSING: requested_model, effective_model, attempt_count, attempts, agent_role
)
```

`parse_ok()` defaults: `requested_model=None` → falls back to `model` (so
this field appears populated), `effective_model=None` → same. But
`agent_role=""` stays empty and `attempts=[]` stays empty.

### Call site 2 — provider exception fallback (line 91)

```python
meta = LLMAttemptMetadata.fallback(
    reason=FALLBACK_REASON_PROVIDER_ERROR,
    provider="openai_compatible",
    model=None,
    validation_errors=[...],
    parse_status="not_attempted",
    # MISSING: attempts, final_error_code, agent_role
)
```

### Call site 3 — parse failure fallback (line 138)

```python
meta = LLMAttemptMetadata.fallback(
    reason=reason,
    provider="openai_compatible",
    model=provider_model,
    latency_ms=latency_ms,
    content_present=content_present,
    repair_attempted=...,
    repair_steps=...,
    validation_errors=...,
    parse_status=outcome_status,
    # MISSING: requested_model, effective_model, attempt_count, attempts, agent_role
)
```

## Why P11 replay works

The P11 replay path in `cases.py` calls `provider.complete()` directly and
builds `attempt_meta` dict by extracting `response.requested_model`,
`response.effective_model`, etc. — it never goes through
`article_modeler.py`.

## Why classify_llm_response works

`classify_llm_response()` in `attempt_metadata.py` extracts all fields from
the response object with `getattr()` before calling `parse_ok()`/`fallback()`.
The article modeler does NOT use `classify_llm_response()` — it builds
metadata manually.

## Fix

Pass `response.requested_model`, `response.effective_model`,
`response.attempt_count`, `response.attempts`, and `agent_role="article_modeler"`
at all three call sites. For the exception path, extract `attempts` and
`error_code` from the caught exception (already available via monkey-patch
from the provider).
