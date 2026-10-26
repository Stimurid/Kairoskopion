# Scientific evidence consistency — native Kairoskopion QualityGate contract

**Status (26 Oct 2026):** Code integrated into the existing `kairoskopion.quality` API and its `evaluate_submission_gate` function; tested against the original P3c raw model answers. **Not** switched on as a universal, mandatory ArticleSeed promotion guard in every caller. Does **not** issue author consent, create manuscript objects or send to journals.

**Original case:** [Kairoskopion #79](https://github.com/Stimurid/Kairoskopion/issues/79) · [P3c/P3d scientific dossier](https://docs.google.com/document/d/1VxwF0WPsJC9a3g3qUGueByGkmZ-V5RD9kOMRfPq1uKg/edit) · [P3 preregistration and explicit posthoc corrections](https://docs.google.com/document/d/1ScJXccjCwwYaf3IXrcd5-1NRzs2B36pHEjlU37EvNIU/edit)

## Actual source-bound inputs

The callable accepts **actual bytes**, not a model-written “verified: true” declaration:

- Original source bytes + independently registered `expected_source_sha256`.
- Frozen original model packet bytes + separately pinned `expected_packet_sha256`.
- Independent numerical oracle bytes + separately registered `expected_oracle_sha256`.
- Raw, unmodified model response bytes.

The source/oracle/packet pins must come from a **trusted Factory/Litops source registry or owner-pre-registered independent evidence**, NEVER from the language model's JSON, the article narrative, or the candidate packet itself. The function cannot determine whether a caller deceptively supplied fake “trusted” pins; runtime source-registry binding remains a separate, explicit integration requirement before claiming system-wide enforcement.

The oracle (schema `KAIROSKOPION_INDEPENDENT_ORACLE_V1`) binds case, source identity and SHA, criterion revision, selected model, pre-registered rational threshold, actual independently computed per-class integer correct/total counts, and the evaluator's initial-to-final weight history. The model packet (schema `KAIROSKOPION_SCIENTIFIC_EVIDENCE_PACKET_V1`) must match the registered identities and criterion. The checker refuses duplicate JSON keys and non-finite numbers, disjoint/missing class totals, unnormalized weight vectors and mismatched source or oracle digests.

## What the native gate actually decides

- **FULL + model answer correct + independently valid scientific criterion:** `QualityGateStatus.PASSED`. This is *technical source warrant only*, not proof of novelty or author acceptance.
- **FULL + independently invalid scientific criterion:** `FAILED_BLOCKING`, even if the model correctly says `NO/REJECT_CLAIM`. A correct rejection is not an admitted claim.
- **FULL + false verdict, false no-change, forbidden action, changed goal or evidence, broken pins, or invalid JSON:** `FAILED_BLOCKING`.
- **SUMMARY with missing history/holdout and correct `UNDETERMINED/UNDETERMINED/REQUEST_CLASS_EVIDENCE`:** `PASSED_WITH_WARNINGS` for truthful **audit abstention**. This is *not* eligible for claim promotion.
- **SUMMARY with unsupported certainty:** `FAILED_BLOCKING`.

The adapter to the existing native `evaluate_submission_gate` is opt-in by `has_empirical_claim=True` or the presence of `empirical_evidence`; both require full `PASSED` evidence and explicit `author_decision=ACCEPT` plus `coauthor_consent_verified=True` to reach **manual submission readiness**. The function **does not send** anything. This is not yet a cross-cutting check in every ArticleSeed creator; inaccurate upstream empirical-claim classification could omit this guard. That gap MUST be closed by source/claim-level mandatory admission in the existing Factory trunk before declaring production rollout.

## Real replay, not invented clean model outputs

The real P3c raw sources (UCI Sonar / Ionosphere) and frozen 30 model answers were replayed with no new model generation and no retrospective grading changes:

- 15/15 FULL original model answers, which were **already invalid by the original JSON action contract**, were blocked.
- 15/15 SUMMARY correct abstentions were recognized as `PASSED_WITH_WARNINGS`, not admitted scholarly claims.
- All 30 submission-readiness attempts were blocked by the unchanged author/coauthor HOLD.
- Two **synthetic truthful positive fixtures** produced technical `PASSED`, and 13 **synthetic truthful negative fixtures** remained blocked. These 15 fixtures were *not* outputs from the historical model.
- The old invalid FULL answers included 13 false scientific acceptances and 10 false no-change statements (overlapping counts); these were not reclassified as successful.

Owner-private AORUS source replay receipt SHA256: `7997c3c2cdab34ea06589cb1e53c5efe8b8719d8055f51881a924aafe836eede`. Frozen input snapshot SHA256: `f49f6040aef37537a5840ec2f5f6469bacd327d36363317853e168d1e4dc6f06`. Independent NumPy oracle SHA256: `2593e488e34af72c41a7dccf8fffd86a498dcd2395a5ee708ffb85dfefa61c4f`. Original auditor outputs SHA256: `e6278c865927b012267852c6fdc691d85212b705be17776128d52309d78266e6`. Original previous P3d receipt SHA256: `8209224ba7ad996bde5794cc3260657930ac07a1bc43730a18a214071a997e35`.

## Executed test coverage

- `tests/test_scientific_evidence_consistency_gate.py` + existing `tests/test_quality.py`: **46/46 passed**.
- Core neighboring routes and graph tests: **106 passed, 1 skipped**.
- An attempted full-suite run passed 879 tests before hitting an **unrelated Windows long temporary-path error** in `test_fulltext_fallback.py`; the isolated failing test passed with a shorter temp path and full-suite rerun uses that corrected environment. Do not represent partial full-suite as a complete green test run.

## Remaining closure gates (do not call completed)

1. Wire **actual trusted source/oracle pins** from original Litops/Factory source registers, and record durable source-gate receipt in existing Factory case storage, not a new detached runtime.
2. Enforce evidence-consistency result on **all empirical ArticleSeed promotion paths**, not only the optional `evaluate_submission_gate` call.
3. Verify exact author/coauthor authority from real consent records, not a self-declared Boolean field.
4. Execute end-to-end cold readback and relevant CI tests for actual promotion, while preserving ArticleSeed=0, DEEP=0, SEND=0 until user authorization.
5. Independently review the scholarly novelty and existing explanations (Carlile 2002/2004, Star–Griesemer, Galison, ordinary metric QA) before advancing C01-R2/C09-R2 beyond author HOLD.

All rights reserved by original authors. Science/World mutation: **NONE**. External journal sending: **DISABLED**. This code is a verifiable engineering improvement, not a new theory of machine scientific subjectivity.
