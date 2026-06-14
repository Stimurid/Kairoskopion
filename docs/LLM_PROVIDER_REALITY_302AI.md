# LLM provider reality — 302.ai gateway

This document records what Kairoskopion's LLM-optional agents actually
observe when talking to the 302.ai OpenAI-compatible gateway. It is a
**post-experiment field note**, not aspirational documentation.

> If you change provider, model, or `response_format` strategy,
> re-run the four-cell isolation probe in §3 and update this file.

---

## 1. Configuration (with secrets never committed)

All provider configuration lives in `.env` in the repo root
(`.gitignore`'d) and is read via `python-dotenv` by every Kairoskopion
entry point that needs an LLM.

```env
KAIROSKOPION_LLM_PROVIDER=openai_compatible
KAIROSKOPION_LLM_MODEL=gpt-4o-mini
KAIROSKOPION_LLM_BASE_URL=https://api.302.ai/v1
KAIROSKOPION_LLM_API_KEY=sk-...                # never commit
KAIROSKOPION_LLM_TIMEOUT_MS=120000             # 30000 is too short for big prompts
```

Defaults if no `.env` is present:

- `LLMConfig.from_env()` returns `None`,
- all `llm_optional` agents fall through to their deterministic path,
- the benchmark harness in `scripts/run_mavrinsky_benchmark.py`
  refuses to score when called with `--require-llm` and the provider
  is not configured (it does not silently fake success).

No user manuscript text is sent to any external LLM unless the
operator deliberately configures the key.

---

## 2. Known good combinations

| model | strict json_schema | result |
|---|---|---|
| `gpt-4o-mini` | yes | works; output sometimes fenced (` ```json … ``` `) |
| `gpt-4o-mini` | no (`json_object` or none) | works, faster |
| `gpt-4.1-mini` | **no** (no `response_format` at all) | works |
| `deepseek-chat` | not measured | flagged as cheap fallback by operator; needs probe |

---

## 3. Known bad combinations

| model | strict json_schema | input size | result |
|---|---|---|---|
| `gpt-4.1-mini` | **yes** | ≥ 8 KB | **hangs ≥ 90 s** then `read timeout` |
| `claude-3-5-haiku-latest` via `/chat/completions` | n/a | n/a | gateway returns HTTP 404 (route does not accept this Claude id) |

The 302.ai gateway does **not reliably** enforce
`response_format: json_schema` with `strict: true` on `gpt-4.1-mini`
for non-trivial prompts. Whether the failure is upstream model
behaviour or gateway translation is not knowable from outside; it is
observed and reproducible.

### Isolation probe (run before any model swap)

```python
import json, time, urllib.request

KEY = "..."
URL = "https://api.302.ai/v1/chat/completions"
schema = {
    "type": "object",
    "properties": {"title": {"type": "string"}, "topic": {"type": "string"}},
    "required": ["title", "topic"],
}
big = ("Abstract: ..." * 200)[:8000]

cells = [
    ("A small no-schema", {"model": "gpt-4.1-mini", "max_tokens": 32,
     "messages": [{"role": "user", "content": "Return {\"title\":\"x\"}"}]}),
    ("B big   no-schema", {"model": "gpt-4.1-mini", "max_tokens": 400,
     "messages": [{"role": "user", "content": f"Extract title:\n{big}"}]}),
    ("C big   strict-schema (the bad cell)", {
        "model": "gpt-4.1-mini", "max_tokens": 400,
        "messages": [{"role": "user", "content": f"Extract title:\n{big}"}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "o", "strict": True,
                                            "schema": schema}}}),
    ("D big   strict-schema, 4o-mini", {
        "model": "gpt-4o-mini", "max_tokens": 400,
        "messages": [{"role": "user", "content": f"Extract title:\n{big}"}],
        "response_format": {"type": "json_schema",
                            "json_schema": {"name": "o", "strict": True,
                                            "schema": schema}}}),
]
for label, body in cells:
    t = time.monotonic()
    try:
        req = urllib.request.Request(URL, data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {KEY}",
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=90) as r:
            _ = r.read()
        print(f"{label:40} OK  {time.monotonic()-t:.1f}s")
    except Exception as e:
        print(f"{label:40} FAIL t={time.monotonic()-t:.1f}s {type(e).__name__}")
```

Expected baseline as of 2026-06-14:

```
A small no-schema                        OK   3.1s
B big   no-schema                        OK   4.2s
C big   strict-schema (the bad cell)     FAIL  ~90s TimeoutError
D big   strict-schema, 4o-mini           OK  ~29s
```

---

## 4. Output-shape quirks the agents are tolerant to

Even with `strict: true` set in the request, observed responses do
**not** strictly match the schema. The OpenAICompatProvider and the
LLM-optional agents are deliberately tolerant.

### JSON wrapping

Observed forms:

- bare JSON: `{"title": "..."}` — handled
- fenced: ` ```json\n{...}\n``` ` — handled by `_parse_json_robust`
- prose + JSON: `"Here is the analysis: {...} hope this helps."` —
  handled by extracting the largest balanced `{…}` block

### Key-name aliases

| agent | expected key | observed alternatives |
|---|---|---|
| `article_modeler` | `protected_core_candidate` | `protected_core`, `protected_core_candidates`, `core_protection` |
| `article_modeler` | `title` | `title_current`, `title_ru`, `title_en`, `title_extracted` |
| `disciplinary_mapper` | `pathways` | `ranked_pathways`, `disciplinary_pathways` |
| `disciplinary_mapper` | `discipline_name` | `discipline`, `pathway_name`, `name` |
| `disciplinary_mapper.fit_strength` | enum `{strong, medium, weak, …}` | `very_high`, `high`, `medium_strong`, `weak_medium`, `very_low`, `moderate` |
| `fit_assessor` | `axes: list[dict]` | `axes: dict[axis_name → detail]`, also `fit_axes`, `fit_vector`, `dimensions`, `assessments` |
| `fit_assessor.axes[].value` | `value` | `status`, `strength`, `rating` |
| `fit_assessor.axes[].reasoning` | `reasoning` | `notes`, `explanation`, `rationale` |

### Type slop

- `protected_core` returned as a single string instead of `list[str]`
  → `article_modeler._to_list` coerces to a one-element list.
- vector entries returned as `{"discipline": {"value": 0.3}}` instead
  of `{"discipline": 0.3}` → `field_position_fit._num()` unwraps
  `{value/center/score/weight: x}`.

### Stochasticity

Three same-config runs of the Mavrinsky baseline yielded
`4 PASS / 4 PASS / 3 PASS` distribution. The pipeline does not chase a
single number; the rubric uses median of 3 and a "no previously-PASSED
check drops to FAIL more than once" stability rule (see
`benchmarks/golden/mavrinsky_article_side_gold.md`).

---

## 5. Practical recommendations

1. **Default to `gpt-4o-mini` on the 302.ai gateway** until the
   strict-schema regression on `gpt-4.1-mini` is resolved.
2. **Do not chase missing fields with prompt hacks.** Make the agents
   tolerant in code; document each new alias.
3. **Keep `temperature` configurable per call site.** Article
   extraction wants `temperature=0`. Pathway / fit
   *reasoning* probably wants 0.2–0.4. Creative reframing (when we
   eventually add it) wants higher. Today the values are hard-coded;
   centralising them in `LLMConfig` is a clean future change.
4. **Strict schema is advisory through 302.ai.** Treat
   `response_format: json_schema strict=true` as a *hint*, not a
   guarantee. Always run output through `_parse_json_robust`.
5. **Re-run the §3 isolation probe** before any model swap.

---

## 6. Out of scope for this doc

- Other gateways (OpenAI direct, Anthropic, Azure) — not measured yet.
- Streaming responses — not used; we read full body.
- Tool-calling / function-calling — not used.
- Embeddings — not used by Kairoskopion.
- Cost / token-budget accounting — handled elsewhere (or not yet).
