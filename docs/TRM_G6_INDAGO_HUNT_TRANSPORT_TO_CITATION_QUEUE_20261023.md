# TRM-CITE — Indago live-hunt output to Z0-bound citation lead queue

Status 2026-10-23. This is source-candidate transport before R1. It does NOT transform a DOI, article title, snippet or model conclusion into a verified quote.

## Purpose and boundary

An actual isolated Indago hunt emits a durable `meta.json` plus `candidates.json` under the Hestia Indago state. The earlier R3 G6B consumer accepts a verified `EvidenceReturn` and now requires operator-held original witness bytes to produce `ANCHORED`. The intervening gap is that a hunt candidate is not yet such an EvidenceReturn.

`citation_indago_hunt_leads.import_hunt_leads` fills the first half of that gap. It binds the recorded hunt to the exact Z0 `CitationRepairCase` + work order + manuscript SHA, records all discovered items as candidates for source-first R1 intake and preserves negative and unexecuted provider requests.

The source-of-truth chain is:

Z0 immutable claim/work-order → live Indago hunt meta+candidates → case-bound `hunt_leads.jsonl` (provider item; NOT full read) → LitOps/owner library first → retrieve / independently read original work/edition/witness → R1 document bytes SHA and precise passage locator → G6B `EvidenceReturn` with local witness path → R2/R4 choices → author-gated reversible R5/R6 copy.

## Contract and exact statuses

- Requires `meta.hunt_id == candidates.hunt_id`; explicit `--task-id` must equal `meta.task_id` and `--work-order-id` must exist in verified Z0 work orders.
- Requires completed hunt status `PASS` or `PARTIAL` and `finished_at`; does not misreport RUNNING/BLOCKED as evidence.
- Four Indago categories are preserved: `new_verified` (PROVIDER_GROUNDED_ITEM), `new_unverified` (UNVERIFIED_ITEM), `hypotheses` (HYPOTHESIS_ONLY), `known_rediscovered` (ALREADY_KNOWN). All are `PROVIDER_ITEM_NOT_FULLTEXT`; all have `source_evidence=[]`, `V1_V5 = NOT_CHECKED`, `publication_ready=false`.
- Duplicate DOI/URL/title records retain their own lead identity with `duplicate_of`, rather than disappearing or being searched anew.
- `not_found` and `unexecuted_provider_requests` are preserved in the receipt; a timed-out publisher is not a false-citation finding.
- The queue is idempotent by hunt and input-byte SHA; reused output with changed hunt bytes fails closed. No manuscript or source file is rewritten.
- No source purchase, provenance of lawful acquisition or official-download gate; user PDFs from Sci-Hub, Flibusta, torrent and archives are accepted at source intake. This module does not itself download them.

## Minimal invocation

```powershell
python -m kairoskopion.services.citation_indago_hunt_leads \
  --audit citation_intake.json \
  --queue citation_work_orders.jsonl \
  --meta <real-hunt-folder>/meta.json \
  --candidates <real-hunt-folder>/candidates.json \
  --task-id TRM_CITE_G6_R3_LIVE_SOURCE_20261023 \
  --work-order-id <id-from-z0> \
  --output <private-case-lead-ledger>
```

## What remains to make the full product work

1. Live G6 hunt `h-20261023T000134Z-trm_cite_g6_r3_live_source_20261023-39129c` must actually finish and produce source leads. Running or publisher-metadata-only results are NOT `EvidenceReturn`.
2. The builder must couple `CHECK_OWNER_LIBRARY_THEN_EXACT_WORK_FULLTEXT` to LitOps/Indago exact-work retrieval and local witness indexing; this port deliberately does not invent passage bytes.
3. True V1–V5 claim-to-source semantic verification, manuscript-author adjudication and reversible updates remain separate operations. No journal submission is authorized by a hunt.
4. Independent tests are provided for 11 cases; complete repo QA remains the separate acceptance gate.

## Source and lineage

Current Hestia port reference: `C:\projects\aorus-indago-full-20261020\services\indago-port\README.md`.
Indago canonical Tasks and Trails Drive: https://docs.google.com/document/d/12WKFKe6Lzxyx2fvWMbjSR63NanmRGNjMII-2hqKrJhA/edit
Citation original integrated draft: https://github.com/Stimurid/Kairoskopion/pull/66
R3 real-byte witness review: https://github.com/Stimurid/Kairoskopion/pull/69
G6 ArticleModels: https://github.com/Stimurid/Kairoskopion/pull/70
