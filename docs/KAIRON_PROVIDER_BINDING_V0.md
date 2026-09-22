# Kairon Provider Binding v0

Status: additive implementation slice on `feature/kairon-provider-binding-v0`.

## Boundary

`ARTIKL.KAIRON` is the semantic organ. `Kairoskopion` is a publication-world observatory and specialist software provider. Provider outputs are evidence-backed observations, diagnostics and candidate pressures; they do not authorize manuscript identity changes.

## First slice

This branch adds a normalized provider contract without deleting or renaming the existing Case pipeline:

- `ArtiklStatePointer`
- `EditorScientificProfile`
- `CorpusArtifactManifest`
- `TargetWorldSnapshot`
- `TargetPressureItem / TargetPressurePack`
- `KaironProviderRequest / KaironProviderResponse`
- `RoundTripComparison`
- `pressure_pack_from_diagnostics()`

The adapter translates existing FitAssessment/MismatchMap-style data into target pressure while preserving evidence refs and unknowns.

## Next slice

1. Add editor-scientific-profile acquisition.
2. Add corpus acquisition manifest and metadata/abstract/fulltext states.
3. Build TargetWorldSnapshot from existing venue/evidence/corpus services.
4. Expose additive provider endpoints.
5. Bind a revised Artikl state and implement round-trip re-evaluation.
6. Only after one successful end-to-end journal exercise, demote old rewrite authority and refactor UI semantics.

## Non-goals

- No production deployment.
- No removal of existing APIs.
- No change to current Artikl semantic authority.
- No automatic manuscript rewrite.
- No claim that current ArticleSemanticProfile or FieldPositionModel is canonical when an Artikl state pointer exists.
