# DisciplineModel schema changelog

## v1.0.0 — 2026-06-17 (initial scaffold)

Phase B0 scaffold. Schema captures discipline as **working tool for
downstream agents**, not as encyclopedia entry. Required fields kept
minimal (id, names, region, source_status, last_updated) so seed
records can be drafted incrementally; the rich working-tool fields are
optional but documented.

Key design choices:

- **`source_status` lifecycle** — `llm_draft` → `needs_review` →
  `user_confirmed` (or `disputed` / `merged` / `deprecated`). New
  candidates surfaced by `semantic_profiler` get `candidate`.
- **Working-tool fields** beyond paradigm/methods: `epistemic_regime`,
  `forms_of_evidence`, `canonical_questions`, `typical_problem_forms`,
  `legitimate_objects`, **`illegitimate_or_borderline_objects`**,
  `argument_styles`, `publication_genres`, `institutional_forms`.
  These exist so the matcher and fit assessor can answer questions
  like "would this object fit?" without re-reading prose.
- **`russian_specificity` + `international_mapping`** — explicit
  cross-region structure so the matcher can carry a Russian paper into
  international venue search and vice versa, without flattening the
  Russian-tradition specifics.

When the schema changes (additive only — fields can be added,
existing fields cannot be removed without a new schema_version):
1. Bump `schema_version` here and in the JSON Schema's `$id`.
2. Add a changelog entry.
3. Migration script in `services/discipline_registry/migrations/` if
   anything stored on disk needs rewriting.
