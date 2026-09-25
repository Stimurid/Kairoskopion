# Kairon Batch Executor v0

Status: production-accepted qualification runtime. No manuscript or semantic-adoption authority.

This slice turns a durable BatchQualificationPlan into observed per-cell Kairon qualification receipts.

Execution per claimed cell:
1. validate authoritative Artikl article state and frozen target identity;
2. load the existing frozen TargetWorld;
3. derive conservative per-article target pressure from frozen evidence;
4. call canonical Kairon transition classification;
5. persist full pressure/transition receipt;
6. update durable cell state;
7. stop before manuscript materialization or semantic adoption.

Scheduler behavior:
- obeys BatchQualificationSpec.concurrency_limit;
- resumes pending/retry cells;
- persists failures instead of losing the interrupted location;
- transition outputs remain proposal-only;
- HOLD is terminal for one frozen-snapshot qualification cell; new target evidence requires a descendant TargetWorld and a new cell;
- author-gated transitions stop as blocked_author.

Sparse eligibility:
- BatchArticleInput.eligible_target_ids restricts an article to evidence-supported targets;
- empty eligibility preserves all-target behavior;
- shared frozen targets remain reusable across every article that explicitly allows them.

Local-first target reuse:
- AcademicWorld, discipline and venue registries are checked;
- repository venue registry, harvested provisional records and evidence packs are checked;
- frozen TargetWorld and VenueMemory remain separate durable layers;
- external discovery remains gated behind a completed local-first receipt.

## Production qualification sequence — B12 through B16

B12 closed production acceptance and the provenance-normalization defect. The accepted runtime landed through PR #4 at 08f2f60426b7c048073a27adaf87339587f62841. A later docs-only currentness merge moved main/prod to f71f7bbec201d61d570245da4e29fc4cea890693 without changing runtime behavior.

B13 proved cross-article reuse. F02_TECHNICAL_DELEGATION and F09_VYGOTSKY_ENGELBART_SIMONDON consumed the same frozen philosophy-of-technology TargetWorld with zero external discovery. Both cells remained state-separated and reached qualification_complete / BRANCH. No manuscript materialization or adoption occurred.

B14 proved memory growth. A previously missing Synthese target was investigated only after the local-first gate, persisted as provisional VenueMemory vmem_af92cff31ae5, and then consumed by a following local probe with zero repeated network acquisition. Provisional memory was not silently promoted to canonical knowledge.

B15 proved frozen-target reuse, immutability and fail-closed behavior. Synthese snapshot targetworld:synthese_b15:4f3d37505bfc was shared by F02 and F09. Both cells stopped at evidence_hold because the Crossref sample was temporally stale and article reference counts were unverified. The frozen snapshot remained unchanged.

B16 proved evidence-debt recovery through descendant refresh. Fresh OpenAlex evidence for Synthese source S255146 produced descendant targetworld:synthese_b16:2fa6c3a9776b with explicit parent lineage and a 50-work 2026 corpus. Re-running F02 and F09 removed target:corpus:temporal_adequacy; both cells reached qualification_complete / BRANCH. article:reference_count remains an explicit non-blocking unknown because the current Artikl source carriers do not support a verified complete bibliography count.

## Current authority boundary

The executor may schedule, acquire under the local-first gate, cache, pressure-test and propose transitions. It does not rewrite a manuscript, reconstruct a bibliography by heuristic, materialize a target variant, or adopt a semantic transition. Those operations remain under ARTIKL.KAIRON / Artikl authority.

## Next implementation frontier

The old note that the real multi-article pilot remains later is closed by B13–B16. The next missing contract is article-side bibliography/source completeness: Artikl needs an evidence-bearing pass that can distinguish a verified bibliography from source traces, donor material and incomplete source maps, then project a verified reference_count into ArticleModel. Target-variant materialization remains downstream of that authority-bearing Artikl pass.
