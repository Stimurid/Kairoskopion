# TRM-G6B — independent source-bytes and passage attestation

Status: 2026-10-23 · source-first R3 return integration candidate · no live provider claim · no merge/deploy.

## Review of the initial worker result (9944a52)
The first additive G6B bridge already tied an Indago EvidenceReturn to the exact Z0 case/work order, preserved negatives and V1–V5 NOT_CHECKED, typed replay failures, and generated an R2–R4 plan. However, a *self-consistent forged passage* could set its own `exact_text`, `text_sha256`, `locator_present`, `passage_occurrences=1`, `source_sha256`, and work/edition/witness identifiers, then become `ANCHORED` with no independent read of the original. The synthetic Frolov fixture demonstrated this conceptual hole. It is NOT a scientifically attested Frolov quotation.

## Review repair
Added `citation_indago_witness_check.attest_passages` as an independent second gate:
- Operator supplies actual original PDF/TXT/MD bytes via `--witness-path`. Publisher origin, purchase, publisher payment, publisher license check, and location of acquisition are NEVER inspected or grounds for rejection.
- The SHA-256 digest is computed over real local bytes, compared with the returned source digest and hash-format witness ID where applicable.
- Exact quotation must actually occur in the source text; verified page-index (PDF) or character-offset (UTF-8 TXT/MD) must address that occurrence, and the count of occurrences is calculated from the document, not trusted from the provider.
- PDF `pdf-page-index:N` and text `text-char-offset:N` are independently inspectable; `printed-page:94` is NOT silently equated with PDF page index 94. Such a reference remains `WITNESS_UNVERIFIED` until a trusted printed-page mapping exists.
- If witness bytes are absent, stored state is `UNVERIFIED` with `source_evidence=[]` and `reported_passages` clearly marked `PROVIDER_REPORTED`. R2 cannot treat this as positive anchored evidence; a new source search or verification remains due.
- Provider fake with self-consistent digest, wrong source SHA, locator disagreement and unrelated content yield typed refusals. Two actually repeated passages yield `ANCHOR_AMBIGUOUS` instead of an arbitrary first match.
- Once real bytes, unique phrase and independently verified locator are present, `ANCHORED` + `OBSERVED` are emitted but all V1–V5 and relation-to-claim remain NOT_CHECKED. This proves the located text exists in those bytes, NOT that the bibliographic identity, originality or thesis entailment is scientifically certified.
- Replaying a `return_id` with a newly attested witness after an unverified original is refused as `REPLAY_ATTESTATION_CHANGED`. To upgrade, the agent must issue an explicitly new return event; old ledgers are not overwritten.

## Independent QA
- Base integrated branch e929f636: 3604 passed, 8 deselected.
- First G6B worker snapshot 9944a52: focused original 75 passed (bridge + R2–R6).
- Reviewer patch: **83 passed** focused (includes eight additional witness-related checks).
- Reviewer patch full project `scripts/run_project_qa.py`: **3620 passed, 8 deselected, 0 failed**.
- `ruff check`, compileall and git diff checks required before final commit. Private PDF bytes and manuscripts are NOT staged into Git.
- No publishing, author approval, external provider invocation, editing of originals, or merger with main.

## Explicitly OPEN
1. Real Indago provider -> envelope adapter -> locally held primary PDF -> R2/R4 E2E still needs observation on AORUS. At present there is a verified replay contract and synthetic fixture, not demonstrated real provider execution.
2. DOCX and scanned/OCR-only PDF independent anchors need explicit stable location mapping before promotion; unknown formats remain UNVERIFIED.
3. Printed-page/edition mapping not solved by PDF page-index; Work/Edition/DOI identity and *scientific* relation-to-claim need separate V1–V5 verification and/or author adjudication.
4. Cross-process partial write after a process crash is not a scientific certificate; durable ledgers and repeated return handling need a crash-replay assessment before production admission.
5. Controlled reading test on two distinct real owner PDF works with published page locations should be the next integration experiment.

## Linkage
- Stacked R1–R6 integration draft PR: https://github.com/Stimurid/Kairoskopion/pull/66
- G6 source field: https://docs.google.com/document/d/1LIMFuJkdVlozDlQFlN-aHCtWnQ5AONcT2E99NAsJWYo/edit
