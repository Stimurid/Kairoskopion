# TRM-074 / M106: bounded actual model-executed manuscript cycle

Status: AORUS staging adapter on existing **Kairoskopion / Kairon provider**, **not** native Indago/WhiteCrow/ARTIKL execution, not production and not an author-approved scientific result.

## Why this exists

The existing `trimurti_scheduler.py` is a real pre-author route phase scheduler, but `stage_operation.py` explicitly says real Indago/WhiteCrow scholarly adapters remain stubs. The existing `publication_runner.py` imports already prepared publication packages; it does not produce research and manuscript prose. `manuscript_draft_intake.py` now verifies actual produced drafts. This operator closes the **first actual model-worker scheduling gap** without inventing a new graph, source registry, scholarly body or parallel publishing backend.

One bounded CLI invocation:
1. Reads independently pinned author source, scientific revision, baseline manuscript, prior independent review and three M105 research tasks.
2. Calls a **fresh read-only Codex scholarly scout**; requires exactly the three M105 task identities, actual source+science SHA and a modest explicitly unaccepted read-depth.
3. Calls a **separate read-only Codex writer** to produce a full new article version (minimum 2,700 words), not a W12 card.
4. Calls a **separate read-only Codex reviewer** required to bind its review to the newly written bytes SHA.
5. Reuses the existing native `manuscript_draft_intake`: import actual author/science/draft bytes, owner HOLD, immutable receipts, no SEND.
6. Emits a deterministic state snapshot and stops after **one** writer and reviewer; an unresolved scientific objection returns `RESEARCH_EVIDENCE_REENTRY`, not automatic publication.

This executor is an explicit **Codex fallback** until genuine Indago and ARTIKL adapters with source-depth and accepted editorial decision contracts can be wired through the same interface. It must never be labeled as native Indago or as a deployed ARTIKL organ.

## Private manifest

Schema `trimurti-manuscript-cycle-v1`; `artifacts` exactly `source/science/baseline/review/research_tasks`, each a relative path within `--input-root` and sha256. Flags `evidence_mode=REAL`, `author_gate=HOLD`, `submit=false`, `article_seed_accepted=false`, `worker=CODEX_SCHOLAR_WRITER_REVIEWER_NOT_NATIVE_INDAGO`, `max_writer_calls=1`, `max_review_calls=1` required. Manifest itself is *not* an author approval.

**Four SHA pins must come from a separately trusted source outside the model-authored manifest** (for C04: scientific Git, exact original-byte registry, M104 reviewer). This operator checks those exact bytes before any model invocation. The private input workspace and provider transcripts must not enter a public engineering Git repository.

PowerShell form (run with `PYTHONPATH=src`):

```powershell
python -m kairoskopion.kairon_provider.manuscript_cycle_runner --manifest <PRIVATE_MANIFEST> --input-root <PRIVATE_INPUT> --output-root <PRIVATE_RUNS> --scientific-repo <PRIVATE_SCIENTIFIC_REPO> --trusted-source-sha256 <PIN_FROM_REGISTRY> --trusted-science-sha256 <PIN_FROM_GIT> --trusted-baseline-sha256 <PIN_FROM_GIT> --trusted-review-sha256 <PIN_FROM_INDEPENDENT_REVIEW> --timeout-seconds 450
```

The cycle ID binds all input and manifest SHA values. Each successful stage is an immutable file and a content-hashed stage event in `state.json`. Re-running the same command independently verifies all bound inputs and existing outputs and **makes no repeated provider calls**. If interrupted after a stage receipt, restart continues from the next stage. If a provider process wrote output but exited before a verified receipt, the operator blocks on an **orphan**, requiring explicit inspection rather than silently adopting untrusted text. Any changed previous output, source, science, baseline, reviewer or manifest blocks.

A model's self-declared scholarly discovery, full text claim or author sign-off **never** changes SOURCE/W12/ArticleSeed/AUTHOR status. This CLI is not the D25 acceptance authority, neither does it make a legal journal submission. It does not rewrite historical accepted versions.

## Acceptance limits

Scientific review is by a distinct model session, not guaranteed independent institutional peer review; digest binding and reviewer JSON shape are deterministic checks, semantic source-depth review is still required. Scholarly scout may use previously acquired local text or explicitly mark abstract-only; it must not claim that referenced books/articles were truly retrieved in full without exact byte evidence. The full native Indago connection is still unimplemented.

A real AORUS case M106 is admissible only after (a) exactly three actual model stages, (b) 2,700+ word draft under author's source and science pins, (c) reviewer digest of draft equals observed SHA, (d) existing draft intake receipt and repeated no-reexecution readback, (e) no canonical author approval or journal send, (f) source/negative reviews and full private logs retained. A mock test cannot be reported as a real science case.

Stop conditions: native scholar evidence unproven, reviewer `REVISION_REQUIRED`, stalled/broken model call, source/manifest drift, tamper, or explicit author HOLD. Do not create new ArticleSeed/W12 merely by writing an article; do not merge/deploy automatically.

Related: Kairoskopion #43/#51/#77 and draft PR #84; scientific Git M101–M105.
