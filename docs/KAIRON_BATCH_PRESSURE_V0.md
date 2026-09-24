# Kairon Batch Pressure v0

Status: qualification branch only.

`derive_batch_target_pressure()` turns a frozen TargetWorld plus an Artikl-governed article projection into a conservative per-article TargetPressurePack. It uses no model-memory venue facts.

Current evidence channels:
- temporal adequacy of the sampled target corpus;
- article-path vs target discipline-path mismatch;
- conceptual/theoretical genre prevalence where corpus models expose it;
- conceptual-method prevalence where corpus models expose it;
- target citation baseline vs verified article reference count;
- corpus-language realization pressure;
- explicit TargetWorld model limitations.

Unknown evidence stays unknown or becomes evidence-needed pressure. A recent snapshot containing an old corpus is treated as stale corpus evidence rather than fresh target knowledge.

`target_variant_branch` maps to the canonical Kairon `BRANCH` transition so language/realization pressure creates a sibling target variant instead of rewriting the parent manuscript in place.

This slice does not replace deep target modeling, formal-policy extraction, editor/corpus analysis or Kairon reconciliation. It is the deterministic first pressure stage for batch cells.

Qualification is included in the 27/27 targeted PASS and the full 3360 PASS / 5 reproduced baseline FAIL repository run recorded in `KAIRON_BATCH_RUNTIME_V0.md`.