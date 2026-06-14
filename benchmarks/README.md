# Kairoskopion benchmarks

This directory holds **rubrics**, not data. Source manuscripts and run
outputs stay outside the repo.

```
benchmarks/
  README.md                          ← you are here
  golden/
    mavrinsky_article_side_gold.md   ← rubric for the Mavrinsky baseline
```

The current baseline is `mavrinsky_baseline_2026_06_14` (see
[`docs/benchmarks/MAVRINSKY_GOLDEN_RUN_REPORT.md`](../docs/benchmarks/MAVRINSKY_GOLDEN_RUN_REPORT.md)
for results).

---

## What runs where

| input | location | committed? |
|---|---|---|
| source manuscript (the article text) | `private_inputs/<name>.txt` | **NO** — `.gitignore`d |
| scenario JSON | `private_inputs/scenarios/<name>.json` | **NO** |
| per-run dossier and stage artifacts | `private_inputs/runs/<run_id>/` | **NO** |
| sanitized score JSON | `private_inputs/runs/<run_id>/SCORE.json` | **NO** |
| rubric / expectation | `benchmarks/golden/<name>_gold.md` | YES |
| baseline summary report | `docs/benchmarks/<NAME>_REPORT.md` | YES (sanitized) |

A sanitized summary may quote the rubric but must not paste the
manuscript body.

---

## Running the Mavrinsky benchmark locally

### 1. Provide private inputs (not committed)

```powershell
# article text (UTF-8, plain or extracted from PDF/DOCX)
$env:KAIROSKOPION_BENCHMARK_ARTICLE = "C:\path\to\mavrinsky_article.txt"

# optional scenario JSON (defaults to a reasonable shape if omitted)
$env:KAIROSKOPION_BENCHMARK_SCENARIO = "C:\path\to\mavrinsky.json"
```

### 2. Configure an LLM provider (optional but recommended)

A real benchmark needs a real LLM. Without it the runner FAILS LOUDLY
(it does not silently fake success). Put the credentials in `.env`
(already `.gitignore`d):

```env
KAIROSKOPION_LLM_PROVIDER=openai_compatible
KAIROSKOPION_LLM_MODEL=gpt-4o-mini
KAIROSKOPION_LLM_BASE_URL=https://api.302.ai/v1
KAIROSKOPION_LLM_API_KEY=sk-...
KAIROSKOPION_LLM_TIMEOUT_MS=120000
```

See [`docs/LLM_PROVIDER_REALITY_302AI.md`](../docs/LLM_PROVIDER_REALITY_302AI.md)
for known 302.ai-gateway quirks (gpt-4.1-mini + strict json_schema
hangs; gpt-4o-mini works; outputs may be fenced).

### 3. Run

```powershell
python scripts/run_mavrinsky_benchmark.py `
    --article  $env:KAIROSKOPION_BENCHMARK_ARTICLE `
    --scenario $env:KAIROSKOPION_BENCHMARK_SCENARIO `
    --output   private_inputs/runs/mavrinsky_$(Get-Date -Format "yyyyMMdd_HHmmss") `
    --require-llm
```

`--require-llm` makes the runner exit with a non-zero status if no LLM
credentials are configured. Omit it to allow a deterministic-only run
(useful for sanity-checking the harness, not for scoring against the
rubric).

The runner writes 16 staged JSON files plus a full snapshot to the
output directory.

### 4. Score against the rubric

```powershell
python scripts/score_against_gold.py `
    --run    private_inputs/runs/mavrinsky_20260614_111122 `
    --output private_inputs/runs/mavrinsky_20260614_111122/SCORE.json
```

The scorer reads the run directory only — never the manuscript text.

---

## Reproducibility envelope

Live-LLM runs are stochastic. A single PASS/PARTIAL/FAIL number is not
the baseline. The baseline is:

- median of 3 consecutive same-config runs ≥ recorded median,
- no previously-PASSED check drops to FAIL more than once in 3 runs.

When introducing a new model, prompt, or fix:

1. Record 3 runs.
2. Report best, median, worst score.
3. Update the baseline file (do not overwrite the previous baseline).

---

## CI

The benchmark is **not** part of `pytest`. The deterministic
unit-test suite (`pytest`) covers the agent-tolerance and parser fixes
that make the live run survive 302.ai gateway quirks. A live LLM call
is never made during normal `pytest`.

A pytest-marked integration test that opt-in skips unless
`KAIROSKOPION_BENCHMARK_LIVE=1` is set may be added later.
