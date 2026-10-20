# MAI W12 × INDAGO W69: source re-entry and scholarly-index checkpoint (2026-10-20)

## Scope and authority

This is the existing TRM074 Factory, LitOps and WhiteCrow **SOURCE / CONTEXT** stage with reused prior INDAGO research. No science, manuscript, author decision or external journal sending is certified by source admission.

Two owner-private families of inputs:

1. Authenticated native Google Sheet W12 53-route read-derived JSONL, source SHA256 `9210da3b761903795907e757950d24c65b99a312554578d0e49860ecde1b9a0c`. These 53 texts are Russian SECONDARY RESEARCH SYNTHESIS per journal route, **not** 53 author-accepted independent papers; original 21-tab XLSX byte equivalence has not been claimed.
2. Authenticated Google Drive *connector text projections* from the preceding INDAGO W0–W69 hunt and author field. These are **not provider-raw/native-revision-certified bytes**. Captured privately on authorized AORUS and never committed: A–F portfolio heads `1ISWZWzWi16ZxYtUP_K4g8gVTZL8zWQ2HHlpG8TaKXcU`; W69 synthesis `1LA565fHI24d8fn_9cE_Kvr8hU8iM4YjMP-SE1tpvT_A`; next-agent handoff `1GTqj3_DZaF2Le7sY2s7h6Qxq_SXERTtTkCaA9pxq16w`; W62–W69 query/source/negative trail `1Dot-bitgPrmAPvHiMlvhv9HZT1YOY0foLnBmkXhp3-g`. Source projections from author A3/A4 `1RnE42iT0_z5yNlSrbczHg6Q5IjXNPURPTkK-9FmfkkQ`, third MAI lesson D `1NXCBvb9f9Ig-LWz0wuFOtS7F74_ybJ985bWxNOTl2b0`, authored event criterion E `1otQ8CjNmKEQ1cfvjsgwStOdiFL6eEUNNZ0bdEjTiNg8`. Original author F from 2025 remains a separately traceable article and is not silently absorbed as a 2026 course result.

The private donor manifest explicitly reports source scope, read depth, Google IDs, URLs and `provider_original_bytes_verified=false`. The W12-source-specific LitOps adapter **rejects** forged Docs IDs, changed sheet range/URL, unapproved author status, or upgraded full-text read-depth.

## Actual AORUS acceptance

The new reusable `scripts/build_mai_w12_factory_case.py` builds a TRM074 manifest with **53 W12 route-summaries plus 7 real previously-authored donor texts = 60 sources**. The existing `scripts/run_factory_source_stage.py` (unchanged) ran one command against an isolated Factory and isolated LitOps root. Readback:

* `new_source_snapshots=60`, `new_whitecrow_sources=60`, `new_whitecrow_contexts=6` (one source+common research context per A–F family).
* Independent cold subprocess replay: `new_source_snapshots=0`, `new_whitecrow_sources=0`, `new_whitecrow_contexts=0`.
* Immutable combined Factory receipt SHA256 `5fb7264cb4bea97f46568d2e0e30d25976ac1e5a4e3072cdd2bd65d3f4d37083`.
* Installed LitOps/WhiteCrow were invoked. This establishes durable SOURCE-AND-CONTEXT; `kairon_evidence_count=0`, `research_wave_count=0`, `article_seed_created=0`, `external_send=DISABLED`.

The second reusable `scripts/build_mai_w12_science_index.py` reads the exact INDAGO 08 A–F source text and materializes **53 route-specific index files**, six family source passages with SHA256 + character anchors and **17 DOI candidate references** across the six *families* from the prior research. Family objections are reused, not treated as 53 independent newly generated scientific critiques; publisher articles were NOT fetched in this wave. All 53 `scholarly_execution_state=HOLD_UNTIL_REAL_ARTIKL_INDAGO_OPERATION` and `author_ready=false`.

A separately stacked Kairoskopion branch PR #50 updates the existing HTML/JSON/CSV Kanban with 53 science HOLD links; the deterministic `run-local` replay stayed **53 CACHED** across science index + editorial-state changes. Board still distinguishes one editorial reply, one sent without confirmation, six drafts and two form preparations. These do not mean manuscript accepted.

## Reproduction on authorized AORUS

Owner-private root: `C:\projects\trimurti\_ops\MAI_W12_PROVIDER_SNAPSHOT_20261020`. Do not push source manifests/private projections to public GitHub.

```powershell
python scripts\build_mai_w12_factory_case.py --packets "<private-root>\packets-v1" --donors "<private-root>\indago_donor_projections\donor_manifest.json" --case-id MAI-W12-INDAGO-PROVENANCE-20261020 --output "<private-root>\MAI_W12_FACTORY_PLUS_INDAGO_60.json"
$env:PYTHONPATH = "src;C:\projects\trimurti\whitecrow\conceptarticle;C:\projects\trimurti\whitecrow\whitecrow-skeleton"
$env:LITOPS_SKIP_DOTENV = "1"
$env:LITOPS_ROOT = "<private-root>\litops_with_indago_60"
python scripts\run_factory_source_stage.py --manifest "<private-root>\MAI_W12_FACTORY_PLUS_INDAGO_60.json" --storage-root "<private-root>\factory_with_indago_60" --litops-root "<private-root>\litops_with_indago_60"
python scripts\build_mai_w12_science_index.py --packets "<private-root>\packets-v1" --indago-head "<private-root>\indago_donor_projections\MAI_08_PORTFOLIO_HEADS_connector_text_projection.txt" --donors "<private-root>\indago_donor_projections\donor_manifest.json" --output "<private-root>\indago_science_index_53"
```

New/relevant PR #58 regression tests: **35 passed** in installed local environment. Source/board branch PR #50 regression tests: **122 passed**. No production/CI claim. The previously observed full suite had six unrelated failing tests and is not certified green.

## Next executable research boundary

Engineering owner #51 must invoke the actual source-bounded **Artikl/WhiteCrow scholarly objection and Indago/Kairon full venue research operations** on 10 then 53, consuming these 53 immutable science-index tasks. Each stage receipt must say which exact published paper was really read (abstract vs sections vs full text), what claim it changes or rejects, an opposing finding, source SHA, operation provider/command and output SHA, route/journal-specific editorial/AI policy and explicit HOLD/revise/admit outcome. Merely indexing W69 and prior DOI cites cannot clear any gate.

Do not send another journal letter through this code. Do not start individual manual article rewrites before batch is eligible for author review. Await author decision for content, coauthors and rights.
