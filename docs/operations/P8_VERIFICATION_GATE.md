# P8 Verification / Promotion Gate

**Date:** 2026-06-27
**Branch:** `feature/round3-p7-4-to-p9-acquisition-verification`

## Purpose

The verification gate decides whether provisional registry records can be
promoted to verified status. It produces an audit trail for every decision.

## Verdicts

| verdict | meaning |
|---------|---------|
| `promote_verified` | Evidence sufficient, adapter-confirmed |
| `promote_local_evidence_supported` | Local evidence supports claim, not externally verified |
| `keep_provisional` | Insufficient evidence, not contradicted |
| `needs_manual_review` | Conflicting or ambiguous evidence |
| `reject` | Contradicted or fabricated evidence |
| `blocked` | Cannot verify (paid API required, source inaccessible) |

## Rules

### General
- Record must have at least one evidence ref
- Evidence kind must be acceptable for the claim type
- No contradictions between evidence sources

### Venue metrics (SJR, CiteScore, h-index, RSCI IF, Scopus quartile)
- Each metric needs its own evidence ref
- Local evidence pack → `local_evidence_supported` (not `externally_verified`)
- Adapter result → `externally_verified`
- LLM inference → stays `provisional`

### Disciplines
- `ru_seed.jsonl` records with `llm_draft` provenance stay provisional
- Local evidence pack corroboration → `local_evidence_supported`
- Model pretraining / LLM draft alone → never verified

### Venue classifications
- VAK status from local evidence pack → `local_evidence_supported`
- Official source → `externally_verified`

## Audit Trail

Each `VerificationDecision` records:
- `record_id`, `record_type`
- `before_status`, `after_status`
- `verdict`, `reason`
- `evidence_refs_count`, `evidence_kinds`
- `has_source_packet`, `has_real_evidence`, `has_llm_only`
- `contradictions`
- `verifier_version`, `verified_at`

## Implementation

`src/kairoskopion/services/verification_gate.py`

Functions:
- `verify_record(record, hub)` → `VerificationDecision`
- `verify_registry(hub)` → `list[VerificationDecision]`
- `summarize_verification(decisions)` → counts by verdict and record type
