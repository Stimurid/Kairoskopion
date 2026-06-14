# State-audit addendum — 2026-06-14 (post Mavrinsky golden-run)

This addendum extends the audit report on `chore/state-audit-2026-06-14`
(see [docs/KAIROSKOPION_STATE_AUDIT_2026_06_14.md](KAIROSKOPION_STATE_AUDIT_2026_06_14.md)
on that branch). It records what changed after the LLM path was
actually exercised against a real Russian philosophical draft on
`fix/llm-agent-tolerance-mavrinsky`.

## Updated to §9 (LLM / prompt reality)

- `gpt-4.1-mini` + `response_format: json_schema strict=true` **hangs**
  through the 302.ai gateway for non-trivial prompts. Isolated by a
  four-cell probe ([docs/LLM_PROVIDER_REALITY_302AI.md §3](LLM_PROVIDER_REALITY_302AI.md#3-known-bad-combinations)).
- `gpt-4o-mini` works through the same gateway but **does not** strictly
  follow `json_schema strict=true`: fences, alias keys, dict-vs-list
  slop are routine. The agents and parser are now tolerant.
- Nine agent/parser/protocol bugs surfaced in real-world output, all
  fixed with 25 regression tests in `tests/test_llm_agent_tolerance.py`.
- `KAIROSKOPION_LLM_TIMEOUT_MS=30000` was too short; the live path now
  defaults to `120000`.
- No manuscript text or LLM raw output is in the repo. `private_inputs/`
  remains `.gitignore`d and verified clean.

## Updated to §1 (executive verdict)

- Backend tests on the LLM-tolerance branch: **1355** (was 1307 on
  `main`, 1330 after FPM + Sprint α).
- LLM path: green on `gpt-4o-mini` via 302.ai with the caveats above.
  Default on a fresh checkout is still deterministic-only.
- Merge plan: [docs/benchmarks/MAVRINSKY_MERGE_PLAN.md](benchmarks/MAVRINSKY_MERGE_PLAN.md).
  Linear stack → FF merge feasible. Tag recommendation
  `v0.2.0-alpha-rc17`.

## What did NOT change

- Public-prod blockers (no auth / no DB / no quotas / no observability).
  The Mavrinsky baseline does not move the prod readiness needle.
- Staging at `kairoskop.mindkampf.ru` — not redeployed in this pass.

## Score reality

Best of three same-config runs: **4 PASS / 3 PARTIAL / 3 FAIL** on the
ten-check rubric. Known FAILs are concentrated on (1) title
extraction, (9) fit_vector in pre-fix snapshots, (10) adaptation
downstream of (9). Details:
[docs/benchmarks/MAVRINSKY_GOLDEN_RUN_REPORT.md](benchmarks/MAVRINSKY_GOLDEN_RUN_REPORT.md).
