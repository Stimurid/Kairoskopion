# TRM-074: manuscript production output intake (author HOLD)

This is a **bounded adapter to the existing Kairoskopion / Trimurti publication Factory**, not a new writing engine, not a completed self-running author, and not a submission actuator.

The gap established on 2026-11-03: W1/W2/WhiteCrow→W3/W12 currently produces journal research routes and author-held claims but does not itself produce a substantive article manuscript. The existing `publication_runner` only imports already prepared evidence and enforces state-machine controls, without transforming a source into prose. A separately running author/editor may produce a draft; this module imports that output with protected provenance before later D14–D27 and D25 review.

## Existing seams, kept distinct

- Indago + WhiteCrow: research and scholarly argument, source-depth and opposition.
- Artikl: produces and revises the scholarly manuscript (actual provider/agent execution still separate).
- `manuscript_draft_intake.py`: verifies pinned original, pinned scientific state and draft file **on every replay**; emits immutable `DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED` receipt.
- Kairoskopion venue/fit and existing `publication_runner`: independent target requirements, QA and submission package only after trusted owner gates.
- Author gate: always HOLD here. A model-written JSON cannot certify approval, scientific novelty, D25 `MANUSCRIPT_GO` or external SEND.

## Local operator

Create a private `input-root` containing actual bound copies of source, scientific packet, and UTF-8 draft. The manifest (below) is also kept private and carries relative paths plus exact SHA-256 hashes. The `source_original_sha256` must match the **original author's bytes**, not a modified export. The agent/producer should be identified with an execution receipt, not just the assistant's summary.

```json
{
  "schema": "trimurti-manuscript-draft-intake-v1",
  "case_id": "T3-TALK-20261019",
  "claim_id": "KC-C04-GUARMEAS-JIBE-CRESTI",
  "route_id": "C-GUARMEAS-JIBE-CRESTI",
  "producer_ref": "C04-agent-run-exact-session-or-log",
  "evidence_mode": "REAL",
  "author_gate": "HOLD",
  "submission_enabled": false,
  "scientific_novelty_accepted": false,
  "article_seed_author_approved": false,
  "source_original_sha256": "<64-lowercase-hex>",
  "artifacts": {
    "source": {"path": "original.txt", "sha256": "<64-lowercase-hex>"},
    "science": {"path": "science.json", "sha256": "<64-lowercase-hex>"},
    "draft": {"path": "draft.md", "sha256": "<64-lowercase-hex>"}
  }
}
```

Run from repository root (with `PYTHONPATH=src`):

```bash
python -m kairoskopion.kairon_provider.manuscript_draft_intake --manifest /private/manifest.json --input-root /private/input --output-root /private/receipts
```

On success: status `DRAFT_CAPTURED_AUTHOR_REVIEW_REQUIRED`, pinned source/science/draft SHA, observed draft bytes/word count, `new_w12_routes=0`. **Not full-text scientific QA**. On any stale/tampered source or changed immutable prior receipt, the operator blocks. Production/remote deploy remains forbidden until separate approval.

## Technical acceptance evidence, 2026-11-03

Tests: `tests/test_manuscript_draft_intake.py` + existing `tests/test_publication_runner.py`: 86 passed on authorized AORUS. This is code-only acceptance. Evidence from a specific C04 draft, cross-process cold replay, D14/D21/D27 independent review, actual model worker scheduling and publication-Factory end-to-end sequencing are separately required. Do not inflate W12 or ArticleSeed.

Related: Kairoskopion #43, #51 and publication operator PR #46/#76. Files derived from private C04 must NOT be committed to public Kairoskopion.
