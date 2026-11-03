# TRM-074 / M106: bounded actual model-executed manuscript cycle

Status: AORUS staging adapter on existing **Kairoskopion / Kairon provider**, **not** native Indago/WhiteCrow/ARTIKL execution, not production and not an author-approved scientific result.

## Why this exists

The existing `trimurti_scheduler.py` is a real pre-author route phase scheduler, but `stage_operation.py` explicitly says real Indago/WhiteCrow scholarly adapters remain stubs. The existing `publication_runner.py` imports already prepared publication packages; it does not produce research and manuscript prose. `manuscript_draft_intake.py` now verifies actual produced drafts. This operator closes the **first actual model-worker scheduling gap** without inventing a new graph, source registry, scholarly body or parallel publishing backend.

One bounded CLI invocation:
1. Reads independently pinned author source, scientific revision, baseline manuscript, prior independent review and three M105 research tasks.
2. Calls a **fresh read-only Codex scholarly scout**; requires exactly the three M105 task identities, actual source+science SHA and a modest explicitly unaccepted read-depth.
3. Calls a **separate read-only Codex writer** to produce a full new article version (minimum 2,700 words), not a W12 card.
4. Calls a **separate read-only Codex reviewer** required to bind its review to the newly written bytes SHA.
5. Reuses the existing native `manuscript_draft_intake`: import actual author/science/draft bytes, owner HOLD, immutable receipts, no SEND.
6. Emits a deterministic state snapshot and stops after **one** writer and reviewer; an unresolved scientific objection returns `RESEARCH_EVIDENCE_REENTRY`, not automatic publication.

This executor is an explicit **Codex fallback** until genuine Indago and ARTIKL adapters with source-depth and accepted editorial decision contracts can be wired through the same interface. It must never be labeled as native Indago or as a deployed ARTIKL organ.

## Private manifest

Schema `trimurti-manuscript-cycle-v1`; `artifacts` exactly `source/science/baseline/review/research_tasks`, each a relative path within `--input-root` and sha256. Flags `evidence_mode=REAL`, `author_gate=HOLD`, `submit=false`, `article_seed_accepted=false`, `worker=CODEX_SCHOLAR_WRITER_REVIEWER_NOT_NATIVE_INDAGO`, `max_writer_calls=1`, `max_review_calls=1` required. Manifest itself is *not* an author approval.

**Four SHA pins must come from a separately trusted source outside the model-authored manifest** (for C04: scientific Git, exact original-byte registry, M104 reviewer). This operator checks those exact bytes before any model invocation. The private input workspace and provider transcripts must not enter a public engineering Git repository.

PowerShell form (run with `PYTHONPATH=src`):

```powershell
python -m kairoskopion.kairon_provider.manuscript_cycle_runner --manifest <PRIVATE_MANIFEST> --input-root <PRIVATE_INPUT> --output-root <PRIVATE_RUNS> --scientific-repo <PRIVATE_SCIENTIFIC_REPO> --trusted-source-sha256 <PIN_FROM_REGISTRY> --trusted-science-sha256 <PIN_FROM_GIT> --trusted-baseline-sha256 <PIN_FROM_GIT> --trusted-review-sha256 <PIN_FROM_INDEPENDENT_REVIEW> --timeout-seconds 450
```

The cycle ID binds all input and manifest SHA values. Each successful stage is an immutable file and a content-hashed stage event in `state.json`. Re-running the same command independently verifies all bound inputs and existing outputs and **makes no repeated provider calls**. If interrupted after a stage receipt, restart continues from the next stage. If a provider process wrote output but exited before a verified receipt, the operator blocks on an **orphan**, requiring explicit inspection rather than silently adopting untrusted text. Any changed previous output, source, science, baseline, reviewer or manifest blocks.

A model's self-declared scholarly discovery, full text claim or author sign-off **never** changes SOURCE/W12/ArticleSeed/AUTHOR status. This CLI is not the D25 acceptance authority, neither does it make a legal journal submission. It does not rewrite historical accepted versions.

## Acceptance limits

Scientific review is by a distinct model session, not guaranteed independent institutional peer review; digest binding and reviewer JSON shape are deterministic checks, semantic source-depth review is still required. Scholarly scout may use previously acquired local text or explicitly mark abstract-only; it must not claim that referenced books/articles were truly retrieved in full without exact byte evidence. The full native Indago connection is still unimplemented.

A real AORUS case M106 is admissible only after (a) exactly three actual model stages, (b) 2,700+ word draft under author's source and science pins, (c) reviewer digest of draft equals observed SHA, (d) existing draft intake receipt and repeated no-reexecution readback, (e) no canonical author approval or journal send, (f) source/negative reviews and full private logs retained. A mock test cannot be reported as a real science case.

Stop conditions: native scholar evidence unproven, reviewer `REVISION_REQUIRED`, stalled/broken model call, source/manifest drift, tamper, or explicit author HOLD. Do not create new ArticleSeed/W12 merely by writing an article; do not merge/deploy automatically.

Related: Kairoskopion #43/#51/#77 and draft PR #84; scientific Git M101–M105.

## Host-level durability and process restrictions

The real worker implementation resolves the Windows `codex.cmd` executable explicitly (PowerShell may otherwise choose `codex.ps1` and a Python child process may return WinError 2). Only a fixed application command is executed; neither manifest nor model output constructs shell commands. Provider stdout and stderr are retained as **private** SHA-bound sidecars on new staging runs, including failure diagnostics where the provider exits. They must not be committed to public engineering Git. The output root uses an atomic single-writer lock; an unexpected crash that leaves it in place requires operator inspection and explicit lock removal, not unattended stale-lease theft. A stage with unreceipted output is an ORPHAN, never silently accepted as a success. These mechanical checks do not replace scientific source depth, independent author/editor authority, or the pending native Indago adapter.


## F2→F3: native organ source-return lane (2026-11-03, staging)

The same existing CLI now accepts an explicit `native` subcommand. Unlike the
legacy Codex-science/writer/reviewer loop, this path invokes actual
`indago_port` source-authority preflight, verifies all immutable files in a
native Indago hunt, and consults the **registered OpenClaw `artikl` agent**
through the actual Gateway. It never calls a generic Codex process as a
stand-in for a native actor.

The manifest is a source-bound case/task/route and explicitly sets exactly one
mode: `REUSE_VERIFIED_NATIVE_HUNT` with an exact prior hunt ID (no new provider
calls) or `EXECUTE_BOUNDED_NATIVE_HUNT` (the port itself executes one real
wave, no `--force`/offline bypass). All three
independently trusted SHA-256 pins for the original author source, current
manuscript and prior independent review are **CLI arguments, not accepted from
the model-authored manifest**. Local ARTIKL rc9 source carrier files are also
byte-SHA read back in the owner-private workspace; the real native agent may
report a cold read but a self-report alone is **not** scientific authority.

Example (PowerShell, from the existing Kairoskopion feature checkout):

```powershell
$env:PYTHONPATH = "./src"
python -m kairoskopion.kairon_provider.manuscript_cycle_runner native `
  --manifest "<private-native-manifest>" `
  --original "<owner-source>" --draft "<exact-author-HOLD-v0.5>" `
  --review "<M116-independent-review>" `
  --port-root "C:/projects/aorus-ecosystem/services/indago-port" `
  --hunts-root "C:/Users/Homee/.openclaw/hestia-body/INDAGO_STATE/hunts" `
  --artikl-workspace "C:/Users/Homee/.openclaw/hestia-body/CHILD_WORKSPACES/artikl" `
  --output-root "<owner-private-run-root>" `
  --trusted-source-sha256 "<external-original-registry-pin>" `
  --trusted-draft-sha256 "<external-draft-git-pin>" `
  --trusted-review-sha256 "<external-review-git-pin>"
```

The source-return is *not* a promotion. A prior Indago result with Crossref
and OpenAlex metadata but zero native full-primary reads causes an automatic
`SOURCE_DEPTH_HOLD`. No author approval, W12 increment or journal send.
Artikl's D14/D15/D24/D25 can return a bounded, origin-pinned
`research_need` in a read-only turn, but this is not yet automated D25
execution and does **not** mean that WhiteCrow executed, the full manuscript
was rewritten, or reviewer objections looped back into a second Indago
research wave. The result intentionally marks `f4_closed_loop=NOT_PASSED`
until those native stages and one genuine post-review retry are implemented
and independently verified.

A restage uses exactly the same manifest digest, pinned original and prior
review; the native Artikl response is an immutable owner-private stdout file
and a SHA-bound receipt. On cold replay the agent model is **not recalled**.
If the process crashes after invoking a native hunt or after writing an
unreceipted agent reply, it blocks for explicit operator triage rather than
inventing a completed model or repeating provider calls. The native port
itself is currently a shared/dirty AORUS working tree; no production merge,
OpenClaw global policy edit or operational rollout is claimed.

Remaining engineering gates: real WhiteCrow source challenge inside the same
controller, verified full-primary scholarly read to repair D15 deficits,
current ARTIKL rc9 semantic D14/D24 → D25 operation evidence, bounded
reviewer-objection → native research retry (not just a HOLD), historical
decision-ledger guards, cross-root deterministic source-stage receipts (#77),
another host cold replay, and at least 10 distinct MAI routes (#51).


## F235/F236: real current Indago + native WhiteCrow D24 (2026-11-03)

The native Indago port previously fetched five Drive authorities serially with a
single ninety-second global authority budget. Large, legitimate
`candidate_queue` and `hunt_ledger` bodies were sometimes fetched after
the budget was already depleted. A strictly bounded parallel live reader is
now committed as an isolated review candidate in
`Stimurid/aorus-ecosystem` branch
`fix/indago-parallel-live-authority-20261103` at
`ef57b281e2433038cc37b1ae0d23b573f63205bc`.
The actual AORUS native plan read all five documents as LIVE_VERIFIED,
using the original metadata/SHA checks, in 17.37 seconds; no model calls.
The port remained subject to the original agent-isolation policy and cannot
promote a cached mirror to LIVE.

With `whitecrow_native_required=true`, the existing native controller
also loads and executes **WhiteCrow's actual pinned FieldCore D24 functions**
from the independently specified local git commit and module SHA. It calls
`build_disciplinary_positioning_report` followed by
`build_research_handoff`; the result is a typed
`ACADEMIC_RESEARCH_REQUEST` with a stable `research_request_id` and
`dispatch_event_id`. Inputs are exact original/draft/reviewer SHA, original
Indago native receipt, and real unresolved independent reviewer findings.
The result is *unambiguous*: insufficient primary-source reading is
`BLOCKED_ON_DUE_DILIGENCE`, so the available semantic operations are only
`FIXATION/CHECK`. The new request is `READY_FOR_RESEARCH` in the
scholarly sense but **not dispatched** through Indago. The original M108
hunt occurred before this request was constructed, so it must NEVER be
falsely claimed as the request's EvidenceReturn. The D24 stage is
deterministic code, not an independent WhiteCrow model literature review.

The stage is included in the SAME native `manuscript_cycle_runner` when
explicitly selected; otherwise the historical native stage remains
backward-compatible. Exact native WhiteCrow code SHA, Git HEAD and cleanliness
are verified before execution, and each report/request/receipt is immutable.
Native Artikl's compact research-return prompt records the D24 request SHA
and pending dispatch status. D14/D15/D24/D25 do not allow manuscript GO
from unverified metadata.

F4 remains OPEN: no one-shot native WhiteCrow→Indago ResearchRequest dispatch
and corresponding source-passage-acquiring EvidenceReturn has yet completed
with matching request/dispatch identity, no WhiteCrow *semantic
requalification* of newly returned full sources, no canonical Artikl D25
revision/reviewer cycle, and no automatic follow-up after critique. The next
edge is a real admission-safe ADD-006 host pickup with original exact request
lineage, bounded source acquisition and WhiteCrow qualification. Do not
relabel historical M108 receipts as satisfying this new request.


### F238 review-source quote admission (2026-11-03)

The *actual* WhiteCrow-main D24 stage is now given the **full candidate
manuscript file**, independently SHA-pinned alongside the exact M116 independent
review. Its `_normalize_issues` verifies the reviewer's proposed candidate
quotation occurs on the claimed 1-based line. Only those literally verifiable
review findings are marked `EXACT_MANUSCRIPT_LINE`. The rest remain explicitly
`UNVERIFIED_REVIEW_QUOTE_NOT_ADMITTED`, retained as unresolved reviewer
questions but not laundered into validated manuscript evidence or "fixed"
defects. This is not an automatic semantic validity claim.

On the C04 v0.5 SHA `0a1cbd31...` and M116 review SHA `4867fa88...`,
a genuine WhiteCrow FieldCore invocation returned **4/6** literal-anchored
objections, **2/6** unverified quoted objections, readiness
`BLOCKED_ON_DUE_DILIGENCE`, a lineage-preserving pending ResearchRequest, and
zero new provider calls. The quote-admission audit and D24 source/code hash
are persisted as immutable owner-private receipts. The previous F236 execution
is historical and MUST NOT be overwritten because the stage contract changed.

F237 canonical WhiteCrow transport serialization and the ADD-006 candidate
one-shot parser have passed read-only tests, but **no current Indago host
claimed the request**. The iMac legacy `house-portal/bin/indago-run.js`
was directly inspected on 2026-11-03: state last written 2026-10-08 and no
active service process; this obsolete carrier must not be patched or presented
as the current host. Actual 2026-11-03 native M108 Indago execution ran on
AORUS `indago_port`. The next F4 step is to bind ADD-006 to that active
host, ensure durable atomic claim before provider calls, preserve
`research_request_id/dispatch_event_id` in a true native evidence return,
then re-qualify via WhiteCrow without widening `CRITIQUE` or granting D25.
