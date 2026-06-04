# Kairoskopion — Litops & WhiteCrow Compatibility

## Integration architecture

Kairoskopion sits between Litops (source/provenance) and WhiteCrow
(field/manuscript).  It does not own primary sources or manuscript evolution.
It creates publication-facing objects and returns structured suggestions.

```
Litops (sources, provenance, context packs, vault)
    ↕
Kairoskopion (article models, venue models, fit, adaptation, submission)
    ↕
WhiteCrow (field, manuscript, protected core, patch queue)
```

## Litops compatibility layer

**Module:** `src/kairoskopion/integrations/litops.py`

Stub interfaces for objects Kairoskopion receives from or sends to Litops:

| Litops concept       | Kairoskopion stub            | Direction |
|----------------------|------------------------------|-----------|
| Source               | `LitopsSourceRef`            | IN        |
| ContextPack          | `LitopsContextPackRef`       | IN/OUT    |
| Artifact             | `LitopsArtifactRef`          | OUT       |
| Vault card           | `LitopsVaultProjection`      | OUT       |
| Workset              | `LitopsWorksetRef`           | IN        |

In standalone mode, Kairoskopion creates internal Source-like and
ContextPack-like structures.  When Litops is connected, these map to real
Litops objects.

## WhiteCrow compatibility layer

**Module:** `src/kairoskopion/integrations/whitecrow.py`

Stub interfaces for objects Kairoskopion receives from or sends to WhiteCrow:

| WhiteCrow concept     | Kairoskopion stub              | Direction |
|-----------------------|--------------------------------|-----------|
| FieldModelReference   | `FieldModelReference`          | IN        |
| ProtectedCore         | `ProtectedCore`                | IN        |
| PatchCandidate        | `PatchCandidate`               | OUT       |
| ExternalDocAction     | `ExternalDocAction`            | OUT       |
| ManuscriptRef         | `WhiteCrowManuscriptRef`       | IN        |
| ArticleTrajectory     | `WhiteCrowArticleTrajectoryRef`| IN        |

## Key rules

1. Kairoskopion never stores raw external files — that is Litops's job.
2. Kairoskopion never directly overwrites manuscript text — it creates patch
   candidates for WhiteCrow.
3. Every `source_ref` in a Kairoskopion object should resolve to a Litops
   Source or an internal standalone source registration.
4. ProtectedCore from WhiteCrow constrains all RewritePlan / ReframePlan
   outputs — core-touching changes require explicit user acceptance.
5. In standalone mode, Kairoskopion creates internal source/context
   registrations that can later be exported to Litops format.
