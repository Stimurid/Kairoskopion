# Current Working State

**Last updated:** 2026-10-06T04:41+03:00
**Branch:** `main`
**Production runtime code HEAD:** `c1f00e984c3f86105250c294f13644b508310945`
**Git-main currentness rule:** read the live branch ref from Git; do not embed a self-referential current-main SHA in this file because updating the file advances main.
**Production domain:** `kairoskop.mindkampf.ru`

---

## Deployment status: LIVE

**`PROD_LIVE / FINALIZATION_GATE_VERIFIED`**

The prior `DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR` state is superseded.

An already-existing repo-scoped self-hosted GitHub Actions runner on
`moderbober-prod-01` was recovered and reused as a one-shot non-SSH actuator.
No SSH/SCP/SFTP/port-22 access was enabled or attempted.

### Deployment evidence

- Previous directly verified production HEAD:
  `91a35cc5434d2a34e7027abfbe8abcab759c43fc`
- Deployed runtime code HEAD:
  `c1f00e984c3f86105250c294f13644b508310945`
- One-shot non-SSH deploy run: `37401804487`
- Runner: `moderbober-prod-01-tinkuy`
- Deploy receipt artifact: `11384979277`
- Service restart: PASS
- `/health`: recovered after normal restart window
- Live OpenAPI exposes:
  - `POST /kairon/provider/submission-packages/finalize`
  - `GET /kairon/provider/submission-packages/{manifest_id}`

Treat the self-hosted runner as a proven emergency/one-shot actuator, **not**
as a generally governed deployment service unless separately established.

## TRM-062 finalization slice

### Canonical runtime code

PR #11 merged as:

`c1f00e984c3f86105250c294f13644b508310945`

The runtime provides a deterministic fail-closed finalization manifest with:

- upstream `submission_pack_id` lineage;
- exact manuscript/artifact revision or SHA;
- frozen TargetWorld package identity/digest;
- current TargetWorld catalog promotion;
- only `PROD_ACCEPTED` / `PROD_OBSERVED` finalizable;
- current policy refs;
- required `SEMANTIC_QA`, `PRIVACY_SCRUB`, `VISUAL_RENDER`;
- live submission route gate;
- author-field gate;
- durable/idempotent manifest storage;
- physical final submission remains human-only.

Legacy `ready_for_manual_submission` remains a pre-artifact skeleton and now
explicitly requires the finalization gate.

## Real production proof — P06

Production TargetWorld:

- snapshot:
  `targetworld:philosophy_technology_prod_acceptance:719491146388`
- package:
  `targetworld:philosophy_technology_prod_acceptance:719491146388@8263d0aad06d70bf`
- catalog status: `PROD_ACCEPTED`
- digest:
  `8263d0aad06d70bfb647ecee0aeb82150dd0cac28f64483506f0fc32e0a928ad`

Production submission manifest:

- run: `37402017234`
- receipt artifact: `11384874860`
- manifest: `submissionpkg:P06:7c1a3afdffe8b26d`
- digest:
  `7c1a3afdffe8b26d42289d90306ba6bd2f3278c82c3ca8d682fa1b4ac9f4bdf7`
- repeat write: idempotent
- durable GET readback: matched

P06 result is intentionally `BLOCKED` only on real external/human gates:

- `author_fields_not_confirmed:OPEN`
- `submission_route_not_live:BLOCKED`
- `live_route_evidence:editorial_manager_development_site`

No technical/package/TargetWorld/QA blocker remains for the P06 P&T package.

## Cross-head production proof — P07

The same live gate was exercised independently on P07.

- production run: `37402407964`
- runner: `moderbober-prod-01-tinkuy`
- receipt artifact: `11385159894`
- manifest: `submissionpkg:P07:3c883749e261be7c`
- digest:
  `3c883749e261be7c989216a9a83ea35870bf2a23e5fb23108f362b4fa33537bd`
- TargetWorld catalog status: `PROD_ACCEPTED`

P07 preflight correctly returns the actual remaining package boundary:

- missing:
  - `manuscript_docx`
  - `title_page`
  - `cover_letter`
  - `submission_checklist`
- QA not yet passed:
  - `SEMANTIC_QA`
  - `PRIVACY_SCRUB`
  - `VISUAL_RENDER`
- `author_fields_not_confirmed:OPEN`
- `submission_route_not_live:BLOCKED`
- `live_route_evidence:editorial_manager_development_site`

Therefore the finalization slice is proven reusable across article heads.

## What is NOT blocked anymore

Do not reopen these as first publication-front blockers:

1. Kairon batch qualification.
2. Durable per-cell receipts.
3. Batch interruption/recovery primitives.
4. Shared immutable TargetWorld exchange catalog.
5. Submission-package finalization gate.
6. Non-SSH one-shot production actuation for this host.

## Current publication-front blocker

The next concrete reusable seam is **upstream package materialization**, not
finalization:

`target sibling → manuscript DOCX + title page + cover letter + submission
checklist → semantic/privacy/render receipts → finalization gate`.

P06 proves this path manually.
P07 proves the missing boundary mechanically.

TRM-062 as a whole therefore remains open for:

- reusable target-sibling/package factory behavior;
- ACTIVE → NEXT target delta reuse;
- artifact-generation/resume/logging that avoids repeated manual rescue.

## Next authorized move

Use P07 as the reproducibility case:

1. inventory its existing target sibling and package carriers;
2. reuse the P06 proven materialization procedure;
3. identify exactly which steps are deterministic/reusable;
4. implement only the smallest package-factory seam needed to create/version:
   manuscript DOCX, title page, cover letter and submission checklist;
5. keep author-owned facts as explicit gates;
6. require semantic/privacy/full-render receipts;
7. rerun the already-live finalization gate;
8. then test the same factory on one more article head or NEXT target.

## Operational invariants

- no SSH;
- no automatic journal submission;
- final `Submit/Send/Confirm` remains Timur-only;
- do not rebuild the finalization gate;
- do not make P07 wait for a global scheduler;
- do not call a pre-artifact readiness skeleton a final package.
