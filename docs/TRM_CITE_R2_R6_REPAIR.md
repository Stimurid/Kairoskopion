# TRM-CITE-002: R2-R6 citation repair (author-gated, reversible, read-only by default)

Status: **code candidate in an isolated worktree. Not merged, not deployed, not a
certified citation verifier.** No real or private author manuscript was read,
written or repaired by this run.

Base commit: `0843839fa33714686096220d671d9447689144f5`.

## What this is

The first callable machine vertical slice of the R2 -> R3 -> R4 -> R5 -> R6 loop
that `citation_intake_z0.py` already names in its `required_operations`. It
turns an **immutable Z0 audit** plus any **existing R1 case states** into typed
objects, and refuses to go further than the evidence supports.

Module: `src/kairoskopion/services/citation_repair_r2_r6.py`
(VERSION `trm-cite-r2-r6-v01`). CLI: `kairoskopion cite-repair`.

## The five objects

| Stage | Object | Contract |
|---|---|---|
| R2 | `IntentReconstruction` | existing claim + context, `desired_support`, verbatim source refs, explicit `uncertainties`, `author_confirmed: false`, `citation_certified: false` |
| R3 | `ResearchReentry` | a **new bounded** request emitted **only** when no carried evidence answers R2; carries prior negative evidence; `supersedes_prior_requests: false`; Indago provenance preserved |
| R4 | `RepairCandidate` x6 | distinct repairs, differing intellectual cost, explicit source-to-claim relation, source/debt explanation, `author_gate: PENDING`, `auto_approved: false` |
| R5 | `ProposalPatch` | exact target manuscript SHA, Z0 anchor, original fragment + old-text SHA, suggested new text, whole-file forward and inverse diff, `author_gate: PENDING`, `manuscript_mutated: false` |
| R6 | `PostPatchCheck` | re-intake of the applied **copy** through the same Z0, retained scientific debt, never a fabricated V1-V5 pass |

R4 repertoire and its source-to-claim relation:

- `BIBLIOGRAPHY_DETAIL_REPAIR` (LOW) - identity corrected, argumentative support still unreviewed.
- `CHANGE_SOURCE` (HIGH) - a new source must carry the existing claim.
- `PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY` (MEDIUM) - source decoupled; the claim is attributed to the author, not to the source.
- `WEAKEN_OR_SPLIT_THESIS` (HIGH) - claim scope reduced to what the source establishes.
- `REMOVE_UNSUPPORTED_CITATION` (MEDIUM) - claim kept, source link deleted.
- `ABSTAIN_NO_CHANGE` (NONE) - no change; debt stays open.

The `PRESENT_NORMATIVE...` relation exists because of the concrete finding in
`docs/TRM_CITE_R1_READER.md`: a publisher article about assessment does **not**
establish the author's stronger norm that a student must reconstruct, test and
transfer the practice that produced the result. The machine must be able to
offer that repair **and** record that it cannot judge whether it is right.

## Author decision is external and bound

`DecisionReceipt` (`trm-cite-r2-decision-receipt-v1`) binds an approval to
`original_manuscript_sha256`, `claim_id`, `candidate_id`, `diff_sha256`,
`original_text_sha256`, **`new_text_sha256`**, the `decision` and the verbatim
`user_input`.

**This module has no function that mints a receipt.** A structural test asserts
that the only receipt-named callables exported are `receipt_identity`,
`receipt_mac` and `validate_decision_receipt`, that no `mint/issue/approve/
authorize/forge` entry point exists, and that **no code path persists a decision
receipt** — an approval is author input, never a pipeline output. An
assistant-generated JSON file is not treated as an approval because:

- `issued_by != "AUTHOR"` -> refused.
- `issuer_role` in `{AI, ASSISTANT, AGENT, MODEL, LLM, AUTOMATION, PIPELINE}` -> refused.
- `witness_class` outside `{HUMAN_AUTHOR_DECISION, SYNTHETIC_TEST}` -> refused.
- `receipt_id` must equal the deterministic identity of the receipt's own
  content **including `synthetic`, `witness_class`, `issuer_role` and
  `decision`**, so it can neither be forged nor re-pointed.
- `decision` must be `APPROVE`; `REJECT` / `REQUEST_REVISION` apply nothing.
- `synthetic: true` or `witness_class: "SYNTHETIC_TEST"` is refused unless the
  caller passes `allow_synthetic_test=True` **from Python**. No command-line
  surface exposes that switch.

### The approval covers the bytes, not a description of them

`apply_patch` recomputes the whole-file diff from the manuscript and requires
it to equal the diff the author signed, and recomputes the inverse diff too. An
approval therefore cannot be replayed against different text. This was found by
review: before the fix, an author could approve a citation *deletion* while an
arbitrary paragraph was written to disk, with every signed field byte-identical.

### Provenance limit (stated honestly)

On a single shared machine a peer process can write any file, so this code
cannot cryptographically establish *who* wrote a receipt. The defence against
that is **operator and process control**, not this module. For an author who
wants a cryptographic signal, `receipt_mac` provides HMAC-SHA256 over the
receipt identity under an author-held key, verified when `author_key` is
supplied (`--author-key-file` on the CLI). The key is never stored, logged, or
included in any receipt. Treat a receipt as author-attested only when it
arrived through a channel the author controls.

## What is deliberately absent

- **The machine never writes scholarly prose.** Only
  `REMOVE_UNSUPPORTED_CITATION` is machine-renderable, and only as a structural
  deletion of the verified fragment. Every other kind returns
  `BLOCKED_NO_SUGGESTED_TEXT` until the author or analyst supplies wording via a
  `trm-cite-r5-candidate-text-v1` file.
- **No repair is offered that asserts an unevidenced defect.** Deleting a
  citation is refused unless an identified source witness was actually
  consulted (SECTION_TEXT or stronger) and R1 explicitly records
  DOES_NOT_SUPPORT_CLAIM together with a negative finding. A BLOCKED/ERROR
  lookup or an OBSERVED transport alone cannot establish a defect.
  An **anchored passage on record vetoes removal** — the machine will not propose deleting a citation it holds
  evidence supports, whatever else is on file.
- **No source search, no fetch, no provider.** R3 is `QUEUED_NOT_EXECUTED` and
  `acquisition_authorized_by_this_object: false`.
- **No V1-V5 promotion anywhere.** R6 always returns all five keys as
  `NOT_CHECKED` with `scientific_status: DEBT_RETAINED_NO_PUBLICATION_PASS`,
  even after a perfectly clean apply. Transport is not certification.
- **No DOCX/PDF claim.** R5 anchoring and apply are implemented only for the
  `line:` body sections of UTF-8 `.md`/`.txt`. DOCX, PDF and structured
  envelopes are refused with an explicit `BLOCKED` status. A native editor
  service is still required; this run did **not** fake DOCX coverage.

## CLI

```powershell
# 1. plan (default action, read-only)
kairoskopion cite-repair plan `
  --audit  <z0>/citation_intake.json `
  --case   cr_<...> `
  --manuscript <local original> `
  --queue  <z0>/citation_work_orders.jsonl `
  --prior-state <r1 states dir> `
  --out <fresh private dir>

# 2. apply, only against an author-issued receipt, onto a FRESH copy
#    --author-key-file verifies the author's HMAC over the receipt
kairoskopion cite-repair apply `
  --manuscript <local original> --proposal plan.json `
  --receipt decision_receipt.json --copy <new path> --out <dir> `
  [--author-key-file <path outside the repository>]

# 3. R6 readback -> exit code 3 (scientific debt, not a pass)
kairoskopion cite-repair check `
  --proposal plan.json --apply-receipt apply_receipt.json --copy <new path> --out <dir>

# 4. undo -> restores exact original bytes from the Z0 snapshot
kairoskopion cite-repair undo `
  --apply-receipt apply_receipt.json --copy <new path> `
  --original-snapshot <z0>/original_snapshots/<sha>.md --restored <new path> --out <dir>
```

`plan` is the default when the mode is omitted. Plan/apply/undo exit `0` on
success and `2` on any typed refusal; `check` exits `3` to keep "technical
readback succeeded" from being read as "science passed".

## Recorded stage result (fictional synthetic Markdown, one blocked hunt)

`trm-cite-r2-r6-plan-v1`, trimmed for length. Note what it does **not** say:
V1-V5 stay `NOT_CHECKED`, every proposal is `PENDING`, and the one renderable
repair is the structural citation deletion — every prose-bearing repair is
`BLOCKED_NO_SUGGESTED_TEXT` because no author wording was supplied.

```json
{
  "schema": "trm-cite-r2-r6-plan-v1",
  "repair_version": "trm-cite-r2-r6-v01",
  "r2_intent": {
    "schema": "trm-cite-r2-intent-v1",
    "citation_kind": "AUTHOR_YEAR",
    "desired_support": "WORK_EDITION_WITNESS_IDENTITY_PLUS_A_PASSAGE_THAT_ENTAILS_THE_CLAIM",
    "verbatim_source_refs": ["Ferrow 2014"],
    "reconstruction_mode": "PROVISIONAL_FROM_Z0_EVIDENCE_ONLY",
    "uncertainties": [
      "AUTHOR_INTENT_NOT_CONFIRMED_WITH_THE_AUTHOR",
      "CLAIM_SUPPORT_NOT_INDEPENDENTLY_VERIFIED",
      "NEGATIVE_EVIDENCE_REQUIRES_NEW_SOURCE_SEARCH",
      "NO_OPERATOR_NOTE_SUPPLIED",
      "ORIGINAL_MANUSCRIPT_MUST_STAY_BYTE_IDENTICAL",
      "VENUE_STYLE_PROFILE_NOT_SUPPLIED"
    ],
    "author_confirmed": false,
    "citation_certified": false
  },
  "r3_reentry": {
    "schema": "trm-cite-r3-reentry-v1",
    "execution_status": "QUEUED_NOT_EXECUTED",
    "acquisition_authorized_by_this_object": false,
    "supersedes_prior_requests": false,
    "indago_hunt": "INDAGO_BOUNDED_HUNT_REQUIRED",
    "reason_codes": ["NEGATIVE_EVIDENCE_REQUIRES_NEW_SOURCE_SEARCH",
                     "NO_ANCHORED_PASSAGE_EVIDENCE_ON_RECORD"],
    "carries_negative_evidence": ["AUTHORIZED_READER_NOT_EXPOSED"]
  },
  "r4_candidates": [
    {"kind": "BIBLIOGRAPHY_DETAIL_REPAIR", "intellectual_cost": "LOW",
     "applicable": false, "refusal_codes": ["NO_OBSERVED_SOURCE_IDENTITY_TO_CORRECT"],
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false},
    {"kind": "CHANGE_SOURCE", "intellectual_cost": "HIGH", "applicable": true,
     "source_to_claim_relation": "NEW_SOURCE_MUST_CARRY_THE_EXISTING_CLAIM",
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false},
    {"kind": "PRESENT_NORMATIVE_AUTHOR_CONCLUSION_EXPLICITLY", "intellectual_cost": "MEDIUM",
     "source_to_claim_relation": "SOURCE_DECOUPLED_CLAIM_ATTRIBUTED_TO_THE_AUTHOR_NOT_TO_THE_SOURCE",
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false},
    {"kind": "WEAKEN_OR_SPLIT_THESIS", "intellectual_cost": "HIGH", "applicable": true,
     "source_to_claim_relation": "CLAIM_SCOPE_REDUCED_TO_WHAT_THE_SOURCE_ESTABLISHES",
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false},
    {"kind": "REMOVE_UNSUPPORTED_CITATION", "intellectual_cost": "MEDIUM", "applicable": true,
     "source_to_claim_relation": "CLAIM_RETAINED_SOURCE_LINK_DELETED",
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false},
    {"kind": "ABSTAIN_NO_CHANGE", "intellectual_cost": "NONE", "applicable": true,
     "author_gate": "PENDING", "auto_approved": false, "verification_certified": false}
  ],
  "r5_proposals": [
    {"applicability": "NOT_APPLICABLE_NO_OBSERVED_SOURCE_IDENTITY_TO_CORRECT"},
    {"applicability": "BLOCKED_NO_SUGGESTED_TEXT",
     "debts": ["SUGGESTED_TEXT_MUST_COME_FROM_THE_AUTHOR_OR_ANALYST"]},
    {"applicability": "BLOCKED_NO_SUGGESTED_TEXT",
     "debts": ["SUGGESTED_TEXT_MUST_COME_FROM_THE_AUTHOR_OR_ANALYST"]},
    {"applicability": "BLOCKED_NO_SUGGESTED_TEXT",
     "debts": ["SUGGESTED_TEXT_MUST_COME_FROM_THE_AUTHOR_OR_ANALYST"]},
    {"applicability": "READY_FOR_AUTHOR_REVIEW",
     "debts": ["AUTHOR_REVIEW_REQUIRED_BEFORE_ANY_APPLY"],
     "author_gate": "PENDING", "manuscript_mutated": false, "applied": false},
    {"applicability": "NO_CHANGE_PROPOSED", "debts": ["ABSTAIN_CARRIES_NO_PATCH"]}
  ],
  "verification": {"V1": "NOT_CHECKED", "V2": "NOT_CHECKED", "V3": "NOT_CHECKED",
                   "V4": "NOT_CHECKED", "V5": "NOT_CHECKED"},
  "citation_gate": "NOT_PUBLICATION_READY",
  "source_certification": "NONE_TRANSPORT_IS_NOT_CERTIFICATION"
}
```

## Fail-closed conditions

Every one of these is a typed refusal (stable `RepairRefusal.code`), never a
degraded success, and never a raw `KeyError`:

- wrong or drifted `source_sha256` (audit vs. file on disk, and at apply time);
- recomputed patched SHA or diff differing from the proposal;
- anchor locator absent, anchor offsets out of range or non-integer, anchor
  offsets not matching the recorded fragment;
- **colliding** anchor text (fragment not unique in its section);
- replacement text that does not contain the verified fragment;
- a proposal missing any field the apply/readback reads;
- a proposal whose `patch_id` does not match its own intent and candidate;
- no repair applicable because the evidence does not support asserting a defect;
- a no-op proposal;
- receipt not bound to this exact patch, or `receipt_id` not matching content;
- receipt `receipt_mac` not matching the author key, or an unreadable key file;
- applying onto the original, or onto an existing file;
- `R6` without a real apply receipt, on a drifted copy, on an unchanged copy,
  with a proposal from a different patch, without the original manuscript path,
  or with an original that changed after apply;
- `undo` with a drifted copy, a missing snapshot, or a mismatched original SHA;
- `case_id` that is not a plain filename component (path traversal);
- prior R1 state bound to a different manuscript version.

Replay is immutable: every artifact is written through
`citation_intake_z0._write_immutable`. Re-planning the same inputs reproduces the
same bytes and the same ids.

## Independent review history

Three adversarial review rounds were run against this module.

1. Found a **CRITICAL** flaw: the receipt bound a diff but the applied text was
   never checked against it, so an author approving a citation deletion could
   have an unrelated paragraph written instead, with every signed field
   byte-identical. Reproduced, then fixed by binding `new_text_sha256` and
   recomputing the full diff at apply time.
2. Found the author gate was **unauthenticated** (an unkeyed identity can be
   hand-minted), that `R6` could silently skip original re-verification, that
   an anchored passage did not veto citation deletion, and that five load-bearing
   checks were untested. All addressed; the false docstring claim was replaced
   with an honest statement of the provenance limit, and the optional keyed
   `receipt_mac` was added.
3. Found raw `KeyError` escapes on forged proposals (breaking the typed-refusal
   contract) and one misleading test. Fixed by validating the whole proposal
   shape up front in both `apply_patch` and `post_patch_check`.

Ten security guards were mutation-tested: disabling each one individually makes
the suite fail. A reviewer had previously found six of them deletable with the
suite still green.

## Provenance

`work_id` / `edition_id` / `witness_id` / `passage_id` are carried per prior
state into `work_edition_witness_provenance.carried_from_prior_states`, with
`operator_declarations_not_independently_proved: true`. Prior R1 evidence that
does not link to the case is **preserved and listed**, never dropped. No second
source store is created.

## Test receipts

All fixtures are fictional synthetic Markdown with an invented source and are
marked as such in the module docstring.

```
python scripts/run_project_qa.py
import_origin=C:\...\worktrees\jx-4beab6a29782\src\kairoskopion\__init__.py
3569 passed, 8 deselected in 84.37s
```

Baseline before this change was `3510 passed, 8 deselected`; the 59 new tests
are `tests/test_citation_repair_r2_r6.py`. Coverage includes: intent
reconstruction, the R4 repertoire and its costs, the evidenced-defect gate and
the anchored-passage veto, R3 conditionality and negative evidence
carry-forward, reversible patch generation, the PENDING gate, receipt binding
and forgery/laundering refusal, keyed MAC verification, sandboxed apply to a
copy with inverse patch, R6 readback with retained debt and original
re-verification, exact-byte undo, replay determinism, CRLF/BOM round-trip,
typed refusals for every malformed record, and DOCX/PDF blocking.

Ten security guards were mutation-tested; all ten are killed by the suite.

## Not verified in this run

- The live spec and architecture Google Docs, GitHub issue #60 and the owner's
  private `R2_R4_SOURCE_REPAIR_CANDIDATES_20261021.json` were **pointers only**
  and were not readable here (outside the workspace and blocked by the execution
  permission policy). The repository's own models and docs were used instead.
- No real manuscript, no real source, no real author approval.
- No merge, deploy, Drive write, external send, or `main` modification.