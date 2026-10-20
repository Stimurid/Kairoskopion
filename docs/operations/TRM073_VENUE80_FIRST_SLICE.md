# TRM-073 / AIxSRT80 — first runnable Factory slice

This slice admits a bounded W2 research-return packet into the existing
`OpportunityGraphStore` and `TargetWorldCatalog`. It creates typed provisional
evidence, negative scholarly-objection events, and author-gated field-reopen
proposals. It never creates `ArticleSeed`, `OpportunityRoute`, `TargetVariant`,
or `World`, and it never sends anything.

## Run and replay

```powershell
$env:PYTHONPATH = "$PWD\src"
python scripts/run_trm073_research_stage.py `
  --research-packet C:\path\to\TRM073_W2_SCIENCE_INPUT.json `
  --storage-root C:\path\to\new-isolated-stage
```

Run the same command again. The JSON result and every staged file hash must be
unchanged. Verify `research_stage/<case>/<wave>/receipt.json` and the independent
`readback.json`. A local packet performs no HTTP call, so 429 recovery is
explicitly `NOT_EXERCISED_LOCAL_PACKET_NO_NETWORK`; immutable IDs, write-once
events, checkpoint receipt, and cold-process replay provide resume behavior.

## Honest funnel and the next 80-route step

The receipt reports separate counts for `discovered_journals`,
`proposed_routes`, `w12_equivalent_routes`, `deep_qualified`,
`author_approved`, and `submission_ready`. W2 yields one discovered journal and
zero routes at all later stages: its 2026 special issue is already published,
publisher full text is not certified as read, and the author gate is `HOLD`.

Generalization is a due-diligence queue, not an 80-title generator. For each
candidate semantic head, the owner/Artikl first records `SPLIT`, `MERGE`,
`RETIRE`, or `KEEP`. Research then returns the strongest opposition and
limitations, read-depth anchors, an actual target venue, current official
editorial path, target-specific thesis/transformation, and the next source
action. Only a distinct claim/version/venue triple satisfying all those fields
counts as W12-equivalent. Track negative discovery and rejected pairs without
counting them. Aim for 60 international and 20 RF routes only where the evidence
supports them; the current first-slice shortfall remains 80.
