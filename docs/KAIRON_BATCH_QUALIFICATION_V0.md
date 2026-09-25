# Kairon Batch Qualification Kernel v0

Status: production-accepted on main and deployed. Runtime authority remains bounded by ARTIKL.KAIRON contracts.

Canonical Artikl owner-merge receipt: Google Doc ID
1TUH6XqQ4uAang80-tPysRtNDYFdC5PWCFEcP7jI8m3E.

Batch protocol: Google Doc ID
1EDbpONQOR0pERRTmv97nq44Rk7_EQ2pMUgw3LsQiOFQ.

## Purpose

The kernel turns the first P06 one-off venue exercise into a deterministic
article x target qualification matrix while preserving the existing
ARTIKL.KAIRON authority boundary.

It does not discover venues, rewrite manuscripts, adopt transitions, refresh a
TargetWorld, or deploy anything. It plans cells that later scheduler stages can
execute.

## Existing substrate reused

Kairoskopion already has:
- Disciplinary Landscape Registry and registry-first acquisition;
- DisciplineIntent, DisciplineMatcher and DisciplinaryPathwayMapper;
- VenueFunnel and VenueFamilyContext;
- FieldPositionModel for discipline, school/tradition/tribe, citation,
  argument, method, audience, geography and institutional axes;
- durable TargetWorld and ProviderRun stores;
- Kairon pressure, transition and frozen-snapshot return-pass contracts.

The batch kernel composes these instead of creating a second venue-search
ontology.

## New contracts

AcademicWorldNode
- open graph node, multi-parent;
- typed from regional publication ecology through discipline/school/venue;
- evidence/provenance fields;
- no closed civilization taxonomy.

LocalFirstAuditReceipt
- proves discipline registry, venue registry and TargetWorld store were checked
  before network discovery;
- rejects external discovery when those checks were skipped.

BatchArticleInput
- retains authoritative ArtiklStatePointer;
- refuses non-ARTIKL semantic authority.

BatchTargetInput
- requires a frozen snapshot_id;
- carries academic-world path and local-first receipt.

BatchCell
- article-specific state against one frozen target snapshot;
- pressure/transition/variant/round-trip slots remain per article.

BatchQualificationPlan
- deterministic article x target matrix;
- explicit snapshot_reuse groups so one TargetWorld can be reused across
  multiple articles without sharing article-specific pressure state.

## Academic-world rule

The old DisciplineModel.region enum is intentionally not expanded inside this
minimal kernel. AcademicWorldNode uses evidence-bearing graph nodes so later
regional coverage can represent RF/post-Soviet, Anglophone, Francophone,
Germanophone, East Asian, South Asian, Southeast Asian, African, MENA, Latin
American/Iberophone and transregional publication ecologies without pretending
those are mutually exclusive civilizations.

A later migration may project this graph back into DisciplineModel after data
and compatibility tests. The batch kernel does not force that migration.

## Acceptance for this slice

1. 2 articles x 2 targets produces 4 cells.
2. One frozen target snapshot can be referenced by several article cells.
3. Local-first receipt survives into each cell.
4. External discovery without prior local checks is rejected.
5. Duplicate article/target IDs are rejected.
6. Target input without snapshot ID is rejected.
7. AcademicWorldNode supports multiple parents.
8. Non-ARTIKL semantic authority is rejected.

Production cutover completed on 2026-09-25; subsequent changes remain separate reviewed actions after targeted and full repository
qualification.


## Production acceptance receipt (2026-09-25)

- main/prod commit: `08f2f60426b7c048073a27adaf87339587f62841`
- PR #4 normalized already-qualified TargetWorld refs and merged after green CI.
- production rollback ref: `prod-pre-batch-20260925` at `3e94eb7fa72595c1c2bd6b35ce0ecba08b565aae`.
- `kairoskopion-api.service` restarted cleanly; `/health` returned `status=ok`; working tree clean.
- production virtualenv intentionally has no pytest; qualification evidence is the green GitHub CI on the exact deployed main head, not an ad-hoc mutation of prod dependencies.
- authority boundary is unchanged: batch/Kairoskopion may acquire, cache, route, pressure-test, and propose; manuscript-state authority remains ARTIKL.KAIRON / Artikl owner-return.
