# TRM G6B — typed Indago R3 evidence-return bridge

Date: 2026-10-22  
Scope: additive local consumer only; no merge, deploy, submission, manuscript edit, or external provider call.

## Result

Implemented `src/kairoskopion/services/citation_indago_r3_bridge.py`, a strict consumer for a recorded `trm-indago-evidence-return-v1` envelope. It binds the return to the immutable Z0 audit and exact citation work order, converts a unique anchored passage to an R1-compatible case state, and can pass that state into the existing R2–R4 planner. A replay-safe CLI is available through:

```text
python -m kairoskopion.services.citation_indago_r3_bridge \
  --audit <citation_intake.json> \
  --queue <citation_work_orders.jsonl> \
  --return-file <evidence-return.json> \
  --ledger <local-ledger-directory>
```

The module is deliberately not an Indago network/provider client.

## Safety and evidence behavior

- Requires exact `case_id`, `work_order_id`, `intake_id`, and manuscript SHA binding. Unknown orders, stale manuscripts, and wrong cases fail closed.
- Requires the source chain `work_id → edition_id → witness_id → passage_id`; each passage must repeat the same work/edition/witness identity as the source.
- Requires attested locator, stable text digest, and occurrence count. If exact text is carried, its digest is recomputed.
- More than one matched passage yields `ANCHOR_AMBIGUOUS`; the first passage is never guessed.
- Stable `evidence_id` is derived from the bound evidence. An identical `return_id` replays idempotently; reuse with changed evidence is refused.
- `NO_PASSAGE`, negative hunts, ambiguity, and provider failures remain negative evidence. Every emitted state keeps `source_to_claim_relation=NOT_CHECKED`; none proves an existing author citation wrong.
- V1–V5 remain `NOT_CHECKED`, `scientific_certification=false`, `citation_gate=NOT_PUBLICATION_READY`, and `author_gate=PENDING`.
- `access_origin` is descriptive only. `OWNER_HELD_PDF` / `OWNER_ARCHIVE` is accepted without a publisher-payment or publisher-provenance gate.
- DOI/work metadata alone cannot create an anchored state: `MATCHED` requires one unique, validated passage.

## Fixtures and tests

Added a real-shape recorded fixture at `tests/fixtures/indago_evidence_return_real_shape.json`. Its content is synthetic and explicitly not a scientific quotation. Added eight tests covering unique happy path, no passage, ambiguity, provider failure, replay, wrong case/orphan work order, fake/cross-source anchors, and a typed Z0/R1/R3/R2–R4 integration receipt.

Executed `python scripts/trm_g6_source_preflight.py`. Result: `SOURCE_PACK_VISIBLE_AND_INTACT` with 12 actual PDF witnesses, 171 extracted pages, 92 index records, 8 analog backlog records, and 0 scientifically qualified pairs.

Targeted test execution used an in-process Windows `os.mkdir` mode normalization because this managed sandbox rejects pytest's mode-0700 temporary directories before test setup. No product behavior was monkeypatched. Results:

```text
tests/test_citation_indago_r3_bridge.py: 8 passed
bridge + Z0 + R1 + R1 batch/corpus/replay + R2-R6 regression: 132 passed
```

## Currentness retained

The 20 seeds and older F03/F08/F01-B/F12/F13 trajectories are unchanged. The eight G3 ArticleModels and 100 G4 seed-target rows remain historical hypotheses with zero qualified pairs. This work changes transport/integration behavior only; it makes no novelty, journal-fit, coauthor-authorization, or submission claim.

## Open status

Real Indago provider execution: **OPEN — NOT DEMONSTRATED**. The receipt says `OPEN_NOT_DEMONSTRATED`. No external provider was invoked during this task.
