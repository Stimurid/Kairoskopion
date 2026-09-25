# Kairon Batch Runtime v0 — durable world graph + local-first resume

Status: production-accepted on main and deployed. Runtime authority remains bounded by ARTIKL.KAIRON contracts.

Builds on feature/kairon-batch-qualification-v0 and the canonical D19 owner-merge / batch protocol.

## Added

- AcademicWorldStore: durable multi-parent publication-world graph under KAIROSKOPION_DATA_DIR/kairon_provider/academic_world.
- BatchQualificationSpec: explicit concurrency/source/freshness/failure/author decision/acceptance policy object.
- BatchRunStore: atomic durable batch plan and per-cell state, with pending_cells() resume semantics.
- probe_local_first(): checks the repository disciplinary landscape, runtime venue registry, frozen TargetWorld store, and VenueMemory before external discovery can be authorized.
- authorize_external_discovery(): converts a completed local probe into an auditable network-discovery permission.
- AcademicWorldNode now carries canonical questions, legitimate objects, provenance, and last-checked state in addition to regional, linguistic, citation and graph links.

## Authority boundaries

This runtime stores and schedules evidence-bearing objects. It does not:
- adopt an Artikl identity change;
- mutate a frozen TargetWorld snapshot;
- turn an LLM-draft discipline card into canonical knowledge;
- infer a civilizational hierarchy;
- deploy itself to production.

## Qualification

New + existing batch tests: 15 PASS.
Adjacent Kairon/provider/registry/venue-memory/discipline tests: 137 PASS.

Full repository run in the available /tmp/kairo-batch-venv:
- 3348 PASS
- 5 FAIL
- 8 deselected
- 16 subtests PASS

Control run on the unchanged parent bff69fa reproduces all five failures in the same environment. Three are FastAPI route-introspection/environment failures in test_blocker_regression; two are the already-known rubric-loader baseline. Therefore branch-specific regressions observed in this run: 0.


## Pilot-001 repair

The first real local-first probe exposed a semantic bug: a discipline-only registry hit was being reported as a generic local hit even when no venue, VenueMemory or TargetWorld existed. The receipt now separates layer_hits and reports target_local_hit, context_only_hit, or local_miss. This prevents disciplinary context from suppressing required target acquisition.


## Scheduler resume hardening

BatchRunStore now exposes claim_cells() bounded by BatchQualificationSpec.concurrency_limit and recover_inflight(), which converts abandoned in_progress cells to retry after worker interruption. This closes the minimal single-writer B10 resume contract; distributed leases remain a later production concern.

## Academic-world routing delta

The local-first boundary now includes AcademicWorldStore itself. Repository routing seeds and durable live graph nodes are checked before external discovery can be authorized. `LocalFirstAuditReceipt.checked_academic_world_store` is mandatory for external discovery.

Repository routing seeds are intentionally low-confidence scaffolds, not claims about academic cultures. The initial graph exposes Russian/post-Soviet, Anglophone, Francophone, Germanophone, East Asian, South Asian, Southeast Asian, African, MENA, Latin American/Iberophone and transregional routes; evidence-backed descendants carry concrete discipline/school/venue structure. Multi-parent nodes are supported.

AcademicWorldStore now reads immutable seed JSONL plus live overrides. A changed live record archives its previous materialization under `academic_world/history` before replacement. Frozen TargetWorld refresh is separately guarded by `persist_target_world_refresh()`, which requires a new descendant snapshot ID and records `parent_snapshot_id`.

New classifier family: `academic_world_resolution_v1`. It sits between `disciplinary_mapping_v2` and `venue_funnel_planning_v2`, selects only local AcademicWorld node IDs, preserves multiple trajectories, treats routing scaffolds as non-substantive, and emits acquisition debt when the local graph lacks evidence.

Current delta qualification:
- targeted batch/runtime/pressure/academic-world suite: 27 PASS;
- full repository: 3360 PASS, 5 FAIL, 8 deselected, 16 subtests PASS;
- the five failures are the same parent-baseline failures previously reproduced in this test environment (3 FastAPI route-introspection/environment, 2 rubric-loader);
- observed branch-specific regressions: 0.

## Production acceptance receipt (2026-09-25)

- main/prod commit: `08f2f60426b7c048073a27adaf87339587f62841`
- PR #4 normalized already-qualified TargetWorld refs and merged after green CI.
- production rollback ref: `prod-pre-batch-20260925` at `3e94eb7fa72595c1c2bd6b35ce0ecba08b565aae`.
- `kairoskopion-api.service` restarted cleanly; `/health` returned `status=ok`; working tree clean.
- production virtualenv intentionally has no pytest; qualification evidence is the green GitHub CI on the exact deployed main head, not an ad-hoc mutation of prod dependencies.
- authority boundary is unchanged: batch/Kairoskopion may acquire, cache, route, pressure-test, and propose; manuscript-state authority remains ARTIKL.KAIRON / Artikl owner-return.
