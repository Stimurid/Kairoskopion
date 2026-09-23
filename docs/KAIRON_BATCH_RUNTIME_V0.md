# Kairon Batch Runtime v0 — durable world graph + local-first resume

Status: qualification branch only. No production authority.

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