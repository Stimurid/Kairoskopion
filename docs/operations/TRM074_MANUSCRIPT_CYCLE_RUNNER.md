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


## F240 / ADD-006 native organ chain — actual exercise 2026-11-03

**The old F234 historical M108 replay is NOT F237 research.** This phase adds
a separate `add006` CLI subcommand on the same existing
`kairon_provider.manuscript_cycle_runner` rather than a parallel Factory.

Path: pinned WhiteCrow F238 D24 `ResearchRequest` + exact one-shot transport →
*real* `indago_port add006-oneshot` host in the isolated AORUS Indago checkout
→ O_EXCL atomic `claim.json` under the existing `HuntLease`
→ native hunt + append-only runtime receipts → complete/PARTIAL
`indago.add006.evidence_return.v1` with original request/dispatch/run/transport
SHA → *actual* pinned WhiteCrow D24
`integrate_research_evidence_return()` / `build_disciplinary_positioning_report()`
→ registered native OpenClaw `artikl` chooses
`MORE_RESEARCH` / HOLD. No Codex substitute.

Specific owner-private prior real run:
`h-20261103T173837Z-trimurti_f237_c04_20261103-27094f`,
`INDAGO:RUN:d427e0184c3c5639:staging-dry1`,
transport sha `b0e4b15dcc7a03addf9e652a44c9ef374c64f837848f44dec1ab7c9ada6b4e29`,
real EvidenceReturn sha
`a2f2d98db59d8c971d75078b31e92cf54d6bf5174a362e09ff482e75e831c9c8`.
8 actual provider calls, 2 waves: one completed, second timed out,
`PARTIAL`, only false-positive lexical Crossref result and metadata.
D15 full-original read not proven.

The Indago-side ADD-006 worker lives on *isolated* AORUS worktree
`F240_add006_isolation_fix`, commit `e3c507e4a27d331f58cadc180d71751afa54cefe`
(no production merge): patched old tool-less-only isolation policy to match
registered live `minimax/MiniMax-M3.1-Flash` workspaceOnly bounded tools,
kept all five LIVE_VERIFIED authority gate, no `--force`, and fixed severe
exactly-once hazards (a conflicting payload cannot reuse a claim; a second
CLAIMED/RUNNING runner cannot send duplicate requests). Explicit recover from
a prior `LIVE_HUNT_BLOCKED` allowed **only** after persistent zero-provider,
no-hunt native evidence and same request/dispatch/run; no recovery after
actual provider calls. 19 ADD006 unit tests passed.

The new `native_add006_factory.py` is the transport-to-organ orchestrator.
Its real-case input is an immutable externally pinned D24 request and
transport, not a free-form model answer. It requires a host-owned claim SHA
and corresponding append-only `direct_hunt_completed` receipt before
scientific use. A native PARTIAL (or even native PASS) **does not certify**
scholarly primary-text reading. D24 only returns a source-depth HOLD and
Artikl must decide whether further research is required; without genuine
science the system will not generate v0.6 or promote novelty.

For staged acceptance the previously executed *actual* Indago + actual native
Artikl stdout were replayed via **one command**, producing
`MORE_RESEARCH_AUTHOR_HOLD`. This demonstrates the integration and replay
but is **not falsely described as one fresh full unattended hunt**. A fresh
manifest triggers `indago_port` from this same CLI, subject to all its
real live authority and isolation controls. The native Artikl handler invokes
OpenClaw for new cases and reuses an immutable SHA-bound transcript for an
unchanged cold replay. A crash with unfinished model/hunt markers blocks
for operator triage instead of blindly issuing duplicate provider calls.

No journal send, no World mutation, 0 accepted article seeds / new W12;
no cross-root production migration or full autorevision cycle F4. The next
real scientific step is another bounded source-specific research need with
full source-body/passage evidence and strongest closest-rival comparisons.
Only then may Artikl choose a versioned scientific rewrite with independent
reader and author HOLD.

## 2026-11-04 / ARTIKL decision ownership correction (ADD-006)

Prior F241 recorded a genuine **negative** registered Artikl evaluation but was
**not an unbiased three-way decision**: `native_add006_factory.py` passed an
outside `revision_eligible` boolean from WhiteCrow source-depth, injected it
into the Artikl prompt, and then rejected `REVISION_CANDIDATE` if D15 had
not declared the evidence sufficient. This mistakenly converted source-quality
evaluation into editorial permission. Treat the historical F241 scientific
receipt as immutable; do not recertify it as a genuinely independent
three-way editorial trial.

Current path: Indago returns typed findings and source provenance; WhiteCrow
reports source depth/known unknowns without an editorial veto; Artikl makes
the choice `MORE_RESEARCH | HOLD_BLOCKED | REVISION_CANDIDATE` using the
actual argumentative content, the current author decisions and the source
qualifications. Incomplete science **does not ban exploratory drafting**.
For `REVISION_CANDIDATE`, the controller records
`EDITORIAL_WORKING_REVISION_PROPOSED_NOT_YET_WRITTEN`, **not** D25
`MANUSCRIPT_GO` and **not** a completed candidate. Writing and independent
review remain separate executable tasks; they are **not proven completed**
by this change.

Keep lightweight provenance: request/return identity, source SHA, atomic
claim/idempotency (avoid duplicate provider spend), accepted-author decision
continuity and publication boundary (author consent, SEND and WORLD mutation).
These describe trusted execution and external effects, not compulsory
defensive paragraph-level editorial speech. D24/D15 adequacy and novelty
status are **annotations about scientific statements**, not universal
conditions for composing a working version.

Acceptance tests cover both a partial-WhiteCrow `REVISION_CANDIDATE`
and a `MORE_RESEARCH` outcome via the same native Factory coordinator,
the actual generated Artikl prompt (no external `revision_eligible`),
and a retained block only on premature D25/release claims.


## M117 / one existing Factory entrypoint: Artikl decision → working manuscript → independent critique

The existing \`python -m kairoskopion.kairon_provider.manuscript_cycle_runner editorial\` subcommand (same Kairoskopion PR #84) consumes the exact owner-private source C04 + currently held v0.5 + actual M116 independent critique + existing M115 science + F241 WhiteCrow report under an immutable SHA-bound manifest. It **does not dispatch Indago, create a new ResearchRequest, or call WhiteCrow as an editorial permission authority**.

- **One native registered \`artikl\` decision:** \`REVISION_CANDIDATE | MORE_RESEARCH | PARK\`. Source-depth information may inform arguments but cannot veto an exploratory manuscript. If the result is \`MORE_RESEARCH\` or \`PARK\`, it ends there with a recorded disposition; no manuscript is fabricated.
- **If Artikl chooses writing:** one separate registered native \`artikl\` invocation must write a complete UTF-8 manuscript to owner-private staging. Check real file size, minimum full-length word count, section structure and source hash. Never mistake a gateway acknowledgment or an outline for a complete manuscript.
- **Existing Factory intake:** \`manuscript_draft_intake.ingest\` receives the real new manuscript + exact original and provisional science packet. It preserves author HOLD, no SEND or automatic novelty certification.
- **Independent reader:** one read-only Codex process reviews the actual new SHA-pinned complete text against the full previous v0.5 and M116; exact reviewer line quotes are checked against the candidate bytes. This remains independent model review, **not** an external peer review or D25 publication approval.
- **Cold repeat:** a completed and unchanged state replays with zero further Artikl/Codex/Indago calls. An interrupted unreceipted model invocation is not silently repeated. No extra article identity or venue route is fabricated.
- Canonical D27 remains *candidate*; M116 protected conceptual nuclei and the M110 editorial preflight are inherited as provisional constraints, not misreported as universally accepted by the author.
- This subcommand is a first concrete editor/writer/reviewer bridge in a real case. It does NOT alone prove the full unrelated-corpus/80-route Trimurti acceptance in owner issue #43.

The actual 4 November 2026 first live case is owner-private at \`C:/projects/trimurti/_ops/T3-TALK-20261019/M117_FACTORY_NATIVE_EDITORIAL_20261104\`. Its manifest must be generated from the real source files, never from a text-only guess. A real first run and external original->version->review Git receipt are required before changing this section's status from \`CANDIDATE\` to \`REAL_CYCLE_PASS\`.
