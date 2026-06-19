# Per-call LLM model routing — design spec

**Status:** spec only — no implementation in this branch.
**Authored:** 2026-06-19 during `feature/intake-routing-and-model-strategy`.
**Owner:** Agentum (LLM provider config layer).

## Problem

All Kairoskopion LLM calls currently use a single global model
(`KAIROSKOPION_LLM_MODEL` env var, read via `LLMConfig.from_env()`).
The same `OpenAICompatProvider` instance is shared across every
agent: `InputClassifier`, `ArticleModeler`, `SemanticProfiler`,
`DisciplinaryPathwayMapper`, `DisciplineMatcher`, `FitAssessor`,
`VenueProfiler`, `DisciplineSourceAcquisition`, `DisciplineSeeder`.

Empirically (see `docs/operations/PROVIDER_ROUTE_RECOVERY_REPORT.md`):

- `claude-sonnet-4-5-20250929` reliably passes the 21-required-field
  ArticleModel schema (7/7 acceptance) but is slow (~110-170 s per
  full intake pipeline) and expensive.
- `claude-haiku-4-5-20251001`, `gpt-4o-mini` return rich structured
  output but consistently miss 3-6 of the 21 strict required keys
  (Track B audit). Loosening 3 fields (this branch) brings them
  closer but acceptance on the full pipeline still untested.
- Trivial call-sites (`InputClassifier` 4-field schema, `DisciplineMatcher`
  closed-set ranking) have no need for Sonnet-class capability.

A one-model-for-all policy is wasteful for cheap calls and risky for
expensive ones.

## Constraints

- No temperature / max_tokens / timeout / retries tuning in Kairoskopion
  code — those belong to Agentum.
- Provider routing must live in env/config layer, NOT inside agent
  business logic. No `if role_id == ...` model dispatch in any agent.
- Existing single-model deployment must keep working byte-identically
  when no per-role overrides are set.
- Health endpoint must surface which model resolves to which role.

## Proposed minimal implementation

Three edits, no agent surgery:

### A. `src/kairoskopion/llm/config.py`

```python
@classmethod
def for_role(cls, role_id: str) -> LLMConfig | None:
    """Return per-role-overridden LLMConfig or fall through to global.

    Override env var pattern: KAIROSKOPION_LLM_MODEL_{ROLE_ID_UPPERCASE}
    e.g. KAIROSKOPION_LLM_MODEL_INPUT_CLASSIFIER=claude-haiku-4-5-20251001
    """
    base = cls.from_env()
    if base is None:
        return None
    override = os.environ.get(
        f"KAIROSKOPION_LLM_MODEL_{role_id.upper().replace('-', '_')}"
    )
    if override and override != base.model:
        return dc.replace(base, model=override)
    return base
```

### B. `src/kairoskopion/api/cases.py`

Replace `_get_llm_provider()` with `_get_llm_provider(role_id: str)`:

```python
def _get_llm_provider(role_id: str = "default") -> OpenAICompatProvider | None:
    cfg = LLMConfig.for_role(role_id)
    if cfg is None or not cfg.api_key:
        return None
    return OpenAICompatProvider(cfg)
```

Each call-site already knows the agent's `role_id`. Update the existing
~9 `_get_llm_provider()` calls inside `Case._build_article_model`,
`Case._run_discipline_matcher`, `Case._build_article_field_position`,
etc., to pass the role.

### C. `src/kairoskopion/api/app.py` `/health`

Already includes `llm.model`. Extend to:

```python
"llm": {
    ...,
    "model_default": cfg.model,
    "model_per_role": LLMConfig.role_routing_map(),  # reads env, returns dict
}
```

## Recommended routing matrix (initial)

| role_id | model | rationale |
|---|---|---|
| `article_modeler` | `claude-sonnet-4-5-20250929` | 18 required fields after this branch; complex argument structure inference |
| `fit_assessor` | `claude-sonnet-4-5-20250929` | 12-axis multi-evidence reasoning, core deliverable |
| `semantic_profiler` | `claude-sonnet-4-5-20250929` | nested taxonomy reasoning; revisit after benchmarking |
| `disciplinary_pathway_mapper` | `claude-sonnet-4-5-20250929` | affects venue pool |
| `venue_profiler` | `claude-sonnet-4-5-20250929` | venue facts persist; risk of polluting registry |
| `input_classifier` | `claude-haiku-4-5-20251001` | 4-field shape, ≤6 KB opening, conservative fallback exists |
| `discipline_matcher` | `claude-haiku-4-5-20251001` | closed-set ranking |
| `discipline_source_acquisition` | `gpt-4o-mini` | URL hint generation |
| `discipline_seeder` | `gpt-4o-mini` | card synth with deterministic fallback |

Deploy by setting the override env vars in
`/opt/kairoskopion/secrets/kairoskopion.env` on the VM and restarting
`kairoskopion-api`.

## Acceptance criteria

1. `test_for_role_override_respected` — per-role env var beats global.
2. `test_for_role_fallback_to_global` — missing override falls through.
3. `test_for_role_no_global_returns_none` — preserves "LLM optional"
   contract when no env at all.
4. `test_provider_status_emits_per_role_map` — `/health` exposes
   resolved routing.
5. `test_cases_factory_passes_role_id` — intake pipeline calls
   `_get_llm_provider("article_modeler")`, `"input_classifier"`, etc.
6. `test_no_overrides_no_behavior_change` — without any overrides,
   every `AgentOutput.llm_usage["model"]` matches pre-change baseline.
7. Live acceptance: full 7-input battery passes with Sonnet on
   `article_modeler` AND Haiku on `input_classifier` simultaneously.

## Out of scope (explicit)

- Per-role temperature / max_tokens / timeout / retries — those stay
  in `OpenAICompatProvider.complete()` signature unchanged.
- Provider-level routing (multiple base_urls) — env handles single
  provider per deploy; multi-provider belongs to Agentum.
- Cost telemetry / billing — separate concern.

## Why this branch only ships the spec

Per the intake-routing-and-model-strategy task brief: "If no safe
mechanism exists, do not invent a large routing framework in this
pass. Produce spec + acceptance tests instead." Implementation lands
in a follow-up branch once Agentum signs off on the env naming and
acceptance criteria.
