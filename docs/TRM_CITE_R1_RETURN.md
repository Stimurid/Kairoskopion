# TRM-CITE-001 R1 machine continuation (2026-10-21)

Status: **PARTIAL; operator execution and independent scientific review pending**.

`citation_r1_batch` imports owner followups against the immutable Z0 audit and queue, verifies the original manuscript SHA and each Z0 work-order identity, and correlates every task independently. Reused child work orders stay reused. R1-05 tasks with empty `work_order_ids` become `AUTHOR_SOURCE_NEED`; no Z0 anchor or intake is invented. Requests grant no acquisition permission. A separate source reader may return real evidence, but the checked-in negative producer records `SOURCE_READER_NOT_AVAILABLE` when no authorized reader is exposed. The consumer persists per-task states and a batch readback, preserving V1–V5 as unchecked and publication readiness at zero. Conflicting replay is rejected by immutable writes.

This delegated workspace could not read the off-worktree private inputs, call a permitted source reader, write the private run directory, or launch Python (`uv trampoline failed to spawn Python child process: permission denied (os error 5)`). Consequently **no actual 13-record run, source probe, pytest pass, or Hub pass is claimed here**. The original manuscript, Field, and Drive were untouched. The issue, PR, and Google Doc were supplied as pointers only and were not fetched.

## Authorized AORUS operator run

Run in the isolated worktree with a working Python that has pytest. These commands keep private records outside Git. The SHA checks are gates, not inferred from the pointer text.

```powershell
$root = 'C:\AI\llm\aiye-executor\worktrees\jx-c9ccfffb2e86'
$base = 'C:\AI\llm\aiye-executor\runs\TRM_CITE_Z0_20261020'
$pilot = Join-Path $base 'r1_five_case_pilot_20261020'
$auditDir = Join-Path $base 'luksha_private_audit\runs\trm-cite-z0-v03_5a84d385e7122acb774a'
$followups = Join-Path $pilot 'r1_evidence_followups.jsonl'
$protocols = Join-Path $pilot 'r1_five_case_protocols_validated.json'
$audit = Join-Path $auditDir 'citation_intake.json'
$queue = Join-Path $auditDir 'citation_work_orders.jsonl'
$run = Join-Path $pilot 'machine_continuation_20261021'
if ((Get-FileHash $followups -Algorithm SHA256).Hash -ne '531CA3D7D2004FF2779C4242569F02B02A2D966E91569F078E45862D8E3DE3A1') { throw 'followup SHA mismatch' }
if ((Get-FileHash $protocols -Algorithm SHA256).Hash -ne 'CABA708D995292BAD5EBCF9F921DD23D81C1AF2203497FF0481569525A5D3691') { throw 'protocol SHA mismatch' }
Set-Location $root
$env:PYTHONPATH = (Join-Path $root 'src')
python -m kairoskopion.services.citation_r1_batch prepare --audit $audit --queue $queue --followups $followups --protocols $protocols --requests (Join-Path $run 'requests') --expected-manuscript-sha256 5a84d385e7122acb774ab3068fd3688b461d102ccadbef3449a5c0d55540c6fb
python -m kairoskopion.services.citation_r1_batch blocked --requests (Join-Path $run 'requests') --returns (Join-Path $run 'returns')
python -m kairoskopion.services.citation_r1_batch consume --audit $audit --queue $queue --followups $followups --protocols $protocols --requests (Join-Path $run 'requests') --returns (Join-Path $run 'returns') --out (Join-Path $run 'states') --expected-manuscript-sha256 5a84d385e7122acb774ab3068fd3688b461d102ccadbef3449a5c0d55540c6fb
Get-Content (Join-Path $run 'requests\manifest.json')
Get-Content (Join-Path $run 'states\result.json')
```

Expected counts from the owner's handoff: 13 tasks, 4 distinct Z0 work orders, 3 author source needs, 5 cases, 13 blocked returns, 0 publication ready. A mismatch requires investigation. The negative run uses two independent producer and consumer processes. A source reader with separately confirmed access can replace each immutable `*.return.json` before consumption with a task-correlated `trm-cite-r1-task-return-v1` and source evidence containing provider, authorization, work/edition/witness IDs, locator, read depth, retrieval timestamp, and passage digest where appropriate. Such evidence is a proposal for V1–V5 review, never automatic certification.

## QA and limitations

`scripts/run_project_qa.py` forces this worktree's `src` import and launches pytest with a short unique Windows basetemp. `pyproject.toml` sets pytest `pythonpath = ["src"]`. A root `sitecustomize.py` now also puts this checkout's `src` first for `python -m unittest discover -s tests`, which does not read pytest configuration and otherwise may load an older installed package. `.aiye/pipeline.json` points to the runner. The pipeline key is a candidate until the Hub actually parses it; no Hub-driven result was available from this sandbox. The existing project pytest setting excludes the eight `network`-marked tests; no additional deselection was introduced.

The manual protocol comparison is structural: each state records case linkage and whether inputs/checks exist. It does not interpret private protocol prose or claim the stronger thesis is supported. Hutchins and Suchman still lack passage pinpoints; Zawacki-Richter does not directly establish the stronger practice-transfer thesis; Luckin is closer to process assessment without proving the author criterion; the quoted organizational-activity term awaits author confirmation; and `subjectis` is not by itself a modern Cartesian subject claim.
