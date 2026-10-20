# LOKI R0 — isolated game reverse engineering (issue #49)

## Status

**Code candidate, synthetic-fixture tested; no real MAI/author corpus validation.**
This slice is an offline, dependency-free and side-effect-free library at
src/kairoskopion/loki/. It is **not** another source-to-ArticleSeed engine,
a journal submission service, a reviewer simulator, a production migration,
or the Git guest UI. Current Factory code, queues, source stores and database
are unmodified. Feature activation in the core pipeline remains OFF.

Canonical entry: https://drive.google.com/drive/folders/1tuA5YBSWXu11MDTwv9tB_URpRwHhKhWE

## What actually works

- Immutable scoped GameModel, GameHypothesis, ProbeRecord, OutcomeEvidence,
  StrategicMove, and StrategyPolicy types.
- Pre-registered probe fingerprints and deterministic differentiation count
  D(p) of rival hypotheses that predict distinct observable outcomes.
- Pareto frontier of probes by discrimination, cost, risk, reversibility;
  no invented confidence numbers or weights.
- Categorical observation update (CONSISTENT, INCONSISTENT, INDETERMINATE,
  NOT_REAL_GAME_EVIDENCE) with rejection of post-hoc mutations and cross-game evidence.
- Advisory strategy with DO_NOT_PLAY (requires verified blocks + protected
  scientific residue + return condition) versus ABSTAIN (missing sources
  or unresolved trade-offs). Only a fully comparable Pareto winner can be
  recommended; no output authorizes a real action.
- Optional *single-writer* read-only-by-default hash-chained, idempotent JSONL
  event ledger in an explicit caller-supplied isolated path. Ledger payloads
  contain IDs/derivations, not raw manuscripts or private correspondence.

## Run without external services

From repository root on PowerShell:

    $env:PYTHONPATH = "$PWD\src"
    python -m pytest tests/test_loki_r0.py -q
    python -m kairoskopion.loki

The demo is explicitly labelled SYNTHETIC_FIXTURE_ONLY and must not be
mistaken for a genuine test of journal hypotheses or evidence acquisition.
Tests use pytest tmp_path for all mutable files.

## Trust and integration boundary

This library validates **declared** provenance/verification labels, but it
does **not** possess the real LitOps/Indago/Kairon authenticated source-admission
adapter. A source_ref and Verification.VERIFIED provided by a caller are
not independently verified by this code. Accordingly:
- A locally constructed PUBLIC_SOURCE test object is a fixture, not a
  certified real-world observation.
- Until trusted ecosystem readback is integrated, external source authority
  is INTEGRATION_NOT_PROVEN, never REAL_DATA_PASS.
- No direct writers to WhiteCrow Field, ArticleModel, source registry, Gmail,
  reviewer responses, human gates, Hub jobs or production target state.
- No multi-writer event store guarantees; real Factory integration must reuse
  its transactional records/receipts rather than promote this development
  JSONL file as canonical truth.
- No semantic venue model fit engine implemented here; game hypotheses and
  declared move effects must come from existing science/field/venue owners
  once admitted, not invented by this module.

## Next R0 vertical (engineering gate)

1. Read main/current Factory receipts and source schema before attaching.
2. Define a *read-only* adapter from the existing source/Article/TargetWorld
   package to GameModel; reuse existing stable IDs and source revisions.
3. For one owner-authorized real MAI case, pin source bytes / reference policy,
   define two genuinely rival hypotheses with pre-registered predictions,
   execute one permitted discriminating observation, record negative evidence,
   and produce StrategyPolicy without acting on it.
4. Add hostile fixtures for forged public source/reviewer evidence, incomplete
   read depth, source version drift, adverse core/protected-field impact,
   idempotent replay and real-world author rights.
5. Run regression on pinned Factory branch with core owner; do not rebase
   or alter #32 -> #36 -> #44 -> #46 and active #43/#53 work.
6. Require explicit OWNER GO for future integration; do not merge or deploy
   based solely on this sidecar's green tests.

**Definition of current success:** CODE_READY + FIXTURE_PASS if the
committed code/tests are independently reproduced. REAL_DATA_PASS,
INTEGRATION_PASS, PROD_DEPLOYED remain unproven.
