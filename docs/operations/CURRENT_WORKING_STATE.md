# Current Working State

**Last updated:** 2026-10-06T04:41+03:00
**Branch:** `main`
**Runtime-code merge:** `c1f00e984c3f86105250c294f13644b508310945` — publication package finalization gate
**Last directly verified production HEAD:** `91a35cc5434d2a34e7027abfbe8abcab759c43fc` on 2026-09-30
**Production domain:** `kairoskop.mindkampf.ru`

---

## Deployment status

**`DEPLOYMENT_BLOCKED_NO_NON_SSH_CONTOUR`**

The publication-front TRM-062 runtime repair is merged and fully green in Git,
but production deployment cannot be executed from the currently authorized
contours.

Owner environment policy still applies:

- SSH / SCP / SFTP / port-22 probes are prohibited.
- SSH retry limit is zero.
- Production may only be changed through an already-authorized non-SSH contour.
- The repository currently has test CI only; no deploy workflow/webhook/pull-agent
  is configured in this repository.
- No authorized remote-terminal / VM actuator is connected in the current
  ChatGPT scene.

Do **not** represent the new finalization endpoint as live until a production
HEAD readback and endpoint smoke prove it.

## Publication-front repair merged on 2026-10-06

### TRM-062 — reproducible submission-package finalization

**Which article:** P06 positive control; P07 next reuse case.

**Which stage:** target-specific package closure →
`READY_FOR_HUMAN_SUBMISSION`.

**What was blocked:** the existing `SubmissionPack` could report
`ready_for_manual_submission` as a pre-artifact readiness skeleton without
binding the exact exported artifact revision/hash, frozen/current TargetWorld
identity, current policy evidence, semantic/privacy/render QA receipts, live
submission route, or author-only factual gates.

**What now exists in canonical code:**

- fail-closed submission finalization manifest;
- deterministic digest and idempotent durable manifest store;
- exact upstream `submission_pack_id` lineage bound into the digest;
- exact manuscript/artifact revision or SHA binding;
- current TargetWorld catalog promotion binding while frozen package bytes stay
  immutable;
- only `PROD_ACCEPTED` / `PROD_OBSERVED` TargetWorld status can finalize;
- `QUALIFIED_DEV`, `PROVIDER_OBSERVED`, `STAGING`, `PROVISIONAL` fail closed;
- default required QA:
  - `SEMANTIC_QA`
  - `PRIVACY_SCRUB`
  - `VISUAL_RENDER`
- live route gate;
- author-field gate;
- authenticated provider finalize/readback endpoints;
- legacy `ready_for_manual_submission` remains backward compatible but now
  carries:
  - `is_final_submission_package=false`
  - `requires_finalization_gate=true`
  - pointer to `/kairon/provider/submission-packages/finalize`
- physical final submission remains human-only.

### Git evidence

- PR #11: `fix(kairon): fail-closed publication package finalization`
- Exact pre-merge branch head:
  `585348ccfdbbffd2c1bd2a55973c90f12a93abff`
- Merge commit:
  `c1f00e984c3f86105250c294f13644b508310945`
- Branch CI: Python 3.11 / 3.12 / 3.13 — full pytest + CLI smoke PASS.
- Post-merge main CI run `37397699250`: Python 3.11 / 3.12 / 3.13 —
  full pytest + CLI smoke PASS.

## Current production boundary

The last directly verified production census on 2026-09-30 found
`/opt/kairoskopion/app` aligned to
`91a35cc5434d2a34e7027abfbe8abcab759c43fc`, with uvicorn on port 8088 and
the public vhost active.

The current ChatGPT web fetch surface cannot access the basic-auth-protected
`/health` or `/openapi.json`, so no newer production HEAD or route presence
has been proven in this scene.

Therefore the authoritative current distinction is:

- **Git / canonical code:** MAIN_MERGED + MAIN_CI_PASS.
- **Production runtime:** last verified older HEAD; new package-finalization
  endpoint **not proven live**.
- **Deploy blocker:** no authorized non-SSH actuator.

## What is NOT blocked anymore

Do not reopen these as the first publication-front blocker:

1. Kairon batch qualification exists in main.
2. Durable per-cell receipts exist.
3. Batch interruption/recovery primitives exist:
   `claim_cells()` + `recover_inflight()`.
4. Shared immutable TargetWorld exchange catalog exists in main.
5. TRM-062 code-side acceptance is complete.

A fully autonomous cross-run scheduler remains a separate open concern, but is
not the first blocker for P06/P07 package closure.

## Next mechanical action

When an authorized non-SSH actuator is available:

1. Deploy current `main` containing runtime-code merge
   `c1f00e984c3f86105250c294f13644b508310945`.
2. Read back production git HEAD.
3. Verify local/public health.
4. Verify OpenAPI contains:
   - `POST /kairon/provider/submission-packages/finalize`
   - `GET /kairon/provider/submission-packages/{manifest_id}`
5. Exercise a blocked smoke: incomplete QA must return `BLOCKED`.
6. Exercise a P06-equivalent complete manifest and GET readback.
7. Verify repeat finalization is idempotent.
8. Record a central HEAD SYNC `RUNTIME_CHANGE`.
9. Reuse the same production gate for P07.

## Do not do

- do not attempt SSH;
- do not build a new scheduler before this runtime deploy/readback is closed;
- do not claim production from Git merge alone;
- do not auto-submit to a journal;
- do not let `ready_for_manual_submission` bypass the finalization gate.
