# Kairon Batch Executor v0

Status: qualification branch only. No production authority.

This slice turns a durable BatchQualificationPlan into observed B5 qualification receipts.

Execution per claimed cell:
1. validate authoritative article state and frozen target identity;
2. load the existing frozen TargetWorld;
3. derive conservative per-article target pressure from frozen evidence;
4. call canonical Kairon transition classification;
5. persist full pressure/transition receipt;
6. update durable cell state;
7. stop before manuscript materialization or semantic adoption.

Scheduler behavior:
- obeys BatchQualificationSpec.concurrency_limit;
- resumes pending/retry cells;
- persists failures instead of losing the interrupted location;
- transition outputs remain proposal-only;
- HOLD is terminal for this frozen-snapshot qualification cell and requires a refreshed descendant snapshot/new qualification cell for new evidence;
- author-gated transitions stop as blocked_author.

Sparse eligibility:
- BatchArticleInput.eligible_target_ids restricts an article to evidence-supported targets;
- empty eligibility preserves all-target behavior;
- shared frozen targets remain reusable across every article that explicitly allows them.

Local-first target reuse:
- runtime venue registry is checked;
- repository venue registry is checked;
- repository harvested provisional venue records are checked;
- repository venue evidence packs are checked;
- frozen TargetWorld and VenueMemory remain separate durable layers;
- external discovery remains gated behind the completed local-first receipt.

This closes planner → qualification execution. B6 materialization, B7 same-snapshot return pass, B8 formal/package closure, and the real multi-article pilot remain later stages.
