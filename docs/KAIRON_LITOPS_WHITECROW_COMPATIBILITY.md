# Kairoskopion — Litops & WhiteCrow Compatibility

## Integration architecture

Kairoskopion sits between Litops (source/provenance) and WhiteCrow
(field/manuscript).  It does not own primary sources or manuscript evolution.
It creates publication-facing objects and returns structured suggestions.

```
Litops (sources, provenance, context packs, vault)
    |
Kairoskopion (article models, venue models, fit, adaptation, submission)
    |
WhiteCrow (field, manuscript, protected core, patch queue)
```

## Current implementation status

### Litops compatibility layer

**Module:** `src/kairoskopion/integrations/litops.py`

| Litops concept       | Kairoskopion stub            | Direction | Status |
|----------------------|------------------------------|-----------|--------|
| Source               | `LitopsSourceRef`            | IN        | Stubbed |
| ContextPack          | `LitopsContextPackRef`       | IN/OUT    | Stubbed |
| Artifact             | `LitopsArtifactRef`          | OUT       | Stubbed |
| Vault card           | `LitopsVaultProjection`      | OUT       | Stubbed |
| Workset              | `LitopsWorksetRef`           | IN        | Stubbed |

### WhiteCrow compatibility layer

**Module:** `src/kairoskopion/integrations/whitecrow.py`

| WhiteCrow concept     | Kairoskopion stub              | Direction | Status |
|-----------------------|--------------------------------|-----------|--------|
| FieldModelReference   | `FieldModelReference`          | IN        | Stubbed |
| ProtectedCore         | `ProtectedCore`                | IN        | Stubbed |
| PatchCandidate        | `PatchCandidate`               | OUT       | Stubbed |
| ExternalDocAction     | `ExternalDocAction`            | OUT       | Stubbed |
| ManuscriptRef         | `WhiteCrowManuscriptRef`       | IN        | Stubbed |
| ArticleTrajectory     | `WhiteCrowArticleTrajectoryRef`| IN        | Stubbed |

### Source acquisition layer (standalone mode)

**Module:** `src/kairoskopion/adapters/source_intake.py`

In standalone mode, Kairoskopion creates internal source registrations
that can later be exported to Litops format.

| Capability | Status |
|-----------|--------|
| Local file registration (md/txt/json) | Implemented |
| Content hash + extraction status | Implemented |
| EvidenceItem creation from snapshot | Implemented |
| Raw text input registration | Implemented |
| 14 source roles (article_input, venue_guidelines, ...) | Implemented |
| URL placeholder (no fetch) | Implemented |
| PDF/DOCX text extraction | Stub only (not_extracted) |
| Real HTTP fetch | Not implemented (MVP) |

### Key rules

1. Kairoskopion never stores raw external files — that is Litops's job.
   In standalone mode, it creates SourceSnapshot references to local files.
2. Kairoskopion never directly overwrites manuscript text — it creates patch
   candidates for WhiteCrow.
3. Every `source_ref` in a Kairoskopion object should resolve to a Litops
   Source or an internal standalone source registration.
4. ProtectedCore from WhiteCrow constrains all RewritePlan / ReframePlan
   outputs — core-touching changes require explicit user acceptance.
5. In standalone mode, Kairoskopion creates internal source/context
   registrations that can later be exported to Litops format.

### What's needed for real integration

**Litops connection:**
- Source registration API call instead of local file registration
- ContextPack creation/retrieval via Litops API
- Artifact export to Litops registry
- Vault card sync with Litops Vault (Obsidian)
- Source freshness/staleness via Litops staleness policy

**WhiteCrow connection:**
- FieldModelReference retrieval from WhiteCrow field
- ProtectedCore import from WhiteCrow manuscript
- PatchCandidate export to WhiteCrow patch queue
- ArticleTrajectory suggestions back to WhiteCrow
- ExternalDocAction export to Google Docs / DOCX bridge

Both integrations are designed as bounded-context boundaries:
Kairoskopion owns publication-facing models and operations;
Litops owns source/provenance; WhiteCrow owns field/manuscript evolution.
